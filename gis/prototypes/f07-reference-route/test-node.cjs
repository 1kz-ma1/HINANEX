'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const { STARTS, DESTINATIONS, CONDITIONS, createSession } = require('./route-model.js');
const here = __dirname;

test('fixtures are fictional diagram points, not real coordinates', () => {
  assert.equal(STARTS.length, 2);
  assert.equal(DESTINATIONS.length, 2);
  assert.equal(CONDITIONS.length, 2);
  for (const p of [...STARTS, ...DESTINATIONS]) {
    assert.match(p.label, /架空/);
    assert.ok(Number.isInteger(p.x) && Number.isInteger(p.y));
    assert.deepEqual(Object.keys(p).sort(), ['id', 'label', 'x', 'y']);
  }
});

test('explicit selection required: initial and missing destination NO-GO', () => {
  const s = createSession();
  assert.equal(s.getState().status, 'UNSELECTED');
  assert.equal(s.getState().route, null);
  assert.equal(s.generate().status, 'NO_GO');
  s.setStart('start-a');
  assert.equal(s.generate().status, 'NO_GO');
  assert.match(s.getState().reason, /NO-GO/);
  assert.equal(s.getState().route, null);
});

test('manual selections show only a schematic; clearing removes it', () => {
  const s = createSession();
  s.setStart('start-a');
  s.setDestination('goal-y');
  assert.equal(s.getState().status, 'READY');
  const shown = s.generate();
  assert.equal(shown.status, 'SHOWN');
  assert.deepEqual(shown.route.points[0], [84, 90]);
  assert.deepEqual(shown.route.points.at(-1), [550, 290]);
  assert.equal(s.clear().route, null);
  assert.equal(s.getState().status, 'READY');
});

test('changing either point or condition purges previous geometry before re-render', () => {
  const s = createSession();
  s.setStart('start-a'); s.setDestination('goal-x');
  const first = s.generate();
  for (const mutate of [() => s.setStart('start-b'), () => s.setDestination('goal-y'), () => s.setCondition('pattern-2')]) {
    const state = mutate();
    assert.equal(state.route, null);
    assert.equal(state.status, 'READY');
    assert.ok(state.revision > first.revision);
    assert.equal(s.generate().status, 'SHOWN');
  }
  const second = s.generate();
  assert.notDeepEqual(first.route.points, second.route.points);
});

test('simulated failure and invalid selections never retain a stale route', () => {
  const s = createSession();
  s.setStart('start-a'); s.setDestination('goal-x');
  s.generate();
  const failed = s.generate({ fail: true });
  assert.equal(failed.route, null);
  assert.equal(failed.status, 'NO_GO');
  assert.match(failed.reason, /NO-GO/);
  s.generate();
  assert.equal(s.setDestination('real-facility-id').route, null);
  assert.equal(s.getState().destination, null);
  assert.equal(s.generate().status, 'NO_GO');
  assert.equal(s.setStart('latitude,longitude').route, null);
  assert.equal(s.getState().start, null);
});

test('model snapshots cannot mutate held geometry', () => {
  const s = createSession();
  s.setStart('start-a'); s.setDestination('goal-x');
  const result = s.generate();
  assert.throws(() => { result.route.points[0][0] = 999; }, TypeError);
  assert.deepEqual(s.getState().route.points[0], [84, 90]);
});

test('local-only CSP and Render bundle destination exclude this prototype', () => {
  const html = fs.readFileSync(path.join(here, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(here, 'app.js'), 'utf8');
  const model = fs.readFileSync(path.join(here, 'route-model.js'), 'utf8');
  const deploy = fs.readFileSync(path.resolve(here, '../../../deploy/build_staging.py'), 'utf8');
  assert.match(html, /connect-src 'none'/);
  assert.match(html, /default-src 'none'/);
  assert.match(html, /架空地点・合成デモ/);
  assert.match(html, /安全性・災害時の通行可能性を保証しません/);
  assert.doesNotMatch(html + app + model, /navigator\.geolocation|fetch\s*\(|XMLHttpRequest|https?:\/\//);
  assert.match(deploy, /_copy_tree\(root \/ "gis" \/ "gis", output_dir \/ "gis" \/ "gis"\)/);
  assert.doesNotMatch(deploy, /_copy_tree\(root \/ "gis", output_dir/);
});
