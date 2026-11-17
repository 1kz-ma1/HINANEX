/* DOM adapter for the standalone, non-networked F07 diagram. */
(function () {
  'use strict';
  const model = window.HINANEX_F07;
  if (!model) throw new Error('F07 model unavailable');
  const session = model.createSession();
  const $ = id => document.getElementById(id);
  const origin = $('origin');
  const destination = $('destination');
  const condition = $('condition');
  const fail = $('simulateFailure');
  const line = $('routeLine');
  const alternativeLine = $('routeLineAlternative');
  const compare = $('compare');
  const status = $('status');
  const action = $('generate');
  const clear = $('clear');
  const reset = $('reset');

  function fill(select, entries, emptyLabel) {
    if (emptyLabel) {
      const option = document.createElement('option');
      option.value = ''; option.textContent = emptyLabel; select.appendChild(option);
    }
    for (const entry of entries) {
      const option = document.createElement('option');
      option.value = entry.id; option.textContent = entry.label; select.appendChild(option);
    }
  }
  fill(origin, model.STARTS, '出発点を選択');
  fill(destination, model.DESTINATIONS, '目的地を選択');
  fill(condition, model.CONDITIONS);

  function draw() {
    const state = session.getState();
    line.setAttribute('points', state.route ? state.route.points.map(p => p.join(',')).join(' ') : '');
    if (state.route) line.removeAttribute('hidden');
    else line.setAttribute('hidden', '');
    alternativeLine.setAttribute('points', state.comparison
      ? state.comparison.points.map(p => p.join(',')).join(' ') : '');
    if (state.comparison) alternativeLine.removeAttribute('hidden');
    else alternativeLine.setAttribute('hidden', '');
    compare.disabled = !(state.status === 'SHOWN' && state.route);
    compare.setAttribute('aria-pressed', state.comparison ? 'true' : 'false');
    compare.textContent = state.comparison ? '形の比較を終了' : '2案の形を比較';
    const comparisonNote = $('comparisonNote');
    comparisonNote.hidden = !state.comparison;
    comparisonNote.textContent = state.comparison
      ? '実線は選択中の模式線、破線はもう一方の模式線です。形だけの比較であり、距離・所要時間・安全性・優劣は判断しません。'
      : '';
    $('diagram').setAttribute('aria-label', state.comparison
      ? '架空地点の2本の模式線を形だけ比較中。実線が選択中、破線がもう一方。現実の経路・安全性・優劣を示しません。'
      : state.route
        ? '架空地点の模式経路を表示中。地理的な位置や安全性を示さない図です。'
        : '架空の出発点と目的地を示す模式図。現在、経路は表示されていません。');
    const startLabel = model.STARTS.find(item => item.id === state.start)?.label || '未選択';
    const destinationLabel = model.DESTINATIONS.find(item => item.id === state.destination)?.label || '未選択';
    const conditionLabel = model.CONDITIONS.find(item => item.id === state.condition)?.label || '未対応（NO-GO）';
    $('selectionSummary').textContent = `選択：${startLabel} → ${destinationLabel} / ${conditionLabel}。${state.route ? '模式線を表示中' : '模式線は未表示'}。`;
    status.textContent = state.reason;
    status.dataset.state = state.status;
    status.dataset.reasonCode = state.reasonCode;
    $('nextAction').textContent = state.comparison
      ? '形の比較中です。「形の比較を終了」で破線だけを消せます。実際の道順や安全性は評価していません。'
      : fail.checked && state.status === 'READY'
        ? '合成失敗モードが有効です。「模式経路を表示」を選ぶとNO-GOを再現します。'
        : state.nextAction;
    action.disabled = !(state.start && state.destination && state.condition);
    clear.disabled = state.status === 'UNSELECTED' || state.status === 'READY';
    for (const id of ['start-a', 'start-b', 'goal-x', 'goal-y']) {
      const marker = $(id);
      marker.classList.toggle('selected', state.start === id || state.destination === id);
    }
  }
  origin.addEventListener('change', () => { session.setStart(origin.value); draw(); });
  destination.addEventListener('change', () => { session.setDestination(destination.value); draw(); });
  condition.addEventListener('change', () => { session.setCondition(condition.value); draw(); });
  fail.addEventListener('change', () => { session.clear(); draw(); });
  action.addEventListener('click', () => { session.generate({ fail: fail.checked }); draw(); });
  clear.addEventListener('click', () => { session.clear(); draw(); });
  compare.addEventListener('click', () => {
    if (session.getState().comparison) session.hideComparison();
    else session.showComparison();
    draw();
  });
  reset.addEventListener('click', () => {
    origin.value = '';
    destination.value = '';
    condition.value = model.CONDITIONS[0].id;
    fail.checked = false;
    session.reset();
    draw();
    origin.focus();
  });
  draw();
})();
