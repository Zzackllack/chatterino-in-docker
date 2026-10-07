"""Read the selected account from Chatterino 2.5.3's persisted settings."""

import json
from dataclasses import dataclass, field
from pathlib import Path


class AccountError(Exception):
    def __init__(self, reason: str, logged_in: int | None = 0) -> None:
        super().__init__(reason)
        self.reason = reason
        self.logged_in = logged_in


@dataclass(frozen=True)
class Account:
    username: str
    user_id: str
    client_id: str
    token: str = field(repr=False)


def selected_account(settings_path: Path, expected_username: str) -> Account:
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except OSError:
        raise AccountError("settings_unavailable", None) from None
    except (ValueError, UnicodeError):
        raise AccountError("settings_invalid", None) from None

    if not isinstance(settings, dict):
        raise AccountError("settings_invalid", None)
    accounts = settings.get("accounts")
    if accounts is None:
        raise AccountError("account_missing")
    if not isinstance(accounts, dict):
        raise AccountError("settings_invalid", None)
    current = accounts.get("current")
    if not isinstance(current, str) or current.strip().lower() != expected_username:
        raise AccountError("account_not_selected")

    for key, entry in accounts.items():
        if key == "current" or not isinstance(entry, dict):
            continue
        username = entry.get("username")
        if (
            not isinstance(username, str)
            or username.strip().lower() != expected_username
        ):
            continue
        values = [entry.get(name) for name in ("userID", "clientID", "oauthToken")]
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise AccountError("missing_credentials")
        user_id, client_id, token = (value.strip() for value in values)
        token = token.removeprefix("oauth:")
        if not token or not token.isascii() or not token.isalnum():
            raise AccountError("missing_credentials")
        return Account(expected_username, user_id, client_id, token)

    raise AccountError("account_missing")
