// The two opponents must remain side by side at both desktop and phone widths.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');

(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:900}});
  const db=JSON.parse(fs.readFileSync('/tmp/scfl-preview/fixture.json','utf8'));
  await page.route('**/api/**',route=>{
   const path=new URL(route.request().url()).pathname;
   if(path==='/api/league')return route.fulfill({json:db});
   if(path==='/api/config')return route.fulfill({json:{enabled:true}});
   return route.fulfill({status:404});
  });
  await page.goto('http://127.0.0.1:8765');
  async function checkPair(selector,label){
   const teams=page.locator(`${selector} .hub-score`).first().locator('.hub-score-team');
   await teams.first().waitFor();assert.equal(await teams.count(),2,`${label}: expected two teams`);
   const left=await teams.nth(0).boundingBox(),right=await teams.nth(1).boundingBox();
   assert(left&&right,`${label}: both teams must be visible`);
   assert(Math.abs(left.y-right.y)<3,`${label}: opponents should share the same row`);
   assert(left.x+left.width<=right.x,`${label}: teams must not overlap`);
  }
  await checkPair('#hubHome','desktop overview');
  await page.getByRole('button',{name:'Matchups',exact:true}).click();
  await checkPair('#matchupList','desktop matchups');
  await page.setViewportSize({width:320,height:844});
  await checkPair('#matchupList','phone matchups');
  await page.getByRole('button',{name:'Overview',exact:true}).click();
  await checkPair('#hubHome','phone overview');
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'phone layout must not overflow');
  // A legacy snapshot may hold provisional standings. An explicit unavailable
  // flag must hide those numbers throughout the site while scores still render.
  Object.assign(db.currentStandings[0],{adjustedWins:9876,adjustedLosses:5432,points:876543.21,average:98765.43,weeks:[{week:1,points:98765.43}]});
  for(const availability of [undefined,false]){
   if(availability===undefined)delete db.yahoo.standingsAvailable;
   else db.yahoo.standingsAvailable=availability;
   await page.reload();
   await page.getByText('Completed standings unavailable; retrying after results are verified.').waitFor();
   assert.equal(await page.locator('#hubHome .hub-summary').count(),0);
  }
  await checkPair('#hubHome','unavailable standings overview');
  await page.locator('.nav-more summary').click();
  await page.getByRole('button',{name:'Teams and rosters',exact:true}).click();
  const metrics=await page.locator('#teamContent .hub-metric strong').allTextContents();
  assert.deepEqual(metrics.slice(0,3),['—','—','—'],'provisional team record and totals must be hidden');
  assert(!((await page.locator('#teamContent').textContent()).includes('98,765.43')),'provisional weekly chart must be hidden');
  console.log('PASS: opponents stay side by side; unverified standings remain hidden while matchups render.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
