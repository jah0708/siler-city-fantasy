import { readSettings,seal,unseal,cookie,setCookie,SESSION,TRANSACTION,decryptSnapshot } from './security.mjs';
import { createYahoo } from './yahoo.mjs';
const SNAPSHOT='https://jah0708.github.io/siler-city-fantasy/data/league-data.enc.json';
const privateHeaders={'Cache-Control':'private, no-store, max-age=0','Pragma':'no-cache','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'};
export function createHandler({env=process.env,fetcher=fetch,yahooFactory=createYahoo}={}){
 let settings,yahoo;
 function response(data,status=200,extra={}){return new Response(JSON.stringify(data),{status,headers:{...privateHeaders,'Content-Type':'application/json',...extra}})}
 function redirect(path,headers={}){return new Response(null,{status:303,headers:{...privateHeaders,Location:path,...headers}})}
 return async request=>{
  let action;
  try{
   settings=readSettings(env);const url=new URL(request.url);action=url.searchParams.get('action')||url.pathname.split('/').at(-1);
   if(action==='config')return response({enabled:settings.enabled});
   if(!settings.enabled)return response({error:'Yahoo sign-in is not enabled on this preview.'},503);
   if(!yahoo)yahoo=yahooFactory(settings,fetcher);
   if(url.origin!==settings.origin)return response({error:'Wrong origin'},400);
   const expected=action==='logout'?'POST':'GET';
   if(request.method!==expected)return response({error:'Method not allowed'},405,{Allow:expected});
   if(action==='login'){
    const {url,transaction}=await yahoo.begin();
    const headers=new Headers({...privateHeaders,Location:url});headers.append('Set-Cookie',setCookie(SESSION,'',0));headers.append('Set-Cookie',setCookie(TRANSACTION,await seal(transaction,settings.key,'oauth',600),600));return new Response(null,{status:303,headers});
   }
   if(action==='callback'){
    const clear={'Set-Cookie':setCookie(TRANSACTION,'',0)}, transaction=await unseal(cookie(request,TRANSACTION),settings.key,'oauth');
    // Reject callbacks not bound to this browser, including error callbacks and duplicate state.
    if(!transaction||url.searchParams.getAll('state').length!==1||url.searchParams.get('state')!==transaction.state)return redirect('/?login_error=invalid_session',clear);
    if(url.searchParams.has('error'))return redirect('/?login_error=cancelled',clear);
    try{
     const current=new URL(settings.redirect);current.search=url.search;
     const member=await yahoo.complete(current,transaction);
     if(!member)return redirect('/?login_error=not_member',clear);
     const headers=new Headers({...privateHeaders,Location:'/'});
     headers.append('Set-Cookie',setCookie(TRANSACTION,'',0));headers.append('Set-Cookie',setCookie(SESSION,await seal(member,settings.key,'member',3600),3600));
     return new Response(null,{status:303,headers});
    }catch{return redirect('/?login_error=verification_failed',clear)}
   }
   if(action==='logout'){
    if(request.headers.get('origin')!==settings.origin)return response({error:'Wrong origin'},403);
    const headers=new Headers({...privateHeaders,Location:'/'});headers.append('Set-Cookie',setCookie(SESSION,'',0));headers.append('Set-Cookie',setCookie(TRANSACTION,'',0));return new Response(null,{status:303,headers});
   }
   const member=await unseal(cookie(request,SESSION),settings.key,'member');
   if(!member?.subject||member.leagueKey!==settings.leagueKey)return response({error:'Sign in with Yahoo to view the league.'},401);
   if(action==='session')return response({authenticated:true,expiresAt:member.exp});
   if(action==='league'){
    const data=await fetcher(SNAPSHOT,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(10000)});
    if(!data.ok)throw new Error('Snapshot unavailable');
    const text=await data.text();if(text.length>6e6)throw new Error('Snapshot too large');
    const db=await decryptSnapshot(JSON.parse(text),settings.password);
    if(db.hub?.leagueKey!==settings.leagueKey)throw new Error('Wrong season snapshot');
    return response(db);
   }
   return response({error:'Not found'},404);
  }catch{return response({error:'Sign-in service is temporarily unavailable.'},503)}
 };
}
