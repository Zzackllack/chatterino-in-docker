"""Internal HTTP endpoint; nginx also serves it at the existing desktop URL."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from monitor import HealthMonitor


def create_server(monitor: HealthMonitor, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.respond()

        def do_HEAD(self) -> None:
            self.respond(head_only=True)

        def respond(self, head_only: bool = False) -> None:
            if self.path != "/health":
                self.send_error(404)
                return
            status, payload = monitor.health()
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head_only:
                self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            # Routine probes are silent; account settings and tokens never enter logs.
            pass

    return ThreadingHTTPServer((host, port), Handler)


def main() -> None:
    data_home = Path(os.environ.get("XDG_DATA_HOME", "/config/.local/share"))
    settings = Path(
        os.environ.get(
            "CHATTERINO_SETTINGS_PATH",
            str(data_home / "chatterino/Settings/settings.json"),
        )
    )
    username = os.environ.get("CHATTERINO_HEALTH_ACCOUNT", "username")
    cache_seconds = int(os.environ.get("CHATTERINO_HEALTH_CACHE_SECONDS", "60"))
    if not username.strip() or not 1 <= cache_seconds <= 3600:
        raise ValueError(
            "Set an account and a cache interval between 1 and 3600 seconds"
        )
    server = create_server(
        HealthMonitor(settings, username, cache_seconds), "0.0.0.0", 8080
    )
    print("Chatterino health endpoint listening on port 8080", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
