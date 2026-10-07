"""Check the process and validate its saved credentials with Twitch."""

import http.client
import json
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from accounts import Account, AccountError, selected_account


@dataclass(frozen=True)
class Validation:
    logged_in: int | None
    reason: str
    expires_in: int | None = None


def validate_token(account: Account) -> Validation:
    # Fixed HTTPS destination: no proxy environment or redirects can receive the token.
    connection = http.client.HTTPSConnection("id.twitch.tv", timeout=5)
    try:
        connection.request(
            "GET",
            "/oauth2/validate",
            headers={"Authorization": f"OAuth {account.token}"},
        )
        response = connection.getresponse()
        if response.status == 401:
            return Validation(0, "token_invalid")
        if response.status != 200:
            return Validation(None, "twitch_unavailable")
        body = response.read(65537)
        if len(body) > 65536:
            return Validation(None, "twitch_response_invalid")
        data = json.loads(body)
        if not isinstance(data, dict):
            return Validation(None, "twitch_response_invalid")
        if not all(
            isinstance(data.get(key), str) and data[key]
            for key in ("login", "user_id", "client_id")
        ):
            return Validation(None, "twitch_response_invalid")
        if (
            data.get("login") != account.username
            or data.get("user_id") != account.user_id
            or data.get("client_id") != account.client_id
        ):
            return Validation(0, "token_identity_mismatch")
        expires_in = data.get("expires_in")
        if type(expires_in) is not int or expires_in < 0:
            return Validation(None, "twitch_response_invalid")
        # HTTP 200 is authoritative, even when expires_in is zero.
        return Validation(1, "authenticated", expires_in)
    except (OSError, http.client.HTTPException):
        return Validation(None, "twitch_unavailable")
    except (ValueError, UnicodeError):
        return Validation(None, "twitch_response_invalid")
    finally:
        connection.close()


def chatterino_running(proc_path: Path = Path("/proc")) -> bool:
    for process in proc_path.iterdir():
        if not process.name.isdecimal():
            continue
        try:
            # Exact comm also works under emulation, where exe points to the emulator.
            if (process / "comm").read_text().strip() != "chatterino":
                continue
            state = (process / "stat").read_text().rpartition(")")[2].split()[0]
            if state not in ("Z", "X"):
                return True
        except (OSError, IndexError):
            continue
    return False


class HealthMonitor:
    def __init__(
        self,
        settings_path: Path,
        username: str,
        cache_seconds: int = 60,
        validator: Callable[[Account], Validation] = validate_token,
        process_check: Callable[[], bool] = chatterino_running,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.settings_path = settings_path
        self.username = username.strip().lower()
        self.cache_seconds = cache_seconds
        self.validator = validator
        self.process_check = process_check
        self.clock = clock
        self.lock = threading.Lock()
        self.cached_account: Account | None = None
        self.cached_validation: Validation | None = None
        self.validated_at = 0.0
        self.checked_at: str | None = None

    def health(self) -> tuple[int, dict[str, object]]:
        # Coalesce simultaneous Docker/HTTP probes into one Twitch request.
        with self.lock:
            running = self.process_check()
            checked_at = None
            expires_in = None
            if not running:
                validation = Validation(None, "chatterino_not_running")
                self.cached_account = None
            else:
                try:
                    account = selected_account(self.settings_path, self.username)
                except AccountError as error:
                    validation = Validation(error.logged_in, error.reason)
                    self.cached_account = None
                else:
                    now = self.clock()
                    ttl = self.cache_seconds
                    if self.cached_validation and self.cached_validation.expires_in:
                        ttl = min(ttl, self.cached_validation.expires_in)
                    if account != self.cached_account or now - self.validated_at >= ttl:
                        self.cached_validation = self.validator(account)
                        self.cached_account = account
                        self.validated_at = self.clock()
                        self.checked_at = datetime.now(timezone.utc).isoformat()
                    assert self.cached_validation is not None
                    validation = self.cached_validation
                    checked_at = self.checked_at
                    if validation.expires_in is not None:
                        elapsed = max(0, self.clock() - self.validated_at)
                        expires_in = max(0, validation.expires_in - math.ceil(elapsed))

            status = "ok" if validation.logged_in == 1 else "error"
            if validation.logged_in is None:
                status = "unknown"
            return (200 if status == "ok" else 503), {
                "status": status,
                "logged_in": validation.logged_in,
                "account": self.username,
                "chatterino_running": running,
                "reason": validation.reason,
                "expires_in": expires_in,
                "checked_at": checked_at,
            }
