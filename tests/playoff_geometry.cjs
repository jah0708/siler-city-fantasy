// Tournament regression: bounded boards, accurate paths, readable opponents, and honest outcomes.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const db=JSON.parse(fs.readFileSync('/tmp/scfl-preview/fixture.json','utf8'));
  const names=Array.from({length:10},(_,i)=>`Team ${i+1}`);
  names[4]='Strive 4 Mediocrity with a very long team name';
  const seeds=Object.fromEntries(names.map((n,i)=>[n,i+1]));
  const game=(a,b,x,y,label)=>({team1:names[a-1],team2:names[b-1],score1:x,score2:y,label});
  db.playoffs['2025']={seeds,champion:names[0],runnerUp:names[1],thirdPlace:names[2],quarterfinals:[game(4,5,105,127),game(3,6,146,107)],semifinals:[game(1,5,130,62),game(2,3,136,116)],final:game(1,2,149,89),placement:[game(3,5,162,78,'Third place'),game(4,6,134,138,'Fifth place')],consolation:{semifinals:[game(7,10,123,114),game(8,9,125,49)],placement:[game(7,8,77,72,'Seventh place'),game(9,10,134,82,'Ninth place')]},finishes:names.map((name,i)=>({name,place:i+1}))};
  for(const year of ['2024','2023']){db.seasons[year]=db.seasons['2025'];db.playoffs[year]={seeds,quarterfinals:[],semifinals:[],final:game(1,2,0,year==='2024'?null:0)}}
  await page.route('**/api/**',route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/league'?db:{enabled:true}}));
  await page.goto('http://127.0.0.1:8765');
  await page.getByRole('button',{name:'Playoffs',exact:true}).click();
  await page.locator('#playoffYears [data-year="2025"]').click();
  const board=page.locator('#playoffBracket > .bracket-section').first();
  const viewport=board.locator('.bracket-viewport');
  const plot=board.locator('.bracket');
  await page.waitForFunction(()=>document.querySelectorAll('#playoffBracket > .bracket-section:first-child .bracket-links path').length===4);
  assert.equal(await board.locator('.is-winner').count(),5,'every completed championship game has one winner');
  assert.equal(await page.locator('.playoff-finishes [role=row]').count(),11);
  const consolation=page.locator('.playoff-secondary .bracket-section').first();
  assert.equal(await consolation.locator('.bracket-game').count(),4);
  assert.equal(await consolation.locator('.bracket-links path').count(),2,'consolation links follow the recorded winners');
  for(const width of [320,390,768,1440,2099]){
   await page.setViewportSize({width,height:1000});
   await viewport.evaluate(el=>el.scrollLeft=0);
   await page.waitForFunction(()=>{const p=document.querySelector('#playoffBracket > .bracket-section:first-child .bracket');return Math.abs(p.querySelector('svg').viewBox.baseVal.width-p.getBoundingClientRect().width)<1});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width}: playoffs must not widen the page`);
   const region=await viewport.boundingBox();
   assert(region.x>=12&&region.x+region.width<=width-12,`${width}: bracket respects both page gutters`);
   const cards=await board.locator('.round').first().locator('.bracket-game').all();
   const a=await cards[0].boundingBox(),b=await cards[1].boundingBox();
   assert(a.y+a.height<b.y,`${width}: matchup cards must not overlap`);
   assert(a.x>=region.x&&a.x+a.width<=region.x+region.width,`${width}: first-round card fits within viewport`);
   const lines=await plot.evaluate(el=>{
    const bounds=el.getBoundingClientRect(),rounds=[...el.querySelectorAll(':scope > .round')];
    return [...el.querySelectorAll('svg path')].map(path=>{
     const [x1,y1,middle,y2,x2]=path.getAttribute('d').match(/-?\d+(?:\.\d+)?/g).map(Number);
     const source=[...rounds.flatMap(r=>[...r.querySelectorAll('.bracket-game')])].find(g=>{const b=g.getBoundingClientRect();return Math.abs(b.right-bounds.left-x1)<1&&Math.abs(b.top+b.height/2-bounds.top-y1)<1});
     const target=[...rounds.flatMap(r=>[...r.querySelectorAll('.bracket-game')])].find(g=>{const b=g.getBoundingClientRect();return Math.abs(b.left-bounds.left-x2)<1&&Math.abs(b.top+b.height/2-bounds.top-y2)<1});
     return {valid:!!(source&&target&&[target.dataset.team1,target.dataset.team2].includes(source.dataset.winner)),x1,x2};
    });
   });
   assert.equal(lines.length,4);assert(lines.every(l=>l.valid&&l.x1<l.x2),`${width}: lines connect the advancing winner to the next recorded opponent`);
   for(const row of await board.locator('.bracket-team').all()){
    const name=await row.locator('.team-label').boundingBox(),score=await row.locator('.bracket-score').boundingBox();
    assert(name.x+name.width<=score.x,`${width}: team and score must not overlap`);
   }
   await viewport.evaluate(el=>el.scrollLeft=el.scrollWidth);
   const final=await board.locator('.round-final .bracket-game').boundingBox();
   assert(final.x>=region.x&&final.x+final.width<=region.x+region.width+1,`${width}: final is fully reachable`);
   await viewport.evaluate(el=>el.scrollLeft=0);
   await page.screenshot({path:`test-results/playoffs-${width}.png`,fullPage:true});
  }
  await page.setViewportSize({width:390,height:844});
  await viewport.focus();await page.keyboard.press('ArrowRight');
  await page.waitForFunction(()=>document.querySelector('#playoffBracket .bracket-viewport').scrollLeft>0);
  for(const year of ['2024','2023']){
   await page.locator(`#playoffYears [data-year="${year}"]`).click();
   assert.equal(await page.locator('#playoffBracket .is-winner').count(),0,'missing or tied scores must never invent a winner');
   assert.equal(await page.locator('#playoffBracket .bracket-score').first().textContent(),'0.00','zero must remain a real score');
  }
  assert.deepEqual(errors,[]);
  console.log('PASS: playoff layouts at five widths; accurate advancement paths, winners, consolation, missing results, zeroes, ties and keyboard access.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
