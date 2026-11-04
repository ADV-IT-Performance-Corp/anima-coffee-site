import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync,mkdtempSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import worker,{intake,sweep,providerForm,parseReceipt} from './worker.mjs';
const now=1800000000000;
const data={client_slug:'anima-coffee',idempotency_key:'11111111-1111-4111-8111-111111111111',consent:true,name:'Synthetic',email:'fixture@example.invalid',roistat_visit:'12345',details:'Synthetic fixture only'};
function db(path=':memory:') {
 const sql=new DatabaseSync(path); sql.exec(readFileSync(new URL('./schema.sql',import.meta.url),'utf8'));
 return {sql,prepare(query){let values=[]; const stmt=sql.prepare(query);return {bind(...v){values=v;return this;},async run(){return stmt.run(...values);},async first(){return stmt.get(...values)||null;},async all(){return {results:stmt.all(...values)};}};}};
}
function env(store=db()) {return {DB:store,TENANT:'anima-coffee',PAYLOAD_KEY:'01'.repeat(32),DELIVERY_ENABLED:'true',ROUTING_VERIFIED:'true',ROISTAT_INTEGRATION_KEY:'fixture-not-a-secret',INTAKE_LIMITER:{async limit(){return {success:true};}}};}
function req(body=data,origin='https://aeo.animacoffee.com.ua') {return new Request('https://reserve.invalid/api/anima/lead',{method:'POST',headers:{Origin:origin,'CF-Connecting-IP':'192.0.2.1','Content-Type':'application/json'},body:JSON.stringify(body)});}
const row=e=>e.DB.sql.prepare('SELECT * FROM leads').get();
const success=async()=>new Response(JSON.stringify({status:'success',data:{id:12,order_id:34}}));
test('durable commit precedes receipt; PII encrypted; retry returns same opaque ID',async()=>{
 const e=env(); const a=await intake(req(),e,now);const receipt=await a.json();assert.equal(a.status,200);assert.equal(receipt.receipt,'stored');assert.equal(row(e).id,receipt.lead_id);assert.ok(!row(e).payload.includes('fixture'));assert.equal((await (await intake(req(),e,now)).json()).lead_id,receipt.lead_id);assert.equal(e.DB.sql.prepare('SELECT count(*) n FROM leads').get().n,1);
});
test('same key different content refused; no existence/contact disclosure',async()=>{
 const e=env();await intake(req(),e,now);assert.equal((await intake(req({...data,name:'Other'}),e,now)).status,409);assert.equal((await intake(req(data,'https://foreign.invalid'),e,now)).status,403);
});
test('foreign tenant, invalid visit, missing consent, oversized streamed body refused',async()=>{
 const e=env();for(const x of [{client_slug:'amc'},{roistat_visit:'bad'},{consent:false},{email:''}]) assert.equal((await intake(req({...data,...x}),e,now)).status,400);
 assert.equal((await intake(req({...data,details:'x'.repeat(13000)}),e,now)).status,413);
 assert.equal((await worker.fetch(req(),{...e,TENANT:'adv'})).status,503);
});
test('no production transport when disabled or route unverified',async()=>{
 const e=env();await intake(req(),e,now);let calls=0;await sweep({...e,DELIVERY_ENABLED:'false'},async()=>{calls++;},now);await sweep({...e,ROUTING_VERIFIED:'false'},async()=>{calls++;},now);assert.equal(calls,0);assert.equal(row(e).state,'queued');
});
test('browser closure and database reopen retain enquiry; scheduled receiver confirms both stages',async()=>{
 const path=join(mkdtempSync(join(tmpdir(),'anima-d1-test-')),'outbox.sqlite');let e=env(db(path));await intake(req(),e,now);e.DB.sql.close();e=env(db(path));let count=0;
 await sweep(e,async(url,options)=>{count++;assert.equal(url,'https://cloud.roistat.com/api/proxy/1.0/leads/add');assert.equal(options.body.get('roistat'),'12345');assert.equal(options.body.get('is_need_callback'),'0');assert.ok(options.body.get('title').includes(row(e).id));return success();},now);
 assert.equal(count,1);assert.equal(row(e).state,'kommo_confirmed');assert.equal(row(e).proxy_id,'12');assert.equal(row(e).kommo_id,'34');await sweep(e,async()=>{throw new Error('duplicate');},now+300000);e.DB.sql.close();
});
test('Roistat outage does not lose stored payload or falsely confirm delivery',async()=>{
 const e=env();await intake(req(),e,now);await sweep(e,async()=>new Response('unavailable',{status:503}),now);assert.equal(row(e).state,'unknown');assert.ok(row(e).payload);
});
test('remote commit then timeout remains unknown; ingress replay and future cron never resubmit',async()=>{
 const e=env();await intake(req(),e,now);let commits=0;const lost=async()=>{commits++;throw new Error('response lost after commit');};await sweep(e,lost,now);await intake(req(),e,now+1);await sweep(e,lost,now+300000);assert.equal(commits,1);assert.equal(row(e).state,'unknown');assert.equal(row(e).attempts,1);
});
test('terminated sending lease is held for reconciliation rather than resent',async()=>{
 const e=env();await intake(req(),e,now);e.DB.sql.prepare("UPDATE leads SET state='sending',next_attempt=?").run(now);let calls=0;await sweep(e,async()=>{calls++;},now+1);assert.equal(calls,0);assert.equal(row(e).state,'unknown');
});
test('200 malformed or arbitrary ID cannot mean Kommo delivery',async()=>{
 for(const body of [{},{status:'ok',id:2},{status:'success',data:{id:1}},{status:'success',data:{id:1,order_id:'bogus'}}]) {
 const e=env();await intake(req(),e,now);await sweep(e,async()=>new Response(JSON.stringify(body)),now);assert.notEqual(row(e).state,'kommo_confirmed');}
 assert.equal(parseReceipt({status:'success',data:{id:1}}).state,'roistat_accepted');
});
test('expiry erases payload and tombstone refuses late retry',async()=>{
 const e=env();await intake(req(),e,now);await sweep({...e,DELIVERY_ENABLED:'false'},success,now+7*86400000);assert.equal(row(e).payload,null);assert.equal(row(e).state,'expired');assert.equal((await intake(req(),e,now+7*86400000)).status,410);
});
test('wrong encryption secret cannot disclose or deliver payload',async()=>{
 const e=env();await intake(req(),e,now);let calls=0;await sweep({...e,PAYLOAD_KEY:'02'.repeat(32)},async()=>{calls++;},now);assert.equal(calls,0);assert.equal(row(e).state,'unknown');
});
test('capacity refuses new intake without evicting acknowledged enquiries',async()=>{
 const e=env();await intake(req(),e,now);const insert=e.DB.sql.prepare('INSERT INTO leads(tenant,idem,id,fingerprint,created,expires,next_attempt) VALUES(?,?,?,?,?,?,?)');for(let i=1;i<500;i++)insert.run('anima-coffee',String(i),String(i),'x',now,now+1000,now);
 assert.equal((await intake(req({...data,idempotency_key:'22222222-2222-4222-8222-222222222222'}),e,now)).status,503);assert.equal((await intake(req(),e,now)).status,200);
});
test('concurrent cron claims emit once',async()=>{
 const e=env();await intake(req(),e,now);let calls=0;const transport=async()=>{calls++;return success();};await Promise.all([sweep(e,transport,now),sweep(e,transport,now)]);assert.equal(calls,1);
});

