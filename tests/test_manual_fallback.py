"""Tests for password-protected, persistent manual matchup backup."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import manual_fallback as backup

PASSWORD = "manual-week-four-five-unit-test-passphrase-2026"


def games_for(week: int) -> list:
    return [
        [f"Team {a}", round(float(100 + a + week), 2),
         f"Team {b}", round(float(100 + b + week), 2)]
        for a, b in ((0, 1), (2, 3), (4, 5), (6, 7), (8, 9))
    ]


class ManualFallbackTests(unittest.TestCase):
    def test_keypair_encrypted_private_key_and_manual_payload(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pub, private = base / "public.json", base / "private.enc.json"
            with patch.object(backup, "PUBLIC_KEY", pub), patch.object(backup, "PRIVATE_KEY", private):
                self.assertTrue(backup.generate_key_files(PASSWORD))
                self.assertFalse(backup.generate_key_files(PASSWORD))
                self.assertNotIn("PRIVATE KEY", private.read_text())
                self.assertNotIn(PASSWORD, private.read_text())
                payload = {"season": 2026, "matchups": {"4": games_for(4), "5": games_for(5)}}
                ciphertext = backup.encrypt_manual_payload(payload, json.loads(pub.read_text()))
                self.assertNotIn("Team 0", json.dumps(ciphertext))
                self.assertEqual(backup.decrypt_manual_payload(
                    backup.validate_private_key(PASSWORD), ciphertext), payload)
                with self.assertRaises(Exception):
                    backup.validate_private_key(PASSWORD + "incorrect")

    def test_recalculate_standings_from_two_new_weeks(self):
        names = {f"Team {number}" for number in range(10)}
        original = {str(week): games_for(week) for week in range(1, 4)}
        before = backup.compute_standings(original, names)
        full = {str(week): games_for(week) for week in range(1, 6)}
        after = backup.compute_standings(full, names)
        self.assertEqual(sum(t["wins"] for t in after), 25)
        self.assertEqual(sum(t["pointWins"] for t in after), 25)
        self.assertEqual(sum(t["adjustedWins"] for t in after), 50)
        self.assertEqual(len(after), 10)
        self.assertEqual(max(t["weeks"][-1]["week"] for t in after), 5)
        self.assertGreater(after[0]["points"], before[0]["points"])

    def test_week_4_to_7_fallback_merges_snapshots_without_regressing_live_scores(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pub, priv, old, supplemental = [
                base / p for p in ("public.json", "private.enc.json", "old.enc.json", "new.enc.json")
            ]
            sources = ((old, {"4", "5"}), (supplemental, {"5", "6", "7"}))
            with patch.object(backup, "PUBLIC_KEY", pub), \
                 patch.object(backup, "PRIVATE_KEY", priv), \
                 patch.object(backup, "MANUAL_SOURCES", sources):
                backup.generate_key_files(PASSWORD)
                previous = {"season": 2026, "matchups": {"4": games_for(4), "5": games_for(5)}}
                newer = {"season": 2026, "matchups": {str(w): games_for(w) for w in (5, 6, 7)}}
                newer["matchups"]["5"][0][1] = 150.55  # Updated Week 5 supersedes the older screenshot.
                public_data = json.loads(pub.read_text())
                old.write_text(json.dumps(backup.encrypt_manual_payload(previous, public_data)))
                supplemental.write_text(json.dumps(backup.encrypt_manual_payload(newer, public_data)))

                initial = {
                    "seasons": {"2018": [{"name": "Old"}]},
                    "currentStandings": [{"name": f"Team {i}"} for i in range(10)],
                    "currentSeason": "2026",
                    "matchups": {str(w): games_for(w) for w in range(1, 4)},
                    "draftOrder": [{"name": "Team 0"}],
                }
                with patch.object(backup, "load_records", return_value=initial), \
                     patch.object(backup, "store_records") as store:
                    self.assertTrue(backup.apply_manual_fallback(PASSWORD))
                    outgoing = store.call_args.args[0]
                    self.assertEqual(outgoing["yahoo"]["week"], 7)
                    self.assertEqual(outgoing["yahoo"]["source"], "manual")
                    self.assertEqual(len(outgoing["matchups"]), 7)
                    self.assertEqual(outgoing["matchups"]["4"], previous["matchups"]["4"])
                    self.assertEqual(outgoing["matchups"]["5"], newer["matchups"]["5"])
                    self.assertEqual(outgoing["matchups"]["7"], newer["matchups"]["7"])
                    self.assertEqual(outgoing["seasons"], initial["seasons"])
                    self.assertEqual(len(outgoing["currentStandings"][0]["weeks"]), 7)
                    self.assertEqual(sum(t["wins"] for t in outgoing["currentStandings"]), 35)
                    self.assertEqual(sum(t["pointWins"] for t in outgoing["currentStandings"]), 35)

                with patch.object(backup, "load_records", return_value=outgoing), \
                     patch.object(backup, "store_records") as store:
                    self.assertFalse(backup.apply_manual_fallback(PASSWORD))
                    store.assert_not_called()

                live6 = copy.deepcopy(outgoing)
                live6["yahoo"] = {"source": "live", "week": 6}
                live6["matchups"]["6"][0][1] = 175.55
                with patch.object(backup, "load_records", return_value=live6), \
                     patch.object(backup, "store_records") as store:
                    self.assertTrue(backup.apply_manual_fallback(PASSWORD))
                    merged = store.call_args.args[0]
                    self.assertEqual(merged["matchups"]["6"][0][1], 175.55)
                    self.assertEqual(merged["matchups"]["7"], newer["matchups"]["7"])
                    self.assertEqual(merged["yahoo"]["week"], 7)

                live7 = copy.deepcopy(outgoing)
                live7["yahoo"] = {"source": "live", "week": 7}
                with patch.object(backup, "load_records", return_value=live7), \
                     patch.object(backup, "store_records") as store:
                    self.assertFalse(backup.apply_manual_fallback(PASSWORD))
                    store.assert_not_called()

                future = copy.deepcopy(outgoing)
                future["yahoo"] = {"source": "live", "week": 8}
                with patch.object(backup, "load_records", return_value=future), \
                     patch.object(backup, "store_records") as store:
                    self.assertFalse(backup.apply_manual_fallback(PASSWORD))
                    store.assert_not_called()

    def test_three_encrypted_sources_validate_nine_week_records_before_storing(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pub, priv = base / "public.json", base / "private.enc.json"
            sources = tuple((base / filename, weeks) for filename, weeks in (
                ("old.enc.json", {"4", "5"}),
                ("corrected.enc.json", {"5", "6", "7"}),
                ("latest.enc.json", {"8", "9"}),
            ))
            payloads = [{"season": 2026, "matchups": {w: games_for(int(w)) for w in weeks}}
                        for _, weeks in sources]
            payloads[1]["matchups"]["5"][0][1] = 150.55
            # Odd-numbered teams win every synthetic game except this Week 5 correction.
            records = {f"Team {i}": [9, 0, 0] if i % 2 else [0, 9, 0] for i in range(10)}
            records.update({"Team 0": [1, 8, 0], "Team 1": [8, 1, 0]})
            payloads[2]["headToHeadCheckpoint"] = {"throughWeek": 9, "records": records}
            initial = {
                "seasons": {"2018": [{"name": "Historical Team"}]},
                "currentSeason": "2026",
                "currentStandings": [{"name": f"Team {i}"} for i in range(10)],
                "matchups": {str(w): games_for(w) for w in range(1, 4)},
                "draftOrder": [{"name": "Team 0"}],
            }
            with patch.object(backup, "PUBLIC_KEY", pub), \
                 patch.object(backup, "PRIVATE_KEY", priv), \
                 patch.object(backup, "MANUAL_SOURCES", sources):
                backup.generate_key_files(PASSWORD)
                public = json.loads(pub.read_text())
                for (path, _), payload in zip(sources, payloads):
                    path.write_text(json.dumps(backup.encrypt_manual_payload(payload, public)))
                with patch.object(backup, "load_records", return_value=copy.deepcopy(initial)), \
                     patch.object(backup, "store_records") as store:
                    self.assertTrue(backup.apply_manual_fallback(PASSWORD))
                    store.assert_called_once()
                    outgoing = store.call_args.args[0]
                    self.assertEqual(outgoing["yahoo"]["week"], 9)
                    self.assertEqual(outgoing["yahoo"]["source"], "manual")
                    self.assertEqual(set(outgoing["matchups"]), {str(w) for w in range(1, 10)})
                    for week, games in initial["matchups"].items():
                        self.assertEqual(outgoing["matchups"][week], games)
                    self.assertEqual(outgoing["matchups"]["4"], payloads[0]["matchups"]["4"])
                    for payload in payloads[1:]:
                        for week, games in payload["matchups"].items():
                            self.assertEqual(outgoing["matchups"][week], games)
                    for key in ("seasons", "currentSeason", "draftOrder"):
                        self.assertEqual(outgoing[key], initial[key])
                    standings = outgoing["currentStandings"]
                    self.assertEqual(len(standings), 10)
                    self.assertTrue(all(len(row["weeks"]) == 9 for row in standings))
                    self.assertEqual({row["name"]: [row["wins"], row["losses"], row["ties"]]
                                      for row in standings}, records)
                    for key, total in (("wins", 45), ("pointWins", 45), ("adjustedWins", 90)):
                        self.assertEqual(sum(row[key] for row in standings), total)

                # A structurally valid but incorrect encrypted checkpoint must fail closed.
                payloads[2]["headToHeadCheckpoint"]["records"]["Team 0"] = [2, 7, 0]
                payloads[2]["headToHeadCheckpoint"]["records"]["Team 1"] = [7, 2, 0]
                sources[2][0].write_text(json.dumps(backup.encrypt_manual_payload(payloads[2], public)))
                with patch.object(backup, "load_records", return_value=copy.deepcopy(initial)), \
                     patch.object(backup, "store_records") as store:
                    with self.assertRaisesRegex(ValueError, "head-to-head checkpoint") as error:
                        backup.apply_manual_fallback(PASSWORD)
                    self.assertNotIn("Team", str(error.exception))
                    store.assert_not_called()

    def test_original_week_4_5_backup_still_works_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            pub, priv, original = [
                base / p for p in ("public.json", "private.enc.json", "old.enc.json")
            ]
            with patch.object(backup, "PUBLIC_KEY", pub), \
                 patch.object(backup, "PRIVATE_KEY", priv), \
                 patch.object(backup, "MANUAL_SOURCES", ((original, {"4", "5"}),)):
                backup.generate_key_files(PASSWORD)
                source = {"season": 2026, "matchups": {"4": games_for(4), "5": games_for(5)}}
                original.write_text(json.dumps(
                    backup.encrypt_manual_payload(source, json.loads(pub.read_text()))
                ))
                initial = {
                    "seasons": {"2018": [{"name": "Old"}]},
                    "currentStandings": [{"name": f"Team {i}"} for i in range(10)],
                    "matchups": {str(w): games_for(w) for w in range(1, 4)},
                }
                with patch.object(backup, "load_records", return_value=initial), \
                     patch.object(backup, "store_records") as store:
                    self.assertTrue(backup.apply_manual_fallback(PASSWORD))
                    self.assertEqual(store.call_args.args[0]["yahoo"]["week"], 5)


    def test_reject_duplicate_team(self):
        games = games_for(4)
        games[0][2] = "Team 2"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            backup.validate_matchups({"4": games})

    def test_reject_bad_score(self):
        games = games_for(4)
        games[0][1] = -30
        with self.assertRaisesRegex(ValueError, "score"):
            backup.validate_matchups({"4": games})


if __name__ == "__main__":
    unittest.main()
