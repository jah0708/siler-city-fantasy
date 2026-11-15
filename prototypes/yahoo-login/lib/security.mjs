import { EncryptJWT, jwtDecrypt } from 'jose';
import { pbkdf2 as derive, createDecipheriv } from 'node:crypto';
import { promisify } from 'node:util';
const pbkdf2=promisify(derive);
export const SESSION='__Host-scfl-session', TRANSACTION='__Host-scfl-oauth';
export function readSettings(env=process.env){
 const enabled=env.YAHOO_LOGIN_ENABLED==='true';
 if(!enabled)return {enabled:false};
 for(const name of ['APP_ORIGIN','YAHOO_CLIENT_ID','YAHOO_CLIENT_SECRET','YAHOO_SCOPES','SESSION_KEY','SCFL_SITE_PASSWORD','SCFL_LEAGUE_KEY'])if(!env[name])throw new Error('Login settings incomplete');
 const origin=new URL(env.APP_ORIGIN);
 if(origin.protocol!=='https:'||origin.origin!==env.APP_ORIGIN)throw new Error('APP_ORIGIN must be an HTTPS origin');
 const key=Buffer.from(env.SESSION_KEY,'base64');
 if(key.length!==32)throw new Error('SESSION_KEY must contain 32 random bytes');
 if(env.SCFL_SITE_PASSWORD.length<20)throw new Error('Invalid data key');
 if(!/^\d+\.l\.844486$/.test(env.SCFL_LEAGUE_KEY))throw new Error('Expected Siler City season-specific league key');
 const scopes=env.YAHOO_SCOPES.split(/[ ,]+/).filter(Boolean);
 if(!scopes.includes('openid')||scopes.length<2)throw new Error('OIDC and approved Fantasy Read scopes required');
 return {enabled:true,origin:origin.origin,key,clientId:env.YAHOO_CLIENT_ID,clientSecret:env.YAHOO_CLIENT_SECRET,scopes:scopes.join(' '),leagueKey:env.SCFL_LEAGUE_KEY,password:env.SCFL_SITE_PASSWORD,redirect:origin.origin+'/api/auth/callback'};
}
export async function seal(payload,key,purpose,seconds){return new EncryptJWT({...payload,purpose}).setProtectedHeader({alg:'dir',enc:'A256GCM'}).setIssuer('scfl-yahoo-prototype').setAudience(purpose).setIssuedAt().setExpirationTime(`${seconds}s`).encrypt(key)}
export async function unseal(token,key,purpose){
 if(!token||token.length>3800)return null;
 try{const {payload}=await jwtDecrypt(token,key,{issuer:'scfl-yahoo-prototype',audience:purpose,keyManagementAlgorithms:['dir'],contentEncryptionAlgorithms:['A256GCM']});return payload.purpose===purpose?payload:null}catch{return null}
}
export function cookie(request,name){const matches=(request.headers.get('cookie')||'').split(';').map(x=>x.trim()).filter(x=>x.startsWith(name+'='));return matches.length===1?matches[0].slice(name.length+1):null}
export function setCookie(name,value,seconds){return `${name}=${value}; Path=/; Max-Age=${seconds}; Secure; HttpOnly; SameSite=Lax`}
export function containsLeague(node,key){
 if(Array.isArray(node))return node.some(n=>containsLeague(n,key));
 if(!node||typeof node!=='object')return false;
 if(Object.hasOwn(node,'league_key')&&node.league_key===key)return true;
 return Object.values(node).some(n=>containsLeague(n,key));
}
export async function decryptSnapshot(payload,password){
 if(payload.version!==1||payload.kdf!=='PBKDF2-SHA256'||!Number.isInteger(payload.iterations)||payload.iterations<200000||payload.iterations>1000000)throw new Error('Invalid snapshot');
 const salt=Buffer.from(payload.salt,'base64'),iv=Buffer.from(payload.nonce,'base64'),cipher=Buffer.from(payload.ciphertext,'base64');
 if(salt.length!==16||iv.length!==12||cipher.length<16||cipher.length>4e6)throw new Error('Invalid snapshot');
 const key=await pbkdf2(password,salt,payload.iterations,32,'sha256');
 const decipher=createDecipheriv('aes-256-gcm',key,iv);decipher.setAAD(Buffer.from('scfl-data-v1'));decipher.setAuthTag(cipher.subarray(-16));
 const db=JSON.parse(Buffer.concat([decipher.update(cipher.subarray(0,-16)),decipher.final()]).toString('utf8'));
 if(!db.seasons||!Array.isArray(db.currentStandings))throw new Error('Incomplete snapshot');
 return db;
}
