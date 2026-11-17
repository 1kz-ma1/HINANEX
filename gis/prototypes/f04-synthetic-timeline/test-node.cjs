'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const { ROWS, COLS, SCENARIOS, createSession, validScenario } = require('./timeline-model.js');

function started(id = 'fiction-a') { const s = createSession(); s.select(id); return s; }

test('fictional fixtures: bounded abstract cells, no geographic/temporal claims', () => {
  assert.equal(ROWS * COLS, 40);
  assert.equal(SCENARIOS.length, 2);
  for (const scenario of SCENARIOS) {
    assert.equal(validScenario(scenario), true);
    assert.match(scenario.label, /^架空/);
    assert.equal(scenario.frames.length, 4);
    for (const frame of scenario.frames) {
      assert.match(frame.label, /^模擬ステップ [0-3]$/);
      assert.deepEqual([...new Set(frame.cells)], frame.cells);
    }
  }
  assert.notDeepEqual(SCENARIOS[0].frames.at(-1), SCENARIOS[1].frames.at(-1));
});

test('unselected, unknown, invalid fixture and missing frame always NO-GO with no cells', () => {
  const s = createSession();
  assert.equal(s.getState().status, 'UNSELECTED');
  assert.equal(s.getState().index, null);
  assert.deepEqual(s.getState().cells, []);
  assert.equal(s.play().status, 'NO_GO');
  assert.equal(s.getState().index, null);
  assert.equal(s.select('real-world-place').reasonCode, 'INVALID_SCENARIO');
  assert.deepEqual(s.getState().cells, []);
  const missing = [{ id: 'fiction-z', label: '架空データ欠損', frames: [{ label: '模擬ステップ 0', cells: ['1-1'] }] }];
  assert.equal(createSession(missing).select('fiction-z').reasonCode, 'INVALID_SCENARIO');
  const wrong = [
    {id:'fiction-z',label:'架空不正',frames:[{label:'模擬ステップ 0',cells:['2-2']},{label:'模擬ステップ 1',cells:['999-999']}]},
    {id:'fiction-z',label:'架空重複',frames:[{label:'模擬ステップ 0',cells:[]},{label:'模擬ステップ 1',cells:[]}]}
  ];
  assert.equal(createSession(wrong).select('fiction-z').status, 'NO_GO');
  const duplicateCells = {id:'fiction-z',label:'架空重複セル',frames:[{label:'模擬ステップ 0',cells:[]},{label:'模擬ステップ 1',cells:['1-1','1-1']}]};
  assert.equal(validScenario(duplicateCells), false);
  assert.equal(validScenario({id:'fiction-z',label:'架空',frames:null}), false);
  assert.equal(s.select('').status, 'UNSELECTED');
});

test('explicit choice displays first static synthetic frame, slider switches exact frames', () => {
  const s = started();
  const initial = s.getState();
  assert.equal(initial.status, 'PAUSED');
  assert.equal(initial.index, 0);
  assert.equal(initial.cells.length, 0); // empty drawing is valid *fiction*, not safety.
  assert.equal(s.seek(2).index, 2);
  assert.deepEqual(s.getState().cells, SCENARIOS[0].frames[2].cells);
  assert.equal(s.seek(3).cells.length, 8);
  assert.equal(s.restart().index, 0);
});

test('play, manual pause, end, restart from end with monotonically invalidated ticks', () => {
  const s = started();
  const playing = s.play();
  assert.equal(playing.status, 'PLAYING');
  assert.equal(s.step(playing.generation).index, 1);
  const paused = s.pause();
  assert.equal(paused.status, 'PAUSED');
  assert.equal(s.step(playing.generation).index, 1);
  let active = s.play();
  for (let i = 0; i < 3; i++) s.step(active.generation);
  assert.equal(s.getState().index, 3);
  assert.equal(s.getState().status, 'PAUSED');
  assert.equal(s.getState().reasonCode, 'ENDED');
  assert.equal(s.step(active.generation).index, 3);
  active = s.play();
  assert.equal(active.index, 0);
  assert.equal(active.status, 'PLAYING');
  assert.ok(active.generation > playing.generation);
});

test('scenario switch, restart and clear revoke old playback generation immediately', () => {
  const s = started();
  const old = s.play();
  s.step(old.generation);
  const replacement = s.select('fiction-b');
  assert.equal(replacement.index, 0);
  assert.equal(replacement.scenarioId, 'fiction-b');
  assert.deepEqual(replacement.cells, ['1-6']);
  assert.equal(s.step(old.generation).index, 0);
  assert.deepEqual(s.getState().cells, ['1-6']);
  const b = s.play();
  const reset = s.restart();
  assert.equal(reset.index, 0);
  assert.equal(s.step(b.generation).index, 0);
  assert.equal(s.clear().index, null);
  assert.deepEqual(s.getState().cells, []);
  assert.equal(s.step(b.generation).status, 'UNSELECTED');
});

test('invalid slider and unsupported selection purge displayed cells fail-closed', () => {
  for (const value of [-1, 4, 1.5, NaN, Infinity, '2', null]) {
    const s = started(); s.seek(3);
    const result = s.seek(value);
    assert.equal(result.status, 'NO_GO');
    assert.equal(result.index, null);
    assert.deepEqual(result.cells, []);
  }
  const s = started();
  s.seek(2);
  const fail = s.select('not-in-fixture');
  assert.equal(fail.status, 'NO_GO');
  assert.deepEqual(fail.cells, []);
  assert.equal(s.select('fiction-b').status, 'PAUSED');
});

test('fixture copy and snapshots prevent mutation or stale geometry resurrection', () => {
  const f = structuredClone(SCENARIOS);
  const s = createSession(f);
  s.select('fiction-a');
  f[0].frames[1].cells.push('4-7');
  s.seek(1);
  assert.deepEqual(s.getState().cells, ['3-1','3-2']);
  const state = s.getState();
  assert.equal(Object.isFrozen(state), true);
  assert.equal(Object.isFrozen(state.cells), true);
  assert.throws(() => state.cells.push('4-7'), TypeError);
  for (let i = 0; i < 48; i++) {
    const before = s.play();
    s.select(i % 2 === 0 ? 'fiction-b' : 'fiction-a');
    const current = s.getState();
    assert.equal(s.step(before.generation).generation, current.generation);
    assert.equal(s.getState().index, 0);
  }
});

test('CSP, all-screen synthetic warning, no external resources and safe native controls', () => {
  const html = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
  const js = fs.readFileSync(path.join(__dirname, 'app.js'), 'utf8');
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /default-src 'none'/);
  assert.match(html, /完全架空・訓練用/);
  assert.match(html, /id="floodGrid"/);
  assert.match(html, /type="range"/);
  for (const id of ['scenario','play','pause','restart','clear','step']) assert.match(html, new RegExp(`id="${id}"`));
  assert.equal((html.match(/role="status"/g) || []).length, 1);
  assert.doesNotMatch(html+js, /(?:navigator\.geolocation|fetch\(|XMLHttpRequest|localStorage|https?:\/\/)/);
});

test('Render staging builder copies only public gis/gis, never sibling prototypes', () => {
  const source = fs.readFileSync(path.resolve(__dirname, '../../../deploy/build_staging.py'), 'utf8');
  assert.match(source, /_copy_tree\(root \/ "gis" \/ "gis", output_dir \/ "gis" \/ "gis"\)/);
  assert.doesNotMatch(source, /_copy_tree\(root \/ "gis"\s*,/);
});
