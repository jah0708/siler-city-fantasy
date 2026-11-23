// Overview presentation must preserve the snapshot and remain readable at each breakpoint.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const db=JSON.parse(fs.readFileSync('/tmp/scfl-preview/fixture.json','utf8'));
  const games=db.hub.schedule['10'];
  games[0].status='preevent';games[0].teams.forEach(t=>t.points=0);
  games[1].status='postevent';games[1].teams.forEach(t=>t.points=0);
  const longName='Strive 4 Mediocrity with a very long fantasy team name';
  const oldName=games[2].teams[0].name;
  games[2].teams[0].name=longName;
  db.currentStandings.find(t=>t.name===oldName).name=longName;
  db.hub.teams.find(t=>t.name===oldName).name=longName;
  db.currentStandings[0].ties=1;
  db.hub.transactions=Array.from({length:4},(_,i)=>({type:'add/drop',timestamp:String(1700000000+i),players:[{name:`Added Player ${i}`,type:'add',from:'Available pool',to:'Team 1'},{name:`Dropped Player ${i}`,type:'drop',from:'Team 1',to:'Available pool'}]}));
  await page.route('**/api/**',route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/league'?db:{enabled:true}}));
  await page.goto('http://127.0.0.1:8765');
  await page.locator('#allMatchups').waitFor();
  assert.equal(await page.locator('#hubHome .overview-game').count(),5);
  assert.equal(await page.locator('.overview-standings-table tbody tr').count(),10);
  assert.equal(await page.locator('.overview-move').count(),4);
  assert.deepEqual(await page.locator('.overview-game').nth(0).locator('b').allTextContents(),['—','—'],'scheduled zeroes remain unplayed');
  assert.deepEqual(await page.locator('.overview-game').nth(1).locator('b').allTextContents(),['0.00','0.00'],'final zeroes remain real scores');
  for(let i=0;i<db.currentStandings.length;i++){
   const row=db.currentStandings[i],actual=page.locator('.overview-standings-table tbody tr').nth(i);
   assert((await actual.innerText()).includes(row.name));
   assert.equal(await actual.locator('.overview-record').textContent(),`${row.adjustedWins}–${row.adjustedLosses}${row.ties?'–'+row.ties:''}`);
  }
  for(const t of db.hub.transactions)for(const p of t.players)assert((await page.locator('.overview-activity-list').textContent()).includes(p.name));
  for(const width of [320,390,768,1000,1440,2099]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width}: overview must not widen the page`);
   for(const card of await page.locator('.overview-game').all()){
    const sides=await card.locator('.hub-score-team').all(),left=await sides[0].boundingBox(),right=await sides[1].boundingBox();
    assert(Math.abs(left.y-right.y)<3&&left.x+left.width<=right.x,`${width}: opponents remain beside each other`);
    const scores=await card.locator('b').all(),a=await scores[0].boundingBox(),b=await scores[1].boundingBox();
    assert(Math.abs(a.y-b.y)<3,`${width}: paired scores stay aligned with long names`);
   }
   for(const row of await page.locator('.overview-standings-table tbody tr').all()){
    const name=await row.locator('th').boundingBox(),record=await row.locator('.overview-record').boundingBox();
    assert(name.x+name.width<=record.x+1,`${width}: standings names and records must not overlap`);
   }
   const match=await page.locator('.overview-scoreboard').boundingBox(),standings=await page.locator('.overview-standings').boundingBox();
   if(width>900)assert(match.x+match.width<=standings.x,`${width}: principal panels are side by side`);
   else assert(match.y+match.height<=standings.y,`${width}: panels stack cleanly`);
   await page.screenshot({path:`test-results/overview-${width}.png`,fullPage:true});
  }
  await page.locator('#allActivity').click();assert(await page.locator('#activity').isVisible());
  await page.getByRole('button',{name:'Overview',exact:true}).click();await page.locator('#allMatchups').click();assert(await page.locator('#matchups').isVisible());
  await page.getByRole('button',{name:'Overview',exact:true}).click();await page.locator('#allStandings').click();assert(await page.locator('#standings').isVisible());
  assert.deepEqual(errors,[]);
  console.log('PASS: overview at six widths; unchanged scores, records, transactions, paired alignment and working navigation.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
