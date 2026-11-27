import test from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORIES, TOTAL_ITEMS, createChecklist } from '../prototypes/f09-preparedness/model.js';

const IDS = CATEGORIES.flatMap(category => category.items.map(item => item.id));

test('F09 initial state: no checked item, every item is unprepared', () => {
  const store = createChecklist();
  assert.equal(TOTAL_ITEMS, 10);
  assert.deepEqual(store.snapshot(), {
    checkedCount: 0, totalCount: 10, uncheckedCount: 10, percent: 0, checkedIds: [],
  });
  for (const id of IDS) assert.equal(store.isChecked(id), false);
});

test('F09 toggle on and off changes checked count and ratio', () => {
  const store = createChecklist();
  assert.equal(store.setChecked('water', true), true);
  assert.equal(store.setChecked('water', true), true); // idempotent
  assert.equal(store.snapshot().percent, 10);
  assert.equal(store.snapshot().checkedCount, 1);
  assert.equal(store.setChecked('water', false), true);
  assert.equal(store.snapshot().percent, 0);
});

test('F09 all reset returns every item to unchecked and zero progress', () => {
  const store = createChecklist();
  for (const id of IDS) assert.equal(store.setChecked(id, true), true);
  assert.equal(store.snapshot().percent, 100);
  store.reset();
  assert.equal(store.snapshot().checkedCount, 0);
  assert.equal(store.snapshot().uncheckedCount, TOTAL_ITEMS);
  assert.deepEqual(store.snapshot().checkedIds, []);
});

test('F09 rejects unknown IDs / malformed values without changing state', () => {
  const store = createChecklist();
  store.setChecked('water', true);
  const before = store.snapshot();
  for (const invalid of ['unknown', '__proto__', '', undefined, null, 42, {}]) {
    assert.equal(store.setChecked(invalid, true), false);
    assert.equal(store.isChecked(invalid), false);
  }
  assert.equal(store.setChecked('water', 'true'), false);
  assert.deepEqual(store.snapshot(), before);
});

test('F09 new session is empty: no cross-instance persistence', () => {
  const first = createChecklist();
  first.setChecked('water', true);
  assert.equal(first.snapshot().checkedCount, 1);
  assert.equal(createChecklist().snapshot().checkedCount, 0);
});

test('F09 exactly scoped to unique, non-personal example IDs', () => {
  assert.equal(new Set(IDS).size, TOTAL_ITEMS);
  assert.deepEqual(CATEGORIES.map(category => category.title), [
    '自宅で備える', '持ち出しに備える', '日ごろから確認する',
  ]);
  assert.ok(CATEGORIES.every(category => category.items.length > 0));
});

 
import {spawnSync} from 'node:child_process';
import {mkdtempSync, mkdirSync, readdirSync, rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const browserScript=fileURLToPath(new URL('./f09-preparedness-browser.cjs',import.meta.url));
test('F09 missing binary, spawn failure and early startup exit finish nonzero and clean profiles',()=>{
  for(const mode of ['missing','spawn-error','early-exit']){
    const scratch=mkdtempSync(join(tmpdir(),'f09-negative-'));
    try{
      const directory=join(scratch,'not-executable');mkdirSync(directory);
      const binary=mode==='missing'?join(scratch,'missing-chrome'):mode==='spawn-error'?directory:process.execPath;
      const started=Date.now();
      const result=spawnSync(process.execPath,[browserScript],{
        env:{...process.env,F09_BROWSER_BIN:binary,TMPDIR:scratch,TMP:scratch,TEMP:scratch,F09_SCREENSHOT:''},
        encoding:'utf8',timeout:20000,
      });
      assert.ifError(result.error);
      assert.equal(result.status,1,mode+': '+result.stderr);
      assert.ok(Date.now()-started<20000,mode+' must terminate');
      assert.match(result.stderr,mode==='missing'?/binary not found/:mode==='spawn-error'?/spawn failed/:/exited during startup/);
      assert.deepEqual(readdirSync(scratch),['not-executable'],mode+' leaves no profile');
    }finally{rmSync(scratch,{recursive:true,force:true});}
  }
});
test('F09 cleanup failure still runs remaining cleaners and returns nonzero',()=>{
  const child=spawnSync(process.execPath,['-e',
    "const {cleanupResources}=require(process.argv[1]);cleanupResources([async()=>{throw Error('injected cleanup failure')},async()=>console.log('remaining cleanup ran')]).catch(e=>{console.error(e);process.exit(1)})",browserScript],
    {encoding:'utf8',timeout:5000});
  assert.ifError(child.error);
  assert.equal(child.status,1);
  assert.match(child.stdout,/remaining cleanup ran/);
  assert.match(child.stderr,/F09 cleanup failed/);
});
test('F09 exact candidate frontend copy excludes all seven private assets, retains public hashes',()=>{
  const root=fileURLToPath(new URL('../../',import.meta.url));
  const script=[
    'from pathlib import Path',
    'from tempfile import TemporaryDirectory',
    'from hashlib import sha256',
    'from deploy.build_staging import _copy_public_frontend, UNPUBLISHED_PREVIEW_PATHS',
    'src=Path("frontend").resolve()',
    'private=["prototypes/f09-preparedness/"+p for p in ["index.html","styles.css","app.js","model.js"]]+["tests/f09-preparedness.test.js","tests/f09-preparedness-browser.cjs","docs/F09_PREPAREDNESS_CHECKLIST_PROTOTYPE_20261117.md"]',
    'controls=["index.html","src/app.js","styles.css","prototypes/f02-shelter-explore/index.html","package.json"]',
    'assert all((src/p).is_file() for p in private), "candidate private source missing"',
    'assert all((src/p).is_file() for p in controls), "public control missing"',
    'with TemporaryDirectory() as scratch:',
    ' dst=Path(scratch)/"frontend"',
    ' _copy_public_frontend(src,dst)',
    ' assert not (dst/"prototypes/f09-preparedness").exists()',
    ' assert all(not (dst/p).exists() for p in private)',
    ' assert all(not (dst/p).exists() for p in UNPUBLISHED_PREVIEW_PATHS)',
    ' assert all((dst/p).is_file() and sha256((src/p).read_bytes()).digest()==sha256((dst/p).read_bytes()).digest() for p in controls)',
    ' assert "f09-preparedness" in (dst/"package.json").read_text(encoding="utf-8"), "metadata boundary changed; review explicitly"',
    ' print("F09_CANDIDATE_COPY: 7/7 private absent, 5/5 public hashes retained; package metadata references remain")',
  ].join('\n');
  const python=process.env.PYTHON|| (process.platform==='win32'?'python':'python3');
  const result=spawnSync(python,['-c',script],{cwd:root,encoding:'utf8',timeout:30000});
  assert.ifError(result.error);
  assert.equal(result.status,0,result.stderr);
  console.log(result.stdout.trim());
});

test('F09 CDP disconnect rejects all outstanding commands and prevents a new send',async()=>{
  const {connectCdp}=createRequire(import.meta.url)(browserScript);
  for(const type of ['close','error']){
    const ws=new EventTarget();
    ws.readyState=WebSocket.OPEN;
    ws.send=()=>{};
    const cdp=connectCdp(ws);
    const pending=[cdp.send('Runtime.evaluate'),cdp.send('Page.reload')];
    const rejected=Promise.all(pending.map(p=>assert.rejects(p,/CDP WebSocket/)));
    ws.readyState=WebSocket.CLOSED;
    ws.dispatchEvent(new Event(type));
    await rejected;
    await assert.rejects(cdp.send('Page.navigate'),/CDP not open/);
  }
});
