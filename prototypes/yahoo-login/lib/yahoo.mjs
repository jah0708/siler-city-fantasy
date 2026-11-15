import * as oidc from 'openid-client';
import { containsLeague } from './security.mjs';
export function createYahoo(settings,fetcher=fetch){
 let configured;
 async function configuration(){
  if(!configured){configured=oidc.discovery(new URL('https://api.login.yahoo.com'),settings.clientId,settings.clientSecret,oidc.ClientSecretBasic(settings.clientSecret),{timeout:10,execute:[oidc.enableNonRepudiationChecks],[oidc.customFetch]:fetcher});configured.catch(()=>{configured=undefined})}
  return configured;
 }
 return {
  async begin(){
   const config=await configuration(),state=oidc.randomState(),nonce=oidc.randomNonce(),verifier=oidc.randomPKCECodeVerifier();
   const url=oidc.buildAuthorizationUrl(config,{redirect_uri:settings.redirect,scope:settings.scopes,state,nonce,code_challenge:await oidc.calculatePKCECodeChallenge(verifier),code_challenge_method:'S256'});
   return {url:url.href,transaction:{state,nonce,verifier}};
  },
  async complete(url,transaction){
   const config=await configuration();
   const tokens=await oidc.authorizationCodeGrant(config,url,{expectedState:transaction.state,expectedNonce:transaction.nonce,pkceCodeVerifier:transaction.verifier,idTokenExpected:true});
   const subject=tokens.claims()?.sub;
   if(!subject||!tokens.access_token)throw new Error('Yahoo identity unavailable');
   const game=settings.leagueKey.split('.')[0];
   // Only the leagues of the user who just authorized, never the commissioner's token.
   const response=await fetcher(`https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=${game}/leagues?format=json`,{headers:{Authorization:`Bearer ${tokens.access_token}`,Accept:'application/json'},signal:AbortSignal.timeout(10000),redirect:'error'});
   if(!response.ok)throw new Error('Yahoo membership unavailable');
   const text=await response.text();if(text.length>2e6)throw new Error('Unexpected Yahoo response');
   if(!containsLeague(JSON.parse(text),settings.leagueKey))return null;
   // No refresh/access/ID token is persisted or returned to the browser.
   return {subject,leagueKey:settings.leagueKey};
  }
 };
}
