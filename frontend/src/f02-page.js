import { createRegionExportController, RegionExportLoadError } from "./region-export-loader.js";
import { buildF02ShelterReference, searchF02Facilities } from "./f02-shelter-reference.js";

const search = document.getElementById("search");
const clearSearch = document.getElementById("clear-search");
const results = document.getElementById("results");
const detail = document.getElementById("detail");
const sources = document.getElementById("sources");
const status = document.getElementById("load-state");
const retryLoad = document.getElementById("retry-load");
const count = document.getElementById("record-count");
const detailTitle = document.getElementById("detail-title");
const returnToRecord = document.getElementById("return-to-record");
const returnToDetail = document.getElementById("return-to-detail");
const clearRecord = document.getElementById("clear-record");
const regionCode = "13123";
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
  returnToRecord.hidden = true;
  returnToRecord.removeAttribute("aria-label");
  returnToDetail.hidden = true;
  clearRecord.hidden = true;
  detail.replaceChildren();
  paragraph(detail, "施設を選択してください。出典はDataset単位で、施設単位の承認とは区別します。");
}
function addDetailField(table, label, value) {
  table.append(create("dt", label), create("dd", value));
}
function renderDetail(record) {
  returnToRecord.hidden = false;
  returnToDetail.hidden = false;
  clearRecord.hidden = false;
  returnToRecord.setAttribute("aria-label", "選択した施設へ戻る（" + record.name + "）");
  detail.replaceChildren();
  detail.append(create("h3", record.name));
  paragraph(detail, "Dの正規化記録を表示しています。施設区分は名称から作成したD内部の分類で、正式な指定ではありません。対象災害への適合、安全性や現在の開設は、この画面では判断しません。", "notice");
  const fields = create("dl");
  addDetailField(fields, "施設ID", record.id);
  addDetailField(fields, "施設名称", record.name);
  addDetailField(fields, "住所（D記録）", valueOrUnknown(record.addressRaw));
  addDetailField(fields, "施設区分（D内部の名称ベース分類・正式指定未確認）", valueOrUnknown(record.facilityTypeRaw));
  addDetailField(fields, "災害区分（D記録値・未解釈）",
    record.disasterValues === null ? "未確認" :
    record.disasterValues.length ? record.disasterValues.join(" / ") : "値の記録なし");
  addDetailField(fields, "位置データ", record.hasCoordinates ?
    "座標値あり（公式の敷地・入口・指定範囲は未承認）" : "座標なし・位置未確認");
  addDetailField(fields, "施設単位の確認", "正式指定・開設状況・入口・災害適合・安全性は未確認");
  addDetailField(fields, "施設単位の出典対応", "Dataset単位の出典のみを表示します。CSVとDの変換整合性確認は、施設の正式指定・位置・運用状況の承認ではありません");
  detail.append(fields);
  const sourceLink = create("a", "データセット全体の出典へ移動");
  sourceLink.href = "#source-title";
  detail.append(sourceLink);
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
    if (src.licenseRaw === "CC BY 2.1 JP") {
      const license = create("a", "CC BY 2.1 JPの利用条件");
      license.className = "license-link";
      license.href = "https://creativecommons.org/licenses/by/2.1/jp/";
      license.target = "_blank";
      license.rel = "noopener noreferrer";
      box.append(license);
    } else {
      paragraph(box, "ライセンスURL: 未確認（一般公開前に個別確認が必要）");
    }
    paragraph(box, "出典：「" + src.name + "」（" + valueOrUnknown(src.publisher) +
      "）をもとにHINANEXが加工して作成しました。");
    paragraph(box, "本画面はDの記録から施設属性を抽出し、HINANEXが表示用に再構成しています。");
    paragraph(box, "江戸川区がこの画面を作成・承認したものではありません。");
    paragraph(box, "資料公開日時: " + valueOrUnknown(src.publishedAt));
    paragraph(box, "Dの資料取得日時: " + valueOrUnknown(src.fetchedAt));
    if (src.url) {
      const link = create("a", "資料URLを開く");
      link.setAttribute("aria-label", "資料URLを開く（" + src.name + "）");
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
  clearSearch.hidden = true;
  if (!reference || reference.state !== "READY") return;
  const matches = searchF02Facilities(reference.records, search.value);
  const shown = matches.slice(0, 50);
  const countMessage = "D記録 " + reference.records.length + "件 / 座標なし " +
    reference.withoutCoordinates + "件 / 検索一致 " + matches.length +
    "件 / 表示 " + shown.length + "件（最大50件。検索で絞り込めます）";
  // Equal result counts need no repeated live-region DOM announcement.
  if (count.textContent !== countMessage) count.textContent = countMessage;
  if (!reference.records.length) {
    status.textContent = "この取得済みDatasetの記録は0件です。地域に避難施設がないという意味ではありません。";
    clearDetail();
    return;
  }
  if (!matches.length) {
    selectedId = null;
    status.textContent = "検索に一致する記録はありません。Datasetの未収録や通信障害とは異なります。";
    clearDetail();
    clearSearch.hidden = false;
    return;
  }
  status.textContent = "Dの掲載記録を表示しています。施設の安全性や開設中を意味しません。";
  // The return target must exist in the displayed first 50 results, not only
  // in the full set of matches after a search change.
  if (selectedId && !shown.some(item => item.id === selectedId)) {
    selectedId = null;
    clearDetail();
  }
  shown.forEach(item => {
    const button = create("button", undefined, "record");
    button.type = "button";
    button.setAttribute("aria-pressed", String(item.id === selectedId));
    button.dataset.recordId = item.id;
    button.append(create("strong", item.name));
    button.append(create("small", item.hasCoordinates ? "座標値あり（指定範囲は未確認）" : "座標なし・位置未確認"));
    button.addEventListener("click", () => {
      selectedId = item.id;
      updateRecordSelection();
      renderDetail(item);
      // Keep the accessible destination without scrolling the user's list.
      detailTitle.focus({ preventScroll: true });
    });
    results.append(button);
  });
}
function updateRecordSelection() {
  // Keep the existing buttons so focus and scroll anchoring remain stable.
  for (const button of results.querySelectorAll(".record")) {
    button.setAttribute("aria-pressed", String(button.dataset.recordId === selectedId));
  }
}
function hideRetry(focusTarget) {
  const wasFocused = document.activeElement === retryLoad;
  retryLoad.hidden = true;
  if (wasFocused) focusTarget.focus();
}
function setFailure(message, canRetry = false) {
  reference = null;
  selectedId = null;
  search.disabled = true;
  search.value = "";
  clearSearch.hidden = true;
  results.replaceChildren();
  sources.replaceChildren();
  count.textContent = "";
  status.classList.add("error");
  status.textContent = "RegionExportを表示できません: " + message +
    "。施設0件と同一視せず、取得または契約を確認してください。";
  clearDetail();
  if (canRetry) {
    retryLoad.hidden = false;
    retryLoad.removeAttribute("aria-disabled");
  } else {
    hideRetry(status);
  }
}
const controller = createRegionExportController({
  async fetchImpl(url, options) {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      throw new RegionExportLoadError("RegionExportの取得先に接続できませんでした", { cause: error });
    }
  },
  onLoading() {
    if (!retryLoad.hidden) retryLoad.setAttribute("aria-disabled", "true");
    status.classList.remove("error");
    status.textContent = "RegionExportを読み込み中です。";
  },
  onSuccess(payload) {
    reference = buildF02ShelterReference(payload, regionCode);
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
    hideRetry(search);
  },
  onError(error) {
    setFailure(error.message, error instanceof RegionExportLoadError);
  },
});
retryLoad.addEventListener("click", () => {
  if (retryLoad.hidden || retryLoad.getAttribute("aria-disabled") === "true") return;
  controller.selectRegion(regionCode);
});
search.addEventListener("input", renderList);
clearSearch.addEventListener("click", () => {
  if (clearSearch.hidden) return;
  search.value = "";
  renderList();
  search.focus();
});
function focusRecord(id) {
  const target = [...results.querySelectorAll(".record")]
    .find(button => button.dataset.recordId === id);
  if (!target) return;
  target.focus({ preventScroll: true });
  target.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "instant" });
}
returnToRecord.addEventListener("click", () => focusRecord(selectedId));
clearRecord.addEventListener("click", () => {
  const clearedId = selectedId;
  selectedId = null;
  updateRecordSelection();
  clearDetail();
  focusRecord(clearedId);
});
controller.selectRegion(regionCode);
