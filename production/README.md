# Chatterino login monitoring

The container exposes `GET /health` and `HEAD /health`. It checks that the
Chatterino process is running, that `username` is the selected account in saved
settings, and that Twitch still accepts that account's OAuth token. It uses
[Twitch's token validation endpoint](https://dev.twitch.tv/docs/authentication/validate-tokens/);
an account entry alone does not prove the credentials are valid.

Example successful response (HTTP 200):

```json
{
  "status": "ok",
  "logged_in": 1,
  "account": "username",
  "chatterino_running": true,
  "reason": "authenticated",
  "expires_in": 3600,
  "checked_at": "2026-10-07T12:00:00+00:00"
}
```

An expired or revoked token returns HTTP 503 with `status: "error"`,
`logged_in: 0`, and `reason: "token_invalid"`. Selecting anonymous mode or another
account also returns 503. Twitch timeouts, unexpected responses, and unreadable
settings return 503 with `status: "unknown"` and `logged_in: null`: these mean the
check could not establish login health. A stopped Chatterino process also fails.
No response or routine log includes the OAuth token.

## Build and monitor

Copy `.env.example` to `.env` and set `CHATTERINO_HEALTH_ACCOUNT` to your Twitch
login and `PASSWORD` to your desktop password. The `.env` file is Git-ignored.

From this directory, rebuild and recreate the container:

```sh
docker compose up -d --build
curl -i http://127.0.0.1:8080/health
```

The bundled AppImage is x86-64, so this image targets an amd64 Docker host.
Docker Desktop's Rosetta emulation on this Mac rejected the AppImage runtime
with `Exec format error`; container smoke checks used a temporary extraction
workaround outside the repository. The production Dockerfile retains the upstream
AppImage extraction command. No Twitch app registration, extra token, or client
secret is needed; the check reads Chatterino's existing credentials as the `abc` user.

Use either of these URLs in an HTTP monitor expecting **200**:

- `https://<existing-chatterino-host>/health` through the existing nginx proxy.
  This inherits desktop Basic Auth and any authentication enabled at your reverse
  proxy. The monitor must authenticate; a redirect to a login page is not a
  successful check.
- `http://<private-host>:8080/health` for direct monitoring. Compose binds this port
  to `127.0.0.1` by default. For a monitor on another machine, set
  `HEALTH_BIND_ADDRESS` to the server's private/NetBird IP and allow that monitor
  to reach it. This port has no authentication; keep it on your private network.

If a separate reverse proxy routes to the health service, explicitly select
container port **8080**. The desktop continues to use port **3000**. Existing
Configure reverse proxy routing separately from the desktop container.

The Docker healthcheck uses this same endpoint. Expired login credentials mark
the container unhealthy. Docker's `restart: unless-stopped` does not restart an
unhealthy running container; reauthenticate in Chatterino to recover. Configure
your deployment platform to alert on this state, since restarting cannot renew
the token.

## Settings and limits

- `CHATTERINO_HEALTH_ACCOUNT`: required selected account; default `username`.
- `CHATTERINO_HEALTH_CACHE_SECONDS`: Twitch result cache; default `60`, range
  `1`–`3600`. Checks run on HTTP requests, including Docker's 30-second probe.
- `CHATTERINO_SETTINGS_PATH`: optional override for the account file; default
  `$XDG_DATA_HOME/chatterino/Settings/settings.json` (under `/config/.local/share`).
- `HEALTH_PORT`: published monitoring port; default `8080`.
- `HEALTH_BIND_ADDRESS`: host interface for direct monitoring; default `127.0.0.1`.

Each request rereads saved settings and checks the process. Credential changes
invalidate the cache immediately; a known token expiry shortens the cache.
Revocations are detected at the next check after the cache expires. Set your
monitor's polling interval accordingly.

This checks **persisted account credentials**, not Chatterino's in-memory account
or its IRC connection. Chatterino may not write a GUI account change until settings
are saved (close its Settings dialog to request a save). A valid token cannot prove
that chat is connected or messages can be sent. Detecting those conditions would
require instrumentation inside Chatterino itself.

The image uses the base image's distinct VNC upstream ports. The previous custom
startup script tried to discover live ports before services started and rewrote
both upstreams to one port; it has been removed. The legacy account migration now
runs before creating its destination directory, so it can actually copy old data.
Initialization runs after the base image applies `PUID`/`PGID`, and before the
desktop starts, to avoid leaving account directories owned by the old UID.

## Local checks

```sh
uv run --no-project python -m unittest discover -s tests -v
docker compose config --quiet
```

The tests use fake credentials and mocked Twitch responses. They verify expired
tokens, unknown results, account switching, cache invalidation/expiry, process
detection, secret omission, and HTTP 200/503 behavior. They do not verify your
live Twitch account or a deployed container.
