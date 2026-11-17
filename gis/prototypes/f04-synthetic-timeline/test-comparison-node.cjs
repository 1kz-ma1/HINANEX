'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const {ROWS, COLS, SCENARIOS, createSession} = require('./timeline-model.js');
const {classify, createComparisonSession} = require('./comparison-model.js');
const here = __dirname;

function ready(id='fiction-a', from=0, to=3) {
  const s = createComparisonSession();
  s.selectScenario(id); s.setBefore(from); s.setAfter(to);
  return s;
}

test('S2: every abstract cell is categorized exactly once, without area inference', () => {
  const d = classify(['0-0','0-1'],['0-1','0-2']);
  assert.deepEqual(d.added,['0-2']);
  assert.deepEqual(d.removed,['0-0']);
  assert.deepEqual(d.continued,['0-1']);
  assert.equal(d.empty.length, ROWS*COLS-3);
  assert.equal([...d.added,...d.removed,...d.continued,...d.empty].length,40);
});

test('S2: an explicit pair and button are required; initial/missing pair NO-GO', () => {
  const s = createComparisonSession();
  assert.equal(s.getState().status,'UNSELECTED');
  assert.equal(s.compare().status,'NO_GO');
  assert.equal(s.getState().comparison,null);
  s.selectScenario('fiction-a');
  assert.equal(s.getState().status,'SELECTING');
  assert.equal(s.getState().comparison,null);
  s.setBefore(0);
  assert.equal(s.compare().reasonCode,'STEP_PAIR_REQUIRED');
  assert.equal(s.getState().comparison,null);
  s.setAfter(3);
  assert.equal(s.getState().status,'READY');
  assert.equal(s.getState().comparison,null);
  assert.equal(s.compare().status,'SHOWN');
});

test('S2: A step 0 to 3 adds eight diagram cells without safety claims', () => {
  const result=ready().compare().comparison;
  assert.deepEqual(result.beforeCells,[]);
  assert.deepEqual(result.afterCells,SCENARIOS[0].frames[3].cells);
  assert.equal(result.added.length,8);
  assert.equal(result.removed.length,0);
  assert.equal(result.continued.length,0);
  assert.equal(result.empty.length,32);
  assert.match(result.summary,/模擬ステップ 0 → 3/);
  assert.match(result.summary,/新規着色 8セル/);
  assert.match(result.summary,/現実の浸水面積・深さ・危険度・時間・安全性を示しません/);
});

test('S2: reverse comparison exchanges added and removed, not safety interpretation', () => {
  const forward=ready().compare().comparison;
  const reverse=ready('fiction-a',3,0).compare().comparison;
  assert.deepEqual(reverse.added,forward.removed);
  assert.deepEqual(reverse.removed,forward.added);
  assert.equal(reverse.removed.length,8);
  assert.equal(reverse.empty.length,32);
});

test('S2: comparing the same step shows unchanged colored and unchanged uncolored', () => {
  const result=ready('fiction-a',3,3).compare().comparison;
  assert.equal(result.added.length,0);
  assert.equal(result.removed.length,0);
  assert.equal(result.continued.length,8);
  assert.equal(result.empty.length,32);
  assert.deepEqual(result.beforeCells,result.afterCells);
});

test('S2: the other fictional scenario has distinct, correct deltas', () => {
  const result=ready('fiction-b',0,3).compare().comparison;
  assert.deepEqual(result.beforeCells,['1-6']);
  assert.equal(result.added.length,5);
  assert.equal(result.removed.length,0);
  assert.equal(result.continued.length,1);
  assert.equal(result.empty.length,34);
});

test('S2: altering either index immediately discards all old comparison geometry', () => {
  const s=ready();
  assert.ok(s.compare().comparison);
  const old=s.getState().revision;
  const changed=s.setBefore(1);
  assert.equal(changed.status,'READY');
  assert.equal(changed.comparison,null);
  assert.ok(changed.revision>old);
  assert.equal(s.compare().comparison.before,1);
  assert.equal(s.setAfter(null).comparison,null);
  assert.equal(s.getState().status,'SELECTING');
  assert.equal(s.compare().status,'NO_GO');
});

