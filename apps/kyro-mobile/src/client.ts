/**
 * Kyro client contract. Tokens are passed per request and are never logged, cached,
 * saved to AsyncStorage, or sent to a different origin.
 */
export const API_ORIGIN=(process.env.EXPO_PUBLIC_API_ORIGIN ||
 'https://ces52hcf3e.execute-api.ap-southeast-2.amazonaws.com').replace(/\/$/,'');
export const COGNITO_HOST=(process.env.EXPO_PUBLIC_COGNITO_HOST ||
 'https://kyro-v4-private-179502447662.auth.ap-southeast-2.amazoncognito.com').replace(/\/$/,'');
/* Pre-alpha uses the existing public PKCE client so its ID-token audience matches the live API. */
export const COGNITO_CLIENT_ID=process.env.EXPO_PUBLIC_COGNITO_CLIENT_ID || '68i1h2nqhvsjruneo12k0u3ahm';
export const isConfigured=Boolean(COGNITO_CLIENT_ID &&
 COGNITO_CLIENT_ID!=='REPLACE_WITH_MOBILE_PUBLIC_APP_CLIENT_ID');

export type Project={id:string;name:string;role:string};
export type Conversation={id:string;title:string};
export type Message={role:string;content:string};
export type WorkspaceFile={path:string};
export type TeamPost={author:string;body:string;created_at:string};
export type Connector={id:string;protocol:string;scope:string;state:string};

export async function kyroApi<T>(idToken:string,path:string,init:{
 method?:'GET'|'POST'|'PUT';body?:unknown;
}={}):Promise<T>{
 if(!idToken)throw new Error('Sign-in required.');
 if(!path.startsWith('/') || path.startsWith('//'))throw new Error('Invalid API path');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(),45000);
 try{
  const response=await fetch(API_ORIGIN+'/api/v3'+path,{
   method:init.method||'GET',
   headers:{Authorization:'Bearer '+idToken,...(init.body===undefined?{}:{'content-type':'application/json'})},
   ...(init.body===undefined?{}:{body:JSON.stringify(init.body)}),
   signal:controller.signal
  });
  const payload=await response.json().catch(()=>({error:'Unexpected API response'}));
  if(response.status===401)throw new Error('Session expired. Sign in again.');
  if(!response.ok)throw new Error(
   typeof payload.error==='string'?payload.error:'Cloud request failed ('+response.status+').'
  );
  return payload as T;
 }finally{clearTimeout(timer);}
}
