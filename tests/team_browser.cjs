// Compact directory, season isolation, keyboard selection, and roster-week regression.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  const db=JSON.parse(fs.readFileSync('/tmp/scfl-preview/fixture.json','utf8'));
  db.seasons['2025']=db.seasons['2025'].map((r,i)=>({...r,name:`Archived Coach ${i+1}`,points:2000+i,average:200+i,weeks:[{week:1,points:101+i,result:'W',pointResult:'P'},{week:2,points:99+i,result:'L',pointResult:'X'}]}));
  const weekOne=db.hub.rosters['1']['t5'];
  db.hub.rosters['1']['t5']=[{...weekOne[0],name:'Week one only player',points:42}];
  await page.route('**/api/**',route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/league'?db:{enabled:true}}));
  await page.goto('http://127.0.0.1:8765');
  await page.locator('.nav-more > summary').click();
  await page.getByRole('button',{name:'Teams and rosters',exact:true}).click();
  assert.equal(await page.locator('#teamDirectory [data-select-team]').count(),10);
  assert.equal(await page.locator('#teamPicker').count(),0,'team selection uses the directory table');
  await page.locator('#teamDirectory [data-select-team="t5"]').focus();
  await page.keyboard.press('Enter');
  assert((await page.locator('#teamIdentity').textContent()).includes('Team 5'));
  assert.equal(await page.locator('#teamDirectory [aria-pressed=true]').count(),1);
  assert.equal(await page.locator('#teamDirectory [data-select-team="t5"]').evaluate(el=>document.activeElement===el),true,'keyboard focus survives selection');
  await page.locator('#rosterWeek').selectOption('1');
  assert((await page.locator('.team-roster').textContent()).includes('Week one only player'));
  assert.equal(await page.locator('.team-roster tbody tr').count(),1);
  await page.locator('#rosterWeek').selectOption('10');
  assert.equal(await page.locator('.team-roster tbody tr').count(),16);
  assert.equal(await page.locator('.team-weekly').getAttribute('open'),null,'weekly detail is collapsed to keep the roster close');
  for(const width of [320,390,768,1440,2099]){
   await page.setViewportSize({width,height:1000});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width}: no horizontal page overflow`);
   const directory=await page.locator('.team-directory-panel').boundingBox(),detail=await page.locator('.team-detail').boundingBox();
   if(width>900){
    assert(directory.x+directory.width<=detail.x,`${width}: directory and detail stay beside each other`);
    assert(Math.abs(directory.y-detail.y)<5,`${width}: columns align at the top`);
    const first=await page.locator('.team-roster tbody tr').first().boundingBox();
    assert(first.y<550,`${width}: the compact roster begins high on the screen`);
   }else{
    assert(directory.y+directory.height<=detail.y,`${width}: directory stacks above the details`);
    assert(directory.height<245,`${width}: team selection remains compact`);
   }
   const rows=await page.locator('.team-roster tbody tr').all();
   assert((await rows[0].boundingBox()).height<=48,`${width}: roster rows remain compact`);
   await page.screenshot({path:`test-results/teams-${width}.png`,fullPage:true});
  }
  await page.locator('#teamYear').selectOption('2025');
  assert.equal(await page.locator('#teamTools').isVisible(),false);
  assert.equal(await page.locator('.team-roster').count(),0,'historical year never displays current players');
  assert((await page.locator('#teamIdentity').textContent()).includes('2025'));
  assert((await page.locator('#teamDirectory').textContent()).includes('Archived Coach'));
  await page.getByRole('button',{name:'Archived Coach 2',exact:true}).click();
  assert((await page.locator('#teamIdentity').textContent()).includes('Archived Coach 2'));
  assert((await page.locator('#teamContent .hub-metric').nth(1).textContent()).includes('2,001.00'));
  assert.equal(await page.locator('.team-weekly tbody tr').count(),2);
  assert(await page.locator('.team-archive-note').isVisible());
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:'test-results/teams-archive-mobile.png',fullPage:true});
  await page.locator('#teamYear').selectOption('2026');
  assert((await page.locator('#teamIdentity').textContent()).includes('Team 5'),'current selection survives year changes');
  assert.equal(await page.locator('.team-roster tbody tr').count(),16);
  await page.locator('#teamYear').selectOption('2025');
  assert((await page.locator('#teamIdentity').textContent()).includes('Archived Coach 2'),'archived selection survives year changes');
  await page.locator('#teamYear').selectOption('2018');
  assert((await page.locator('#teamContent').textContent()).includes('playoff seeds may differ'));
  assert.deepEqual(errors,[]);
  console.log('PASS: tabular team selection, five compact layouts, keyboard focus, roster weeks, year-scoped results and no current-player leakage into archives.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
