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

    def test_member_frontend_and_old_link_have_no_password_gate(self):
        redirect=(secure_site.ROOT/'index.html').read_text()
        page=(secure_site.ROOT/'web/league.html').read_text()
        self.assertIn('https://siler-city-login-trial.vercel.app/',redirect)
        self.assertIn("location.replace('https://siler-city-login-trial.vercel.app/')",redirect)
        self.assertNotIn('location.search',redirect)
        for html in [redirect,page]:
            self.assertNotIn('id="league-data"',html)
            self.assertNotIn('id="unlockPassword"',html)
            self.assertNotIn('league-data.enc.json',html)
        self.assertIn("fetch('/api/league'",page)
        self.assertIn('Sign in with Yahoo',page)
        self.assertNotIn('Use the current league site',page)

    def test_atomic_server_archive_does_not_rewrite_the_frontend(self):
        records={'seasons':{'2018':[{'name':'Old Team'}]},'currentStandings':[{'name':'Secret Team'}]}
        original=(secure_site.ROOT/'index.html').read_text()
        with tempfile.TemporaryDirectory() as folder:
            encrypted=Path(folder)/'archive.enc.json'
            with patch.object(secure_site,'ENCRYPTED',encrypted):
                secure_site.store_records(records,PASSWORD)
                self.assertEqual(secure_site.load_records(PASSWORD),records)
                self.assertNotIn('Secret Team',encrypted.read_text())
                self.assertEqual(json.loads(encrypted.read_text())['version'],2)
        self.assertEqual((secure_site.ROOT/'index.html').read_text(),original)

    def test_incomplete_data_is_never_published(self):
        with self.assertRaises(ValueError):
            secure_site.store_records({"seasons": {"2018": []}}, PASSWORD)

    def test_regular_workflows_do_not_depend_on_the_retired_shared_password(self):
        for workflow in (secure_site.ROOT/'.github/workflows').glob('*.yml'):
            self.assertNotIn('SCFL_SITE_PASSWORD',workflow.read_text(),workflow.name)


