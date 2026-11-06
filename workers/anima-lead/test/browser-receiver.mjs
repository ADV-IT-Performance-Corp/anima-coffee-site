// Test-only IPC bridge: actual Worker + local workerd/D1. All outbound fetches denied.
import {Miniflare,convertV4MiniflareOptions,NoOpLog} from 'miniflare';
import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import {readFileSync,mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {createInterface} from 'node:readline';
const root=fileURLToPath(new URL('../',import.meta.url));
const built=await build({entryPoints:[join(root,'src/index.js')],bundle:true,write:false,format:'esm',platform:'browser'});
const persist=mkdtempSync(join(tmpdir(),'anima-browser-worker-'));
const options={...convertV4MiniflareOptions({cf:false,modules:true,script:built.outputFiles[0].text,compatibilityDate:'2026-11-04',
 d1Databases:['DB'],ratelimits:{INTAKE_LIMITER:{namespace_id:'1001',simple:{limit:1000,period:60}}},
 bindings:{TENANT:'anima-coffee',PAYLOAD_KEY:'01'.repeat(32),DELIVERY_ENABLED:'false'},
 outboundService:()=>{throw new Error('External network denied in browser contract test');}}),
 log:new NoOpLog(),resourcePersistencePath:persist,telemetry:{enabled:false}};
let mf=new Miniflare(options);
const say=value=>process.stdout.write(JSON.stringify(value)+'\n');
try {
 let db=await mf.getD1Database('DB');
 for(const statement of readFileSync(join(root,'schema.sql'),'utf8').split(';').filter(x=>x.trim())) await db.prepare(statement).run();
 say({ready:true});
 for await(const line of createInterface({input:process.stdin,crlfDelay:Infinity})) {
  const input=JSON.parse(line);
  if(input.op==='restart') {await mf.dispose();mf=new Miniflare(options);db=await mf.getD1Database('DB');say({ready:true});continue;}
  if(input.op==='count') {say(await db.prepare('SELECT count(*) AS count FROM leads').first());continue;}
  const response=await mf.dispatchFetch('https://reserve.invalid/api/anima/lead',{method:'POST',
   headers:{Origin:'https://aeo.animacoffee.com.ua','CF-Connecting-IP':'192.0.2.1','Content-Type':'application/json'},body:JSON.stringify(input.payload)});
  say({status:response.status,body:await response.json()});
 }
} finally {await mf.dispose();}
