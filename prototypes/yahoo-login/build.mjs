import {readFile,writeFile,mkdir,copyFile,cp} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../../',import.meta.url), out=new URL('./public/',import.meta.url);
await mkdir(out,{recursive:true});
let html=await readFile(new URL('index.html',root),'utf8');
const start=html.indexOf('    async function unlockLeague(){'),end=html.indexOf('    async function initialize(){',start);
if(start<0||end<0)throw new Error('League page structure changed');
html=html.slice(0,start)+`    async function unlockLeague(){
      const panel=document.getElementById('unlockPanel');
      const result=await fetch('/api/league',{credentials:'same-origin',cache:'no-store'});
      if(result.ok){const db=await result.json();panel.hidden=true;document.body.classList.remove('locked');return db;}
      const config=await fetch('/api/config',{cache:'no-store'}).then(r=>r.ok?r.json():{enabled:false}).catch(()=>({enabled:false}));
      const errors={not_member:'This Yahoo account is not a member of Siler City. Try the account you use for the league.',cancelled:'Sign-in was cancelled. You can try again.',invalid_session:'Your sign-in expired. Please try again.',verification_failed:'We could not verify your league membership. Please try again.'};
      const error=new URLSearchParams(location.search).get('login_error');
      if(error)history.replaceState(null,'',location.pathname);
      document.getElementById('loginStatus').textContent=errors[error]||(!config.enabled?'This sign-in trial has not been connected to Yahoo yet.':result.status===503?'The league data is temporarily unavailable. Please try again.':'');
      document.getElementById('yahooLogin').hidden=!config.enabled;
      return new Promise(()=>{});
    }

`+html.slice(end);
const a=html.indexOf('<section class="unlock"'), b=html.indexOf('</section>',a)+10;
html=html.slice(0,a)+`<section class="unlock" id="unlockPanel"><div class="unlock-card"><img src="scfl-logo.png" alt="Siler City Fantasy League logo"><h1>Your league. Your Yahoo.</h1><p>Sign in with the Yahoo account you use for Siler City. Only league members can enter.</p><a id="yahooLogin" class="hub-btn" href="/api/auth/login" hidden>Sign in with Yahoo</a><p id="loginStatus" role="status" aria-live="polite"></p><p><a href="https://jah0708.github.io/siler-city-fantasy/">Use the current league site</a></p></div></section>`+html.slice(b);
html=html.replace('</head>','<style>#yahooLogin[hidden]{display:none}</style></head>');
html=html.replace('<script src="assets/hub.js"></script>',`<script src="assets/hub.js"></script><script>const initializeHub=window.initLeagueHub;window.initLeagueHub=db=>{initializeHub(db);document.getElementById('lockLeague').textContent='Sign out';document.getElementById('lockLeague').onclick=()=>{const form=document.createElement('form');form.method='POST';form.action='/api/auth/logout';document.body.appendChild(form);form.submit()}};</script>`);
await writeFile(new URL('index.html',out),html);
await copyFile(new URL('scfl-logo.png',root),new URL('scfl-logo.png',out));
await cp(fileURLToPath(new URL('assets/',root)),fileURLToPath(new URL('assets/',out)),{recursive:true});
// No data files, passwords, tokens, source .env files or API code are copied publicly.
console.log('Built the isolated Yahoo sign-in frontend; no league records included.');