class YahooTests(unittest.TestCase):
    def test_adjusted_wins_and_points(self):
        games = [
            [("a", "Alpha", 101.0), ("b", "Beta", 98.0)],
            [("c", "Charlie", 109.0), ("d", "Delta", 95.0)],
            [("e", "Echo", 120.0), ("f", "Foxtrot", 100.0)],
            [("g", "Golf", 90.0), ("h", "Hotel", 99.0)],
            [("i", "India", 85.0), ("j", "Juliet", 88.0)],
        ]
        with patch.object(yahoo, "week_matchups", return_value=games), patch.object(yahoo, "nfl_week_complete", return_value=True):
            week, standings, matchups = yahoo.standings_and_scores("token", "league", 1, 17)
        self.assertEqual((week, len(standings), len(matchups["1"])), (1, 10, 5))
        alpha = next(x for x in standings if x["name"] == "Alpha")
        self.assertEqual((alpha["wins"], alpha["pointWins"], alpha["adjustedWins"]), (1, 1, 2))

    def test_incomplete_scoreboard_does_not_replace_history(self):
        with patch.object(yahoo, "week_matchups", return_value=[]):
            with self.assertRaises(RuntimeError):
                yahoo.standings_and_scores("token", "league", 2, 17)

    def test_unstarted_scoreboard_is_not_counted_as_completed_week(self):
        def payload(status):
            return {"matchups": [{"matchup": {"status": status[i], "teams": [
                {"team": {"team_key": f"t{i}a", "name": f"A{i}", "team_points": {"total": "0"}}},
                {"team": {"team_key": f"t{i}b", "name": f"B{i}", "team_points": {"total": "0"}}},
            ]}} for i in range(5)]}
        with patch.object(yahoo, "api", return_value=payload(["preevent"] * 5)):
            self.assertEqual(yahoo.week_matchups("token", "league", 2), [])
        with patch.object(yahoo, "api", return_value=payload(["midevent"] + ["preevent"] * 4)):
            self.assertEqual(yahoo.week_matchups("token", "league", 2), [])
        with patch.object(yahoo, "api", return_value=payload([""] * 5)):
            self.assertEqual(yahoo.week_matchups("token", "league", 2), [])
        with patch.object(yahoo, "api", return_value=payload(["postevent"] * 5)):
            self.assertEqual(len(yahoo.week_matchups("token", "league", 2)), 5)

    def test_unstarted_current_week_preserves_previous_adjusted_records(self):
        games = [[(f"t{i}a", f"A{i}", 100.0+i), (f"t{i}b", f"B{i}", 90.0+i)] for i in range(5)]
        with patch.object(yahoo, "week_matchups", side_effect=[games, []]), patch.object(yahoo, "nfl_week_complete", return_value=True):
            week, rows, matchups = yahoo.standings_and_scores("token", "league", 2, 17)
        self.assertEqual(week, 1)
        self.assertEqual(list(matchups), ["1"])
        self.assertTrue(all(len(row["weeks"]) == 1 for row in rows))
        self.assertTrue(all(row["ties"] == 0 for row in rows))

    def test_nfl_final_gate_rejects_live_missing_and_wrong_week(self):
        def scoreboard(completed=True):
            return {"season":{"year":2026},"week":{"number":10},"events":[{"id":str(i),"status":{"type":{"completed":completed}}} for i in range(13)]}
        with patch.object(yahoo,"request_json",return_value=scoreboard()):
            self.assertTrue(yahoo.nfl_week_complete(2026,10))
        pending=scoreboard();pending['events'][-1]['status']['type']['completed']=False
        for data in (pending, {**scoreboard(),"week":{"number":9}}, {**scoreboard(),"events":[]}, {**scoreboard(),"events":scoreboard()['events'][:11]}):
            with patch.object(yahoo,"request_json",return_value=data):self.assertFalse(yahoo.nfl_week_complete(2026,10))
        with patch.object(yahoo,"request_json",side_effect=RuntimeError('offline')):self.assertFalse(yahoo.nfl_week_complete(2026,10))

    def test_even_final_yahoo_matchups_wait_for_last_nfl_game(self):
        games=[[(f"t{i}a",f"A{i}",100+i),(f"t{i}b",f"B{i}",90+i)] for i in range(5)]
        with patch.object(yahoo,'week_matchups',side_effect=[games,games]), patch.object(yahoo,'nfl_week_complete',side_effect=[True,False]):
            week,rows,matchups=yahoo.standings_and_scores('token','league',2,17,2026)
        self.assertEqual((week,list(matchups)),(1,['1']))
        self.assertTrue(all(len(row['weeks'])==1 for row in rows))
        with patch.object(yahoo,'week_matchups',side_effect=[games,games]), patch.object(yahoo,'nfl_week_complete',return_value=True):
            week,rows,matchups=yahoo.standings_and_scores('token','league',2,17,2026)
        self.assertEqual((week,list(matchups)),(2,['1','2']))
        self.assertTrue(all(len(row['weeks'])==2 for row in rows))

    def test_week_rollover_does_not_bypass_a_postponed_game(self):
        games=[[(f"t{i}a",f"A{i}",100+i),(f"t{i}b",f"B{i}",90+i)] for i in range(5)]
        with patch.object(yahoo,'week_matchups',side_effect=[games,games,games]), patch.object(yahoo,'nfl_week_complete',side_effect=[True,False]):
            week,rows,matchups=yahoo.standings_and_scores('token','league',3,17,2026)
        self.assertEqual((week,list(matchups)),(1,['1']))
        self.assertTrue(all(len(row['weeks'])==1 for row in rows))

    def test_unconfirmed_top_half_cutoff_tie_does_not_choose_a_team_key(self):
        settled=[[(f"t{i}a",f"A{i}",100+i),(f"t{i}b",f"B{i}",90+i)] for i in range(5)]
        tied=[[(f"t{i}a",f"A{i}",100),(f"t{i}b",f"B{i}",100)] for i in range(5)]
        with patch.object(yahoo,'week_matchups',side_effect=[settled,tied]), patch.object(yahoo,'nfl_week_complete',return_value=True):
            week,rows,matchups=yahoo.standings_and_scores('token','league',2,17,2026)
        self.assertEqual((week,list(matchups)),(1,['1']))
        self.assertTrue(all(len(row['weeks'])==1 for row in rows))

    def test_stat_correction_updates_an_already_completed_week(self):
        games=[[(f"t{i}a",f"A{i}",100+i),(f"t{i}b",f"B{i}",90+i)] for i in range(5)]
        corrected=[list(game) for game in games]
        corrected[0]=[("t0a","A0",101.5),("t0b","B0",90)]
        with patch.object(yahoo,'week_matchups',side_effect=[games,[],corrected,[]]), patch.object(yahoo,'nfl_week_complete',return_value=True):
            _,before,_=yahoo.standings_and_scores('token','league',2,17,2026)
            _,after,_=yahoo.standings_and_scores('token','league',2,17,2026)
        self.assertEqual(next(r for r in before if r['name']=='A0')['points'],100)
        self.assertEqual(next(r for r in after if r['name']=='A0')['points'],101.5)

    def test_existing_provisional_live_week_rolls_back_but_schedule_refreshes(self):
        initial={'seasons':{'2025':[{}]},'currentStandings':[{'name':'Live'}], 'matchups':{'10':[]}, 'yahoo':{'week':10,'source':'live'},'hub':{}}
        rows=[{'name':f'Team {i}'} for i in range(10)]
        with patch.dict('os.environ',{'YAHOO_CLIENT_SECRET':PASSWORD}), patch.object(yahoo,'load_records',return_value=initial), \
             patch.object(yahoo,'apply_manual_fallback'), patch.object(yahoo,'refresh_access_token',return_value='access'), \
             patch.object(yahoo,'find_league',return_value=('470.l.844486',2026)), \
             patch.object(yahoo,'league_metadata',return_value=(10,17,'Siler City')), \
             patch.object(yahoo,'standings_and_scores',return_value=(9,rows,{'9':[['A',1,'B',0]]})), \
             patch.object(yahoo,'collect_hub',return_value={'schedule':{'10':[{'status':'midevent'}]}}), \
             patch.object(yahoo,'store_records') as store:
            self.assertEqual(yahoo.main(),0)
            result=store.call_args.args[0]
            self.assertEqual(result['yahoo']['week'],9)
            self.assertEqual(result['currentStandings'],rows)
            self.assertEqual(result['hub']['schedule']['10'][0]['status'],'midevent')

    def test_newer_manual_week_is_preserved_while_live_schedule_refreshes(self):
        initial={'seasons':{'2025':[{}]},'currentSeason':'2026','currentStandings':[{'name':'Manual'}], 'matchups':{'9':[]}, 'yahoo':{'week':9,'source':'manual'},'hub':{}}
        with patch.dict('os.environ',{'YAHOO_CLIENT_SECRET':PASSWORD}), patch.object(yahoo,'load_records',return_value=initial), \
             patch.object(yahoo,'apply_manual_fallback'), patch.object(yahoo,'refresh_access_token',return_value='access'), \
             patch.object(yahoo,'find_league',return_value=('470.l.844486',2026)), \
             patch.object(yahoo,'league_metadata',return_value=(10,17,'Siler City')), \
             patch.object(yahoo,'standings_and_scores',return_value=(8,[{'name':'Older'}],{})), \
             patch.object(yahoo,'collect_hub',return_value={'schedule':{'10':[{'status':'midevent'}]}}), \
             patch.object(yahoo,'store_records') as store:
            self.assertEqual(yahoo.main(),0)
            result=store.call_args.args[0]
            self.assertEqual(result['yahoo']['week'],9)
            self.assertEqual(result['currentStandings'][0]['name'],'Manual')
            self.assertEqual(result['hub']['schedule']['10'][0]['status'],'midevent')

    def test_ambiguous_manual_fallback_does_not_block_yahoo_or_live_matchups(self):
        initial={'seasons':{'2025':[{}]},'currentSeason':'2026','currentStandings':[{'name':'Confirmed'}], 'matchups':{'9':[]}, 'yahoo':{'week':9,'finalizedThrough':9,'standingsAvailable':True,'source':'live'},'hub':{}}
        with patch.dict('os.environ',{'YAHOO_CLIENT_SECRET':PASSWORD}), patch.object(yahoo,'load_records',return_value=initial), \
             patch.object(yahoo,'apply_manual_fallback',side_effect=yahoo.TopHalfCutoffTie('ambiguous')), patch.object(yahoo,'refresh_access_token',return_value='access'), \
             patch.object(yahoo,'find_league',return_value=('470.l.844486',2026)), \
             patch.object(yahoo,'league_metadata',return_value=(10,17,'Siler City')), \
             patch.object(yahoo,'standings_and_scores',side_effect=yahoo.FinalResultsUnavailable('NFL feed unavailable')), \
             patch.object(yahoo,'collect_hub',return_value={'week':10,'schedule':{'10':[{'status':'midevent'}]}}), \
             patch.object(yahoo,'store_records') as store:
            self.assertEqual(yahoo.main(),0)
            result=store.call_args.args[0]
            self.assertEqual(result['yahoo']['finalizedThrough'],9)
            self.assertEqual(result['currentStandings'][0]['name'],'Confirmed')
            self.assertEqual(result['hub']['schedule']['10'][0]['status'],'midevent')

    def test_verified_snapshot_survives_historical_feed_outage_and_refreshes_live_feed(self):
        initial={'seasons':{'2025':[{}]},'currentSeason':'2026','currentStandings':[{'name':'Confirmed'}], 'matchups':{'9':[]}, 'yahoo':{'week':9,'finalizedThrough':9,'standingsAvailable':True,'source':'live'},'hub':{}}
        with patch.dict('os.environ',{'YAHOO_CLIENT_SECRET':PASSWORD}), patch.object(yahoo,'load_records',return_value=initial), \
             patch.object(yahoo,'apply_manual_fallback'), patch.object(yahoo,'refresh_access_token',return_value='access'), \
             patch.object(yahoo,'find_league',return_value=('470.l.844486',2026)), \
             patch.object(yahoo,'league_metadata',return_value=(10,17,'Siler City')), \
             patch.object(yahoo,'standings_and_scores',side_effect=yahoo.FinalResultsUnavailable('NFL feed unavailable')), \
             patch.object(yahoo,'collect_hub',return_value={'week':10,'schedule':{'10':[{'status':'midevent'}]}}), \
             patch.object(yahoo,'store_records') as store:
            self.assertEqual(yahoo.main(),0)
            result=store.call_args.args[0]
            self.assertEqual(result['yahoo']['finalizedThrough'],9)
            self.assertTrue(result['yahoo']['standingsAvailable'])
            self.assertEqual(result['currentStandings'][0]['name'],'Confirmed')
            self.assertEqual(result['hub']['schedule']['10'][0]['status'],'midevent')

    def test_unverified_legacy_snapshot_is_marked_unavailable_on_feed_outage(self):
        initial={'seasons':{'2025':[{}]},'currentSeason':'2026','currentStandings':[{'name':'Provisional'}], 'matchups':{'10':[]}, 'yahoo':{'week':10,'source':'live'},'hub':{}}
        with patch.dict('os.environ',{'YAHOO_CLIENT_SECRET':PASSWORD}), patch.object(yahoo,'load_records',return_value=initial), \
             patch.object(yahoo,'apply_manual_fallback'), patch.object(yahoo,'refresh_access_token',return_value='access'), \
             patch.object(yahoo,'find_league',return_value=('470.l.844486',2026)), \
             patch.object(yahoo,'league_metadata',return_value=(10,17,'Siler City')), \
             patch.object(yahoo,'standings_and_scores',side_effect=yahoo.FinalResultsUnavailable('NFL feed unavailable')), \
             patch.object(yahoo,'collect_hub',return_value={'week':10,'schedule':{'10':[{'status':'midevent'}]}}), \
             patch.object(yahoo,'store_records') as store:
            self.assertEqual(yahoo.main(),0)
            result=store.call_args.args[0]
            self.assertFalse(result['yahoo']['standingsAvailable'])
            self.assertEqual(result['yahoo']['finalizedThrough'],0)
            self.assertEqual(result['yahoo']['week'],0)
            self.assertEqual(result['hub']['schedule']['10'][0]['status'],'midevent')

    def test_nfl_scoreboard_os_error_fails_closed(self):
        with patch.object(yahoo,'request_json',side_effect=TimeoutError('timeout')):
            self.assertFalse(yahoo.nfl_week_complete(2026,10))

    def test_transient_yahoo_scoreboard_failure_preserves_verified_prefix(self):
        games=[[(f"t{i}a",f"A{i}",100+i),(f"t{i}b",f"B{i}",90+i)] for i in range(5)]
        with patch.object(yahoo,'week_matchups',side_effect=[games,TimeoutError('offline')]), patch.object(yahoo,'nfl_week_complete',return_value=True):
            week,rows,matchups=yahoo.standings_and_scores('token','league',2,17,2026)
        self.assertEqual((week,list(matchups)),(1,['1']))
        self.assertEqual(len(rows),10)

    def test_pending_authorization_has_error_code(self):
        err = yahoo.YahooError(403, "This application is not authorized to perform this action")
        self.assertEqual(err.code, 403)
        self.assertIn("not authorized", err.description.lower())

    def test_invalid_refresh_token_does_not_block_encrypted_site_bootstrap(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<!doctype html>not yet protected", encoding="utf-8")
            encrypted = Path(tmp) / "data" / "league-data.enc.json"
            with patch.dict("os.environ", {"YAHOO_CLIENT_SECRET": PASSWORD}), \
                patch.object(yahoo, "ENCRYPTED", encrypted), \
                patch.object(yahoo, "load_records", return_value={"seasons": {"2018": [{}]}, "currentStandings": [{}]}), \
                patch.object(yahoo, "store_records") as store, \
                patch.object(yahoo, "apply_manual_fallback", return_value=False), \
                patch.object(yahoo, "refresh_access_token", side_effect=yahoo.YahooError(400, "Invalid refresh token")):
                self.assertEqual(yahoo.main(), 0)
                store.assert_not_called()

    def test_unexpected_yahoo_oauth_error_remains_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = Path(tmp) / "index.html"
            index.write_text("<!doctype html>not yet protected", encoding="utf-8")
            encrypted = Path(tmp) / "data" / "league-data.enc.json"
            with patch.dict("os.environ", {"YAHOO_CLIENT_SECRET": PASSWORD}), \
                patch.object(yahoo, "ENCRYPTED", encrypted), \
                patch.object(yahoo, "load_records", return_value={"seasons": {"2018": [{}]}, "currentStandings": [{}]}), \
                patch.object(yahoo, "store_records") as store, \
                patch.object(yahoo, "apply_manual_fallback", return_value=False), \
                patch.object(yahoo, "refresh_access_token", side_effect=yahoo.YahooError(400, "Unknown Yahoo error")):
                with self.assertRaises(yahoo.YahooError):
                    yahoo.main()
                store.assert_not_called()



if __name__ == "__main__":
    unittest.main()
