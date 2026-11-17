/* DOM adapter for private F04 synthetic prototype: no network, no storage. */
(function () {
  'use strict';
  const model = window.HINANEX_F04;
  if (!model) throw new Error('F04 state model unavailable');
  const session = model.createSession();
  const $ = id => document.getElementById(id);
  const select = $('scenario');
  const slider = $('step');
  const grid = $('floodGrid');
  const play = $('play');
  const pause = $('pause');
  const restart = $('restart');
  const clear = $('clear');
  let timer = null;

  for (const item of model.SCENARIOS) {
    const option = document.createElement('option');
    option.value = item.id;
    option.textContent = item.label;
    select.appendChild(option);
  }
  for (let row = 0; row < model.ROWS; row++) {
    for (let col = 0; col < model.COLS; col++) {
      const cell = document.createElement('span');
      cell.className = 'cell';
      cell.dataset.cell = `${row}-${col}`;
      cell.setAttribute('aria-hidden', 'true');
      grid.appendChild(cell);
    }
  }
  const cells = [...grid.querySelectorAll('.cell')];
  function stopTimer() {
    if (timer !== null) window.clearInterval(timer);
    timer = null;
  }
  function render() {
    const state = session.getState();
    const hasFrame = state.index !== null && state.status !== 'NO_GO';
    const painted = hasFrame ? new Set(state.cells) : new Set();
    for (const cell of cells) cell.classList.toggle('filled', painted.has(cell.dataset.cell));
    grid.dataset.paintedCount = String(painted.size);
    grid.setAttribute('aria-label', hasFrame
      ? `完全架空の訓練用模式グリッド。${state.label}、塗られたセル${painted.size}個。実際の安全・浸水・地図を示しません。`
      : '訓練用の模式グリッド。NO-GO、合成データの表示はありません。');
    $('emptyOverlay').hidden = hasFrame;
    $('emptyOverlay').textContent = state.status === 'NO_GO' ? 'NO-GO｜合成データを表示できません' : 'シナリオ未選択｜NO-GO';
    slider.disabled = !hasFrame;
    slider.max = String(state.lastIndex ?? 0);
    slider.value = String(state.index ?? 0);
    $('timeLabel').textContent = hasFrame ? `${state.label} / 全${state.lastIndex + 1}ステップ` : '未選択';
    play.disabled = !hasFrame || state.status === 'PLAYING';
    pause.disabled = state.status !== 'PLAYING';
    restart.disabled = !hasFrame;
    $('status').textContent = state.reason;
    $('status').dataset.state = state.status;
    $('status').dataset.reasonCode = state.reasonCode;
    $('nextAction').textContent = state.status === 'NO_GO'
      ? '架空シナリオを明示的に選び直してください。前の模式図は消去されています。'
      : state.status === 'UNSELECTED'
        ? '架空シナリオの選択が必要です。'
        : '再生・一時停止・スライダーを操作できます。現実の時間ではありません。';
    if (state.status !== 'PLAYING') stopTimer();
  }
  function change(action) { stopTimer(); action(); render(); }
  select.addEventListener('change', () => change(() => session.select(select.value)));
  play.addEventListener('click', () => {
    stopTimer();
    const state = session.play();
    render();
    if (state.status !== 'PLAYING') return;
    const generation = state.generation;
    timer = window.setInterval(() => {
      session.step(generation);
      render();
    }, 850);
  });
  pause.addEventListener('click', () => change(() => session.pause()));
  restart.addEventListener('click', () => change(() => session.restart()));
  clear.addEventListener('click', () => {
    change(() => session.clear());
    select.value = '';
    select.focus({ preventScroll: true });
  });
  slider.addEventListener('input', () => change(() => session.seek(Number(slider.value))));
  render();
})();
