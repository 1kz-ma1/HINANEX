(() => {
  "use strict";
  const get = id => document.getElementById(id);
  const panel = get("mapEvidenceReplayPanel");
  const mapApi = window.HINANEX_PRESENTATION_TOUR;
  const opener = get("mapHistoricalEvidenceDemo");
  const tabs = Array.from(panel.querySelectorAll("[data-evidence-case]"));
  const stages = Array.from(panel.querySelectorAll("[data-replay-stage]"));
  const expected = [
    ["trace", "T0", "TECHNICAL_SOURCE_OUTPUT_CONSISTENCY", "C_MACHINE_TRACE_PASSED_HUMAN_PENDING"],
    ["abstain", "T1", "UNVERIFIED_PHYSICAL_SITE_NOT_EVALUABLE", "NOT_EVALUABLE"],
    ["negative", "T0_TEST", "SYNTHETIC_NEGATIVE_TEST_NOT_REAL_MISMATCH", "SYNTHETIC_INVALID_INPUT_REJECTED"]
  ];
  const lengths = [6, 6, 6, 7]; // 25 seconds/case, with a 15-second introductory frame.
  let deck = null;
  let caseIndex = 0;
  let stage = -1;
  let remaining = 15;
  let state = "idle";
  let interval = null;
  let generation = 0;
  // Leaflet camera control reuses the existing source-coordinate-only GIS tour.
  // Neither present-day D records nor a campus address are 2019 event shelter evidence.
  let mapSession = false;
  let mapRestore = true;
  let mapRequest = 0;
  let mapMovePending = false;
  let mapReady = false;
  function mapStatus(message) {
    get("mapEvidenceReplayMapStatus").textContent = message;
    get("mapEvidenceReplayMapLabelText").textContent = message;
  }
  function stopMapMovement() {
    ++mapRequest;
    if (mapSession && mapMovePending) mapApi.halt();
    mapMovePending = false;
  }
  function beginMapSession() {
    if (!mapApi || typeof mapApi.begin !== "function" ||
      typeof mapApi.focus !== "function" || typeof mapApi.halt !== "function" ||
      typeof mapApi.end !== "function") {
      mapStatus("地図の案内機能を確認できません。施設位置の移動は行いません。");
      return;
    }
    mapRestore = true;
    mapApi.begin();
    mapSession = true;
    mapReady = false;
    get("mapEvidenceReplayMapLabel").hidden = false;
    mapStatus("現行地域の避難施設の元座標を確認中。2019年当日の避難先ではありません。");
  }
  async function focusMapContext() {
    if (!mapSession || panel.hidden || !deck) return;
    if (mapMovePending) stopMapMovement();
    const token = ++mapRequest;
    mapMovePending = true;
    mapReady = false;
    mapStatus("江戸川区の現行地域の避難施設を確認して地図を移動中。2019年の避難先は特定しません。");
    let result;
    try {
      const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
      // focus() moves only to *real source coordinates* extracted from D.
      result = await mapApi.focus("13123", !reduced, false);
    } catch (_) {
      result = { state: "unavailable" };
    }
    if (token !== mapRequest || !mapSession || panel.hidden) return;
    mapMovePending = false;
    if (result?.state === "mapped" && Number.isSafeInteger(result.total) &&
      Number.isSafeInteger(result.mapped) && result.total >= result.mapped &&
      result.mapped > 0) {
      mapReady = true;
      mapStatus("現行地域の避難施設：取得 " + result.total + "件／元座標あり " +
        result.mapped + "件／位置未確認 " + (result.total - result.mapped) +
        "件。地図マークは2019年当日の避難先ではありません。");
    } else if (result?.state === "unlocated") {
      mapStatus("現行地域の避難施設を取得しましたが確認済み座標がありません。地図は移動していません。");
    } else {
      mapStatus("現行地域の避難施設の位置を確認できず、地図移動は未実施です。未取得は施設不存在を意味しません。");
    }
  }
  function endMapSession() {
    stopMapMovement();
    if (mapSession) mapApi.end(mapRestore);
    mapSession = false;
    mapReady = false;
    get("mapEvidenceReplayMapLabel").hidden = true;
  }

  function requireEvidence(data) {
    const check = (condition, reason) => {
      if (!condition) throw new Error("C evidence contract: " + reason);
    };
    check(data && typeof data === "object" &&
      data.schema_id === "hinanex.c.midterm_explanation_cases.v0.1" &&
      data.presentation_only === true && data.historical_replay_executed === false &&
      data.historical_prediction_approved === false && data.human_c_approved === false,
      "unsupported approval or replay status");
    check(data.approved_actual_building_pairs === 0 &&
      data.approved_historical_prediction_inputs === 0 &&
      data.prediction_denominator === null && data.prediction_numerator === null &&
      data.t1_opening_prediction_accuracy === "NOT_EVALUABLE" &&
      data.t2_hazard_prediction_accuracy === "NOT_RUN", "unknown forecast incorrectly approved");
    check(Array.isArray(data.cases) && data.cases.length === 3, "three C cases required");
    check(Array.isArray(data.sources) && data.sources.length === 4, "C sources absent");
    const ids = new Set(["school", "campus", "newsletter", "cross"]);
    check(new Set(data.sources.map(s => s.id)).size === 4, "source registry has duplicates");
    for (const source of data.sources) {
      check(ids.has(source.id) && typeof source.title === "string" &&
        typeof source.machine_audit_url === "string" &&
        /^https:\/\/github\.com\/1kz-ma1\/HINANEX\/actions\/runs\/\d+$/.test(source.machine_audit_url),
        "source audit link invalid");
      if (source.id === "cross") {
        check(source.official_url === null && source.raw_sha256 === null, "cross report is not a raw original");
      } else {
        check(typeof source.official_url === "string" &&
          /^https:\/\/www\.city\.edogawa\.tokyo\.jp\//.test(source.official_url) &&
          /^[0-9a-f]{64}$/.test(source.raw_sha256), "official source provenance invalid");
      }
    }
    data.cases.forEach((item, idx) => {
      const [id, track, kind, result] = expected[idx];
      check(item && item.id === id && item.track === track && item.kind === kind &&
        item.result === result && item.real_prediction_finding === null &&
        item.seconds === 25, "case kind or predictive verdict changed");
      check(Array.isArray(item.source_ids) && item.source_ids.length &&
        item.source_ids.every(s => ids.has(s)), "case sources invalid");
      for (const key of ["label", "question", "input_title", "input_text", "output_title",
        "output_text", "audit_title", "audit_text", "review_label", "takeaway"]) {
        check(typeof item[key] === "string" && item[key].trim(), "missing C wording: " + key);
      }
    });
    return data;
  }

  window.HINANEX_VALIDATE_EVIDENCE = requireEvidence;

  function clearClock() {
    if (interval !== null) window.clearInterval(interval);
    interval = null;
  }
  function setStatus(text) { get("mapEvidenceReplayStatus").textContent = text; }
  function makeLink(label, uri) {
    const a = document.createElement("a");
    a.href = uri;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = label + " ↗";
    return a;
  }
  function displaySources(item) {
    const root = get("mapEvidenceReplaySources");
    root.replaceChildren();
    for (const sourceId of item.source_ids) {
      const source = deck.sources.find(s => s.id === sourceId);
      if (!source) continue;
      if (source.official_url) root.append(makeLink(source.title + "・原本", source.official_url));
      root.append(makeLink(source.title + "・C監査", source.machine_audit_url));
    }
  }
  function render() {
    if (!deck) return;
    const item = deck.cases[caseIndex];
    tabs.forEach(tab => tab.setAttribute("aria-pressed", String(tab.dataset.evidenceCase === item.id)));
    stages.forEach((node, index) => {
      node.dataset.state = stage === index ? "active" : stage > index ? "done" : "upcoming";
    });
    get("mapEvidenceReplayTrack").textContent = item.track + "｜" +
      (item.id === "negative" ? "合成負系テスト / 実災害の予測不一致ではない" :
        item.id === "abstain" ? "比較不可・建物未承認" : "原本と抽出の技術的照合");
    get("mapEvidenceReplayQuestion").textContent = item.question;
    get("mapEvidenceReplayCounter").textContent = (caseIndex + 1) + " / 3";
    get("mapEvidenceReplayTime").textContent = state === "complete" ? "説明終了" :
      "この工程 残り " + remaining + " 秒";
    const stagesText = [
      [item.input_title, item.input_text],
      [item.output_title, item.output_text],
      [item.audit_title, item.audit_text],
      ["結論と限界", item.takeaway]
    ];
    const content = stage < 0 ?
      ["まずは根拠から確認", "同じ災害の資料でも、抽出の整合、判定できない事項、合成テストは別々の意味です。15秒の導入後、4つの検証工程を順に表示します。"] :
      stagesText[stage];
    get("mapEvidenceReplayStageLabel").textContent = stage < 0 ?
      "INTRO / 予測再現ではない説明演出" :
      "STEP 0" + (stage + 1) + " / " + ["OFFICIAL SOURCE", "HINANEX OUTPUT", "INDEPENDENT C AUDIT", "VERIFICATION STATUS"][stage];
    get("mapEvidenceReplayStageTitle").textContent = content[0];
    get("mapEvidenceReplayStageText").textContent = content[1];
    get("mapEvidenceReplayProgress").style.width = (stage < 0 ? 0 : (stage + 1) * 25) + "%";
    get("mapEvidenceReplayFinding").textContent = stage === 3 ? item.review_label :
      "検証工程を確認中 — 結果を先に確定しません";
    get("mapEvidenceReplayTakeaway").textContent = stage === 3 ? item.takeaway :
      "検証資料を順番に表示しています。画面上の再生は新たな判定を実行しません。";
    displaySources(item);
    get("mapEvidenceReplayPlay").disabled = state === "playing" || state === "loading";
    get("mapEvidenceReplayPause").disabled = state !== "playing";
    get("mapEvidenceReplayPrev").disabled = state === "loading" || (caseIndex === 0 && stage <= -1);
    get("mapEvidenceReplayNext").disabled = state === "loading" || state === "complete";
    get("mapEvidenceReplayRestart").disabled = state === "loading";
  }
  function moveForward() {
    if (stage < 3) stage++;
    else if (caseIndex < deck.cases.length - 1) { caseIndex++; stage = 0; }
    else {
      clearClock();
      state = "complete";
      remaining = 0;
      setStatus("3つのケースの説明が終了しました。予測のMATCH/MISMATCHは未検証です。");
      render();
      return;
    }
    remaining = stage < 0 ? 15 : lengths[stage];
    if (stage === 0) void focusMapContext();
    setStatus("ケース " + (caseIndex + 1) + " の工程 " + (stage + 1) + " / 4 を説明中。");
    render();
  }
  function tick() {
    if (state !== "playing" || !deck || panel.hidden) return;
    remaining--;
    if (remaining <= 0) moveForward();
    else get("mapEvidenceReplayTime").textContent = "この工程 残り " + remaining + " 秒";
  }
  function play() {
    if (!deck || state === "loading") return;
    if (state === "complete") { restart(); return; }
    if (state === "playing") return;
    state = "playing";
    clearClock();
    interval = window.setInterval(tick, 1000);
    if (stage === 0 && !mapReady && !mapMovePending) void focusMapContext();
    setStatus("再生中：現行施設の地図移動 → 原本 → HINANEX → C監査 → 結論。");
    render();
  }
  function pause() {
    if (state !== "playing") return;
    clearClock();
    if (mapMovePending) {
      stopMapMovement();
      mapStatus("地図移動を一時停止。再生すると現行地域の避難施設の位置確認を再開します。");
    }
    state = "paused";
    setStatus("一時停止中。ケースを選ぶか、再生ボタンで続けられます。");
    render();
  }
  function selectCase(index) {
    if (!deck || index < 0 || index >= deck.cases.length) return;
    clearClock();
    stopMapMovement();
    caseIndex = index;
    stage = 0;
    remaining = lengths[0];
    state = "paused";
    setStatus("ケース " + (caseIndex + 1) + " を選択。地図は現行地域の避難施設の参考位置です。");
    render();
    void focusMapContext();
  }
  function restart() {
    if (!deck) return;
    clearClock();
    stopMapMovement();
    caseIndex = 0;
    stage = -1;
    remaining = 15;
    state = "paused";
    render();
    play();
  }
  function next() {
    if (!deck || state === "loading" || state === "complete") return;
    pause();
    moveForward();
    if (state !== "complete") { state = "paused"; render(); }
  }
  function previous() {
    if (!deck || state === "loading") return;
    pause();
    if (stage > 0) stage--;
    else if (stage === 0) {
      if (caseIndex > 0) { caseIndex--; stage = 3; }
      else stage = -1;
    }
    remaining = stage < 0 ? 15 : lengths[stage];
    state = "paused";
    setStatus("前の工程へ移動しました。");
    render();
  }
  function close() {
    if (panel.hidden) return;
    generation++;
    clearClock();
    endMapSession();
    state = "idle";
    panel.hidden = true;
    opener.setAttribute("aria-expanded", "false");
    // The old map tour should be restored, but its map camera/data must not change.
    get("mapTourOpen").click();
    opener.focus();
  }
  async function open() {
    if (!panel.hidden) return;
    // Stop the older camera tour before the evidence player takes focus.
    get("mapTourClose").click();
    panel.hidden = false;
    opener.setAttribute("aria-expanded", "true");
    get("mapEvidenceReplayClose").focus();
    clearClock();
    state = "loading";
    deck = null;
    get("mapEvidenceReplayContent").hidden = true;
    get("mapEvidenceReplayMapLabel").hidden = true;
    mapStatus("現行地域の避難施設の位置情報はまだ取得していません。");
    tabs.forEach(b => { b.disabled = true; });
    setStatus("Cが固定した説明データを取得中です。未取得を検証成功として表示しません。");
    const request = ++generation;
    try {
      const url = new URL("../../evidence/2019_edogawa_evidence_cases.json", document.baseURI);
      const response = await window.fetch(url, { cache: "no-store" });
      if (!response.ok) throw new Error("C evidence HTTP " + response.status);
      const verified = requireEvidence(await response.json());
      if (request !== generation || panel.hidden) return;
      deck = verified;
      tabs.forEach(b => { b.disabled = false; });
      get("mapEvidenceReplayContent").hidden = false;
      beginMapSession();
      restart();
    } catch (error) {
      if (request !== generation || panel.hidden) return;
      clearClock();
      deck = null;
      state = "error";
      get("mapEvidenceReplayContent").hidden = true;
      setStatus("公式根拠に基づく説明データを確認できません。デモは停止しました。地図上の予測・施設の状態は変更していません。");
      console.error("HINANEX C explanation unavailable", error);
    }
  }
  opener.addEventListener("click", open);
  get("mapEvidenceReplayClose").addEventListener("click", close);
  tabs.forEach((tab, index) => tab.addEventListener("click", () => selectCase(index)));
  get("mapEvidenceReplayPlay").addEventListener("click", play);
  get("mapEvidenceReplayPause").addEventListener("click", pause);
  get("mapEvidenceReplayNext").addEventListener("click", next);
  get("mapEvidenceReplayPrev").addEventListener("click", previous);
  get("mapEvidenceReplayRestart").addEventListener("click", restart);
  document.addEventListener("keydown", event => {
    if (panel.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopImmediatePropagation?.();
      close();
      return;
    }
    if (event.key === "Tab") {
      const focusable = Array.from(panel.querySelectorAll('button:not([disabled]),a[href]'));
      if (!focusable.length) return;
      const first = focusable[0], last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault(); first.focus();
      }
    }
  }, true);
  document.addEventListener("visibilitychange", () => { if (document.hidden) pause(); });
  function onManualMapGesture() {
    if (panel.hidden) return;
    mapRestore = false; // Do not undo the viewer's manual navigation on close.
    pause();
    stopMapMovement();
    if (mapSession) mapApi.halt(); // Even a completed focus() may still be flying.
  }
  for (const type of ["pointerdown", "wheel", "touchstart"]) {
    get("map").addEventListener(type, onManualMapGesture, { passive: true });
  }
})();