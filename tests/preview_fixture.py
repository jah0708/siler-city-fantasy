"""Synthetic, non-league data for browser regression checks only."""
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from secure_site import encrypt_records
from manual_fallback import compute_standings
out=Path('/tmp/scfl-preview');(out/'data').mkdir(parents=True,exist_ok=True)
shutil.copy(ROOT/'index.html',out/'index.html');shutil.copy(ROOT/'scfl-logo.png',out/'scfl-logo.png');shutil.copytree(ROOT/'assets',out/'assets',dirs_exist_ok=True)
now=datetime.now(timezone.utc).isoformat()
matches={str(w):[[f'Team {i}',100+i+w,f'Team {i+1}',110+i+w] for i in range(0,10,2)] for w in range(1,11)}
rows=compute_standings(matches,{f'Team {i}' for i in range(10)})
players={f't{i}':[{'key':f'p{i}_{j}','name':f'Player {i}-{j}','position':['QB','RB','WR','TE','K','DEF'][j%6],'nflTeam':'CAR','status':'Q' if j==3 else '', 'slot':'BN' if j>8 else ['QB','RB','WR','TE','K','DEF'][j%6],'bye':12,'points':round(8+j*.7,2),'eligible':[],'stats':{'9':'320'}} for j in range(16)] for i in range(10)}
hub={'version':1,'week':10,'checkedAt':now,'teams':[{'key':f't{i}','name':f'Team {i}','logo':'','managers':[f'Manager {i}']} for i in range(10)],'rosters':{str(w):players for w in range(1,11)},'playerStats':{p['key']:{**p,'points':123} for v in players.values() for p in v},'available':[{'key':f'a{i}','name':f'Free Agent {i}','position':'RB','nflTeam':'BUF','points':25.3,'stats':{},'bye':12,'ownership':'freeagents'} for i in range(30)],'draft':[{'pick':i+1,'round':1,'teamKey':f't{i}','playerKey':f'p{i}_0','name':f'Player {i}-0','position':'QB'} for i in range(10)],'transactions':[{'type':'add/drop','timestamp':str(int(datetime.now().timestamp())),'players':[{'name':'Player Example','type':'add','from':'','to':'Team 1'}]}], 'schedule':{'10':[{'status':'midevent','teams':[{'name':f'Team {i}','points':100+i},{'name':f'Team {i+1}','points':110+i}]} for i in range(0,10,2)]},'statCategories':{'9':'Rushing yards'},'sections':{s:{'status':'ok','updatedAt':now} for s in ['teams','rosters','playerStats','available','transactions','draft','schedule']}}
hub['schedule']['11']=[{'status':'preevent','teams':[{'name':f'Team {i}','points':0},{'name':f'Team {i+1}','points':0}]} for i in range(0,10,2)]
db={'seasons':{'2025':rows},'currentStandings':rows,'currentSeason':'2026','matchups':matches,'playoffs':{},'draftOrder':[{'name':f'Team {i}'} for i in range(10)],'yahoo':{'week':10,'source':'live','lastUpdated':now},'hub':hub}
(out/'data/league-data.enc.json').write_text(json.dumps(encrypt_records(db,'local-preview-only-password-2026')))
