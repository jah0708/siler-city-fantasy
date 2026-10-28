"""Regression tests for the one-time Yahoo OAuth authorization-code workflow."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import authorize_yahoo
import yahoo_token


ENV = {
    "YAHOO_CLIENT_ID": "id",
    "YAHOO_CLIENT_SECRET": "secret",
    "YAHOO_REFRESH_TOKEN": "old-token",
    "YAHOO_AUTH_CODE": "one-time-authorization-code",
}


class OAuthAuthorizationTests(unittest.TestCase):
    def test_exchange_uses_registered_callback_and_persists_encrypted_token(self):
        with patch.dict(os.environ, ENV), \
             patch.object(authorize_yahoo, "request_json", return_value={
                 "access_token": "access", "refresh_token": "new-refresh"
             }) as request, \
             patch.object(authorize_yahoo, "persist_refresh_token") as persist:
            authorize_yahoo.main()
            data = request.call_args.kwargs["data"]
            self.assertEqual(data["grant_type"], "authorization_code")
            self.assertEqual(data["code"], ENV["YAHOO_AUTH_CODE"])
            self.assertEqual(data["redirect_uri"], authorize_yahoo.REDIRECT_URI)
            persist.assert_called_once_with(
                "secret", "old-token", "new-refresh", replace_existing=True
            )

    def test_new_app_authorization_replaces_old_app_encryption(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("old-app-secret", "old-token", "old-refresh")
                with patch.dict(os.environ, ENV), \
                     patch.object(authorize_yahoo, "request_json", return_value={
                         "access_token": "access", "refresh_token": "new-refresh"
                     }):
                    authorize_yahoo.main()
                self.assertEqual(
                    yahoo_token.select_refresh_token("secret", "old-token"), "new-refresh"
                )
                with self.assertRaises(RuntimeError):
                    yahoo_token.select_refresh_token("old-app-secret", "old-token")
                self.assertNotIn("new-refresh", target.read_text(encoding="utf-8"))

    def test_failed_new_app_authorization_preserves_saved_token(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("old-app-secret", "old-token", "old-refresh")
                before = target.read_bytes()
                with patch.dict(os.environ, ENV), \
                     patch.object(authorize_yahoo, "request_json", side_effect=RuntimeError("Rejected grant")):
                    with self.assertRaisesRegex(RuntimeError, "Rejected grant"):
                        authorize_yahoo.main()
                self.assertEqual(target.read_bytes(), before)
                self.assertEqual(
                    yahoo_token.select_refresh_token("old-app-secret", "old-token"), "old-refresh"
                )

    def test_missing_code_never_calls_yahoo(self):
        with patch.dict(os.environ, {**ENV, "YAHOO_AUTH_CODE": ""}), \
             patch.object(authorize_yahoo, "request_json") as request:
            with self.assertRaisesRegex(RuntimeError, "YAHOO_AUTH_CODE"):
                authorize_yahoo.main()
            request.assert_not_called()

    def test_missing_yahoo_refresh_token_is_not_saved(self):
        with patch.dict(os.environ, ENV), \
             patch.object(authorize_yahoo, "request_json", return_value={"access_token": "access"}), \
             patch.object(authorize_yahoo, "persist_refresh_token") as persist:
            with self.assertRaisesRegex(RuntimeError, "without returning a refresh token"):
                authorize_yahoo.main()
            persist.assert_not_called()

    def test_full_mobile_callback_url_can_be_used(self):
        env = {**ENV, "YAHOO_AUTH_CODE":
            "https://jah0708.github.io/siler-city-fantasy/?code=fresh-code&state=test"}
        with patch.dict(os.environ, env), \
             patch.object(authorize_yahoo, "request_json", return_value={
                 "refresh_token": "new-refresh"
             }) as request, \
             patch.object(authorize_yahoo, "persist_refresh_token"):
            authorize_yahoo.main()
            self.assertEqual(request.call_args.kwargs["data"]["code"], "fresh-code")

    def test_callback_must_match_registered_redirect(self):
        env = {**ENV, "YAHOO_AUTH_CODE": "https://other.example/?code=do-not-use"}
        with patch.dict(os.environ, env), \
             patch.object(authorize_yahoo, "request_json") as request:
            with self.assertRaisesRegex(RuntimeError, "not the configured"):
                authorize_yahoo.main()
            request.assert_not_called()



if __name__ == "__main__":
    unittest.main()

