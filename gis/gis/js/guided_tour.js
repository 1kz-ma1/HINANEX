(() => {
  "use strict";
  const get = id => document.getElementById(id);
  const api = window.HINANEX_PRESENTATION_TOUR;
  const panel = get("mapTourPanel");
  const steps = [
    {
      code: "13123", title: "江戸川区｜出典のある施設を調べる",
      description: "最初は実際のD施設の座標付きレコード1件に近づきます（単なる表示例で、推奨施設ではありません）。安全性・開設状況は未判定です。"
    },
    {
      code: "15100", title: "新潟市｜地図の移動で施設を自動表示",
      description: "ユーザーが地域ボタンを押さなくても、閲覧範囲にある元座標付き施設を確認できます。洪水適合に関するODSの記号・階数条件はUNKNOWNです。"
    },
    {
      code: "23100", title: "名古屋市｜位置がないデータは地図に置かない",
      description: "取得した施設記録があっても、元データに座標がなければ推測でピンを置きません。情報の欠損も明確に伝えます。"
    }
  ];
  let state = "idle";
  let index = -1;
  let playbackId = 0;
  let timer = null;
  function clearTimer() {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  }
  function renderState() {
    const active = state === "playing" || state === "preparing";
    const suspended = state === "paused";
    get("mapTourStart").disabled = active || suspended;
    get("mapTourPause").disabled = !(active || suspended);
    get("mapTourPause").textContent = suspended ? "再開" : "一時停止";
    get("mapTourNext").disabled = !(active || suspended);
    get("mapTourStop").disabled = !(active || suspended || state === "completed");
    const current = Math.min(index + 1, steps.length);
    get("mapTourProgress").textContent = state === "idle" ? "開始前" :
      state === "completed" ? "3 / 3｜完了" :
      state === "paused" ? current + " / 3｜一時停止" :
      current + " / 3｜再生中";
  }
  function displayStep(step, result) {
    get("mapTourTitle").textContent = step.title;
    get("mapTourDescription").textContent = step.description;
    get("mapTourSourceStatus").textContent =
      result.state === "mapped"
        ? "元データの座標あり " + result.mapped + "件（取得レコード " + result.total + "件）。表示は安全性の判定ではありません。"
      : result.state === "unlocated"
        ? "取得レコード " + result.total + "件、座標確認済み 0件。位置は推測しません。"
      : result.state === "cancelled"
        ? "デモを中断しました。"
        : "この地域のRegionExportを取得・確認できませんでした。施設が存在しないという意味ではありません。";
  }
  async function runStep(next) {
    clearTimer();
    index = next;
    if (next >= steps.length) {
      state = "completed";
      get("mapTourTitle").textContent = "ガイド付きデモを終了しました";
      get("mapTourDescription").textContent = "QRから地図を触るか、分析・根拠から元データを確認できます。";
      get("mapTourSourceStatus").textContent = "開始前の地図に戻るには「停止・元の位置へ」を押してください。";
      renderState();
      return;
    }
    state = "preparing";
    renderState();
    const nonce = ++playbackId;
    const step = steps[index];
    get("mapTourTitle").textContent = step.title;
    get("mapTourDescription").textContent = "確認済みの施設位置を読み込み中です。読み込みが完了すると地図が動きます…";
    get("mapTourSourceStatus").textContent = "";
    let result;
    try {
      const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
      result = await api.focus(step.code, !reduced, index === 0);
    } catch (_) {
      result = { state: "unavailable", mapped: 0, total: 0 };
    }
    if (nonce !== playbackId || state === "paused") return;
    displayStep(step, result);
    state = "playing";
    renderState();
    // Presenter can pause/skip at any point; the last step remains visible
    // long enough to explain why data with no coordinates has no map pin.
    timer = window.setTimeout(() => { timer = null; runStep(index + 1); }, 6500);
  }
  function begin() {
    if (state !== "idle" && state !== "completed") return;
    api.begin();
    runStep(0);
  }
  function pause() {
    if (state === "paused") {
      runStep(Math.max(0, index));
      return;
    }
    if (state !== "playing" && state !== "preparing") return;
    clearTimer();
    playbackId++;
    api.halt();
    state = "paused";
    renderState();
  }
  function stop(restore = true) {
    clearTimer();
    playbackId++;
    api.end(restore);
    state = "idle";
    index = -1;
    get("mapTourTitle").textContent = "地域を巡るデモ";
    get("mapTourDescription").textContent = "江戸川区→新潟市→名古屋市。災害予測・避難推奨ではありません。";
    get("mapTourSourceStatus").textContent = "";
    renderState();
  }
  function open() {
    if (!panel.hidden) return;
    // This is a presenter-only control, never opened by demo=audience.
    get("mapShareClose").click();
    for (const menu of ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"]) get(menu).open = false;
    get("mapAudienceIntro").hidden = true;
    if (!get("mapSettingsPanel").hidden) get("mapSettingsClose").click();
    panel.hidden = false;
  }
  function close() {
    stop(true);
    panel.hidden = true;
  }
  get("mapTourOpen").addEventListener("click", () => { open(); });
  get("mapTourClose").addEventListener("click", close);
  get("mapTourStart").addEventListener("click", begin);
  get("mapTourPause").addEventListener("click", pause);
  get("mapTourNext").addEventListener("click", () => {
    if (state !== "playing" && state !== "paused" && state !== "preparing") return;
    api.halt();
    runStep(index + 1);
  });
  get("mapTourStop").addEventListener("click", () => stop(true));
  const mapElement = get("map");
  for (const type of ["pointerdown", "wheel", "touchstart"]) {
    mapElement.addEventListener(type, pause, { passive: true });
  }
  document.addEventListener("keydown", event => {
    if (panel.hidden) return;
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) pause();
  });
  get("mapShareOpen").addEventListener("click", () => { if (!panel.hidden) close(); });
  for (const name of ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"]) {
    get(name).addEventListener("toggle", () => {
      if (get(name).open && !panel.hidden) close();
    });
  }
  renderState();
})();