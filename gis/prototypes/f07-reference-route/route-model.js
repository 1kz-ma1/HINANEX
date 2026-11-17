/* F07 local synthetic-only state model. Diagram coordinates are SVG units, not geography. */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HINANEX_F07 = api;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const STARTS = Object.freeze([
    Object.freeze({ id: 'start-a', label: '架空の出発点 A', x: 84, y: 90 }),
    Object.freeze({ id: 'start-b', label: '架空の出発点 B', x: 84, y: 290 })
  ]);
  const DESTINATIONS = Object.freeze([
    Object.freeze({ id: 'goal-x', label: '架空の目的地 X', x: 550, y: 90 }),
    Object.freeze({ id: 'goal-y', label: '架空の目的地 Y', x: 550, y: 290 })
  ]);
  const CONDITIONS = Object.freeze([
    Object.freeze({ id: 'pattern-1', label: '模式線パターン 1' }),
    Object.freeze({ id: 'pattern-2', label: '模式線パターン 2' })
  ]);
  const choose = (items, id) => items.find(item => item.id === id) || null;
  function pointsFor(start, destination, patternId) {
    const via = patternId === 'pattern-1'
      ? [[235, start.y], [400, destination.y]]
      : [[205, 190], [420, 190]];
    return [[start.x, start.y], ...via, [destination.x, destination.y]];
  }

  function createSession() {
    let start = null;
    let destination = null;
    let condition = CONDITIONS[0];
    let route = null;
    let comparison = null;
    let status = 'UNSELECTED';
    let reason = '出発点と目的地を明示的に選んでください。';
    let reasonCode = 'POINTS_REQUIRED';
    let nextAction = 'まず架空の出発点と目的地を選択してください。';
    let revision = 0;
    function snapshot() {
      return Object.freeze({ start: start && start.id, destination: destination && destination.id,
        condition: condition && condition.id, status, reason, reasonCode, nextAction, revision,
        route: route && Object.freeze({
          points: Object.freeze(route.points.map(p => Object.freeze([...p]))),
          revision: route.revision
        }),
        comparison: comparison && Object.freeze({
          pattern: comparison.pattern,
          points: Object.freeze(comparison.points.map(p => Object.freeze([...p]))),
          revision: comparison.revision
        }) });
    }
    function invalidate() {
      revision += 1;
      route = null;
      comparison = null;
      status = !condition ? 'NO_GO' : start && destination ? 'READY' : 'UNSELECTED';
      reason = !condition ? 'NO-GO：未対応の表示条件です。模式線パターンを明示的に選び直してください。'
        : status === 'READY' ? '条件が変更されました。表示するには再生成してください。'
        : '出発点と目的地を明示的に選んでください。';
      reasonCode = !condition ? 'UNSUPPORTED_CONDITION'
        : status === 'READY' ? 'READY' : 'POINTS_REQUIRED';
      nextAction = !condition ? '表示条件から模式線パターン1または2を明示的に選び直してください。'
        : status === 'READY' ? '「模式経路を表示」を選ぶと、架空地点だけの模式線を生成します。'
        : !start && !destination ? 'まず架空の出発点と目的地を選択してください。'
        : !start ? '架空の出発点を選択してください。'
        : '架空の目的地を選択してください。';
      return snapshot();
    }
    return Object.freeze({
      getState: snapshot,
      setStart(id) { start = choose(STARTS, id); return invalidate(); },
      setDestination(id) { destination = choose(DESTINATIONS, id); return invalidate(); },
      setCondition(id) { condition = choose(CONDITIONS, id); return invalidate(); },
      clear() { return invalidate(); },
      showComparison() {
        // No auto-routing: only an explicit action after a successful synthetic draw.
        if (status !== 'SHOWN' || !route || route.revision !== revision ||
            !start || !destination || !condition) {
          comparison = null;
          return snapshot();
        }
        const other = condition.id === 'pattern-1' ? 'pattern-2' : 'pattern-1';
        comparison = {pattern: other, points: pointsFor(start, destination, other), revision};
        return snapshot();
      },
      hideComparison() { comparison = null; return snapshot(); },
      reset() {
        start = null;
        destination = null;
        condition = CONDITIONS[0];
        return invalidate();
      },
      generate(options = {}) {
        // Delete the old geometry BEFORE validation or any possible failure.
        revision += 1;
        route = null;
        comparison = null;
        if (!condition) {
          status = 'NO_GO'; reason = 'NO-GO：未対応の表示条件です。模式線パターンを明示的に選び直してください。';
          reasonCode = 'UNSUPPORTED_CONDITION';
          nextAction = '表示条件から模式線パターン1または2を明示的に選び直してください。';
        } else if (!start || !destination) {
          status = 'NO_GO'; reason = 'NO-GO：出発点と目的地の明示選択が必要です。';
          reasonCode = 'POINTS_REQUIRED';
          nextAction = !start && !destination ? '架空の出発点と目的地を選択してください。'
            : !start ? '架空の出発点を選択してください。' : '架空の目的地を選択してください。';
        } else if (options.fail === true) {
          status = 'NO_GO'; reason = 'NO-GO：合成経路を作成できませんでした。旧経路は破棄しました。';
          reasonCode = 'SYNTHETIC_FAILURE';
          nextAction = '「経路生成失敗を合成する」のチェックを外してから、もう一度「模式経路を表示」を選んでください。';
        } else {
          route = { points: pointsFor(start, destination, condition.id), revision };
          status = 'SHOWN';
          reason = '合成模式線を表示しています。現実の経路・安全・通行可能性を示しません。';
          reasonCode = 'SHOWN';
          nextAction = '選択や条件を変更すると以前の模式線は消えます。「表示を解除」でも消去できます。';
        }
        return snapshot();
      }
    });
  }
  return Object.freeze({ STARTS, DESTINATIONS, CONDITIONS, createSession });
});
