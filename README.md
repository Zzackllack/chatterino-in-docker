# chatterino-in-docker

Run Chatterino in a LinuxServer KasmVNC container, access its desktop in a browser,
and monitor whether the selected Twitch account's saved credentials are still valid.

The current setup is in [`production/`](production/README.md):

Copy `production/.env.example` to `production/.env` and set your Twitch login
and desktop password before starting the container.

```sh
cd production
docker compose up -d --build
curl -i http://127.0.0.1:8080/health
```

The image targets an amd64 Docker host. The existing desktop URL exposes `/health`
behind its authentication; the direct monitoring port binds to loopback by default.
See the production documentation for account selection, private-network monitoring,
HTTP status codes, token caching, and the limits of checking persisted credentials.

## Layout

- `production/`: current image, Compose configuration, and login health service.
- `production/tests/`: automated tests for the health endpoint.
- `tests/`: earlier KasmVNC, Webtop, and Xpra container experiments.
- `prebuilt/`: earlier Ubuntu Chatterino build-image Dockerfile.

Run the current checks from the repository root:

```sh
uv run --no-project python -m unittest discover -s production/tests -v
docker compose -f production/docker-compose.yaml config --quiet
```