test('S2: scenario change, clear, and unknown scenario never reuse old comparison', () => {
  const s=ready();
  s.compare();
  const generation=s.getState().revision;
  const next=s.selectScenario('fiction-b');
  assert.equal(next.status,'SELECTING');
  assert.equal(next.before,null);
  assert.equal(next.after,null);
  assert.equal(next.comparison,null);
  assert.ok(next.revision>generation);
  s.setBefore(0); s.setAfter(3);
  assert.equal(s.compare().comparison.added.length,5);
  assert.equal(s.selectScenario('real-river').reasonCode,'INVALID_SCENARIO');
  assert.equal(s.getState().comparison,null);
  assert.equal(s.getState().scenarioId,null);
  assert.equal(s.clear().status,'UNSELECTED');
});

test('S2: corrupt fixtures, duplicates and invalid indices fail closed', () => {
  const corrupt=[
    {id:'fiction-z',label:'架空の欠損',frames:[{label:'模擬ステップ 0',cells:['0-0']}]},
    {id:'fiction-y',label:'架空の不正',frames:[{label:'模擬ステップ 0',cells:[]},{label:'模擬ステップ 1',cells:['999-999']}]}
  ];
  for(const fixture of corrupt) {
    const s=createComparisonSession([fixture]);
    assert.equal(s.selectScenario(fixture.id).status,'NO_GO');
    assert.equal(s.getState().comparison,null);
  }
  const dup=[SCENARIOS[0],SCENARIOS[0]];
  assert.equal(createComparisonSession(dup).selectScenario('fiction-a').status,'NO_GO');
  for(const wrong of [-1,4,1.3,'2',NaN,Infinity]) {
    const s=ready();
    s.compare();
    const result=s.setBefore(wrong);
    assert.equal(result.status,'NO_GO');
    assert.equal(result.comparison,null);
    assert.equal(result.before,null);
    assert.equal(result.after,null);
  }
});

test('S2: frozen snapshots and fixture copy prevent external mutation', () => {
  const fixtures=structuredClone(SCENARIOS);
  const s=createComparisonSession(fixtures);
  s.selectScenario('fiction-a');
  fixtures[0].frames[3].cells.push('4-7');
  s.setBefore(0);s.setAfter(3);
  const snap=s.compare();
  assert.equal(snap.comparison.added.length,8);
  assert.equal(Object.isFrozen(snap),true);
  assert.equal(Object.isFrozen(snap.comparison),true);
  assert.equal(Object.isFrozen(snap.comparison.added),true);
  assert.throws(()=>snap.comparison.added.push('4-7'),TypeError);
});

test('S2: repeated changes never resurrect stale pair; S1 playback remains independent', () => {
  const s1=createSession();
  s1.select('fiction-a');
  const s2=createComparisonSession();
  let last=s2.getState().revision;
  for(let i=0;i<40;i++){
    const id=i%2 ? 'fiction-a':'fiction-b';
    const state=s2.selectScenario(id);
    assert.equal(state.comparison,null);
    assert.ok(state.revision>last);
    s2.setBefore(0);s2.setAfter(3);
    assert.equal(s2.compare().status,'SHOWN');
    last=s2.getState().revision;
  }
  assert.equal(s1.getState().index,0);
  assert.equal(s1.play().status,'PLAYING');
  assert.equal(s2.getState().status,'SHOWN');
  assert.equal(s1.pause().status,'PAUSED');
  assert.equal(s2.getState().status,'SHOWN');
});

test('S2: the page preserves S1 accessibility/safety and never inserts unapproved networking', () => {
  const html=fs.readFileSync(path.join(here,'index.html'),'utf8');
  const app=fs.readFileSync(path.join(here,'comparison-app.js'),'utf8');
  const model=fs.readFileSync(path.join(here,'comparison-model.js'),'utf8');
  assert.match(html,/完全架空・訓練用/);
  assert.match(html,/実際の浸水面積・浸水深・危険度・到達時間/);
  assert.match(html,/connect-src 'none'/);
  assert.equal((html.match(/role="status"/g)||[]).length,1); // Existing S1 status.
  assert.match(html,/aria-live="polite"/);
  assert.match(html,/src="\.\/comparison-model\.js"/);
  assert.match(html,/src="\.\/comparison-app\.js"/);
  assert.match(html,/id="comparisonSummary"/);
  for(const id of ['compareBefore','compareAfter','compareRun','compareClear','compareGridBefore','compareGridAfter','compareGridDelta'])
    assert.match(html,new RegExp('id="'+id+'"'));
  assert.doesNotMatch(html+app+model,/(?:navigator\.geolocation|fetch\(|XMLHttpRequest|localStorage|https?:\/\/)/);
  assert.match(app,/state\.selectScenario\(scenario\.value\)/);
  assert.match(app,/state\.clear\(\)/);
  assert.match(model,/result = null; \/\/ Always remove the old result/);
});
