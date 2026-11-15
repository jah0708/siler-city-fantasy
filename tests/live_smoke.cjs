// Production-shape verification. No private values or screenshots are logged or uploaded.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:390,height:844}}), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  // Decrypt only in runner memory. Browser API fixture checks rendering; Yahoo
  // identity, session cryptography and denial are covered by the server tests.
  const db=JSON.parse(require('node:child_process').execFileSync('python',['-c',"import os,json,sys;sys.path.insert(0,'scripts');from secure_site import load_records;print(json.dumps(load_records(os.environ['YAHOO_CLIENT_SECRET'])))"],{encoding:'utf8',maxBuffer:8_000_000}));
  await page.route('**/api/league',route=>route.fulfill({json:db}));
  await page.goto('http://127.0.0.1:8766');
  await page.locator('#hubHome #allMatchups').waitFor();
  assert.equal(await page.locator('#favoriteTeam option').count(),10);
  for(const view of ['teams','players','compare','activity','standings','matchups','playoffs','draft','history']){
   await page.locator(`[data-view="${view}"]`).click();
   assert(await page.locator(`#${view}`).isVisible(),view+' view did not open');
  }
  await page.locator('[data-view="players"]').click();
  assert((await page.locator('#playerResults tbody tr').count())>=200,'Player import unexpectedly small');
  const stats=await page.locator('#playerResults td.num').allTextContents();
  assert(stats.some(s=>s!=='—'),'Season fantasy points missing');
  await page.locator('#playerResults [data-player]').first().click();await page.locator('#playerDialog[open]').waitFor();
  assert((await page.locator('#playerDialog dt').count())>1,'Player statistics missing');
  await page.locator('#closePlayer').click();
  await page.locator('[data-view="teams"]').click();
  assert((await page.locator('#teamContent tbody tr').count())>=10,'Current roster missing');
  assert((await page.locator('#teamContent td.num').allTextContents()).some(s=>s!=='—'),'Roster points missing');
  await page.locator('[data-view="draft"]').click();assert((await page.locator('#draftPicks tbody tr').count())>=100,'Draft results missing');
  await page.locator('[data-view="clubhouse"]').click();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Mobile page overflow');
  assert.deepEqual(errors,[]);
  console.log('PASS: server archive decrypted in runner memory; all ten views render; roster, season stats and draft populated; mobile width valid.');
 } finally {await browser.close()}
})().catch(()=>{console.error('Live clubhouse verification failed. See the named assertion in local reproduction; private page content is not logged.');process.exit(1)});
