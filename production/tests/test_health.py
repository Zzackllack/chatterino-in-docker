"""Exercise login failures, caching, credential changes and the HTTP contract."""

import http.client
import json
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "health"))

from accounts import Account
from monitor import HealthMonitor, Validation, chatterino_running, validate_token
from server import create_server


class HealthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = Path(self.directory.name) / "settings.json"
        self.now = 100.0
        self.running = True
        self.validator = Mock(return_value=Validation(1, "authenticated", 3600))
        self.monitor = HealthMonitor(
            self.settings,
            "username",
            validator=self.validator,
            process_check=lambda: self.running,
            clock=lambda: self.now,
        )
        self.write_settings()

    def write_settings(
        self, current: str = "username", token: str = "testtoken"
    ) -> None:
        self.settings.write_text(
            json.dumps(
                {
                    "accounts": {
                        "current": current,
                        "uid123": {
                            "username": "username",
                            "userID": "123",
                            "clientID": "client123",
                            "oauthToken": token,
                        },
                    }
                }
            )
        )

    def test_valid_login_does_not_expose_credentials(self) -> None:
        status, payload = self.monitor.health()
        self.assertEqual(
            (status, payload["status"], payload["logged_in"]), (200, "ok", 1)
        )
        self.assertEqual(payload["account"], "username")
        self.assertEqual(payload["expires_in"], 3600)
        self.assertIsNotNone(payload["checked_at"])
        self.assertNotIn("testtoken", json.dumps(payload))
        self.assertNotIn("testtoken", repr(self.validator.call_args.args[0]))

    def test_expired_token_is_unhealthy(self) -> None:
        self.validator.return_value = Validation(0, "token_invalid")
        status, payload = self.monitor.health()
        self.assertEqual(
            (status, payload["logged_in"], payload["reason"]), (503, 0, "token_invalid")
        )

    def test_twitch_outage_is_unknown(self) -> None:
        self.validator.return_value = Validation(None, "twitch_unavailable")
        status, payload = self.monitor.health()
        self.assertEqual(
            (status, payload["status"], payload["logged_in"]), (503, "unknown", None)
        )

    def test_saved_account_is_not_enough_when_another_account_is_selected(self) -> None:
        for current in ("", "otheruser", "justinfan12345"):
            with self.subTest(current=current):
                self.write_settings(current=current)
                status, payload = self.monitor.health()
                self.assertEqual((status, payload["logged_in"]), (503, 0))
                self.assertEqual(payload["reason"], "account_not_selected")
        self.validator.assert_not_called()

    def test_missing_or_unreadable_settings_never_report_success(self) -> None:
        cases = (
            ("{broken", "settings_invalid", None),
            ("[]", "settings_invalid", None),
            ('{"accounts":123}', "settings_invalid", None),
            ('{"accounts":{"current":"username"}}', "account_missing", 0),
        )
        for contents, reason, logged_in in cases:
            with self.subTest(reason=reason):
                self.settings.write_text(contents)
                status, payload = self.monitor.health()
                self.assertEqual(
                    (status, payload["reason"], payload["logged_in"]),
                    (503, reason, logged_in),
                )
        self.settings.unlink()
        self.assertEqual(self.monitor.health()[1]["reason"], "settings_unavailable")
        self.validator.assert_not_called()

    def test_missing_credentials_and_header_injection_are_rejected(self) -> None:
        for token in ("", "oauth:", "token\r\nOther: injected"):
            with self.subTest(token=token):
                self.write_settings(token=token)
                self.assertEqual(
                    self.monitor.health()[1]["reason"], "missing_credentials"
                )
        self.validator.assert_not_called()

    def test_process_stopped_is_unhealthy_even_with_a_valid_cached_token(self) -> None:
        self.monitor.health()
        self.running = False
        status, payload = self.monitor.health()
        self.assertEqual(status, 503)
        self.assertFalse(payload["chatterino_running"])
        self.assertEqual(payload["reason"], "chatterino_not_running")
        self.running = True
        self.monitor.health()
        self.assertEqual(self.validator.call_count, 2)

    def test_cache_coalesces_requests_and_refreshes_after_sixty_seconds(self) -> None:
        with ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(lambda _: self.monitor.health(), range(16)))
        self.assertTrue(all(status == 200 for status, _ in responses))
        self.validator.assert_called_once()
        self.now += 59
        self.assertEqual(self.monitor.health()[1]["expires_in"], 3541)
        self.validator.assert_called_once()
        self.now += 1
        self.validator.return_value = Validation(0, "token_invalid")
        self.assertEqual(self.monitor.health()[0], 503)
        self.assertEqual(self.validator.call_count, 2)

    def test_token_change_and_account_switch_bypass_cache(self) -> None:
        self.monitor.health()
        self.write_settings(token="oauth:replacement")
        self.monitor.health()
        self.assertEqual(self.validator.call_count, 2)
        self.assertEqual(self.validator.call_args.args[0].token, "replacement")
        self.write_settings(current="")
        self.assertEqual(self.monitor.health()[0], 503)
        self.write_settings(token="replacement")
        self.assertEqual(self.monitor.health()[0], 200)
        self.assertEqual(self.validator.call_count, 3)

    def test_known_expiry_shortens_cache(self) -> None:
        self.validator.return_value = Validation(1, "authenticated", 10)
        self.monitor.health()
        self.now += 10
        self.validator.return_value = Validation(0, "token_invalid")
        self.assertEqual(self.monitor.health()[0], 503)
        self.assertEqual(self.validator.call_count, 2)

    def test_http_get_head_and_failure_status(self) -> None:
        server = create_server(self.monitor, "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port)
            self.addCleanup(connection.close)
            connection.request("GET", "/health")
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(response.getheader("Cache-Control"), "no-store")
            self.assertEqual(json.loads(response.read())["logged_in"], 1)
            connection.request("HEAD", "/health")
            response = connection.getresponse()
            self.assertEqual((response.status, response.read()), (200, b""))
            self.write_settings(current="")
            connection.request("GET", "/health")
            response = connection.getresponse()
            self.assertEqual(response.status, 503)
            self.assertEqual(json.loads(response.read())["logged_in"], 0)
            connection.request("GET", "/settings.json")
            response = connection.getresponse()
            self.assertEqual(response.status, 404)
            response.read()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_process_detection_does_not_match_health_server(self) -> None:
        root = Path(self.directory.name)
        process = root / "123"
        process.mkdir()
        (process / "comm").write_text("python3\n")
        (process / "stat").write_text("123 (python3) S 1 2 3\n")
        self.assertFalse(chatterino_running(root))
        (process / "comm").write_text("chatterino\n")
        (process / "stat").write_text("123 (chatterino) S 1 2 3\n")
        self.assertTrue(chatterino_running(root))
        (process / "stat").write_text("123 (chatterino) Z 1 2 3\n")
        self.assertFalse(chatterino_running(root))


class TwitchValidationTests(unittest.TestCase):
    @patch("monitor.http.client.HTTPSConnection")
    def test_twitch_transport_and_response_handling(
        self, connection_class: Mock
    ) -> None:
        account = Account("username", "123", "client123", "testtoken")
        connection = connection_class.return_value
        response = connection.getresponse.return_value
        good = {
            "login": "username",
            "user_id": "123",
            "client_id": "client123",
            "expires_in": 3600,
        }
        cases = (
            (200, json.dumps(good).encode(), Validation(1, "authenticated", 3600)),
            (
                200,
                json.dumps({**good, "expires_in": 0}).encode(),
                Validation(1, "authenticated", 0),
            ),
            (401, b"{}", Validation(0, "token_invalid")),
            (429, b"{}", Validation(None, "twitch_unavailable")),
            (503, b"{}", Validation(None, "twitch_unavailable")),
            (302, b"{}", Validation(None, "twitch_unavailable")),
            (200, b"not json", Validation(None, "twitch_response_invalid")),
            (200, b"[]", Validation(None, "twitch_response_invalid")),
            (200, b"{}", Validation(None, "twitch_response_invalid")),
            (200, b"x" * 65537, Validation(None, "twitch_response_invalid")),
            (
                200,
                json.dumps({**good, "login": "anotheruser"}).encode(),
                Validation(0, "token_identity_mismatch"),
            ),
            (
                200,
                json.dumps({**good, "user_id": "456"}).encode(),
                Validation(0, "token_identity_mismatch"),
            ),
            (
                200,
                json.dumps({**good, "client_id": "otherclient"}).encode(),
                Validation(0, "token_identity_mismatch"),
            ),
            (
                200,
                json.dumps({**good, "expires_in": -1}).encode(),
                Validation(None, "twitch_response_invalid"),
            ),
        )
        for status, body, expected in cases:
            with self.subTest(status=status, expected=expected):
                response.status = status
                response.read.return_value = body
                self.assertEqual(validate_token(account), expected)
        connection_class.assert_called_with("id.twitch.tv", timeout=5)
        connection.request.assert_called_with(
            "GET", "/oauth2/validate", headers={"Authorization": "OAuth testtoken"}
        )
        connection.getresponse.side_effect = TimeoutError()
        self.assertEqual(
            validate_token(account), Validation(None, "twitch_unavailable")
        )
        self.assertEqual(connection.close.call_count, len(cases) + 1)


if __name__ == "__main__":
    unittest.main()
