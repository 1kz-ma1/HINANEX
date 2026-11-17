/* F04 S2: synthetic-only comparison; row-col identifiers are diagram indices. */
(function (root, factory) {
  'use strict';
  const api = factory(root && root.HINANEX_F04,
    typeof module === 'object' && module.exports ? require('./timeline-model.js') : null);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HINANEX_F04_COMPARE = api;
})(typeof window !== 'undefined' ? window : null, function (browserCore, nodeCore) {
  'use strict';
  const core = nodeCore || browserCore;
  if (!core || !core.validScenario) throw new Error('F04 S1 model missing');

  function classify(before, after) {
    const oldCells = new Set(before);
    const newCells = new Set(after);
    const added = [], removed = [], continued = [], empty = [];
    // Diagram order only. These are NOT world coordinates or measured areas.
    for (let row = 0; row < core.ROWS; row++) {
      for (let col = 0; col < core.COLS; col++) {
        const cell = `${row}-${col}`;
        if (oldCells.has(cell) && newCells.has(cell)) continued.push(cell);
        else if (oldCells.has(cell)) removed.push(cell);
        else if (newCells.has(cell)) added.push(cell);
        else empty.push(cell);
      }
    }
    return {added, removed, continued, empty};
  }

  function createComparisonSession(fixtures = core.SCENARIOS) {
    let scenario = null;
    let before = null;
    let after = null;
    let result = null;
    let status = 'UNSELECTED';
    let reasonCode = 'SCENARIO_REQUIRED';
    let reason = '架空シナリオを先に選択してください。';
    let revision = 0;

    function snapshot() {
      const comparison = result ? Object.freeze({
        before: result.before,
        after: result.after,
        beforeCells: Object.freeze([...result.beforeCells]),
        afterCells: Object.freeze([...result.afterCells]),
        added: Object.freeze([...result.added]),
        removed: Object.freeze([...result.removed]),
        continued: Object.freeze([...result.continued]),
        empty: Object.freeze([...result.empty]),
        summary: result.summary,
        revision: result.revision
      }) : null;
      return Object.freeze({
        scenarioId: scenario ? scenario.id : null,
        stepCount: scenario ? scenario.frames.length : 0,
        before, after, comparison, status, reasonCode, reason, revision
      });
    }
    function fail(code, message) {
      revision += 1;
      result = null;
      status = 'NO_GO';
      reasonCode = code;
      reason = message;
      return snapshot();
    }
    function choose(field, value) {
      revision += 1;
      result = null; // A changed input immediately erases every previously shown comparison.
      if (!scenario) return fail('SCENARIO_REQUIRED', 'NO-GO：架空シナリオを選択してください。');
      if (value !== null && (!Number.isInteger(value) || value < 0 || value >= scenario.frames.length)) {
        before = null;
        after = null;
        return fail('INVALID_STEP', 'NO-GO：不正な模擬ステップです。古い比較を破棄しました。');
      }
      if (field === 'before') before = value;
      else after = value;
      status = before === null || after === null ? 'SELECTING' : 'READY';
      reasonCode = status;
      reason = status === 'READY'
        ? '比較する2ステップを選びました。「2時点を比較」で結果を表示します。'
        : '比較元と比較先の2ステップを明示選択してください。';
      return snapshot();
    }

    return Object.freeze({
      getState: snapshot,
      selectScenario(id) {
        revision += 1;
        scenario = null;
        before = null;
        after = null;
        result = null;
        if (id === '') {
          status = 'UNSELECTED'; reasonCode = 'SCENARIO_REQUIRED';
          reason = '架空シナリオを先に選択してください。';
          return snapshot();
        }
        const candidate = Array.isArray(fixtures) ? fixtures.find(s => s && s.id === id) : null;
        if (!candidate || !core.validScenario(candidate) ||
            fixtures.filter(s => s && s.id === id).length !== 1) {
          return fail('INVALID_SCENARIO', 'NO-GO：欠損・不正・未対応の架空シナリオです。比較は表示しません。');
        }
        // Keep an isolated snapshot: future fixture mutation cannot rewrite the active comparison.
        scenario = {
          id: candidate.id,
          frames: candidate.frames.map(f => ({cells: [...f.cells]}))
        };
        status = 'SELECTING'; reasonCode = 'STEP_PAIR_REQUIRED';
        reason = '比較元と比較先の模擬ステップを選択してください。';
        return snapshot();
      },
      setBefore(index) { return choose('before', index); },
      setAfter(index) { return choose('after', index); },
      compare() {
        revision += 1;
        result = null; // Always remove the old result BEFORE any validation.
        if (!scenario) return fail('SCENARIO_REQUIRED', 'NO-GO：架空シナリオは未選択です。');
        const valid = value => Number.isInteger(value) && value >= 0 && value < scenario.frames.length;
        if (!valid(before) || !valid(after)) {
          return fail('STEP_PAIR_REQUIRED', 'NO-GO：比較する2つの模擬ステップを選択してください。');
        }
        const beforeCells = [...scenario.frames[before].cells];
        const afterCells = [...scenario.frames[after].cells];
        const delta = classify(beforeCells, afterCells);
        result = {
          before, after, beforeCells, afterCells, ...delta, revision,
          summary: `架空の模擬ステップ ${before} → ${after}：新規着色 ${delta.added.length}セル、着色解除 ${delta.removed.length}セル、着色継続 ${delta.continued.length}セル、無着色継続 ${delta.empty.length}セル。現実の浸水面積・深さ・危険度・時間・安全性を示しません。`
        };
        status = 'SHOWN'; reasonCode = 'COMPARISON_SHOWN';
        reason = '完全架空の2時点とセルの変化を表示中です。';
        return snapshot();
      },
      clear() {
        revision += 1;
        scenario = null; before = null; after = null; result = null;
        status = 'UNSELECTED'; reasonCode = 'SCENARIO_REQUIRED';
        reason = '架空シナリオを先に選択してください。';
        return snapshot();
      }
    });
  }
  return Object.freeze({classify, createComparisonSession});
});
