(() => {
  "use strict";
  const get = id => document.getElementById(id);
  const api = window.HINANEX_PRESENTATION_TOUR;
  const panel = get("mapTourPanel");
  // Three distinct *data-display cases*, not three evacuation recommendations.
  // Never derive safety, suitability or opening from source counts.
  const steps = [
    {
      code: "13123", title: "江戸川区｜元座標がある施設",
      description: "元データの座標付き施設に近づきます（推奨施設ではありません）。開設状況・安全性は未確認です。"
    },
    {
      code: "15100", title: "新潟市｜別の地域の実データ",
      description: "新潟市の元座標付き地域の避難施設を表示します。洪水適合に関するODSの記号・階数条件は未確定（UNKNOWN）です。"
    },
    {
      code: "23100", title: "名古屋市｜座標がない施設一覧",
      description: "施設記録は取得できても元座標がなければ地図へピンを置きません。地図は前の位置のままです。位置・安全性・開設状況は未確認です。"
    }
  ];
  const codes = steps.map(item => item.code);
  const summaries = new Map(codes.map(code => [code, "未再生"]));
  let state = "idle";
  let index = -1;
  let sequence = [];
  let playbackId = 0;
  let timer = null;
  let restoreViewOnStop = true;
  function clearTimer() {
    if (timer !== null) window.clearTimeout(timer);
    timer = null;
  }
  function updateComparison() {
    for (const step of steps) {
      get("mapTourCompare" + step.code).textContent = summaries.get(step.code);
      const selected = sequence[index]?.code === step.code &&
        (state === "preparing" || state === "playing" || state === "paused");
      get("mapTourCase" + step.code).setAttribute("aria-pressed", String(selected));
    }
  }
  function renderState() {
    const active = state === "playing" || state === "preparing";
    const suspended = state === "paused";
    get("mapTourStart").disabled = active || suspended;
    get("mapTourPause").disabled = !(active || suspended);
    get("mapTourPause").textContent = suspended ? "再開" : "一時停止";
    get("mapTourNext").disabled = !(active || suspended) || index >= sequence.length - 1;
    get("mapTourStop").disabled = !(active || suspended || state === "completed");
    const count = sequence.length || steps.length;
    const current = Math.min(index + 1, count);
    get("mapTourProgress").textContent = state === "idle" ? "開始前" :
      state === "completed" ? count + " / " + count + "｜完了" :
      current + " / " + count + (suspended ? "｜一時停止" :
        state === "preparing" ? "｜取得中" : "｜再生中");
    updateComparison();
  }
  function displayStep(step, result) {
    get("mapTourTitle").textContent = step.title;
    get("mapTourDescription").textContent = step.description;
    const total = Number.isSafeInteger(result?.total) && result.total >= 0 ? result.total : null;
    const mapped = Number.isSafeInteger(result?.mapped) && result.mapped >= 0 ? result.mapped : null;
    if (result?.state === "mapped" && total !== null && mapped !== null && mapped <= total) {
      summaries.set(step.code, "取得 " + total + "件｜元座標あり " + mapped +
        "件｜座標未確認 " + (total - mapped) + "件");
      get("mapTourSourceStatus").textContent = summaries.get(step.code) +
        "。元データの座標あり。取得した施設データの内訳であり、網羅数・安全性・開設状況は未確認です。";
    } else if (result?.state === "unlocated" && total !== null) {
      summaries.set(step.code, "取得 " + total + "件｜元座標あり 0件｜位置未確認");
      get("mapTourSourceStatus").textContent = summaries.get(step.code) +
        "。座標確認済み 0件。位置は推測しません。地図は前の位置のままです。元データの施設一覧を参照してください。";
    } else {
      summaries.set(step.code, "データ未取得・未確認（施設なしとは断定できません）");
      get("mapTourSourceStatus").textContent = summaries.get(step.code) +
        "。この地域のRegionExportを取得・確認できませんでした。施設が存在しないという意味ではありません。";
    }
    updateComparison();
  }
  async function runStep(next) {
    clearTimer();
    index = next;
    if (next >= sequence.length) {
      state = "completed";
      get("mapTourTitle").textContent = "選択したデモを終了しました";
      get("mapTourDescription").textContent = "下の3地域の取得結果を比較し、どれでも個別再生できます。";
      get("mapTourSourceStatus").textContent =
        "表示数は取得できた施設データの数です。避難先の安全性や開設状況は判定していません。";
      renderState();
      return;
    }
    state = "preparing";
    renderState();
    const nonce = ++playbackId;
    const step = sequence[index];
    get("mapTourTitle").textContent = step.title;
    get("mapTourDescription").textContent = "元データの取得状況を確認しています…";
    get("mapTourSourceStatus").textContent = "";
    summaries.set(step.code, "取得中（件数未確認）");
    updateComparison();
    let result;
    try {
      const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
      result = await api.focus(step.code, !reduced, step.code === "13123");
    } catch (_) {
      result = { state: "unavailable" };
    }
    // Changing a mode, stopping, closing or pausing makes old HTTP results
    // ineligible to overwrite the current comparison or map description.
    if (nonce !== playbackId || state === "paused") return;
    displayStep(step, result);
    state = "playing";
    renderState();
    timer = window.setTimeout(() => {
      timer = null;
      runStep(index + 1);
    }, 6500);
  }
  function markInterruptedFetch() {
    if (state === "preparing" && sequence[index]) {
      summaries.set(sequence[index].code, "取得中断・未確認");
    }
  }
  function startRun(nextCodes) {
    // Only literal, known 地域の施設データ cases; never take coordinates, raw
    // source URLs or custom disaster descriptions from the UI.
    if (!nextCodes.length || nextCodes.some(code => !codes.includes(code))) return;
    clearTimer();
    markInterruptedFetch();
    playbackId++;
    if (state !== "idle") api.end(restoreViewOnStop);
    restoreViewOnStop = true;
    sequence = nextCodes.map(code => steps.find(step => step.code === code));
    index = -1;
    state = "idle";
    for (const code of nextCodes) summaries.set(code, "未再生");
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
    markInterruptedFetch();
    playbackId++;
    api.halt();
    state = "paused";
    renderState();
  }
  function stop(restore = true) {
    clearTimer();
    markInterruptedFetch();
    playbackId++;
    if (state !== "idle") api.end(restore && restoreViewOnStop);
    restoreViewOnStop = true;
    state = "idle";
    index = -1;
    sequence = [];
    get("mapTourTitle").textContent = "3つの地域データを比較";
    get("mapTourDescription").textContent =
      "地域を選んで個別に再生、または3地域を続けて比較できます。災害予測や避難推奨ではありません。";
    get("mapTourSourceStatus").textContent = "";
    renderState();
  }
  function open() {
    if (!panel.hidden) return;
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
  get("mapTourOpen").addEventListener("click", open);
  get("mapTourClose").addEventListener("click", close);
  get("mapTourStart").addEventListener("click", () => startRun(codes));
  for (const step of steps) {
    get("mapTourCase" + step.code).addEventListener("click", () => startRun([step.code]));
  }
  get("mapTourPause").addEventListener("click", pause);
  get("mapTourNext").addEventListener("click", () => {
    if (!["playing", "paused", "preparing"].includes(state) ||
        index >= sequence.length - 1) return;
    markInterruptedFetch();
    playbackId++;
    api.halt();
    runStep(index + 1);
  });
  get("mapTourStop").addEventListener("click", () => stop(true));
  const mapElement = get("map");
  for (const type of ["pointerdown", "wheel", "touchstart"]) {
    mapElement.addEventListener(type, () => {
      // Keep the step timer running, but respect the manually chosen camera
      // when the presenter is closed or stopped.
      if (!panel.hidden) restoreViewOnStop = false;
    }, { passive: true });
  }
  document.addEventListener("keydown", event => {
    if (panel.hidden) return;
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key))
      restoreViewOnStop = false;
  });
  get("mapShareOpen").addEventListener("click", () => { if (!panel.hidden) close(); });
  // Ordinary toolbar interaction must not terminate a playing presentation.
  renderState();
})();