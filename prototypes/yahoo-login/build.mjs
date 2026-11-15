import {readFile,writeFile,mkdir,copyFile,cp,rm} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../../',import.meta.url),out=new URL('./public/',import.meta.url);
const html=await readFile(new URL('web/league.html',root),'utf8');
if(!html.includes("fetch('/api/league'")||html.includes('id="unlockPassword"')||html.includes('league-data.enc.json'))throw Error('Unsafe league frontend');
// Rebuild from an allowlist so obsolete data and password files cannot survive.
await rm(out,{recursive:true,force:true});await mkdir(out,{recursive:true});
await writeFile(new URL('index.html',out),html);
await copyFile(new URL('scfl-logo.png',root),new URL('scfl-logo.png',out));
await cp(fileURLToPath(new URL('assets/',root)),fileURLToPath(new URL('assets/',out)),{recursive:true});
console.log('Built Yahoo-only league frontend; no league records or secrets included.');
