/* Private league dashboard: all data arrives only after browser decryption. */
window.initLeagueHub = function(db) {
  'use strict';
  const hub=db.hub||{}, teams=hub.teams||[], byKey=Object.fromEntries(teams.map(t=>[t.key,t]));
  const $=id=>document.getElementById(id), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=v=>v==null?'—':Number(v).toLocaleString(undefined,{maximumFractionDigits:2,minimumFractionDigits:2});
  const num=v=>Number.isFinite(Number(v))?Number(v):0;
  const safeURL=v=>{try{const u=new URL(v);return u.protocol==='https:'?esc(u.href):''}catch{return ''}};
  const image=(url,cls='hub-portrait')=>safeURL(url)?`<img loading="lazy" class="${cls}" src="${safeURL(url)}" alt="">`:'';
  const empty=msg=>`<div class="hub-empty">${esc(msg)}</div>`;
  const date=v=>v?new Date(v).toLocaleString(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}):'Not yet synced';
  const badge=(v,warn=false)=>v?` <span class="hub-badge ${warn?'warn':''}">${esc(v)}</span>`:'';
  const note=name=>{const s=hub.sections?.[name];return (s?.status&&s.status!=='ok'?`<div class="hub-notice">${esc(hub.errors?.[name]||'Showing previously saved data.')}</div>`:'')+(s?.updatedAt?`<p class="hub-sub">Updated ${esc(date(s.updatedAt))}</p>`:'')};
  const teamOptions=teams.map(t=>`<option value="${esc(t.key)}">${esc(t.name)}</option>`).join('');
  const current=String(hub.week||db.yahoo?.week||''), rosterWeeks=Object.keys(hub.rosters||{}).sort((a,b)=>b-a);
  let saved='';try{saved=localStorage.getItem('scfl-favorite-team')||''}catch{}
  let favorite=byKey[saved]?saved:teams[0]?.key||'';
  const select=(id,label,options)=>`<label>${label}<select id="${id}">${options}</select></label>`;
  const metric=(label,value,sub='')=>`<article class="card hub-metric"><small>${esc(label)}</small><strong>${esc(value)}</strong><span>${esc(sub)}</span></article>`;
  const playerLink=p=>`<button class="hub-link" data-player="${esc(p.key)}">${esc(p.name)}</button>`;
  const roster=(key,week=current)=>hub.rosters?.[week]?.[key]||[];
  const season=p=>hub.playerStats?.[p.key]?.points??null;
  const rowFor=key=>db.currentStandings.find(r=>r.name===byKey[key]?.name);
  const displayRecord=r=>r?`${r.adjustedWins??0}–${r.adjustedLosses??0}`:'—';
  function navigate(view){document.querySelector(`.nav-btn[data-view="${view}"]`)?.click();window.scrollTo({top:0,behavior:'instant'})}
  function wirePlayers(el){el.querySelectorAll('[data-player]').forEach(b=>b.onclick=()=>showPlayer(b.dataset.player))}
  function table(headers,rows){return `<div class="card hub-table-wrap"><table class="hub-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`}
  function scores(games){return games.length?games.map(g=>`<div class="hub-score"><small>${esc(g.status==='postevent'?'Final':g.status==='midevent'?'In progress':'Scheduled')}</small>${g.teams.map(t=>`<strong>${esc(t.name)}</strong><b>${fmt(t.points)}</b>`).join('')}</div>`).join(''):empty('No matchup data saved for this week.')}
  function moves(list){return list.length?list.map(t=>`<article class="hub-move"><div class="hub-move-head">${badge(t.type)}<small>${esc(date(Number(t.timestamp)*1000))}</small></div>${t.players.map(p=>`<p><strong>${esc(p.name)}</strong>${badge(p.type)}<span class="hub-sub">${esc(p.from||'Available pool')} → ${esc(p.to||'Available pool')}</span></p>`).join('')}</article>`).join(''):empty('No completed transactions in this snapshot.')}
  function renderHome(){
    const rows=db.currentStandings||[], weeks=rows.flatMap(t=>(t.weeks||[]).map(w=>({...w,name:t.name}))), best=weeks.reduce((a,b)=>b.points>(a?.points??-1)?b:a,null);
    const recent=rows.map(t=>({name:t.name,avg:(t.weeks||[]).slice(-3).reduce((a,w)=>a+w.points,0)/Math.max(1,(t.weeks||[]).slice(-3).length)})).sort((a,b)=>b.avg-a.avg);
    const last=hub.checkedAt||db.yahoo?.lastUpdated, stale=last&&Date.now()-Date.parse(last)>8*3600000;
    $('hubHome').innerHTML=`<div class="hub-status"><i class="status-dot"></i><strong>${stale?'Saved Yahoo snapshot':'Yahoo snapshot'}</strong><span>${esc(date(last))}</span><span>• Refresh scheduled every 3 hours</span></div>
    <div class="hub-intro"><article class="hub-feature"><p class="eyebrow">The league clubhouse</p><h2>Every matchup.<br>Every move. All here.</h2><p>Follow your team, scout the player pool, and settle the debate with the numbers. Your league. Your adjusted scoring.</p><button class="hub-btn" id="scoutButton">Explore the player pool ↗</button></article><article class="card hub-panel"><h3>Your corner of the league</h3><label class="hub-field">Follow a team on this device<select id="favoriteTeam">${teamOptions}</select></label><div id="favoriteSummary"></div><button class="hub-btn" id="openFavorite">Open team profile →</button></article></div>
    ${!hub.version?empty('Expanded league data is waiting for its first Yahoo sync. Your standings and history are ready in their tabs.'):''}
    <div class="hub-metrics">${metric('League teams',teams.length||rows.length,'All ten in one place')}${metric('Highest weekly score',fmt(best?.points),best?best.name+' · Week '+best.week:'Awaiting scores')}${metric('Recent scoring leader',fmt(recent[0]?.avg),recent[0]?recent[0].name+' · last 3-week average':'Awaiting scores')}${metric('Available player pool',(hub.available||[]).length,'Sorted by actual season points')}</div>
    <div class="hub-grid"><article class="card hub-panel"><h3>Week ${esc(current)} · around the league</h3>${scores(hub.schedule?.[current]||[])}${note('schedule')}</article><article class="card hub-panel"><h3>Latest league moves</h3>${moves((hub.transactions||[]).slice(0,4))}<button class="hub-btn" id="allActivity">View activity →</button>${note('transactions')}</article></div>`;
    $('favoriteTeam').value=favorite;
    function update(){favorite=$('favoriteTeam').value;try{localStorage.setItem('scfl-favorite-team',favorite)}catch{} const r=rowFor(favorite);$('favoriteSummary').innerHTML=`<p><strong>${esc(displayRecord(r))}</strong> adjusted record <span class="hub-sub">${fmt(r?.points)} season points · ${roster(favorite).length} players</span></p>`;}
    $('favoriteTeam').onchange=update;update();$('scoutButton').onclick=()=>navigate('players');$('allActivity').onclick=()=>navigate('activity');$('openFavorite').onclick=()=>{$('teamPicker').value=favorite;renderTeam();navigate('teams')};
  }
  $('teamTools').innerHTML=select('teamPicker','Team',teamOptions)+select('rosterWeek','Roster week',rosterWeeks.map(w=>`<option value="${w}">Week ${w}</option>`).join(''));
  $('teamPicker').value=favorite;
  function renderTeam(){
    const key=$('teamPicker').value, week=$('rosterWeek').value||current, team=byKey[key], ps=roster(key,week), row=rowFor(key);
    if(!team){$('teamContent').innerHTML=empty('Team profiles will appear after the next successful roster sync.');return}
    const points=row?.weeks||[], max=Math.max(1,...points.map(w=>w.points));
    const slots=ps.slice().sort((a,b)=>['BN','IR','IR+'].includes(a.slot)-['BN','IR','IR+'].includes(b.slot));
    $('teamContent').innerHTML=`<div class="hub-team-title">${image(team.logo,'hub-team-logo')}<div><h3>${esc(team.name)}</h3><p>${esc(team.managers.join(' · '))}</p></div></div><div class="hub-metrics">${metric('Adjusted record',displayRecord(row),'Matchup wins + top-half wins')}${metric('Season points',fmt(row?.points))}${metric('Weekly average',fmt(row?.average))}${metric('Roster alerts',ps.filter(p=>p.status).length,'Yahoo injury/status flags')}</div>
    <article class="card hub-panel"><h3>Weekly scoring</h3><div class="hub-bars">${points.map(w=>`<div class="hub-bar" title="Week ${w.week}: ${fmt(w.points)}"><small>${fmt(w.points)}</small><i style="height:${Math.round(w.points/max*100)}px"></i><span>W${w.week}</span></div>`).join('')}</div></article><h3>Week ${esc(week)} roster</h3>
    ${ps.length?table(['Slot','Player','NFL','Week points','Season points','Bye'],slots.map(p=>`<tr><td>${badge(p.slot)}</td><td>${image(p.image)}${playerLink(p)}${badge(p.status,true)}<span class="hub-sub">${esc(p.position)}</span></td><td>${esc(p.nflTeam)}</td><td class="num">${fmt(p.points)}</td><td class="num">${fmt(season(p))}</td><td>${esc(p.bye||'—')}</td></tr>`).join('')):empty('This roster has not been imported yet.')}${note('rosters')}<p class="hub-sub">Week points follow the selected week. Season points are from the latest season snapshot.</p>`;
    wirePlayers($('teamContent'));
  }
  $('teamPicker').onchange=renderTeam;$('rosterWeek').onchange=renderTeam;renderTeam();
  let pool=[];const seen=new Set();
  teams.forEach(t=>roster(t.key).forEach(p=>{pool.push({...p,owner:t.name,available:false,season:season(p)});seen.add(p.key)}));
  (hub.available||[]).forEach(p=>{if(!seen.has(p.key))pool.push({...p,owner:p.ownership==='waivers'?'Waivers':'Available',available:true,season:p.points})});
  $('playerTools').innerHTML='<label>Find a player<input id="playerSearch" type="search" placeholder="Name, NFL team, or fantasy team"></label>'+select('playerPosition','Position','<option value="">All positions</option>'+['QB','RB','WR','TE','K','DEF'].map(p=>`<option>${p}</option>`).join(''))+select('playerOwner','Pool','<option value="all">All imported players</option><option value="available">Available / waivers</option><option value="rostered">On a roster</option>')+select('playerSort','Sort','<option value="points">Season points</option><option value="name">Player name</option>');
  function renderPlayers(){const q=$('playerSearch').value.trim().toLowerCase(),pos=$('playerPosition').value,owner=$('playerOwner').value;
    const filtered=pool.filter(p=>(!q||[p.name,p.nflTeam,p.owner].join(' ').toLowerCase().includes(q))&&(!pos||p.position.split(',').includes(pos)||p.eligible?.includes(pos))&&(owner==='all'||p.available===(owner==='available'))).sort((a,b)=>$('playerSort').value==='name'?a.name.localeCompare(b.name):(b.season??-Infinity)-(a.season??-Infinity));
    $('playerCount').textContent=`${filtered.length} players · current rosters + up to 200 available players by season points`;
    $('playerResults').innerHTML=filtered.length?table(['Player','NFL','Fantasy team / availability','Season points','Bye'],filtered.map(p=>`<tr><td>${image(p.image)}${playerLink(p)}${badge(p.status,true)}<span class="hub-sub">${esc(p.position)}</span></td><td>${esc(p.nflTeam)}</td><td>${esc(p.owner)}</td><td class="num">${fmt(p.season)}</td><td>${esc(p.bye||'—')}</td></tr>`).join('')):empty('No players match these filters. Try another name or position.');wirePlayers($('playerResults'));$('playerFreshness').innerHTML=note('available')+note('playerStats');}
  ['playerSearch','playerPosition','playerOwner','playerSort'].forEach(id=>$(id).addEventListener(id==='playerSearch'?'input':'change',renderPlayers));renderPlayers();
  function showPlayer(key){const p=pool.find(p=>p.key===key)||hub.playerStats?.[key];if(!p)return;const stats=hub.playerStats?.[key]||p;
    $('playerDialogBody').innerHTML=`<header><div><p class="eyebrow">Player detail</p><h2>${esc(p.name)}</h2></div><button class="hub-btn" id="closePlayer">Close</button></header><p>${esc(p.position)} · ${esc(p.nflTeam)} ${badge(p.statusNote||p.status,true)}</p><p>${esc(p.owner||'')} · Bye: ${esc(p.bye||'—')}</p><h3>Season statistics</h3><dl><dt>Fantasy points</dt><dd>${fmt(p.season??stats.points)}</dd>${Object.entries(stats.stats||{}).filter(([id])=>hub.statCategories?.[id]).map(([id,v])=>`<dt>${esc(hub.statCategories[id])}</dt><dd>${esc(v)}</dd>`).join('')}</dl><p class="hub-sub">Actual results from the latest Yahoo snapshot. These are not projections.</p>`;
    $('closePlayer').onclick=()=>$('playerDialog').close();$('playerDialog').showModal();}
  $('activityTools').innerHTML=select('activityKind','Transaction type','<option value="">All completed moves</option><option value="trade">Trades</option><option value="add">Adds</option><option value="drop">Drops</option>')+'<label>Search activity<input id="activitySearch" type="search" placeholder="Player or team"></label>';
  function renderActivity(){const kind=$('activityKind').value,q=$('activitySearch').value.toLowerCase();const list=(hub.transactions||[]).filter(t=>(!kind||t.type.includes(kind))&&(!q||JSON.stringify(t.players).toLowerCase().includes(q)));$('activityContent').innerHTML=moves(list)+note('transactions');}
  $('activityKind').onchange=renderActivity;$('activitySearch').oninput=renderActivity;renderActivity();
  $('draftTools').innerHTML=select('draftTeam','Team','<option value="">All teams</option>'+teamOptions)+select('draftRound','Round','<option value="">All rounds</option>'+[...new Set((hub.draft||[]).map(p=>p.round))].sort((a,b)=>a-b).map(r=>`<option value="${esc(r)}">Round ${esc(r)}</option>`).join(''));
  function renderDraft(){const picks=(hub.draft||[]).filter(p=>(!$('draftTeam').value||p.teamKey===$('draftTeam').value)&&(!$('draftRound').value||String(p.round)===$('draftRound').value));$('draftPicks').innerHTML=picks.length?table(['Pick','Round','Player','Position','Team'],picks.map(p=>`<tr><td>${esc(p.pick)}</td><td>${esc(p.round)}</td><td><strong>${esc(p.name)}</strong></td><td>${badge(p.position)}</td><td>${esc(byKey[p.teamKey]?.name||'Unknown team')}</td></tr>`).join('')):empty('No draft picks available for these filters.');$('draftFreshness').innerHTML=note('draft');}
  $('draftTeam').onchange=renderDraft;$('draftRound').onchange=renderDraft;renderDraft();
  $('compareTools').innerHTML=select('compareA','First team',teamOptions)+select('compareB','Second team',teamOptions);if(teams[1])$('compareB').value=teams[1].key;
  function renderCompare(){const keys=[$('compareA').value,$('compareB').value];$('compareContent').innerHTML=keys.map(key=>{const t=byKey[key];if(!t)return empty('Team comparison awaits the next sync.');const ps=roster(key),r=rowFor(key),total=ps.reduce((a,p)=>a+num(season(p)),0);return `<article class="card hub-panel"><h3>${esc(t.name)}</h3><p>${esc(displayRecord(r))} adjusted · ${fmt(r?.points)} team points</p>${['QB','RB','WR','TE','K','DEF'].map(pos=>{const group=ps.filter(p=>p.position.split(',').includes(pos)),score=group.reduce((a,p)=>a+num(season(p)),0);return `<div class="hub-position"><strong><span>${pos} · ${group.length} players</span><span>${fmt(score)}</span></strong><i style="width:${total?Math.max(1,score/total*100):0}%"></i><span class="hub-sub">${group.map(p=>esc(p.name)).join(', ')||'No players'}</span></div>`}).join('')}</article>`}).join('');}
  $('compareA').onchange=renderCompare;$('compareB').onchange=renderCompare;renderCompare();renderHome();
  // Broaden the existing scoreboard to include scheduled weeks without changing custom standings.
  const schedule=hub.schedule||{}, weeks=[...new Set([...Object.keys(db.matchups||{}),...Object.keys(schedule)])].sort((a,b)=>a-b);
  $('matchupWeeks').innerHTML=weeks.map(w=>`<button class="year-btn" data-week="${esc(w)}">Week ${esc(w)}</button>`).join('');
  function renderSchedule(w){const games=schedule[w];$('matchupList').innerHTML=games?`<div class="hub-panel">${scores(games)}</div>`:(db.matchups?.[w]||[]).map(g=>`<div class="game"><span class="game-team">${esc(g[0])}</span><span class="game-score">${fmt(g[1])}</span><span class="versus">vs</span><span class="game-score">${fmt(g[3])}</span><span class="game-team">${esc(g[2])}</span></div>`).join('');$('matchupWeeks').querySelectorAll('button').forEach(b=>b.classList.toggle('active',b.dataset.week===w));$('matchupSourceNote').textContent='Yahoo matchup snapshot · '+date(hub.sections?.schedule?.updatedAt||db.yahoo?.lastUpdated);}
  $('matchupWeeks').querySelectorAll('button').forEach(b=>b.onclick=()=>renderSchedule(b.dataset.week));if(weeks.length)renderSchedule(weeks.includes(current)?current:weeks.at(-1));
  $('lockLeague').onclick=()=>location.reload();
};
