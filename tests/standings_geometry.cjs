// Regression for the standings table escaping the page and its sticky columns.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  const db=JSON.parse(fs.readFileSync('/tmp/scfl-preview/fixture.json','utf8'));
  db.currentStandings[0].name='Strive 4 Mediocrity — a very long fantasy team name';
  db.currentStandings[0].ties=1;
  db.currentStandings[0].weeks[0].result='T';
  // Include a sparse final week: its heading and score must not disappear.
  db.currentStandings[0].weeks.push({week:17,points:175.5,result:'W',pointResult:'P'});
  await page.route('**/api/**',route=>route.fulfill({json:new URL(route.request().url()).pathname==='/api/league'?db:{enabled:true}}));
  await page.goto('http://127.0.0.1:8765');
  await page.getByRole('button',{name:'Standings',exact:true}).click();
  assert.equal(await page.locator('#standingsBody tr').count(),10);
  assert((await page.locator('#standingsHead').innerText()).includes('Week 17'));
  assert((await page.locator('#standingsBody tr').first().locator('.adjusted-record').innerText()).endsWith('–1'));
  assert.equal(await page.locator('.result-chip[aria-label="Matchup: tie"]').count(),1);
  for(const width of [320,390,768,1440,2099]){
   await page.setViewportSize({width,height:1000});
   const before=await page.locator('#standingsTableWrap').evaluate(el=>{
    el.scrollLeft=0;const box=el.getBoundingClientRect();
    return {left:box.left,right:box.right,width:box.width,viewport:innerWidth,docWidth:document.documentElement.scrollWidth,scroll:el.scrollWidth,overflow:getComputedStyle(el).overflowX};
   });
   assert(before.docWidth<=width,`${width}: page must not scroll horizontally`);
   assert(before.left>=12&&before.right<=width-12,`${width}: table must respect both page gutters`);
   assert.equal(before.overflow,'auto');
   assert(before.scroll>before.width,`${width}: all 17 weeks must scroll within the table`);
   const team=page.locator('#standingsBody tr').first().locator('.team');
   const start=await team.boundingBox();
   await page.locator('#standingsTableWrap').evaluate(el=>el.scrollLeft=el.scrollWidth);
   const end=await team.boundingBox();
   assert(Math.abs(start.x-end.x)<1,`${width}: team must remain fixed while weeks scroll`);
   const last=await page.locator('#standingsBody tr').first().locator('.week-cell').last().boundingBox();
   assert(last.x+last.width<=before.right+1&&last.x>=end.x+end.width,`${width}: final week must be readable beside the sticky team`);
   assert.equal(await page.locator('#standingsBody tr').first().locator('.week-cell').last().locator('.week-score').innerText(),'175.50');
   await page.locator('#standingsTableWrap').evaluate(el=>el.scrollLeft=0);
   await page.screenshot({path:`test-results/standings-${width}.png`,fullPage:true});
  }
  await page.locator('#standingsTableWrap').focus();
  await page.keyboard.press('ArrowRight');
  await page.waitForFunction(()=>document.getElementById('standingsTableWrap').scrollLeft>0);
  await page.locator('#standingYears [data-year="2018"]').click();
  assert(await page.locator('#standings2018Note').isVisible());
  assert.equal(await page.locator('#standingsTableWrap').evaluate(el=>el.scrollLeft),0);
  console.log('PASS: standings contained at 320, 390, 768, 1440 and 2099px; sticky names, all weeks, ties, keyboard scrolling and season switching.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exit(1)});
