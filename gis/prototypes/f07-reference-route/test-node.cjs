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

test('unsupported condition fails closed and cannot reuse stale schematic', () => {
  const s = createSession();
  s.setStart('start-a'); s.setDestination('goal-x');
  const shown = s.generate();
  assert.equal(shown.status, 'SHOWN');
  const invalid = s.setCondition('walking-time-or-route-api');
  assert.equal(invalid.condition, null);
  assert.equal(invalid.status, 'NO_GO');
  assert.match(invalid.reason, /NO-GO/);
  assert.equal(invalid.route, null);
  const stillInvalid = s.generate();
  assert.equal(stillInvalid.status, 'NO_GO');
  assert.equal(stillInvalid.route, null);
  assert.ok(stillInvalid.revision > shown.revision);
  assert.equal(s.setCondition('pattern-2').status, 'READY');
  const recovered = s.generate();
  assert.equal(recovered.status, 'SHOWN');
  assert.deepEqual(recovered.route.points[1], [205, 190]);
});

test('repeated selection and condition edits never resurrect stale route geometry', () => {
  const s = createSession();
  s.setStart('start-a'); s.setDestination('goal-x');
  let previous = s.generate().revision;
  for (let i = 0; i < 32; i++) {
    const mutation = i % 4 === 0 ? s.setDestination('goal-y')
      : i % 4 === 1 ? s.setStart('start-b')
      : i % 4 === 2 ? s.setCondition('pattern-2')
      : s.setCondition('pattern-1');
    assert.equal(mutation.route, null);
    assert.equal(mutation.status, 'READY');
    assert.ok(mutation.revision > previous);
    const current = s.generate();
    assert.equal(current.status, 'SHOWN');
    assert.equal(current.route.revision, current.revision);
    previous = current.revision;
  }
});

test('reason codes provide actionable guidance without claiming real-route safety', () => {
  const s = createSession();
  assert.equal(s.getState().reasonCode, 'POINTS_REQUIRED');
  assert.match(s.getState().nextAction, /架空の出発点/);
  assert.equal(s.generate().reasonCode, 'POINTS_REQUIRED');
  s.setStart('start-a');
  assert.match(s.getState().nextAction, /架空の目的地/);
  s.setDestination('goal-x');
  assert.equal(s.getState().reasonCode, 'READY');
  assert.match(s.getState().nextAction, /模式経路を表示/);
  assert.equal(s.generate().reasonCode, 'SHOWN');
  assert.match(s.getState().nextAction, /表示を解除/);
  const denied = s.setCondition('unsupported-pattern');
  assert.equal(denied.reasonCode, 'UNSUPPORTED_CONDITION');
  assert.match(denied.nextAction, /選び直してください/);
  assert.equal(denied.route, null);
  const noGo = s.generate();
  assert.equal(noGo.reasonCode, 'UNSUPPORTED_CONDITION');
  assert.equal(noGo.route, null);
  s.setCondition('pattern-2');
  const failed = s.generate({fail: true});
  assert.equal(failed.reasonCode, 'SYNTHETIC_FAILURE');
  assert.match(failed.nextAction, /チェックを外して/);
  assert.equal(failed.route, null);
  assert.doesNotMatch(failed.nextAction, /(?:安全な避難先|通行可能です|実際の経路を案内)/);
});

test('reset clears selections, failure aftermath, and geometry with monotonic revision', () => {
  const s = createSession();
  s.setStart('start-b'); s.setDestination('goal-y'); s.setCondition('pattern-2');
  const shown = s.generate();
  const reset = s.reset();
  assert.equal(reset.start, null);
  assert.equal(reset.destination, null);
  assert.equal(reset.condition, 'pattern-1');
  assert.equal(reset.status, 'UNSELECTED');
  assert.equal(reset.reasonCode, 'POINTS_REQUIRED');
  assert.equal(reset.route, null);
  assert.ok(reset.revision > shown.revision);
  assert.equal(s.generate().status, 'NO_GO');
  const afterNoGo = s.reset();
  assert.equal(afterNoGo.status, 'UNSELECTED');
  assert.equal(afterNoGo.route, null);
  assert.equal(afterNoGo.condition, 'pattern-1');
  assert.equal(s.reset().route, null);
  s.setStart('start-a'); s.setDestination('goal-x');
  assert.equal(s.generate().status, 'SHOWN');
});

