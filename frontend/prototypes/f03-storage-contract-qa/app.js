/* HINANEX independent demo. No backend, no location permission, no network request. */
(() => {
  'use strict';
  const STORAGE_KEY = 'hinanex.preparedness.demo.v1';
  const SCHEMA_VERSION = 1;
  const REGIONS = Object.freeze({
    '13123': '東京都 江戸川区',
    '15100': '新潟県 新潟市',
    '23100': '愛知県 名古屋市'
  });
  const state = { region: null, mode: 'none', canStore: true, loadIssue: null, view: 'setup' };
  const $ = id => document.getElementById(id);
  const regionInputs = [...document.querySelectorAll('input[name="region"]')];
  const viewButtons = [...document.querySelectorAll('[data-view]')];
  // Deliberate load only: no localStorage read, write, or probe on startup.

  function readSavedRegion() {
    try {
      // A read is triggered only after the user requests saved settings.
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (raw === null) {
        state.region = null;
        state.mode = 'none';
        state.loadIssue = null;
        setFeedback('保存済み設定はありません。保存せずに利用できます。');
        updateDraftSelect();
        updateSavedUI();
        return;
      }
      const data = JSON.parse(raw);
      if (!data || typeof data !== 'object' || Array.isArray(data) ||
          Object.keys(data).sort().join(',') !== 'schema_version,selected_region' ||
          data.schema_version !== SCHEMA_VERSION ||
          typeof data.selected_region !== 'string' ||
          !Object.hasOwn(REGIONS, data.selected_region)) {
        state.region = null;
        state.mode = 'unconfirmed';
        state.loadIssue = '以前の保存内容を読み込めませんでした。地域を選び直してください。';
      } else {
        state.region = data.selected_region;
        state.mode = 'saved';
        state.loadIssue = null;
        setFeedback('保存済み設定を確認しました。', 'success');
      }
    } catch (err) {
      // Storage denial and invalid data are different cases.
      state.region = null;
      state.mode = 'unconfirmed';
      if (err instanceof SyntaxError) {
        state.loadIssue = '保存データの形式を読み込めませんでした。地域を選び直してください。';
      } else {
        state.canStore = false;
        state.loadIssue = 'このブラウザでは端末保存を使用できません。選択内容は再読み込みで消えます。';
      }
    }
    updateDraftSelect();
    updateSavedUI();
    if (state.loadIssue) setFeedback(state.loadIssue, 'warning');
  }

  function updateDraftSelect() {
    regionInputs.forEach(input => { input.checked = input.value === state.region; });
    updateControls();
  }

  function selectedDraft() { return document.querySelector('input[name="region"]:checked')?.value ?? null; }

  function updateControls() {
    const draft = selectedDraft();
    $('save-btn').disabled = draft === null;
    $('save-btn-label').textContent = state.region && state.region !== draft ? '選んだ地域に更新' : 'この地域を保存';
    $('clear-btn').disabled = state.region === null && state.mode !== 'unconfirmed';
  }

  function setFeedback(message, type = '') {
    $('save-feedback').textContent = message;
    $('save-feedback').className = 'feedback' + (type ? ` ${type}` : '');
  }

  function updateSavedUI() {
    const name = state.region ? REGIONS[state.region] : null;
    $('side-region').textContent = name ?? '地域未設定';
    $('saved-region-display').textContent = name ?? '地域は未設定です';
    $('emergency-region-name').textContent = name ?? '地域未設定';
    if (state.mode === 'saved') {
      $('side-hint').textContent = 'このブラウザに地域コードを保存済み';
      $('save-state-display').textContent = '✓ このブラウザに保存済み';
      $('saved-detail').textContent = '同じ端末・ブラウザで再訪問した場合は「保存済み設定を確認」を押すと読めます。';
      $('emergency-region-detail').textContent = '端末に保存された地域です。リンク先で地域を選び、発表情報を確認してください。';
    } else if (state.mode === 'unconfirmed') {
      $('side-hint').textContent = '端末の保存状況を確認できません';
      $('save-state-display').textContent = '！保存状況は未確認です';
      $('saved-detail').textContent = '表示中の地域と端末の保存内容が異なる可能性があります。「保存済み設定を確認」で再確認するか、「保存を削除」を押してください。削除できない場合はブラウザのサイトデータ設定を確認してください。';
      $('emergency-region-detail').textContent = '端末の保存状況は未確認です。表示中の地域が保存されているとは限りません。';
    } else if (state.mode === 'temporary') {
      $('side-hint').textContent = '一時選択中・再読み込みで消えます';
      $('save-state-display').textContent = '！一時選択（保存できていません）';
      $('saved-detail').textContent = '端末への保存を確認できません。再読み込み後の表示は保証されず、以前の保存内容が復元される場合もあります。';
      $('emergency-region-detail').textContent = '一時選択中です。保存・再読み込み後の復元は保証されません。外部サイトの地域指定とは連動しません。';
    } else {
      $('side-hint').textContent = '登録なしでも公式情報を確認できます';
      $('save-state-display').textContent = 'まだ地域が保存されていません';
      $('saved-detail').textContent = '登録しなくても、緊急時の公式情報へのリンクを使えます。';
      $('emergency-region-detail').textContent = '登録なしでも公式サイトへアクセスできます。各サイトで必要な地域を指定してください。';
    }
    updateControls();
  }

  function saveRegion() {
    const draft = selectedDraft();
    if (!draft || !Object.hasOwn(REGIONS, draft)) {
      setFeedback('地域を選択してください。', 'warning');
      return;
    }
    // Commit the displayed region only after the browser accepts the write.
    // A failed update must never replace an older, still-persisted choice in UI.
    const previousSavedRegion = state.mode === 'saved' ? state.region : null;
    let writeAccepted = false;
    try {
      const payload = JSON.stringify({ selected_region: draft, schema_version: SCHEMA_VERSION });
      window.localStorage.setItem(STORAGE_KEY, payload);
      writeAccepted = true;
      // No "saved" success unless a read-back confirms persistence.
      if (window.localStorage.getItem(STORAGE_KEY) !== payload) throw new Error('write unconfirmed');
      state.region = draft;
      state.canStore = true;
      state.mode = 'saved';
      setFeedback(`${REGIONS[draft]}をこのブラウザに保存しました。`, 'success');
    } catch (err) {
      state.canStore = false;
      if (writeAccepted) {
        // A write can succeed before verification fails. Neither the old nor new
        // value is confirmed: never keep a stale "saved" badge or auto-rollback.
        state.region = previousSavedRegion ?? draft;
        state.mode = 'unconfirmed';
        setFeedback('更新に失敗しました。端末の保存状況を確認できません。表示中の地域と保存内容が異なる場合があります。保存済み設定を再確認するか、保存を削除してください。', 'warning');
      } else if (previousSavedRegion) {
        // Keep the committed region; the draft radio selection remains available to retry.
        state.region = previousSavedRegion;
        state.mode = 'saved';
        setFeedback(`更新に失敗しました。${REGIONS[previousSavedRegion]}の保存内容を引き続き表示しています。選んだ新しい地域は反映されていません。`, 'warning');
      } else {
        state.region = draft;
        state.mode = 'temporary';
        setFeedback('端末に保存できませんでした。一時選択として使えますが、再読み込み後の表示は保証されません。以前の保存内容が残る場合もあります。', 'warning');
      }
    }
    updateSavedUI();
  }

  function clearRegion() {
    if (state.region === null && state.mode !== 'unconfirmed') return;
    try {
      window.localStorage.removeItem(STORAGE_KEY);
      if (window.localStorage.getItem(STORAGE_KEY) !== null) {
        state.mode = 'unconfirmed';
        setFeedback('削除を確認できませんでした。保存データが残っている可能性があります。サイトデータの設定を確認してください。', 'warning');
        updateSavedUI();
        return;
      }
      state.region = null;
      state.mode = 'none';
      regionInputs.forEach(input => { input.checked = false; });
      setFeedback('地域設定を削除しました。再読み込みしても未設定のままです。', 'success');
    } catch (err) {
      // If storage deletion failed, we must not claim it was deleted persistently.
      state.canStore = false;
      state.mode = 'unconfirmed';
      setFeedback('端末の保存データの削除を確認できませんでした。ブラウザのサイトデータ設定を確認してください。', 'warning');
      updateSavedUI();
      return;
    }
    updateSavedUI();
  }

  function showView(name, moveFocus = true) {
    if (name !== 'setup' && name !== 'emergency') return;
    state.view = name;
    $('setup-view').hidden = name !== 'setup';
    $('emergency-view').hidden = name !== 'emergency';
    $('current-breadcrumb').textContent = name === 'setup' ? 'ふだんの準備' : '緊急時の確認';
    document.querySelectorAll('.nav-item').forEach(button => {
      const active = button.dataset.view === name;
      button.classList.toggle('is-active', active);
      if (active) button.setAttribute('aria-current', 'page');
      else button.removeAttribute('aria-current');
    });
    if (moveFocus) {
      window.scrollTo({ top: 0, behavior: 'instant' });
      $(name === 'setup' ? 'setup-title' : 'emergency-title').setAttribute('tabindex', '-1');
      $(name === 'setup' ? 'setup-title' : 'emergency-title').focus({ preventScroll: true });
    }
  }

  function updateConnection() {
    const offline = navigator.onLine === false;
    $('connection-pill').classList.toggle('offline', offline);
    $('connection-label').textContent = offline ? 'オフライン（端末判定）' : 'オンライン表示（端末判定）';
    $('offline-explanation').classList.toggle('is-offline', offline);
    $('offline-message').textContent = offline
      ? '現在オフラインと判定されています。外部の公的サイトから最新情報を確認するには、通信が必要です。保存済みの地域名は表示できます。'
      : '外部の公的サイトを利用するには通信が必要です。通信が切れると最新情報を確認できません。この表示は実際の接続先の正常動作を保証しません。';
  }

  regionInputs.forEach(input => input.addEventListener('change', () => {
    updateControls();
    if (state.region && selectedDraft() !== state.region) setFeedback('地域の変更は「選んだ地域に更新」を押すと反映されます。');
    else if (state.region && selectedDraft() === state.region) setFeedback('現在の設定地域が選ばれています。');
    else setFeedback('「この地域を保存」を押すと、ブラウザ内に登録します。');
  }));
  $('load-btn').addEventListener('click', readSavedRegion);
  $('save-btn').addEventListener('click', saveRegion);
  $('clear-btn').addEventListener('click', clearRegion);
  viewButtons.forEach(btn => btn.addEventListener('click', () => showView(btn.dataset.view)));
  window.addEventListener('online', updateConnection);
  window.addEventListener('offline', updateConnection);
  updateDraftSelect();
  updateSavedUI();
  updateConnection();
})();
