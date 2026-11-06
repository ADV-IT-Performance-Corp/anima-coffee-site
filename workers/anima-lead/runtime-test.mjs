import {Miniflare,convertV4MiniflareOptions} from 'miniflare';
import {readFileSync,mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
const built=await build({stdin:{contents:`import app from './src/index.js';
export default {async fetch(r,e) {
 if(new URL(r.url).pathname === '/__test/sweep') {await app.scheduled(null,e);return new Response('ok');}
 return app.fetch(r,e);
}};`,resolveDir:fileURLToPath(new URL('.',import.meta.url))},bundle:true,write:false,format:'esm',platform:'browser'});
const script=built.outputFiles[0].text;
let calls=0;
const persist=mkdtempSync(join(tmpdir(),'anima-miniflare-'));
const options={cf:false,modules:true,script,compatibilityDate:'2026-11-04',d1Databases:['DB'],d1Persist:persist,ratelimits:{INTAKE_LIMITER:{namespace_id:'1001',simple:{limit:10,period:60}}},
 bindings:{TENANT:'anima-coffee',PAYLOAD_KEY:'01'.repeat(32),DELIVERY_ENABLED:'true',ROUTING_VERIFIED:'true',ROISTAT_INTEGRATION_KEY:'fake-fixture'},
 outboundService:async request=>{calls++;assert.equal(new URL(request.url).hostname,'cloud.roistat.com');const body=new URL(request.url).searchParams;assert.equal(body.get('roistat'),'1234');return new Response(JSON.stringify({status:'success',data:{id:90,order_id:91}}));}};
let mf=new Miniflare({...convertV4MiniflareOptions(options),resourcePersistencePath:persist,telemetry:{enabled:false}});
try {
 let db=await mf.getD1Database('DB');
 const schema=readFileSync(new URL('./schema.sql',import.meta.url),'utf8');
 for(const statement of schema.split(';').filter(x=>x.trim())) await db.prepare(statement).run();
 const input={client_slug:'anima-coffee',idempotency_key:'11111111-1111-4111-8111-111111111111',consent:true,email:'fixture@example.invalid',roistat_visit:'1234'};
 const send=()=>mf.dispatchFetch('https://reserve.invalid/api/anima/lead',{method:'POST',headers:{Origin:'https://aeo.animacoffee.com.ua','CF-Connecting-IP':'192.0.2.1','Content-Type':'application/json'},body:JSON.stringify(input)});
 let response=await send();assert.equal(response.status,200);const first=await response.json();assert.equal(first.receipt,'stored');
 await mf.dispose();mf=new Miniflare({...convertV4MiniflareOptions(options),resourcePersistencePath:persist,telemetry:{enabled:false}});db=await mf.getD1Database('DB');
 response=await send();const again=await response.json();assert.equal(response.status,200,JSON.stringify(again));assert.equal(again.lead_id,first.lead_id);
 const sweepResponse=await mf.dispatchFetch('https://reserve.invalid/__test/sweep');assert.equal(sweepResponse.status,200,await sweepResponse.text());
 const saved=await db.prepare('SELECT state,proxy_id,kommo_id FROM leads').first();
 assert.deepEqual(saved,{state:'kommo_confirmed',proxy_id:'90',kommo_id:'91'});
 await mf.dispatchFetch('https://reserve.invalid/__test/sweep');assert.equal(calls,1);
 console.log('PASS: local workerd+D1 commit, process restart, original receipt, cron sweep, synthetic Roistat+Kommo IDs, no duplicate');
} finally {await mf.dispose();}