test('one live status region announces error plus recovery; explicit reset is separate from line clear', () => {
  const html = fs.readFileSync(path.join(here, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(here, 'app.js'), 'utf8');
  assert.equal((html.match(/role="status"/g) || []).length, 1);
  assert.match(html, /<div class="feedback" role="status" aria-live="polite" aria-atomic="true">/);
  assert.match(html, /id="nextAction"/);
  assert.match(html, /id="reset" type="button"/);
  assert.match(app, /session\.reset\(\)/);
  assert.match(app, /origin\.focus\(\)/);
});

test('comparison is explicit, diagram-only, and never auto-selected or recommended', () => {
  const s = createSession();
  assert.equal(s.getState().comparison, null);
  assert.equal(s.showComparison().comparison, null);
  s.setStart('start-a'); s.setDestination('goal-y');
  assert.equal(s.showComparison().comparison, null);
  const shown = s.generate();
  assert.equal(shown.comparison, null);
  const compared = s.showComparison();
  assert.equal(compared.status, 'SHOWN');
  assert.equal(compared.condition, 'pattern-1');
  assert.equal(compared.comparison.pattern, 'pattern-2');
  assert.deepEqual(compared.route.points, shown.route.points);
  assert.equal(compared.comparison.revision, compared.route.revision);
  assert.notDeepEqual(compared.comparison.points, compared.route.points);
  assert.deepEqual(compared.comparison.points[0], compared.route.points[0]);
  assert.deepEqual(compared.comparison.points.at(-1), compared.route.points.at(-1));
  assert.equal(s.showComparison().revision, shown.revision);
  assert.equal(s.hideComparison().comparison, null);
  assert.deepEqual(s.getState().route.points, shown.route.points);
});

test('comparison is purged before any reselect, failure, clear, reset or regeneration', () => {
  const changes = [
    s => s.setStart('start-b'),
    s => s.setDestination('goal-x'),
    s => s.setCondition('pattern-2'),
    s => s.setCondition('unknown-pattern'),
    s => s.generate({fail: true}),
    s => s.clear(),
    s => s.reset(),
    s => s.generate()
  ];
  for (const mutate of changes) {
    const s = createSession();
    s.setStart('start-a'); s.setDestination('goal-y');
    s.generate();
    assert.ok(s.showComparison().comparison);
    const before = s.getState().revision;
    const result = mutate(s);
    assert.equal(result.comparison, null);
    assert.ok(result.revision >= before);
    assert.equal(s.hideComparison().comparison, null);
    if (result.status !== 'SHOWN') {
      assert.equal(s.showComparison().comparison, null);
    } else {
      assert.equal(s.showComparison().comparison?.revision, result.route.revision);
    }
  }
});

test('comparison snapshot geometry is deeply immutable and safe UI labels stay limited to drawing shape', () => {
  const s = createSession();
  s.setStart('start-b'); s.setDestination('goal-x'); s.setCondition('pattern-2');
  s.generate();
  const v = s.showComparison();
  assert.equal(v.comparison.pattern, 'pattern-1');
  assert.throws(() => { v.comparison.points[0][0] = 999; }, TypeError);
  assert.throws(() => { v.comparison.pattern = 'pattern-9'; }, TypeError);
  assert.deepEqual(s.getState().comparison.points[0], [84, 290]);
  const html = fs.readFileSync(path.join(here, 'index.html'), 'utf8');
  const app = fs.readFileSync(path.join(here, 'app.js'), 'utf8');
  assert.match(html, /id="compare"[^>]*aria-pressed="false"/);
  assert.match(html, /id="routeLineAlternative"/);
  assert.match(app, /安全性・優劣は判断しません/);
  assert.doesNotMatch(html + app, /navigator\.geolocation|fetch\s*\(|XMLHttpRequest|https?:\/\//);
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
