/* F04 private fictional state machine. Grid indices are never real-world coordinates. */
(function (root, factory) {
  'use strict';
  const api = factory(root && root.HINANEX_F04_DATA,
    typeof module === 'object' && module.exports ? require('./synthetic-data.js') : null);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.HINANEX_F04 = api;
})(typeof window !== 'undefined' ? window : null, function (browserData, nodeData) {
  'use strict';
  const { ROWS, COLS, SCENARIOS } = nodeData || browserData || {};
  if (!Number.isInteger(ROWS) || !Number.isInteger(COLS) || !Array.isArray(SCENARIOS)) {
    throw new Error('F04 synthetic fixture missing');
  }
  function validScenario(s) {
    if (!s || typeof s !== 'object' || typeof s.id !== 'string' || !/^fiction-[a-z]$/.test(s.id) ||
        typeof s.label !== 'string' || !s.label.startsWith('架空') ||
        !Array.isArray(s.frames) || s.frames.length < 2 || s.frames.length > 12) return false;
    return s.frames.every((f, index) => {
      if (!f || f.label !== `模擬ステップ ${index}` || !Array.isArray(f.cells)) return false;
      const unique = new Set();
      for (const cell of f.cells) {
        if (typeof cell !== 'string' || !/^(0|[1-9][0-9]*)-(0|[1-9][0-9]*)$/.test(cell)) return false;
        const [row, col] = cell.split('-').map(Number);
        if (row >= ROWS || col >= COLS || unique.has(cell)) return false;
        unique.add(cell);
      }
      return true;
    });
  }
  function createSession(fixtures = SCENARIOS) {
    let scenario = null;
    let index = null;
    let status = 'UNSELECTED';
    let reason = '架空シナリオを明示的に選択してください。';
    let reasonCode = 'SCENARIO_REQUIRED';
    let generation = 0;
    function snapshot() {
      const frame = scenario && index !== null ? scenario.frames[index] : null;
      return Object.freeze({
        scenarioId: scenario ? scenario.id : null, status, reason, reasonCode,
        index, lastIndex: scenario ? scenario.frames.length - 1 : null,
        label: frame ? frame.label : null,
        cells: Object.freeze(frame ? [...frame.cells] : []), generation
      });
    }
    function purge(nextStatus, code, message) {
      generation += 1;
      scenario = null;
      index = null;
      status = nextStatus;
      reasonCode = code;
      reason = message;
      return snapshot();
    }
    return Object.freeze({
      getState: snapshot,
      select(id) {
        // Immediately drop the old frame and invalidate any in-flight timer callback.
        if (id === '') return purge('UNSELECTED', 'SCENARIO_REQUIRED', '架空シナリオを選択してください。');
        const candidate = Array.isArray(fixtures) ? fixtures.find(s => s && s.id === id) : null;
        if (!candidate || !validScenario(candidate) ||
            fixtures.filter(s => s && s.id === id).length !== 1) {
          return purge('NO_GO', 'INVALID_SCENARIO', 'NO-GO：未対応・欠損・不正な合成シナリオです。旧表示を破棄しました。');
        }
        generation += 1;
        // Copy all cell arrays; subsequent fixture mutation cannot change the active view.
        scenario = { id: candidate.id, frames: candidate.frames.map(f => ({
          label: f.label, cells: [...f.cells]
        })) };
        index = 0;
        status = 'PAUSED';
        reasonCode = 'READY';
        reason = '合成ステップを表示中。再生・スライダーで切り替えられます。';
        return snapshot();
      },
      play() {
        if (!scenario || index === null) {
          return purge('NO_GO', 'SCENARIO_REQUIRED', 'NO-GO：架空シナリオの選択が必要です。');
        }
        generation += 1;
        if (index === scenario.frames.length - 1) index = 0;
        status = 'PLAYING';
        reasonCode = 'PLAYING';
        reason = '合成ステップを再生中。実際の洪水の進行や所要時間ではありません。';
        return snapshot();
      },
      pause() {
        generation += 1;
        if (!scenario) return purge('NO_GO', 'SCENARIO_REQUIRED', 'NO-GO：シナリオは未選択です。');
        status = 'PAUSED';
        reasonCode = 'PAUSED';
        reason = '一時停止しました。模式図のみを示しています。';
        return snapshot();
      },
      seek(position) {
        generation += 1;
        if (!scenario || !Number.isInteger(position) || position < 0 || position >= scenario.frames.length) {
          return purge('NO_GO', 'INVALID_STEP', 'NO-GO：時点が未選択または範囲外です。旧表示を破棄しました。');
        }
        index = position;
        status = 'PAUSED';
        reasonCode = 'PAUSED';
        reason = '選択した合成ステップを表示中。実時間や予測ではありません。';
        return snapshot();
      },
      step(expectedGeneration) {
        // A late timeout must never change the new scenario after switch/restart/pause.
        if (status !== 'PLAYING' || expectedGeneration !== generation || !scenario) return snapshot();
        if (index < scenario.frames.length - 1) index += 1;
        if (index === scenario.frames.length - 1) {
          generation += 1;
          status = 'PAUSED'; reasonCode = 'ENDED';
          reason = '合成再生が終了しました。もう一度再生すると最初から表示します。';
        }
        return snapshot();
      },
      restart() {
        generation += 1;
        if (!scenario) return purge('NO_GO', 'SCENARIO_REQUIRED', 'NO-GO：架空シナリオが選択されていません。');
        index = 0; status = 'PAUSED'; reasonCode = 'RESTARTED';
        reason = '最初の合成ステップへ戻りました。';
        return snapshot();
      },
      clear() {
        return purge('UNSELECTED', 'SCENARIO_REQUIRED', '架空シナリオを選択してください。');
      }
    });
  }
  return Object.freeze({ ROWS, COLS, SCENARIOS, validScenario, createSession });
});
