"""Start the built desktop and verify its login monitor before publishing."""

import base64
import http.client
import json
import ssl
import subprocess
import sys
import time


def docker(*args: str) -> str:
    return subprocess.check_output(["docker", *args], text=True).strip()


def request(
    port: int, *, authenticated: bool = False, tls: bool = False
) -> tuple[int, bytes]:
    headers = {}
    if authenticated:
        credentials = base64.b64encode(b"admin:ci-only-placeholder").decode()
        headers["Authorization"] = f"Basic {credentials}"
    if tls:
        # The desktop ships a self-signed certificate; this probe stays on loopback.
        connection = http.client.HTTPSConnection(
            "127.0.0.1", port, timeout=5, context=ssl._create_unverified_context()
        )
    else:
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    try:
        connection.request("GET", "/health", headers=headers)
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def check(container: str) -> None:
    ports = json.loads(
        docker("inspect", "--format", "{{json .NetworkSettings.Ports}}", container)
    )
    health_port, http_port, https_port = (
        int(ports[f"{port}/tcp"][0]["HostPort"]) for port in (8080, 3000, 3001)
    )
    # Use a separate settings file so the GUI cannot overwrite the test fixture.
    docker(
        "exec",
        container,
        "python3",
        "-c",
        'from pathlib import Path; Path("/tmp/smoke-settings.json").write_text('
        '\'{"accounts":{"current":"anonymous"}}\')',
    )
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            status, body = request(health_port)
            payload = json.loads(body)
            if payload.get("chatterino_running"):
                break
        except (OSError, ValueError, http.client.HTTPException):
            pass
        time.sleep(2)
    else:
        raise RuntimeError("Chatterino did not start within 90 seconds")

    assert status == 503, (status, payload)
    assert payload["logged_in"] == 0 and payload["reason"] == "account_not_selected", (
        payload
    )
    for port, tls in ((http_port, False), (https_port, True)):
        assert request(port, tls=tls)[0] == 401, (
            "Desktop health proxy must require authentication"
        )
        status, body = request(port, authenticated=True, tls=tls)
        assert status == 503 and json.loads(body)["chatterino_running"], (status, body)
    docker("exec", container, "nginx", "-t")
    owner = docker(
        "exec", container, "stat", "-c", "%u:%g", "/config/.local/share/chatterino"
    )
    assert owner == "1000:1000", owner
    print(
        "Chatterino started; direct and authenticated HTTP/HTTPS health checks passed"
    )


def main(image: str) -> None:
    container = docker(
        "run",
        "--detach",
        "--shm-size=1g",
        "--publish",
        "127.0.0.1::8080",
        "--publish",
        "127.0.0.1::3000",
        "--publish",
        "127.0.0.1::3001",
        "--env",
        "CUSTOM_USER=admin",
        "--env",
        "PASSWORD=ci-only-placeholder",
        "--env",
        "PUID=1000",
        "--env",
        "PGID=1000",
        "--env",
        "HOME=/config",
        "--env",
        "XDG_CONFIG_HOME=/config/.config",
        "--env",
        "XDG_DATA_HOME=/config/.local/share",
        "--env",
        "XDG_CACHE_HOME=/config/.cache",
        "--env",
        "CHATTERINO_HEALTH_ACCOUNT=username",
        "--env",
        "CHATTERINO_SETTINGS_PATH=/tmp/smoke-settings.json",
        image,
    )
    try:
        check(container)
    except Exception:
        subprocess.run(["docker", "logs", container], check=False)
        raise
    finally:
        subprocess.run(["docker", "rm", "--force", "--volumes", container], check=True)


if __name__ == "__main__":
    main(sys.argv[1])
