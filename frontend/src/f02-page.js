import { createRegionExportController } from "./region-export-loader.js";
import { buildF02ShelterReference, searchF02Facilities } from "./f02-shelter-reference.js";

const search = document.getElementById("search");
const results = document.getElementById("results");
const detail = document.getElementById("detail");
const sources = document.getElementById("sources");
const status = document.getElementById("load-state");
const count = document.getElementById("record-count");
const detailTitle = document.getElementById("detail-title");
let reference = null;
let selectedId = null;

function create(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
function valueOrUnknown(value) {
  return typeof value === "string" && value.trim() ? value : "未確認";
}
function paragraph(parent, text, className) {
  parent.append(create("p", text, className));
}
function clearDetail() {
  detail.replaceChildren();
  paragraph(detail, "施設を選択してください。出典はDataset単位で、施設単位の承認とは区別します。");
}
function addDetailField(table, label, value) {
  table.append(create("dt", label), create("dd", value));
}
function renderDetail(record) {
  detail.replaceChildren();
  detail.append(create("h3", record.name));
  paragraph(detail, "Dの正規化記録に含まれる元属性です。正式な指定、対象災害への適合、安全性や現在の開設は、この画面では判断しません。", "notice");
  const fields = create("dl");
  addDetailField(fields, "施設ID", record.id);
  addDetailField(fields, "施設名称", record.name);
  addDetailField(fields, "住所（D記録）", valueOrUnknown(record.addressRaw));
  addDetailField(fields, "施設種別（D記録）", valueOrUnknown(record.facilityTypeRaw));
  addDetailField(fields, "災害区分（D記録値・未解釈）",
    record.disasterValues === null ? "未確認" :
    record.disasterValues.length ? record.disasterValues.join(" / ") : "値の記録なし");
  addDetailField(fields, "位置データ", record.hasCoordinates ?
    "座標値あり（公式の敷地・入口・指定範囲は未承認）" : "座標なし・位置未確認");
  addDetailField(fields, "施設単位の確認", "正式指定・開設状況・入口・災害適合・安全性は未確認");
  addDetailField(fields, "施設単位の出典対応", "この画面はDataset単位の出典のみ表示。行単位の独立照合は未承認");
  detail.append(fields);
}
function renderSources() {
  sources.replaceChildren();
  if (!reference || reference.state !== "READY" || reference.evidence.length === 0) {
    paragraph(sources, "Dataset単位の出典が確認できません。");
    return;
  }
  reference.evidence.forEach(src => {
    const box = create("div", undefined, "source");
    box.append(create("h3", src.name));
    paragraph(box, "発行元: " + valueOrUnknown(src.publisher));
    paragraph(box, "利用ライセンス（D記録）: " + valueOrUnknown(src.licenseRaw));
    paragraph(box, "本画面はDの記録から施設属性を抽出し、HINANEXが表示用に再構成しています。");
    paragraph(box, "資料公開日時: " + valueOrUnknown(src.publishedAt));
    paragraph(box, "Dの資料取得日時: " + valueOrUnknown(src.fetchedAt));
    if (src.url) {
      const link = create("a", "資料URLを開く");
      link.href = src.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      box.append(link);
    } else {
      paragraph(box, "HTTPSの出典URL: 未確認");
    }
    sources.append(box);
  });
}
function renderList() {
  results.replaceChildren();
  if (!reference || reference.state !== "READY") return;
  const matches = searchF02Facilities(reference.records, search.value);
  const shown = matches.slice(0, 50);
  count.textContent = "D記録 " + reference.records.length + "件 / 座標なし " +
    reference.withoutCoordinates + "件 / 検索一致 " + matches.length +
    "件 / 表示 " + shown.length + "件（最大50件。検索で絞り込めます）";
  if (!reference.records.length) {
    status.textContent = "この取得済みDatasetの記録は0件です。地域に避難施設がないという意味ではありません。";
    clearDetail();
    return;
  }
  if (!matches.length) {
    status.textContent = "検索に一致する記録はありません。Datasetの未収録や通信障害とは異なります。";
    clearDetail();
    return;
  }
  status.textContent = "Dの掲載記録を表示しています。施設の安全性や開設中を意味しません。";
  if (selectedId && !matches.some(item => item.id === selectedId)) {
    selectedId = null;
    clearDetail();
  }
  shown.forEach(item => {
    const button = create("button", undefined, "record");
    button.type = "button";
    button.setAttribute("aria-pressed", String(item.id === selectedId));
    button.append(create("strong", item.name));
    button.append(create("small", item.hasCoordinates ? "座標値あり（指定範囲は未確認）" : "座標なし・位置未確認"));
    button.addEventListener("click", () => {
      selectedId = item.id;
      renderList();
      renderDetail(item);
      detailTitle.focus();
    });
    results.append(button);
  });
}
function setFailure(message) {
  reference = null;
  selectedId = null;
  search.disabled = true;
  search.value = "";
  results.replaceChildren();
  sources.replaceChildren();
  count.textContent = "";
  status.classList.add("error");
  status.textContent = "RegionExportを表示できません: " + message +
    "。施設0件と同一視せず、取得または契約を確認してください。";
  clearDetail();
}
const controller = createRegionExportController({
  onLoading() {
    status.classList.remove("error");
    status.textContent = "RegionExportを読み込み中です。";
  },
  onSuccess(payload) {
    reference = buildF02ShelterReference(payload, "13123");
    selectedId = null;
    if (reference.state === "NO_DATASET") {
      setFailure("shelter_location Datasetが収録されていません");
      return;
    }
    search.disabled = false;
    status.classList.remove("error");
    clearDetail();
    renderSources();
    renderList();
  },
  onError(error) {
    setFailure(error.message);
  },
});
search.addEventListener("input", renderList);
controller.selectRegion("13123");
