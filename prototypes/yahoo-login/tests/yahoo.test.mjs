import test from 'node:test';import assert from 'node:assert/strict';import {generateKeyPair,exportJWK,SignJWT} from 'jose';
import {createYahoo} from '../lib/yahoo.mjs';import {baseEnv} from './fixtures.mjs';import {readSettings} from '../lib/security.mjs';
const issuer='https://api.login.yahoo.com',settings=readSettings(baseEnv);
async function provider(mode='valid'){
 const {publicKey,privateKey}=await generateKeyPair('RS256'),other=await generateKeyPair('RS256');
 const jwk={...await exportJWK(publicKey),kid:'test',use:'sig',alg:'RS256'};let nonce;const paths=[];
 const fetcher=async(input,options={})=>{
  const url=String(input instanceof Request?input.url:input);paths.push(url);
  if(url.endsWith('/.well-known/openid-configuration'))return Response.json({issuer,authorization_endpoint:issuer+'/oauth2/request_auth',token_endpoint:issuer+'/oauth2/get_token',jwks_uri:issuer+'/jwks',response_types_supported:['code'],subject_types_supported:['public'],id_token_signing_alg_values_supported:['RS256'],token_endpoint_auth_methods_supported:['client_secret_basic'],code_challenge_methods_supported:['S256']});
  if(url.endsWith('/jwks'))return Response.json({keys:[jwk]});
  if(url.endsWith('/oauth2/get_token')){
   const body=new URLSearchParams(options.body);assert(body.get('code_verifier'));assert.equal(body.get('redirect_uri'),settings.redirect);
   const jwt=await new SignJWT({nonce:mode==='nonce'?'wrong':nonce}).setProtectedHeader({alg:'RS256',kid:'test'}).setIssuer(mode==='issuer'?'https://attacker.example':issuer).setAudience(mode==='audience'?'wrong-client':settings.clientId).setSubject('test-member').setIssuedAt().setExpirationTime(mode==='expired'?Math.floor(Date.now()/1000)-120:'1h').sign(mode==='signature'?other.privateKey:privateKey);
   return Response.json({access_token:'test-access-token',refresh_token:'never-persist-this',id_token:jwt,token_type:'Bearer',expires_in:3600});
  }
  if(url.startsWith('https://fantasysports.yahooapis.com/')){
   assert(url.includes('/users;use_login=1/games;game_keys=999/leagues'));
   assert.equal(options.headers.Authorization,'Bearer test-access-token');
   return Response.json({users:[{games:[{leagues:[{league:[{league_key:mode==='nonmember'?'999.l.123':settings.leagueKey}]}]}]}]});
  }
  throw new Error('Unexpected endpoint');
 };
 const yahoo=createYahoo(settings,fetcher);const start=await yahoo.begin();nonce=new URL(start.url).searchParams.get('nonce');return {yahoo,start,paths};
}
function callback(state){return new URL(settings.redirect+'?code=one-use-code&state='+state)}
test('OIDC verifies signed Yahoo identity and user-scoped membership with PKCE',async()=>{const {yahoo,start}=await provider();const url=new URL(start.url);assert.equal(url.searchParams.get('code_challenge_method'),'S256');assert.equal(url.searchParams.get('scope'),settings.scopes);const result=await yahoo.complete(callback(start.transaction.state),start.transaction);assert.deepEqual(result,{subject:'test-member',leagueKey:settings.leagueKey});assert(!JSON.stringify(result).includes('token'));});
for(const mode of ['signature','nonce','issuer','audience','expired'])test('rejects invalid ID token: '+mode,async()=>{const {yahoo,start,paths}=await provider(mode);await assert.rejects(yahoo.complete(callback(start.transaction.state),start.transaction));assert(!paths.some(x=>x.includes('fantasysports')));});
test('OIDC state mismatch rejected before token request',async()=>{const {yahoo,start,paths}=await provider();await assert.rejects(yahoo.complete(callback('attacker'),start.transaction));assert(!paths.some(x=>x.endsWith('/oauth2/get_token')));});
test('valid identity without Siler City membership is denied',async()=>{const {yahoo,start}=await provider('nonmember');assert.equal(await yahoo.complete(callback(start.transaction.state),start.transaction),null);});
