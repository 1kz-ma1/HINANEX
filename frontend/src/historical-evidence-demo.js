import { validateEvidenceDeck } from "./historical-evidence-model.js";
const $ = (id) => document.getElementById(id);
const caseButtons = [...document.querySelectorAll("[data-case-id]")];
let deck = null;
let current = 0;
let remaining = 25;
let timer = null;
const labels = {
  trace: "T0｜原本と出力の整合（予測MATCHではない）",
  abstain: "T1｜比較不可（正誤を評価できない）",
  negative: "合成回帰テスト｜実災害のMISMATCHではない",
};
function stopClock() {
  if (timer !== null) clearInterval(timer);
  timer = null;
  if ($("pauseButton")) $("pauseButton").disabled = true;
}
function updateControls() {
  $("playButton").disabled = current >= deck.cases.length;
  $("pauseButton").disabled = timer === null;
  $("nextButton").disabled = current >= deck.cases.length - 1;
  $("secondsRemaining").textContent = "残り " + remaining + "秒";
}
function sourceLink(title, url) {
  const a = document.createElement("a");
  a.textContent = title + " ↗";
  a.href = url;
  a.target = "_blank";
  a.rel = "noopener noreferrer";
  return a;
}
function drawCase() {
  const item = deck.cases[current];
  caseButtons.forEach(b => {
    b.setAttribute("aria-pressed", String(b.dataset.caseId === item.id));
  });
  $("caseTrack").textContent = labels[item.id];
  $("caseTitle").textContent = item.label;
  $("caseQuestion").textContent = item.question;
  $("caseProgress").textContent = String(current + 1).padStart(2, "0") + " / 03";
  $("inputTitle").textContent = item.input_title;
  $("inputText").textContent = item.input_text;
  $("outputTitle").textContent = item.output_title;
  $("outputText").textContent = item.output_text;
  $("auditTitle").textContent = item.audit_title;
  $("auditText").textContent = item.audit_text;
  $("reviewLabel").textContent = item.review_label;
  $("caseTakeaway").textContent = item.takeaway;
  $("caseKind").textContent = item.kind === "SYNTHETIC_NEGATIVE_TEST_NOT_REAL_MISMATCH"
    ? "SYNTHETIC TEST ONLY" : "REAL SOURCE / LIMITED VALIDATION";
  const root = $("sourceLinks");
  root.replaceChildren();
  for (const key of item.source_ids) {
    const source = deck.sources.find(s => s.id === key);
    if (!source) continue;
    if (source.official_url) root.append(sourceLink(source.title + "／公式資料", source.official_url));
    root.append(sourceLink(source.title + "／C監査", source.machine_audit_url));
  }
  updateControls();
}
function chooseCase(idx) {
  stopClock();
  current = idx;
  remaining = deck.cases[current].seconds;
  drawCase();
}
function advance() {
  if (current === deck.cases.length - 1) {
    stopClock();
    $("loadStatus").textContent = "3ケースの説明を終了しました。実災害の予測成績は未検証です。";
    $("playButton").disabled = true;
    $("nextButton").disabled = true;
    $("secondsRemaining").textContent = "説明終了";
    return false;
  }
  current += 1;
  remaining = deck.cases[current].seconds;
  drawCase();
  return true;
}
function play() {
  if (!deck || timer !== null) return;
  $("loadStatus").textContent = "説明ガイド再生中（画面は検証結果を変更しません）";
  timer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      if (!advance()) return;
    }
    updateControls();
  }, 1000);
  updateControls();
}
async function loadEvidence() {
  try {
    const location = new URL("../../evidence/2019_edogawa_evidence_cases.json", import.meta.url);
    const response = await fetch(location, { cache: "no-store" });
    if (!response.ok) throw new Error("HTTP " + response.status);
    deck = validateEvidenceDeck(await response.json());
    for (const b of caseButtons) b.disabled = false;
    $("walkthrough").hidden = false;
    $("loadStatus").textContent = "Cの過去災害T0説明データを確認しました（人手承認前）。";
    chooseCase(0);
    for (const button of caseButtons) {
      button.addEventListener("click", () => chooseCase(deck.cases.findIndex(c => c.id === button.dataset.caseId)));
    }
    $("playButton").addEventListener("click", play);
    $("pauseButton").addEventListener("click", () => {
      stopClock();
      $("loadStatus").textContent = "一時停止中";
    });
    $("nextButton").addEventListener("click", () => { stopClock(); advance(); });
    $("resetButton").addEventListener("click", () => {
      chooseCase(0);
      $("loadStatus").textContent = "先頭のケースに戻りました。";
    });
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) stopClock();
    });
  } catch (error) {
    stopClock();
    $("walkthrough").hidden = true;
    $("loadStatus").textContent =
      "検証資料を確認できません。説明デモを停止しました。Cの承認状態や結果を推測で補いません。";
    console.error("HINANEX educational evidence gate failed", error);
  }
}
void loadEvidence();
