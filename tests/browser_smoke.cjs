const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const db=JSON.parse(require('node:fs').readFileSync('/tmp/scfl-preview/fixture.json','utf8'));let signedIn=false;db.currentStandings[0].ties=1;db.currentStandings[0].weeks[0].result='T';db.hub.playoffs={enabled:true,startWeek:15,endWeek:17,teamsCount:6,weeks:{}};
 await page.route('**/api/**',async route=>{const path=new URL(route.request().url()).pathname;if(path==='/api/config')return route.fulfill({json:{enabled:true}});if(path==='/api/league')return route.fulfill({status:signedIn?200:401,json:signedIn?db:{error:'Sign in'}});if(path==='/api/auth/login'){signedIn=true;return route.fulfill({status:303,headers:{location:'/'}})}if(path==='/api/auth/logout'){assert.equal(route.request().method(),'POST');signedIn=false;return route.fulfill({status:303,headers:{location:'/'}})}return route.fulfill({status:404});});
 await page.goto('http://127.0.0.1:8765');await page.getByRole('link',{name:'Sign in with Yahoo',exact:true}).waitFor();assert.equal(await page.locator('input[type=password]').count(),0);assert.equal(await page.locator('main').isVisible(),false);
 await page.getByRole('link',{name:'Sign in with Yahoo',exact:true}).click();await page.locator('#hubHome #allMatchups').waitFor();
 await page.reload();await page.locator('#hubHome #allMatchups').waitFor();assert.equal(await page.locator('main').isVisible(),true);
 const standingsNav=page.locator('[data-view="standings"]');await standingsNav.focus();await standingsNav.press('Enter');
 assert.equal(await standingsNav.getAttribute('aria-current'),'page');assert.equal(await standingsNav.getAttribute('aria-controls'),'standings');
 assert.equal(await page.evaluate(()=>document.activeElement.closest('.view')?.id),'standings');
 const firstYear=page.locator('#standingYears button').first();const lastYear=page.locator('#standingYears button').last();
 assert.equal(await firstYear.getAttribute('aria-pressed'),'true');assert(!(await page.locator('#standings2018Note').isVisible()));await lastYear.focus();await lastYear.press('Enter');
 assert.equal(await lastYear.getAttribute('aria-pressed'),'true');assert.equal(await firstYear.getAttribute('aria-pressed'),'false');assert(await page.locator('#standings2018Note').isVisible());assert((await page.locator('#standings2018Note').textContent()).includes('playoff seeds may differ'));await firstYear.click();assert(!(await page.locator('#standings2018Note').isVisible()));
 await page.locator('[data-view="clubhouse"]').click();
 assert((await page.locator('#hubHome').textContent()).includes('Standings'));await page.locator('#allStandings').click();assert(await page.locator('#standingsBody tr').count()===10);assert(await page.locator('#standingsBreakdown').isVisible());assert.equal(await page.evaluate(()=>document.activeElement.id),'standingsBreakdown');const tieCell=page.locator('#standingsBody tr').first().locator('td').filter({hasText:/^T$/}).first();assert.equal(await tieCell.textContent(),'T');assert(!(await tieCell.getAttribute('class')||'').includes('result-loss'));assert.equal(await page.locator('#standingsSummary').count(),0);await page.locator('[data-view="clubhouse"]').click();await page.locator('#allMatchups').click();assert((await page.locator('#matchupList').textContent()).includes('Team'));await page.locator('[data-view="clubhouse"]').click();await page.screenshot({path:'test-results/clubhouse-desktop.png',fullPage:true});
 await page.locator('[data-view="matchups"]').click();
 await page.locator('#matchupWeeks [data-week="11"]').click();
 assert.deepEqual(await page.locator('#matchupList .hub-score').first().locator('b').allTextContents(), ['—','—'], 'scheduled scores should not be displayed as 0–0');
 await page.locator('[data-view="standings"]').click();
 await page.locator('#standingYears button').first().click();
 assert((await page.locator('#standingNote').textContent()).includes('standings update after the week is final'));
 const openView=async view=>{if(['teams','players','activity','draft','history'].includes(view))await page.locator('.nav-more > summary').click();await page.locator(`[data-view="${view}"]`).click()};
 for(const view of ['teams','players','activity','standings','matchups','playoffs','draft','history']){
  await openView(view);assert(await page.locator(`#${view}`).isVisible());
 }
 await openView('playoffs');assert(await page.locator('nav > .shell > [data-view="playoffs"]').isVisible());assert.equal(await page.locator('.playoff-race-rows > div').count(),10);assert((await page.locator('.playoff-cutoff').textContent()).includes('Top 6'));assert.equal(await page.locator('.playoff-cutoff').evaluate(el=>Array.from(el.parentElement.children).indexOf(el)),6);assert((await page.locator('#playoffBracket').textContent()).includes('actual Yahoo playoff seeds may differ'));assert((await page.locator('#playoffBracket').textContent()).includes('automatically'));await page.locator('#playoffYears [data-year="2025"]').click();assert((await page.locator('#playoffNote').textContent()).includes('2025'));
 // Yahoo-reported playoff matchups appear automatically after the data changes.
 db.hub.playoffs.weeks={'15':[{status:'postevent',playoffs:'1',isConsolation:false,teams:[{name:'Team 1',points:120.5},{name:'Team 2',points:99.25}]},{status:'postevent',playoffs:'1',isConsolation:true,teams:[{name:'Team 5',points:80},{name:'Team 6',points:70}]}],'16':[{status:'midevent',playoffs:null,isConsolation:null,teams:[{name:'Team 3',points:50},{name:'Team 4',points:40}]}]};
 await page.reload();await page.locator('#allMatchups').waitFor();await openView('playoffs');assert(await page.getByRole('heading',{name:'Yahoo postseason-week matchups'}).isVisible());assert((await page.locator('.playoff-week').first().textContent()).includes('Week 16'));assert((await page.locator('.playoff-week').first().textContent()).includes('Postseason-week matchup'));assert((await page.locator('.playoff-week').last().textContent()).includes('Consolation'));assert((await page.locator('.playoff-week').last().textContent()).includes('Team 1'));assert((await page.locator('.playoff-week').last().textContent()).includes('120.50'));assert((await page.locator('.playoff-week').last().textContent()).includes('99.25'));assert((await page.locator('.playoff-week').last().textContent()).includes('Final'));assert.equal(await page.locator('#playoffBracket > section').first().getAttribute('class'),'playoff-games');assert(await page.locator('.playoff-race').isVisible());
 await page.locator('.nav-more > summary').focus();await page.keyboard.press('Enter');assert(await page.locator('.nav-more').evaluate(el=>el.open));await page.keyboard.press('Escape');assert(!(await page.locator('.nav-more').evaluate(el=>el.open)));assert(await page.locator('.nav-more > summary').evaluate(el=>document.activeElement===el));
 await openView('players');assert(await page.getByRole('link',{name:/Add or trade players on Yahoo/}).isVisible());await page.locator('#playerSearch').fill('Player 2-0');assert.equal(await page.locator('#playerResults tbody tr').count(),1);
 await page.locator('#playerResults [data-player]').click();await page.locator('#playerDialog[open]').waitFor();await page.getByRole('button',{name:'Close',exact:true}).click();
 await page.locator('#playerSearch').fill('nobody xyz');assert.equal(await page.locator('#playerResults tbody tr').count(),0);
 await openView('teams');assert(await page.getByRole('link',{name:/Make roster moves on Yahoo/}).isVisible());await page.locator('#teamPicker').selectOption('t5');assert((await page.locator('#teamContent').textContent()).includes('Team 5'));await page.locator('#rosterWeek').selectOption('1');
 await openView('draft');await page.locator('#draftTeam').selectOption('t2');assert.equal(await page.locator('#draftPicks tbody tr').count(),1);
 await page.setViewportSize({width:390,height:844});await page.locator('[data-view="clubhouse"]').click();await page.screenshot({path:'test-results/clubhouse-mobile.png',fullPage:true});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'page must not overflow mobile');
 assert((await page.locator('[data-view="matchups"]').boundingBox()).height>=44,'navigation touch target too small');
 // A missing verified baseline must never reveal provisional standings, while historical seasons remain usable.
 db.yahoo.standingsAvailable=false;await page.reload();await page.locator('#allMatchups').waitFor();
 await page.locator('[data-view="standings"]').click();assert(await page.locator('#standingsUnavailable').isVisible());assert(!(await page.locator('#standingsTableWrap').isVisible()));assert.equal(await page.locator('#standingsBody tr').count(),0);
 await page.locator('#standingYears [data-year="2025"]').click();assert(!(await page.locator('#standingsUnavailable').isVisible()));assert(await page.locator('#standingsTableWrap').isVisible());assert.equal(await page.locator('#standingsBody tr').count(),10);
 await page.locator('#standingYears button').first().click();assert(await page.locator('#standingsUnavailable').isVisible());assert(!(await page.locator('#standingsTableWrap').isVisible()));
 delete db.yahoo.standingsAvailable;await page.reload();await page.locator('#allMatchups').waitFor();await page.locator('[data-view="standings"]').click();assert(await page.locator('#standingsUnavailable').isVisible());assert.equal(await page.locator('#standingsBody tr').count(),0);
 db.yahoo.standingsAvailable=true;await page.reload();await page.locator('#allMatchups').waitFor();
 await page.locator('.nav-more > summary').click();await page.locator('#lockLeague').click();await page.locator('#unlockPanel').waitFor();assert.equal(await page.locator('main').isVisible(),false);
 await page.reload();await page.locator('#unlockPanel').waitFor();assert.equal(await page.locator('main').isVisible(),false);
 assert.equal(await page.locator('input[type=password]').count(),0);
 await page.getByRole('link',{name:'Sign in with Yahoo',exact:true}).waitFor();
 await page.route('https://siler-city-login-trial.vercel.app/**',route=>route.fulfill({body:'Yahoo member site'}));await page.goto('http://127.0.0.1:8765/legacy.html?code=must-not-forward#old');await page.waitForURL('https://siler-city-login-trial.vercel.app/');assert.equal(page.url(),'https://siler-city-login-trial.vercel.app/');
 assert.deepEqual(errors,[]);console.log('PASS: Yahoo-only entry, all 10 views, player details, roster week, draft, refresh, sign-out and mobile.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
