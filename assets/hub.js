/* Private league dashboard: data arrives through the authenticated server. */
window.initLeagueHub = function(db) {
  'use strict';
  const hub=db.hub||{}, teams=hub.teams||[], byKey=Object.fromEntries(teams.map(t=>[t.key,t]));
  const $=id=>document.getElementById(id), esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt=v=>v==null?'—':Number(v).toLocaleString(undefined,{maximumFractionDigits:2,minimumFractionDigits:2});
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
  const standingsAvailable=db.yahoo?.standingsAvailable===true;
  // Historical snapshots can contain provisional records; never expose them as
  // current standings when a completed-week baseline has not been verified.
  const rowFor=key=>standingsAvailable?(db.currentStandings||[]).find(r=>r.name===byKey[key]?.name):undefined;
  const displayRecord=r=>r?`${r.adjustedWins??0}–${r.adjustedLosses??0}${r.ties?`–${r.ties}`:''}`:'—';
  function navigate(view){document.querySelector(`.nav-btn[data-view="${view}"]`)?.click();window.scrollTo({top:0,behavior:'instant'})}
  function wirePlayers(el){el.querySelectorAll('[data-player]').forEach(b=>b.onclick=()=>showPlayer(b.dataset.player))}
  function table(headers,rows){return `<div class="card hub-table-wrap"><table class="hub-table"><thead><tr>${headers.map(h=>`<th>${h}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></div>`}
  function scores(games){return games.length?games.map(g=>`<div class="hub-score"><small>${esc(g.status==='postevent'?'Final':g.status==='midevent'?'In progress':g.status==='saved'?'Saved results':'Scheduled')}</small><div class="hub-score-pair">${g.teams.slice(0,2).map((t,i)=>`${i?'<span class="hub-score-versus">vs</span>':''}<div class="hub-score-team ${i?'hub-score-away':'hub-score-home'}"><strong>${esc(t.name)}</strong><b>${g.status==='preevent' && Number(t.points)===0 ? '—' : fmt(t.points)}</b></div>`).join('')}</div></div>`).join(''):empty('No matchup data saved for this week.')}
  function moves(list){return list.length?list.map(t=>`<article class="hub-move"><div class="hub-move-head">${badge(t.type)}<small>${esc(date(Number(t.timestamp)*1000))}</small></div>${t.players.map(p=>`<p><strong>${esc(p.name)}</strong>${badge(p.type)}<span class="hub-sub">${esc(p.from||'Available pool')} → ${esc(p.to||'Available pool')}</span></p>`).join('')}</article>`).join(''):empty('No completed transactions in this snapshot.')}
  const schedule=hub.schedule||{};
  function matchupGames(week){
    const scheduled=schedule[week]||[], stored=db.matchups?.[week]||[];
    const complete=scheduled.length===5 && new Set(scheduled.flatMap(g=>(g.teams||[]).map(t=>t.name))).size===10;
    const scheduleTime=Date.parse(hub.sections?.schedule?.updatedAt||'')||0;
    const scoreTime=Date.parse(db.yahoo?.lastUpdated||'')||0;
    if(complete && (scheduleTime>=scoreTime || stored.length!==5)) return {games:scheduled, source:'schedule'};
    if(stored.length===5) return {games:stored.map(g=>({status:'saved',teams:[{name:g[0],points:g[1]},{name:g[2],points:g[3]}]})),source:'scores'};
    return {games:scheduled,source:'schedule'};
  }
  const activity=(hub.transactions||[]).slice().sort((a,b)=>Number(b.timestamp||0)-Number(a.timestamp||0));
  function teamMark(name){
    const words=String(name||'Team').replace(/([a-z])([A-Z])/g,'$1 $2').replace(/[^a-z0-9]+/gi,' ').trim().split(/\s+/);
    const letters=(words.length>1?words[0][0]+words.at(-1)[0]:words[0].slice(0,2)).toUpperCase();
    const tone=[...String(name||'')].reduce((sum,c)=>sum+c.charCodeAt(0),0)%6;
    return `<span class="overview-team-mark tone-${tone}" aria-hidden="true">${esc(letters)}</span>`;
  }
  function homeScores(games){
    return games.length?games.map(g=>`<article class="hub-score overview-game"><div class="overview-game-meta"><small class="${g.status==='midevent'?'is-progress':''}">${esc(g.status==='postevent'?'Final':g.status==='midevent'?'In progress':g.status==='saved'?'Saved results':'Scheduled')}</small></div><div class="hub-score-pair">${(g.teams||[]).slice(0,2).map((t,i)=>`${i?'<span class="hub-score-versus">vs</span>':''}<div class="hub-score-team ${i?'hub-score-away':'hub-score-home'}"><span class="overview-team-name">${teamMark(t.name)}<strong>${esc(t.name)}</strong></span><b>${g.status==='preevent'&&Number(t.points)===0?'—':fmt(t.points)}</b></div>`).join('')}</div></article>`).join(''):empty('No matchup data saved for this week.');
  }
  function homeMoves(list){
    return list.length?`<div class="overview-activity-list">${list.map(t=>`<article class="overview-move"><div class="overview-move-meta"><span class="overview-move-kind">${esc(t.type==='add/drop'?'Add / drop':t.type==='trade'?'Trade':t.type==='drop'?'Drop':'Add')}</span><time>${esc(date(Number(t.timestamp)*1000))}</time></div><div class="overview-move-players">${(t.players||[]).map(p=>`<div class="overview-player-move"><span class="overview-move-icon ${p.type==='drop'?'is-drop':''}" aria-hidden="true">${p.type==='drop'?'−':p.type==='add'?'+':'↔'}</span><div><strong>${esc(p.name)}</strong><span class="overview-move-direction">${esc(p.from||'Available pool')} → ${esc(p.to||'Available pool')}</span></div><span class="sr-only">${esc(p.type||'')}</span></div>`).join('')}</div></article>`).join('')}</div>`:empty('No completed transactions in this snapshot.');
  }
  function renderHome(){
    const rows=standingsAvailable?(db.currentStandings||[]):[];
    const match=matchupGames(current), last=match.source==='schedule'?hub.sections?.schedule?.updatedAt:db.yahoo?.lastUpdated;
    $('hubHome').innerHTML=`<header class="overview-heading"><div><h2>League overview</h2><p>${esc(db.currentSeason||'2026')} season${teams.length?' · '+teams.length+' teams':''}</p></div><div class="overview-heading-tools"><div class="hub-status overview-refresh"><span class="overview-refresh-mark" aria-hidden="true">↻</span><div><strong>Updated ${esc(date(last))}</strong><span>Refreshes about every 3 hours</span></div></div><a class="overview-yahoo" href="https://football.fantasysports.yahoo.com/f1/844486" target="_blank" rel="noopener noreferrer">Manage team on Yahoo ↗</a></div></header>
    <div class="hub-intro overview-grid"><section class="overview-panel overview-scoreboard" aria-labelledby="overviewMatchupsTitle"><div class="overview-panel-head"><div><h3 id="overviewMatchupsTitle">Week ${esc(current)} matchups</h3><p>Scores may change while games are in progress.</p></div><button class="hub-btn" id="allMatchups">All weeks →</button></div><div class="overview-games">${homeScores(match.games)}</div>${match.source==='schedule'?`<div class="overview-panel-foot">${note('schedule')}</div>`:''}</section>
    <section class="overview-panel overview-standings" aria-labelledby="overviewStandingsTitle"><div class="overview-panel-head"><div><h3 id="overviewStandingsTitle">Standings</h3><p>${standingsAvailable?'Through Week '+esc(db.yahoo?.week||'—')+' · Completed weeks':'Awaiting verified final results'}</p></div><button class="hub-btn" id="allStandings">Full standings →</button></div>${standingsAvailable?`<div class="hub-summary"><table class="overview-standings-table"><caption class="sr-only">Current adjusted standings</caption><thead><tr><th scope="col"><span class="sr-only">Rank</span>#</th><th scope="col">Team</th><th scope="col">Record</th><th scope="col">Points</th></tr></thead><tbody>${rows.map(t=>`<tr><td><span class="overview-rank ${Number(t.rank)===1?'is-first':''}">${esc(t.rank)}</span></td><th scope="row"><span class="overview-standing-team">${teamMark(t.name)}<span>${esc(t.name)}</span></span></th><td class="overview-record">${esc(displayRecord(t))}</td><td class="overview-points">${fmt(t.points)}</td></tr>`).join('')}</tbody></table></div><div class="overview-panel-foot overview-standings-note">Adjusted record = matchup wins + top-half scoring wins. Updates after the week is final; later corrections may change results.</div>`:'<p class="hub-empty">Completed standings unavailable; retrying after results are verified.</p>'}</section></div>
    <section class="overview-panel overview-activity" aria-labelledby="overviewActivityTitle"><div class="overview-panel-head"><div><h3 id="overviewActivityTitle">Latest league moves</h3><p>Completed adds, drops, and trades.</p></div><button class="hub-btn" id="allActivity">View activity →</button></div>${homeMoves(activity.slice(0,4))}<div class="overview-panel-foot">${note('transactions')}</div></section>`;
    $('allMatchups').onclick=()=>navigate('matchups');$('allStandings').onclick=()=>window.openStandingsBreakdown();$('allActivity').onclick=()=>navigate('activity');
  }
  const currentSeason=String(db.currentSeason||'2026');
  const teamYears=[...new Set([currentSeason,...Object.keys(db.seasons||{})])].filter(y=>/^\d{4}$/.test(y)).sort((a,b)=>Number(b)-Number(a));
  let teamYear=currentSeason;
  const selectedTeams={[currentSeason]:favorite};
  $('teamYear').innerHTML=teamYears.map(y=>`<option value="${esc(y)}">${esc(y)}</option>`).join('');
  $('teamYear').value=teamYear;
  $('teamTools').innerHTML=select('rosterWeek','Roster week',rosterWeeks.map(w=>`<option value="${esc(w)}">Week ${esc(w)}</option>`).join(''));
  function teamEntries(){
    if(teamYear===currentSeason)return teams.map(t=>({...t,row:rowFor(t.key)})).sort((a,b)=>(a.row?.rank??99)-(b.row?.rank??99));
    return (db.seasons?.[teamYear]||[]).map((row,i)=>({key:`archive-${teamYear}-${i}`,name:row.name,managers:[],row}));
  }
  function renderTeamDirectory(){
    const scrollTop=$('teamDirectory').querySelector('.team-directory-scroll')?.scrollTop||0;
    const entries=teamEntries();
    if(!entries.some(t=>t.key===selectedTeams[teamYear]))selectedTeams[teamYear]=entries[0]?.key||'';
    $('teamDirectory').innerHTML=entries.length?`<div class="team-directory-scroll"><table class="team-picker-table" aria-label="Choose a team for ${esc(teamYear)}"><thead><tr><th scope="col">#</th><th scope="col">Team</th><th scope="col">Record</th><th scope="col">Points</th></tr></thead><tbody>${entries.map(t=>`<tr data-team-key="${esc(t.key)}" class="${t.key===selectedTeams[teamYear]?'is-selected':''}"><td>${esc(t.row?.rank??'—')}</td><th scope="row"><button type="button" data-select-team="${esc(t.key)}" aria-pressed="${t.key===selectedTeams[teamYear]}">${esc(t.name)}</button></th><td>${esc(displayRecord(t.row))}</td><td>${fmt(t.row?.points)}</td></tr>`).join('')}</tbody></table></div>`:empty('No teams are saved for this year.');
    const scroller=$('teamDirectory').querySelector('.team-directory-scroll');if(scroller)scroller.scrollTop=scrollTop;
    renderTeam();requestAnimationFrame(scrollSelectedTeam);
  }
  function scrollSelectedTeam(){
    const panel=$('teamDirectory').querySelector('.team-directory-scroll'),row=panel?.querySelector('.is-selected');
    if(!panel?.clientHeight||!row)return;
    const p=panel.getBoundingClientRect(),r=row.getBoundingClientRect(),head=panel.querySelector('thead').getBoundingClientRect().height;
    if(r.top<p.top+head)panel.scrollTop-=p.top+head-r.top;else if(r.bottom>p.bottom)panel.scrollTop+=r.bottom-p.bottom;
  }
  new ResizeObserver(()=>requestAnimationFrame(scrollSelectedTeam)).observe($('teamDirectory'));
  function weeklyResults(points,open=false){
    if(!points.length)return '';
    return `<details class="team-weekly" ${open?'open':''}><summary>Weekly results <span>${points.length} completed weeks</span></summary>${table(['Week','Score','Matchup','Top half'],points.map(w=>`<tr><th scope="row">${esc(w.week)}</th><td class="num">${fmt(w.points)}</td><td>${esc(w.result||'—')}</td><td>${esc(w.pointResult==='P'?'Yes':w.pointResult==='X'?'No':'—')}</td></tr>`).join(''))}</details>`;
  }
  function renderTeam(){
    const archived=teamYear!==currentSeason, team=teamEntries().find(t=>t.key===selectedTeams[teamYear]);
    $('teamTools').hidden=archived;
    if(!team){$('teamIdentity').innerHTML='';$('teamContent').innerHTML=empty('Team profiles will appear after the next successful roster sync.');return}
    const week=$('rosterWeek').value||current, ps=archived?[]:roster(team.key,week), row=team.row;
    const points=(row?.weeks||[]).slice().sort((a,b)=>Number(a.week)-Number(b.week));
    const average=row?.average??(points.length?points.reduce((sum,w)=>sum+Number(w.points||0),0)/points.length:null);
    $('teamIdentity').innerHTML=`<div class="hub-team-title">${archived?'':image(team.logo,'hub-team-logo')}<div><h3>${esc(team.name)}</h3><p>${esc(teamYear)}${team.managers?.length?' · '+esc(team.managers.join(' · ')):archived?' · Season archive':''}</p></div></div>`;
    const metrics=`<div class="hub-metrics">${metric('Adjusted record',displayRecord(row))}${metric('Season points',fmt(row?.points))}${metric('Weekly average',fmt(average))}${archived?metric('Season rank',row?.rank??'—'):metric('Roster alerts',ps.filter(p=>p.status).length)}</div>`;
    if(archived){
      $('teamContent').innerHTML=metrics+`<p class="team-archive-note">Player rosters were not saved for ${esc(teamYear)}. These are the recorded regular-season results.</p>`+weeklyResults(points,true)+(teamYear==='2018'?'<p class="hub-sub">2018 rankings follow the original regular-season order; recorded playoff seeds may differ.</p>':'');
      return;
    }
    const slots=ps.slice().sort((a,b)=>['BN','IR','IR+'].includes(a.slot)-['BN','IR','IR+'].includes(b.slot));
    $('teamContent').innerHTML=metrics+(standingsAvailable?weeklyResults(points):'<p class="hub-empty">Completed standings unavailable; retrying after results are verified.</p>')+`<div class="team-roster-head"><h3>Week ${esc(week)} roster</h3><span>${ps.length} players</span></div><div class="team-roster">${ps.length?table(['Slot','Player','NFL','Week points','Season points','Bye'],slots.map(p=>`<tr><td>${badge(p.slot)}</td><td><div class="roster-player">${image(p.image)}<span>${playerLink(p)}${badge(p.status,true)}<small class="roster-position">${esc(p.position)}</small></span></div></td><td>${esc(p.nflTeam)}</td><td class="num">${fmt(p.points)}</td><td class="num">${fmt(season(p))}</td><td>${esc(p.bye||'—')}</td></tr>`).join('')):empty('This roster has not been imported yet.')}</div>${note('rosters')}<p class="hub-sub team-score-note">Week points follow the selected week. Season points use the latest snapshot.</p>`;
    wirePlayers($('teamContent'));
  }
  $('teamDirectory').onclick=event=>{
    const row=event.target.closest('tr[data-team-key]');if(!row)return;
    selectedTeams[teamYear]=row.dataset.teamKey;
    if(teamYear===currentSeason){favorite=row.dataset.teamKey;try{localStorage.setItem('scfl-favorite-team',favorite)}catch{}}
    renderTeamDirectory();
    if(event.detail===0)[...$('teamDirectory').querySelectorAll('button')].find(b=>b.dataset.selectTeam===selectedTeams[teamYear])?.focus({preventScroll:true});
  };
  $('teamYear').onchange=()=>{teamYear=$('teamYear').value;renderTeamDirectory()};
  $('rosterWeek').onchange=renderTeam;
  renderTeamDirectory();
  let pool=[];const seen=new Set();
  teams.forEach(t=>roster(t.key).forEach(p=>{pool.push({...p,owner:t.name,available:false,season:season(p)});seen.add(p.key)}));
  (hub.available||[]).forEach(p=>{if(!seen.has(p.key))pool.push({...p,owner:p.ownership==='waivers'?'Waivers':'Available',available:true,season:p.points})});
  $('playerTools').innerHTML='<label>Find a player<input id="playerSearch" type="search" placeholder="Name, NFL team, or fantasy team"></label>'+select('playerPosition','Position','<option value="">All positions</option>'+['QB','RB','WR','TE','K','DEF'].map(p=>`<option>${p}</option>`).join(''))+select('playerOwner','Pool','<option value="all">All imported players</option><option value="available">Available / waivers</option><option value="rostered">On a roster</option>')+select('playerSort','Sort','<option value="points">Season points</option><option value="name">Player name</option>');
  function renderPlayers(){const q=$('playerSearch').value.trim().toLowerCase(),pos=$('playerPosition').value,owner=$('playerOwner').value;
    const filtered=pool.filter(p=>(!q||[p.name,p.nflTeam,p.owner].join(' ').toLowerCase().includes(q))&&(!pos||p.position.split(',').includes(pos)||p.eligible?.includes(pos))&&(owner==='all'||p.available===(owner==='available'))).sort((a,b)=>$('playerSort').value==='name'?a.name.localeCompare(b.name):(b.season??-Infinity)-(a.season??-Infinity));
    $('playerCount').textContent=`${filtered.length} players · current rosters + up to 200 available players by season points`;
    $('playerResults').innerHTML=filtered.length?table(['Player','NFL','Fantasy team / availability','Season points','Bye'],filtered.map(p=>`<tr><td>${image(p.image)}${playerLink(p)}${badge(p.status,true)}<span class="hub-sub">${esc(p.position)}</span></td><td>${esc(p.nflTeam)}</td><td>${esc(p.owner)}</td><td class="num">${fmt(p.season)}</td><td>${esc(p.bye||'—')}</td></tr>`).join('')):empty('No players match these filters. Try another name or position.');wirePlayers($('playerResults'));$('playerFreshness').innerHTML=note('available')+note('playerStats');}
  ['playerSearch','playerPosition','playerOwner','playerSort'].forEach(id=>$(id).addEventListener(id==='playerSearch'?'input':'change',renderPlayers));renderPlayers();
  function showPlayer(key){const historical=Object.values(hub.rosters||{}).flatMap(week=>Object.values(week).flat()).find(p=>p.key===key);const p=pool.find(p=>p.key===key)||hub.playerStats?.[key]||historical;if(!p)return;const stats=hub.playerStats?.[key]||(!historical||pool.some(x=>x.key===key)?p:{});
    $('playerDialogBody').innerHTML=`<header><div><p class="eyebrow">Player detail</p><h2>${esc(p.name)}</h2></div><button class="hub-btn" id="closePlayer">Close</button></header><p>${esc(p.position)} · ${esc(p.nflTeam)} ${badge(p.statusNote||p.status,true)}</p><p>${esc(p.owner||'')} · Bye: ${esc(p.bye||'—')}</p><h3>Season statistics</h3><dl><dt>Fantasy points</dt><dd>${fmt(p.season??stats.points)}</dd>${Object.entries(stats.stats||{}).filter(([id])=>hub.statCategories?.[id]).map(([id,v])=>`<dt>${esc(hub.statCategories[id])}</dt><dd>${esc(v)}</dd>`).join('')}</dl><p class="hub-sub">Actual results from the latest Yahoo snapshot. These are not projections.</p>`;
    $('closePlayer').onclick=()=>$('playerDialog').close();$('playerDialog').showModal();}
  $('activityTools').innerHTML=select('activityKind','Transaction type','<option value="">All completed moves</option><option value="trade">Trades</option><option value="add">Adds</option><option value="drop">Drops</option>')+'<label>Search activity<input id="activitySearch" type="search" placeholder="Player or team"></label>';
  function renderActivity(){const kind=$('activityKind').value,q=$('activitySearch').value.toLowerCase();const list=activity.filter(t=>(!kind||t.type.includes(kind))&&(!q||JSON.stringify(t.players).toLowerCase().includes(q)));$('activityContent').innerHTML=moves(list)+note('transactions');}
  $('activityKind').onchange=renderActivity;$('activitySearch').oninput=renderActivity;renderActivity();
  $('draftTools').innerHTML=select('draftTeam','Team','<option value="">All teams</option>'+teamOptions)+select('draftRound','Round','<option value="">All rounds</option>'+[...new Set((hub.draft||[]).map(p=>p.round))].sort((a,b)=>a-b).map(r=>`<option value="${esc(r)}">Round ${esc(r)}</option>`).join(''));
  function renderDraft(){const picks=(hub.draft||[]).filter(p=>(!$('draftTeam').value||p.teamKey===$('draftTeam').value)&&(!$('draftRound').value||String(p.round)===$('draftRound').value));$('draftPicks').innerHTML=picks.length?table(['Pick','Round','Player','Position','Team'],picks.map(p=>`<tr><td>${esc(p.pick)}</td><td>${esc(p.round)}</td><td><strong>${esc(p.name)}</strong></td><td>${badge(p.position)}</td><td>${esc(byKey[p.teamKey]?.name||'Unknown team')}</td></tr>`).join('')):empty('No draft picks available for these filters.');$('draftFreshness').innerHTML=note('draft');}
  $('draftTeam').onchange=renderDraft;$('draftRound').onchange=renderDraft;renderDraft();
  renderHome();
  // Broaden the existing scoreboard to include scheduled weeks without changing custom standings.
  const weeks=[...new Set([...Object.keys(db.matchups||{}),...Object.keys(schedule)])].sort((a,b)=>a-b);
  $('matchupWeeks').innerHTML=weeks.map(w=>`<button class="year-btn" data-week="${esc(w)}">Week ${esc(w)}</button>`).join('');
  function renderSchedule(w){const result=matchupGames(w), stamp=result.source==='schedule'?hub.sections?.schedule?.updatedAt:db.yahoo?.lastUpdated;
    $('matchupList').innerHTML=`<div class="hub-panel">${scores(result.games)}${result.source==='schedule'?note('schedule'):''}</div>`;
    $('matchupWeeks').querySelectorAll('button').forEach(b=>{const active=b.dataset.week===w;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
    $('matchupSourceNote').textContent=(result.source==='scores'?'Saved scoreboard':'Yahoo matchup snapshot')+' · '+date(stamp)+' · Scores may change while games are in progress';
  }
  $('matchupWeeks').querySelectorAll('button').forEach(b=>b.onclick=()=>renderSchedule(b.dataset.week));
  if(weeks.length){const selected=weeks.includes(current)?current:weeks.at(-1);renderSchedule(selected);requestAnimationFrame(()=>{const row=$('matchupWeeks'),btn=row.querySelector('.active');if(btn) row.scrollLeft=btn.offsetLeft-row.offsetLeft-Math.max(0,(row.clientWidth-btn.offsetWidth)/2)});}
  $('lockLeague').textContent='Sign out';
  $('lockLeague').onclick=()=>{const form=document.createElement('form');form.method='POST';form.action='/api/auth/logout';document.body.appendChild(form);form.submit()};
};
