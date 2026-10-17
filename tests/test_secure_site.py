"""Privacy, HTML conversion and Yahoo scoring tests for encrypted SCFL Pages."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import secure_site
import update_from_yahoo as yahoo

PASSWORD = "unit-test-unique-long-password-2026"


class PrivacyTests(unittest.TestCase):
    def test_encrypt_roundtrip_with_wrong_password_rejection(self):
        original = {"seasons": {"2018": [{"name": "Stephen"}]},
                    "currentStandings": [{"name": "Secret Test Team"}]}
        payload = secure_site.encrypt_records(original, PASSWORD)
        self.assertNotIn("Stephen", json.dumps(payload))
        self.assertNotIn("Secret Test Team", json.dumps(payload))
        self.assertEqual(secure_site.decrypt_records(payload, PASSWORD), original)
        with self.assertRaises(Exception):
            secure_site.decrypt_records(payload, PASSWORD + "-wrong")

    def test_rejects_short_password(self):
        with self.assertRaises(ValueError):
            secure_site.encrypt_records({"x": 1}, "too-easy")

    def test_real_site_converts_without_plaintext(self):
        html = secure_site.INDEX.read_text(encoding="utf-8")
        if 'id="unlockPanel"' in html:
            self.assertNotIn('id="league-data"', html)
            self.assertEqual(secure_site.protected_html(html), html)
            return
        self.assertIn('id="league-data"', html)
        transformed = secure_site.protected_html(html)
        self.assertIn('body class="locked"', transformed)
        self.assertIn('id="unlockPanel"', transformed)
        self.assertIn('id="unlockPassword"', transformed)
        self.assertNotIn('id="league-data"', transformed)
        self.assertIn("db.yahoo?.week", transformed)
        self.assertIn("Fantasy data provided by", transformed)
        self.assertIn("matchWeeks", transformed)
        self.assertEqual(secure_site.protected_html(transformed), transformed)

    def test_atomic_encrypted_store_with_synthetic_html(self):
        legacy = """<!doctype html>
<html><head><style>
  </style></head>
<body><main>League</main><footer>Siler City Fantasy League · League records sourced from the commissioner workbook</footer>
<script id="league-data" type="application/json">{"seasons":{"2018":[{"name":"Old Team"}]},"currentStandings":[{"name":"Secret Team"}]}</script>
<script>
    const db=JSON.parse(document.getElementById('league-data').textContent);
yearButtons(document.getElementById('matchupWeeks'),renderMatchups,['1','2','3']);renderMatchups('3');
  </script>
</body>
</html>"""
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            index = root / "index.html"
            encrypted = root / "data" / "league-data.enc.json"
            index.write_text(legacy, encoding="utf-8")
            with patch.object(secure_site, "INDEX", index), patch.object(secure_site, "ENCRYPTED", encrypted):
                records = secure_site.load_records(PASSWORD)
                secure_site.store_records(records, PASSWORD)
                self.assertEqual(secure_site.load_records(PASSWORD), records)
                self.assertNotIn("Old Team", index.read_text(encoding="utf-8"))
                self.assertNotIn("Secret Team", encrypted.read_text(encoding="utf-8"))
                self.assertIn("unlockPanel", index.read_text(encoding="utf-8"))

    def test_incomplete_data_is_never_published(self):
        with self.assertRaises(ValueError):
            secure_site.store_records({"seasons": {"2018": []}}, PASSWORD)


class YahooTests(unittest.TestCase):
    def test_adjusted_wins_and_points(self):
        games = [
            [("a", "Alpha", 101.0), ("b", "Beta", 99.0)],
            [("c", "Charlie", 109.0), ("d", "Delta", 95.0)],
            [("e", "Echo", 120.0), ("f", "Foxtrot", 100.0)],
            [("g", "Golf", 90.0), ("h", "Hotel", 99.0)],
            [("i", "India", 85.0), ("j", "Juliet", 88.0)],
        ]
        with patch.object(yahoo, "week_matchups", return_value=games):
            week, standings, matchups = yahoo.standings_and_scores("token", "league", 1, 17)
        self.assertEqual((week, len(standings), len(matchups["1"])), (1, 10, 5))
        alpha = next(x for x in standings if x["name"] == "Alpha")
        self.assertEqual((alpha["wins"], alpha["pointWins"], alpha["adjustedWins"]), (1, 1, 2))

    def test_incomplete_scoreboard_does_not_replace_history(self):
        with patch.object(yahoo, "week_matchups", return_value=[]):
            with self.assertRaises(RuntimeError):
                yahoo.standings_and_scores("token", "league", 2, 17)

    def test_pending_authorization_has_error_code(self):
        err = yahoo.YahooError(403, "This application is not authorized to perform this action")
        self.assertEqual(err.code, 403)
        self.assertIn("not authorized", err.description.lower())

    def test_invalid_refresh_token_does_not_block_encrypted_site_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<!doctype html>not yet protected", encoding="utf-8")
            encrypted = Path(tmp) / "data" / "league-data.enc.json"
            with patch.dict("os.environ", {"SCFL_SITE_PASSWORD": PASSWORD}), \
                patch.object(yahoo, "INDEX", index), \
                patch.object(yahoo, "ENCRYPTED", encrypted), \
                patch.object(yahoo, "load_records", return_value={"seasons": {"2018": [{}]}, "currentStandings": [{}]}), \
                patch.object(yahoo, "store_records") as store, \
                patch.object(yahoo, "apply_manual_fallback", return_value=False), \
                patch.object(yahoo, "refresh_access_token", side_effect=yahoo.YahooError(400, "Invalid refresh token")):
                self.assertEqual(yahoo.main(), 0)
                store.assert_called_once()

    def test_unexpected_yahoo_oauth_error_remains_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<!doctype html>not yet protected", encoding="utf-8")
            encrypted = Path(tmp) / "data" / "league-data.enc.json"
            with patch.dict("os.environ", {"SCFL_SITE_PASSWORD": PASSWORD}), \
                patch.object(yahoo, "INDEX", index), \
                patch.object(yahoo, "ENCRYPTED", encrypted), \
                patch.object(yahoo, "load_records", return_value={"seasons": {"2018": [{}]}, "currentStandings": [{}]}), \
                patch.object(yahoo, "store_records") as store, \
                patch.object(yahoo, "apply_manual_fallback", return_value=False), \
                patch.object(yahoo, "refresh_access_token", side_effect=yahoo.YahooError(400, "Unknown Yahoo error")):
                with self.assertRaises(yahoo.YahooError):
                    yahoo.main()
                store.assert_called_once()



if __name__ == "__main__":
    unittest.main()