test('rate limit denies spoofed-origin flood before DB writes; missing binding fails closed',async()=>{
 const e=env();let seen;
 e.INTAKE_LIMITER={async limit({key}){seen=key;return {success:false};}};
 assert.equal((await intake(req(),e,now)).status,429);assert.equal(row(e),undefined);assert.match(seen,/^[0-9a-f]{64}$/);assert.ok(!seen.includes('192.0.2.1'));
 delete e.INTAKE_LIMITER;assert.equal((await intake(req(),e,now)).status,503);
});

test('retention sweep preserves an active send until its receipt can commit',async()=>{
 const e=env();await intake(req(),e,now);
 e.DB.sql.prepare('UPDATE leads SET expires=?').run(now+100);
 let release,started;
 const ready=new Promise(resolve=>{started=resolve;});
 const held=new Promise(resolve=>{release=resolve;});
 const sending=sweep(e,async()=>{started();await held;return success();},now);
 await ready;await sweep({...e,DELIVERY_ENABLED:'false'},success,now+101);
 assert.equal(row(e).state,'sending');assert.ok(row(e).payload);
 release();await sending;assert.equal(row(e).state,'kommo_confirmed');
 await sweep({...e,DELIVERY_ENABLED:'false'},success,now+300000);
 assert.equal(row(e).payload,null);assert.equal(row(e).kommo_id,'34');
});
