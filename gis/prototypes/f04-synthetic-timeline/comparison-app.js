/* F04 S2 UI adapter. Never reads geolocation, requests APIs or mutates S1 playback. */
(function () {
  'use strict';
  const comparison = window.HINANEX_F04_COMPARE;
  if (!comparison) throw new Error('F04 comparison model unavailable');
  const state = comparison.createComparisonSession();
  const $ = id => document.getElementById(id);
  const scenario = $('scenario');
  const fromSelect = $('compareBefore');
  const toSelect = $('compareAfter');
  const compareButton = $('compareRun');
  const clearButton = $('compareClear');
  const panels = [
    {id: 'compareGridBefore', overlay: 'compareOverlayBefore', kind: 'beforeCells'},
    {id: 'compareGridAfter', overlay: 'compareOverlayAfter', kind: 'afterCells'},
    {id: 'compareGridDelta', overlay: 'compareOverlayDelta', kind: 'delta'}
  ];
  const gridCells = new Map();

  for (const panel of panels) {
    const grid = $(panel.id);
    const cells = [];
    for (let row = 0; row < window.HINANEX_F04.ROWS; row++) {
      for (let col = 0; col < window.HINANEX_F04.COLS; col++) {
        const el = document.createElement('span');
        el.className = 'compare-cell';
        el.dataset.cell = `${row}-${col}`;
        el.setAttribute('aria-hidden', 'true');
        grid.appendChild(el);
        cells.push(el);
      }
    }
    gridCells.set(panel.id, cells);
  }

  function resetSteps() {
    for (const select of [fromSelect, toSelect]) {
      const placeholder = document.createElement('option');
      placeholder.value = '';
      placeholder.textContent = '模擬ステップを選択';
      select.replaceChildren(placeholder);
      const count = state.getState().stepCount;
      for (let i = 0; i < count; i++) {
        const option = document.createElement('option');
        option.value = String(i);
        option.textContent = `模擬ステップ ${i}`;
        select.appendChild(option);
      }
      select.value = '';
    }
  }

  function paint(panel, result) {
    const grid = $(panel.id);
    const elements = gridCells.get(panel.id);
    const active = result !== null;
    const classifications = active && panel.kind === 'delta' ? [
      ['newly', new Set(result.added)],
      ['removed', new Set(result.removed)],
      ['continued', new Set(result.continued)],
      ['empty', new Set(result.empty)]
    ] : [];
    const filled = active && panel.kind !== 'delta' ? new Set(result[panel.kind]) : new Set();
    for (const el of elements) {
      el.className = 'compare-cell';
      if (!active) continue;
      if (panel.kind === 'delta') {
        for (const [category, set] of classifications) {
          if (set.has(el.dataset.cell)) { el.classList.add('compare-' + category); break; }
        }
      } else if (filled.has(el.dataset.cell)) el.classList.add('compare-filled');
    }
    grid.dataset.active = active ? 'true' : 'false';
    grid.dataset.filledCount = active
      ? String(panel.kind === 'delta' ? result.added.length + result.removed.length + result.continued.length : filled.size)
      : '0';
    grid.setAttribute('aria-label', !active
      ? '完全架空の比較グリッド。NO-GO、結果は未表示。'
      : panel.kind === 'delta'
        ? `完全架空の差分模式図。新規着色${result.added.length}、着色解除${result.removed.length}、着色継続${result.continued.length}、無着色継続${result.empty.length}セル。現実の浸水ではありません。`
        : `完全架空の${panel.kind === 'beforeCells' ? '比較元' : '比較先'}グリッド。${filled.size}セル着色。実際の浸水を示しません。`);
    const overlay = $(panel.overlay);
    overlay.hidden = active;
    overlay.textContent = '比較結果未表示｜NO-GO';
  }

  function render() {
    const s = state.getState();
    const validScenario = Boolean(s.scenarioId);
    fromSelect.disabled = !validScenario;
    toSelect.disabled = !validScenario;
    compareButton.disabled = !validScenario || s.before === null || s.after === null;
    clearButton.disabled = !validScenario;
    $('compareStatus').dataset.state = s.status;
    $('compareStatus').dataset.reasonCode = s.reasonCode;
    $('compareStatus').textContent = s.reason;
    $('comparisonSummary').textContent = s.comparison
      ? s.comparison.summary
      : 'NO-GO：比較結果は未表示です。2つの模擬ステップを明示選択して比較してください。';
    for (const panel of panels) paint(panel, s.comparison);
    const delta = s.comparison;
    $('comparisonCounts').hidden = !delta;
    if (delta) {
      for (const [id, count] of [
        ['addedCount', delta.added.length], ['removedCount', delta.removed.length],
        ['continuedCount', delta.continued.length], ['emptyCount', delta.empty.length]
      ]) $(id).textContent = String(count);
    } else {
      for (const id of ['addedCount', 'removedCount', 'continuedCount', 'emptyCount']) $(id).textContent = '—';
    }
  }

  scenario.addEventListener('change', () => {
    state.selectScenario(scenario.value); // always clears old comparison before new case
    resetSteps();
    render();
  });
  $('clear').addEventListener('click', () => {
    state.clear(); // S1 clears the scenario in its own handler
    resetSteps();
    render();
  });
  fromSelect.addEventListener('change', () => {
    state.setBefore(fromSelect.value === '' ? null : Number(fromSelect.value));
    render();
  });
  toSelect.addEventListener('change', () => {
    state.setAfter(toSelect.value === '' ? null : Number(toSelect.value));
    render();
  });
  compareButton.addEventListener('click', () => { state.compare(); render(); });
  clearButton.addEventListener('click', () => {
    state.selectScenario(scenario.value);
    resetSteps();
    render();
    fromSelect.focus({preventScroll:true});
  });

  resetSteps();
  render();
})();
