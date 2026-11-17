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
  const status = $('status');
  const action = $('generate');
  const clear = $('clear');

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
    $('diagram').setAttribute('aria-label', state.route
      ? '架空地点の模式経路を表示中。地理的な位置や安全性を示さない図です。'
      : '架空の出発点と目的地を示す模式図。現在、経路は表示されていません。');
    const startLabel = model.STARTS.find(item => item.id === state.start)?.label || '未選択';
    const destinationLabel = model.DESTINATIONS.find(item => item.id === state.destination)?.label || '未選択';
    const conditionLabel = model.CONDITIONS.find(item => item.id === state.condition)?.label || '未対応（NO-GO）';
    $('selectionSummary').textContent = `選択：${startLabel} → ${destinationLabel} / ${conditionLabel}。${state.route ? '模式線を表示中' : '模式線は未表示'}。`;
    status.textContent = state.reason;
    status.dataset.state = state.status;
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
  draw();
})();
