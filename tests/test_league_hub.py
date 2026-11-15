import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from league_hub import player, collect


def p(key='p1'):
    return [[{'player_key':key},{'name':{'full':'Sample Player'}},{'display_position':'RB'},
             {'eligible_positions':[{'position':'RB'},{'position':'W/R/T'}]},
             {'selected_position':[{'coverage_type':'week'},{'week':'10'},{'position':'BN'}]}],
            {'player_points':{'coverage_type':'week','total':'0'},
             'player_stats':{'stats':[{'stat':{'stat_id':'9','value':'42'}}]}}]

class HubTests(unittest.TestCase):
    def test_yahoo_nested_player_and_zero_points(self):
        result=player(p())
        self.assertEqual(result['name'],'Sample Player')
        self.assertEqual(result['points'],0)
        self.assertEqual(result['slot'],'BN')
        self.assertEqual(result['eligible'],['RB','W/R/T'])
        self.assertEqual(result['stats'],{'9':'42'})
        self.assertIsNone(player([{'player_key':'p2'}])['points'])

    def test_failed_sections_retain_prior_data_and_private_fields_are_omitted(self):
        teams=[{'team':[[{'team_key':f'game.l.1.t.{i}'},{'name':f'Team {i}'},
                         {'managers':[{'manager':{'nickname':'Coach','email':'private@example.com','guid':'secret'}}]}]]} for i in range(10)]
        paths=[]
        def api(path, token):
            paths.append(path)
            if path.endswith('/teams'): return {'teams':teams}
            raise RuntimeError('private error body')
        old={'available':[{'name':'Saved Player'}],'sections':{'available':{'updatedAt':'2026-01-01T00:00:00Z'}}}
        result=collect('token','game.l.1',1,1,old,api)
        self.assertEqual(result['available'],old['available'])
        self.assertEqual(result['sections']['available']['status'],'stale')
        self.assertEqual(result['sections']['available']['updatedAt'],'2026-01-01T00:00:00Z')
        self.assertNotIn('private@example.com',str(result))
        self.assertNotIn('secret',str(result))
        self.assertNotIn('private error body',str(result))
        self.assertFalse(any('standings' in x or 'pending_trade' in x or 'type=waiver' in x for x in paths))
        self.assertNotIn('errors',old)

    def test_full_import_and_historical_roster_cache(self):
        paths=[]
        keys=[f'game.l.1.t.{i}' for i in range(10)]
        def api(path, token):
            paths.append(path)
            if path.endswith('/teams'):
                return {'teams':[{'team':[{'team_key':k,'name':f'Team {i}'}]} for i,k in enumerate(keys)]}
            if path.endswith('/settings'): return {'settings':{'uses_playoff':'0'}}
            if '/stat_categories' in path: return {'stats':[{'stat':{'stat_id':'9','display_name':'Rush yards'}}]}
            if '/roster;' in path or '/players;' in path: return {'players':[{'player':p()}]}
            if '/transactions;' in path: return {'transactions':[{'transaction':{'type':'trade','transaction_key':'tr1','timestamp':'1','players':[{'player':p()}]}}]}
            if '/draftresults' in path: return {'draft_results':[{'draft_result':{'pick':'1','round':'1','team_key':keys[0],'player_key':'p1'}}]}
            if '/matchups' in path: return {'matchups':[{'matchup':{'week':'3','status':'preevent','teams':[{'team':{'team_key':keys[0],'name':'Team 0'}},{'team':{'team_key':keys[1],'name':'Team 1'}}]}}]}
            raise AssertionError(path)
        old={'rosters':{'1':{k:[player(p())] for k in keys}}}
        result=collect('t','game.l.1',3,3,old,api)
        self.assertEqual(len(result['rosters']),3)
        self.assertFalse(any('/roster;week=1/' in x for x in paths))
        self.assertEqual(len(result['rosters']['3']),10)
        self.assertEqual(len(result['schedule']['3']),1)
        self.assertEqual(result['draft'][0]['name'],'Sample Player')
        self.assertEqual(result['errors'],{})

    def test_playoff_settings_and_actual_games_are_imported_without_guessing(self):
        keys=[f'game.l.1.t.{i}' for i in range(10)]
        paths=[]
        def api(path, token):
            paths.append(path)
            if path.endswith('/teams'): return {'teams':[{'team':[{'team_key':k,'name':f'Team {i}'}]} for i,k in enumerate(keys)]}
            if path.endswith('/settings'): return {'settings':{'uses_playoff':'1','playoff_start_week':'15','num_playoff_teams':'6'}}
            if '/scoreboard;week=15' in path:
                game={'week':'15','status':'postevent','is_playoffs':'1','is_consolation':'0','winner_team_key':keys[0],
                      'teams':[{'team':{'team_key':keys[0],'name':'Team 0','team_points':{'total':'120.5'}}},
                               {'team':{'team_key':keys[1],'name':'Team 1','team_points':{'total':'115'}}}]}
                regular={'week':'15','status':'postevent','is_playoffs':'0',
                         'teams':[{'team':{'team_key':keys[2],'name':'Team 2'}},{'team':{'team_key':keys[3],'name':'Team 3'}}]}
                unknown={'week':'15','status':'midevent',
                         'teams':[{'team':{'team_key':keys[4],'name':'Team 4'}},{'team':{'team_key':keys[5],'name':'Team 5'}}]}
                consolation={'week':'15','status':'preevent','is_consolation':'1',
                             'teams':[{'team':{'team_key':keys[6],'name':'Team 6'}},{'team':{'team_key':keys[7],'name':'Team 7'}}]}
                return {'matchups':[{'matchup':game},{'matchup':game},{'matchup':regular},
                                    {'matchup':unknown},{'matchup':consolation}]}
            if '/scoreboard;week=16' in path: return {'matchups':[]}
            if '/stat_categories' in path: return {'stats':[{'stat':{'stat_id':'9','display_name':'Rush yards'}}]}
            if '/roster;' in path or '/players;' in path: return {'players':[{'player':p()}]}
            if '/transactions;' in path: return {'transactions':[]}
            if '/draftresults' in path: return {'draft_results':[{'draft_result':{'pick':'1','round':'1','team_key':keys[0],'player_key':'p1'}}]}
            if '/matchups' in path: return {'matchups':[{'matchup':{'week':'1','teams':[{'team':{'team_key':keys[0],'name':'Team 0'}},{'team':{'team_key':keys[1],'name':'Team 1'}}]}}]}
            raise AssertionError(path)
        result=collect('t','game.l.1',16,17,{},api)
        pinfo=result['playoffs']
        self.assertEqual((pinfo['enabled'],pinfo['startWeek'],pinfo['endWeek'],pinfo['teamsCount']),(True,15,17,6))
        self.assertEqual(list(pinfo['weeks']),['15'])
        self.assertEqual(len(pinfo['weeks']['15']),4)
        game=pinfo['weeks']['15'][0]
        self.assertEqual([p['points'] for p in game['teams']],[120.5,115.0])
        self.assertEqual(game['winnerKey'],keys[0]);self.assertFalse(game['isConsolation'])
        self.assertEqual(pinfo['weeks']['15'][1]['playoffs'],'0')
        self.assertIsNone(pinfo['weeks']['15'][1]['isConsolation'])
        self.assertIsNone(pinfo['weeks']['15'][2]['playoffs'])
        self.assertIsNone(pinfo['weeks']['15'][2]['isConsolation'])
        self.assertTrue(pinfo['weeks']['15'][3]['isConsolation'])
        self.assertFalse(any('/scoreboard;week=17' in x for x in paths))
        self.assertEqual(result['sections']['playoffs']['status'],'ok')
        paths.clear()
        before_playoffs=collect('t','game.l.1',14,17,{},api)
        self.assertEqual(before_playoffs['playoffs']['teamsCount'],6)
        self.assertEqual(before_playoffs['playoffs']['weeks'],{})
        self.assertFalse(any('/scoreboard;' in path for path in paths))

    def test_missing_playoff_feed_keeps_last_good_results(self):
        keys=[f'game.l.1.t.{i}' for i in range(10)]
        previous={'leagueKey':'game.l.1','playoffs':{'enabled':True,'startWeek':15,'endWeek':17,'teamsCount':6,
                  'weeks':{'15':[{'teams':[{'key':keys[0],'name':'Team 0'},{'key':keys[1],'name':'Team 1'}]},
                                 {'teams':[{'key':keys[2],'name':'Team 2'},{'key':keys[3],'name':'Team 3'}]}]}},
                  'sections':{'playoffs':{'updatedAt':'2026-12-01T00:00:00Z','status':'ok'}}}
        reported_pairs=[(0,1)]
        def api(path, token):
            if path.endswith('/teams'): return {'teams':[{'team':[{'team_key':k,'name':f'Team {i}'}]} for i,k in enumerate(keys)]}
            if path.endswith('/settings'): return {'settings':{'uses_playoff':'1','playoff_start_week':'15','num_playoff_teams':'6'}}
            if '/scoreboard;week=15' in path:
                return {'matchups':[{'matchup':{'teams':[{'team':{'team_key':keys[a],'name':f'Team {a}'}},
                                                        {'team':{'team_key':keys[b],'name':f'Team {b}'}}]}}
                                    for a,b in reported_pairs]}
            raise RuntimeError('Other section unavailable')
        result=collect('t','game.l.1',15,17,previous,api)
        self.assertEqual(result['playoffs'],previous['playoffs'])
        self.assertEqual(result['sections']['playoffs'],{'updatedAt':'2026-12-01T00:00:00Z','status':'stale'})
        # Commissioner changes with a complete number of matchups should flow
        # through; only a truncated response is held as stale.
        reported_pairs[:]=[(0,4),(2,3)]
        corrected=collect('t','game.l.1',15,17,previous,api)
        self.assertEqual(corrected['sections']['playoffs']['status'],'ok')
        self.assertEqual(corrected['playoffs']['weeks']['15'][0]['teams'][1]['key'],keys[4])

if __name__=='__main__':unittest.main()
