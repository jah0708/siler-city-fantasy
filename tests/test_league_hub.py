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
        self.assertFalse(any('settings' in x or 'standings' in x or 'pending_trade' in x or 'type=waiver' in x for x in paths))
        self.assertNotIn('errors',old)

    def test_full_import_and_historical_roster_cache(self):
        paths=[]
        keys=[f'game.l.1.t.{i}' for i in range(10)]
        def api(path, token):
            paths.append(path)
            if path.endswith('/teams'):
                return {'teams':[{'team':[{'team_key':k,'name':f'Team {i}'}]} for i,k in enumerate(keys)]}
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

if __name__=='__main__':unittest.main()
