import {
  EvidenceContractError, parseEvidenceCase, PUBLISHED_SOURCES,
} from "./evidence-case-view-model.js";

// This page operates solely on a C-public educational case. No RegionExport
// API, GIS routing or live evacuation facilities are invoked.
const sourceStatus = document.getElementById("caseSourceStatus");
const content = document.getElementById("caseContent");
const error = document.getElementById("caseError");
const errorText = document.getElementById("caseErrorText");
const inputs = document.getElementById("caseFile");
const previewButton = document.getElementById("loadCasePreview");
const chooseFileButton = document.getElementById("chooseCaseFile");
const previewPath = "./mock/shimokamata-evidence-ui-preview.json";
let requestNumber = 0;

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (typeof text === "string") node.textContent = text;
  return node;
}

function officialSourceAnchor(key, caption) {
  const source = PUBLISHED_SOURCES[key];
  // Only C-contract-pinned Edogawa municipal source URLs may open; never
  // make clickable links from arbitrary imported JSON.
  const link = element("a", "", caption ?? source.title);
  link.href = source.url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  return link;
}

function renderContext(model) {
  const addresses = document.getElementById("caseAddresses");
  addresses.replaceChildren();
  for (const [label, value] of [
    ["旧校舎の住所", model.addresses.old],
    ["現行学校の住所", model.addresses.newSchool],
    ["2026年区資料の新校舎表記", model.addresses.newPlanRaw],
  ]) {
    addresses.append(element("dt", "", label), element("dd", "", value));
  }
}

function renderStages(model) {
  const list = document.getElementById("caseStages");
  list.replaceChildren();
  for (const stage of model.stages) {
    const li = element("li", "case-step" + (stage.isCurrentUnknown ? " case-step--unknown" : ""));
    const number = element("span", "case-step-num", String(stage.number));
    number.setAttribute("aria-hidden", "true");
    const copy = element("div");
    const heading = element("h3", "", stage.label);
    const message = element("p", "", stage.message);
    const links = element("div", "case-step-facts");
    links.append(element("span", "", "根拠となる資料： "));
    stage.sourceKeys.forEach((key) => {
      links.append(officialSourceAnchor(key));
    });
    copy.append(heading, message, links);
    if (stage.isCurrentUnknown) {
      const note = element("p", "case-scope",
        "未確認とは安全・危険を判断できない状態です。避難先として選択するための評価ではありません。");
      copy.append(note);
    }
    li.append(number, copy);
    list.append(li);
  }
}

function renderSources(model) {
  const list = document.getElementById("caseSources");
  list.replaceChildren();
  for (const source of model.sources) {
    const item = element("li");
    item.append(officialSourceAnchor(source.key));
    item.append(element("p", "", "文書の対象・記録日：" + source.date +
      "（現在の施設運用を示す日時ではありません）"));
    const details = element("details");
    const summary = element("summary", "", "出典の固定SHA256を確認");
    const digest = element("code", "", "SHA256 " + source.sha256);
    details.append(summary, digest);
    item.append(details);
    list.append(item);
  }
}

function hideAll() {
  content.hidden = true;
  error.hidden = true;
  document.getElementById("caseStages").replaceChildren();
  document.getElementById("caseSources").replaceChildren();
  document.getElementById("caseAddresses").replaceChildren();
}

function setStatus(text, kind) {
  sourceStatus.textContent = text;
  sourceStatus.dataset.kind = kind;
}

function showFailure(cause) {
  hideAll();
  error.hidden = false;
  errorText.textContent = cause instanceof EvidenceContractError
    ? cause.message
    : "読込に失敗しました。C公開用JSONの正しい版をご確認ください。";
  setStatus("データは拒否されました。以前の表示も破棄しています。", "error");
}

function showValid(data, mode) {
  // Full contract validation always precedes *any* browser DOM update.
  const model = parseEvidenceCase(data);
  hideAll();
  renderContext(model);
  renderStages(model);
  renderSources(model);
  content.hidden = false;
  error.hidden = true;
  setStatus(mode === "preview"
    ? "画面確認用サンプルを表示中（Cの新規原本確認や現在の開設確認ではありません）"
    : "選択したC公開用JSONの構造を検証して表示中（出典の原本や現在の状況は再検証していません）",
  mode);
}

async function loadPreview() {
  const token = ++requestNumber;
  hideAll();
  setStatus("表示サンプルを読込中…", "loading");
  try {
    const r = await fetch(previewPath, { cache: "no-store" });
    if (!r.ok) throw new Error("Preview unavailable");
    const parsed = await r.json();
    if (token !== requestNumber) return;
    showValid(parsed, "preview");
  } catch (e) {
    if (token === requestNumber) showFailure(e);
  }
}

async function readChosenFile() {
  const file = inputs.files?.[0];
  if (!file) return;
  const token = ++requestNumber;
  hideAll();
  setStatus("C公開用JSONの構造を検証中…", "loading");
  try {
    if (file.size > 256 * 1024) throw new EvidenceContractError("JSONファイルが大きすぎます");
    const data = JSON.parse(await file.text());
    if (token !== requestNumber) return;
    showValid(data, "file");
  } catch (e) {
    if (token === requestNumber) showFailure(e);
  } finally {
    inputs.value = "";
  }
}

inputs.addEventListener("change", readChosenFile);
chooseFileButton.addEventListener("click", () => inputs.click());
previewButton.addEventListener("click", loadPreview);
loadPreview();
