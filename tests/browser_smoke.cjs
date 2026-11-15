const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8765');await page.locator('#unlockPassword').fill('wrong-password-long-enough');await page.locator('#unlockForm button').click();await page.getByText('Unable to unlock. Check the password and try again.').waitFor();
 assert.equal(await page.locator('main').isVisible(),false);
 await page.locator('#unlockPassword').fill('local-preview-only-password-2026');await page.locator('#unlockForm button').click();await page.locator('#hubHome .hub-feature').waitFor();
 await page.screenshot({path:'test-results/clubhouse-desktop.png',fullPage:true});
 for(const view of ['teams','players','compare','activity','standings','matchups','playoffs','draft','history']){
  await page.locator(`[data-view="${view}"]`).click();assert(await page.locator(`#${view}`).isVisible());
 }
 await page.locator('[data-view="players"]').click();await page.locator('#playerSearch').fill('Player 2-0');assert.equal(await page.locator('#playerResults tbody tr').count(),1);
 await page.locator('#playerResults [data-player]').click();await page.locator('#playerDialog[open]').waitFor();await page.getByRole('button',{name:'Close',exact:true}).click();
 await page.locator('#playerSearch').fill('nobody xyz');assert.equal(await page.locator('#playerResults tbody tr').count(),0);
 await page.locator('[data-view="teams"]').click();await page.locator('#teamPicker').selectOption('t5');assert((await page.locator('#teamContent').textContent()).includes('Team 5'));await page.locator('#rosterWeek').selectOption('1');
 await page.locator('[data-view="draft"]').click();await page.locator('#draftTeam').selectOption('t2');assert.equal(await page.locator('#draftPicks tbody tr').count(),1);
 await page.setViewportSize({width:390,height:844});await page.locator('[data-view="clubhouse"]').click();await page.screenshot({path:'test-results/clubhouse-mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'page must not overflow mobile');
 await page.locator('#lockLeague').click();await page.locator('#unlockPanel').waitFor();assert.equal(await page.locator('main').isVisible(),false);
 assert.deepEqual(errors,[]);console.log('PASS: password gate, all 10 views, player search/details, roster week, draft filtering, lock, mobile width, no JS errors.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
