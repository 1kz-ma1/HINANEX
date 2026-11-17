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

  function createSession() {
    let start = null;
    let destination = null;
    let condition = CONDITIONS[0];
    let route = null;
    let status = 'UNSELECTED';
    let reason = '出発点と目的地を明示的に選んでください。';
    let revision = 0;
    function snapshot() {
      return Object.freeze({ start: start && start.id, destination: destination && destination.id,
        condition: condition.id, status, reason, revision,
        route: route && Object.freeze({
          points: Object.freeze(route.points.map(p => Object.freeze([...p]))),
          revision: route.revision
        }) });
    }
    function invalidate() {
      revision += 1;
      route = null;
      status = start && destination ? 'READY' : 'UNSELECTED';
      reason = status === 'READY' ? '条件が変更されました。表示するには再生成してください。'
        : '出発点と目的地を明示的に選んでください。';
      return snapshot();
    }
    return Object.freeze({
      getState: snapshot,
      setStart(id) { start = choose(STARTS, id); return invalidate(); },
      setDestination(id) { destination = choose(DESTINATIONS, id); return invalidate(); },
      setCondition(id) { condition = choose(CONDITIONS, id) || CONDITIONS[0]; return invalidate(); },
      clear() { return invalidate(); },
      generate(options = {}) {
        // Delete the old geometry BEFORE validation or any possible failure.
        revision += 1;
        route = null;
        if (!start || !destination) {
          status = 'NO_GO'; reason = 'NO-GO：出発点と目的地の明示選択が必要です。';
        } else if (options.fail === true) {
          status = 'NO_GO'; reason = 'NO-GO：合成経路を作成できませんでした。旧経路は破棄しました。';
        } else {
          const via = condition.id === 'pattern-1'
            ? [[235, start.y], [400, destination.y]]
            : [[205, 190], [420, 190]];
          route = { points: [[start.x, start.y], ...via, [destination.x, destination.y]], revision };
          status = 'SHOWN';
          reason = '合成模式線を表示しています。現実の経路・安全・通行可能性を示しません。';
        }
        return snapshot();
      }
    });
  }
  return Object.freeze({ STARTS, DESTINATIONS, CONDITIONS, createSession });
});
