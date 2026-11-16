import test from 'node:test';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import {createHandler,applyHistoricalPlayoffPatch} from '../lib/handler.mjs';
import historicalPatch from '../lib/historical-playoff-patch.mjs';
import {seal,SESSION} from '../lib/security.mjs';
import {baseEnv} from './fixtures.mjs';

function encrypt(records,pair){
 const raw=pair.publicKey.export({format:'der',type:'spki'}).subarray(-32);
 const publicKey={version:1,algorithm:'X25519-HKDF-SHA256-A256GCM',public_key:raw.toString('base64'),key_id:createHash('sha256').update(raw).digest('hex').slice(0,16)};
 const child=spawnSync('python',['-c',"import json,sys;sys.path.insert(0,'../../scripts');from export_login_snapshot import encrypt_snapshot;v=json.load(sys.stdin);print(json.dumps(encrypt_snapshot(v['records'],v['public'])))"],{cwd:new URL('../',import.meta.url),input:JSON.stringify({records,public:publicKey}),encoding:'utf8'});
 assert.equal(child.status,0,child.stderr);return JSON.parse(child.stdout);
}
test('workbook correction is encrypted for the configured member key',()=>{
 const payload=historicalPatch;
 const pub=JSON.parse(readFileSync(new URL('../../../.github/login-trial-public-key.json',import.meta.url)));
 assert.equal(payload.key_id,pub.key_id);assert(!JSON.stringify(payload).includes('Stephen'));
});
test('historical patch applies all recorded seasons without altering the current season',()=>{
 const db={playoffs:Object.fromEntries(Array.from({length:9},(_,i)=>[2018+i,{champion:null}]))};
 const p=Object.fromEntries(Array.from({length:9},(_,i)=>[2018+i,{seeds:{A:1},champion:'A',finishes:[{place:1,name:'A'}],final:{team1:'A',score1:null},yahooArchive:null}]));
 assert.equal(applyHistoricalPlayoffPatch(db,p),db);
 for(let y=2018;y<=2025;y++){assert.equal(db.playoffs[y].seeds.A,1);assert.equal(db.playoffs[y].champion,'A');assert.equal(db.playoffs[y].finishes[0].name,'A');assert.equal(db.playoffs[y].final.score1,null);assert.equal(db.playoffs[y].yahooArchive,null);}
 assert.deepEqual(db.playoffs[2026],{champion:null});

});
test('authenticated responses merge the encrypted workbook patch; wrong keys do not block access',async()=>{
 const pair=generateKeyPairSync('x25519'),other=generateKeyPairSync('x25519');
 const env={...baseEnv,DATA_PRIVATE_KEY:pair.privateKey.export({format:'pem',type:'pkcs8'})};
 const records={seasons:{2018:[]},currentStandings:[],hub:{leagueKey:env.SCFL_LEAGUE_KEY},playoffs:{2018:{champion:null}}};
 const correction={2018:{seeds:{Example:1}}},snapshot=encrypt(records,pair);
 const token=await seal({subject:'test-member',leagueKey:env.SCFL_LEAGUE_KEY},Buffer.from(env.SESSION_KEY,'base64'),'member',3600);
 const request=()=>new Request(env.APP_ORIGIN+'/api/league',{headers:{cookie:SESSION+'='+token}});
 const serve=historicalPatch=>createHandler({env,historicalPatch,fetcher:async()=>Response.json(snapshot),yahooFactory:()=>({})});
 const anonymous=await serve(encrypt(correction,pair))(new Request(env.APP_ORIGIN+'/api/league'));
 assert.equal(anonymous.status,401);
 const updated=await serve(encrypt(correction,pair))(request());assert.equal(updated.status,200);
 assert.deepEqual((await updated.json()).playoffs[2018].seeds,{Example:1});
 const fallback=await serve(encrypt(correction,other))(request());assert.equal(fallback.status,200);
 assert.deepEqual((await fallback.json()).playoffs[2018],records.playoffs[2018]);
 const absent=await serve(null)(request());assert.equal(absent.status,200);
 assert.deepEqual((await absent.json()).playoffs[2018],records.playoffs[2018]);
});
