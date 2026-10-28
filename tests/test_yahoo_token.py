"""Tests for Yahoo rotating refresh-token storage."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import yahoo_token


class RotatingRefreshTokenTests(unittest.TestCase):
    def test_rotated_token_is_encrypted_and_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                self.assertEqual(yahoo_token.select_refresh_token("secret-A", "seed-old"), "seed-old")
                self.assertTrue(yahoo_token.persist_refresh_token("secret-A", "seed-old", "new-token"))
                self.assertEqual(yahoo_token.select_refresh_token("secret-A", "seed-old"), "new-token")
                self.assertFalse(yahoo_token.persist_refresh_token("secret-A", "seed-old", "new-token"))
                raw = target.read_text(encoding="utf-8")
                self.assertNotIn("seed-old", raw)
                self.assertNotIn("new-token", raw)
                self.assertEqual(json.loads(raw)["version"], 1)

    def test_new_seed_token_replaces_older_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("secret-A", "seed-old", "rotated-old")
                self.assertEqual(yahoo_token.select_refresh_token("secret-A", "seed-new"), "seed-new")
                yahoo_token.persist_refresh_token("secret-A", "seed-new", "rotated-new")
                self.assertEqual(yahoo_token.select_refresh_token("secret-A", "seed-new"), "rotated-new")

    def test_wrong_client_secret_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("secret-A", "seed", "rotated")
                with self.assertRaises(RuntimeError):
                    yahoo_token.select_refresh_token("secret-B", "seed")

    def test_invalid_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            target.write_text("not-json", encoding="utf-8")
            with patch.object(yahoo_token, "STATE_PATH", target):
                with self.assertRaises(RuntimeError):
                    yahoo_token.select_refresh_token("secret-A", "seed")

    def test_regular_refresh_cannot_overwrite_another_apps_state(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("secret-A", "seed", "old-token")
                before = target.read_bytes()
                with self.assertRaises(RuntimeError):
                    yahoo_token.persist_refresh_token("secret-B", "seed", "new-token")
                self.assertEqual(target.read_bytes(), before)

    def test_empty_reauthorization_token_cannot_replace_saved_state(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "token.enc.json"
            with patch.object(yahoo_token, "STATE_PATH", target):
                yahoo_token.persist_refresh_token("secret-A", "seed", "old-token")
                before = target.read_bytes()
                with self.assertRaises(ValueError):
                    yahoo_token.persist_refresh_token("secret-B", "seed", "", replace_existing=True)
                self.assertEqual(target.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()

