const REGION_CONFIGS = {
  "13123": {
    code: "13123",
    key: "edogawa",
    label: "東京都 江戸川区",
    autoUrl: "../../pipeline/data/output/edogawa.json"
  },
  "15100": {
    code: "15100",
    key: "niigata",
    label: "新潟県 新潟市",
    autoUrl: "../../pipeline/data/output/niigata.json"
  },
  "23100": {
    code: "23100",
    key: "nagoya",
    label: "愛知県 名古屋市",
    autoUrl: "../../pipeline/data/output/nagoya.json"
  }
};

const FLOOD_REFERENCE_URL = "https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/{z}/{x}/{y}.png";

const map = L.map("map", {
  zoomControl: true,
  attributionControl: true,
  preferCanvas: true
}).setView([35.704, 139.882], 13);

map.createPane("officialFloodPane");
map.getPane("officialFloodPane").style.zIndex = 410;
map.createPane("boundaryPane");
map.getPane("boundaryPane").style.zIndex = 450;
map.createPane("shelterPane");
map.getPane("shelterPane").style.zIndex = 600;

const baseMap = L.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png", {
  minZoom: 5,
  maxZoom: 18,
  maxNativeZoom: 18,
  attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>'
}).addTo(map);

const officialFloodLayer = L.tileLayer(FLOOD_REFERENCE_URL, {
  pane: "officialFloodPane",
  minZoom: 2,
  maxZoom: 18,
  maxNativeZoom: 17,
  opacity: 0.58,
  attribution: '出典：<a href="https://disaportal.gsi.go.jp/" target="_blank" rel="noopener">ハザードマップポータルサイト</a>'
}).addTo(map);

const boundaryGroup = L.layerGroup().addTo(map);
const shelterGroup = L.layerGroup().addTo(map);
L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

const regionSelect = document.getElementById("region");
const requestedRegionCode = new URL(window.location.href).searchParams.get("region");
if (requestedRegionCode && REGION_CONFIGS[requestedRegionCode]) {
  regionSelect.value = requestedRegionCode;
}

let selectedRegionCode = regionSelect.value;
let boundaryBounds = null;
let shelterBounds = null;
let currentShelterSummary = null;
let autoLoadSequence = 0;
let autoLoadAbortController = null;
const externalTileWarnings = new Set();

function currentRegion() {
  return REGION_CONFIGS[selectedRegionCode];
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeExternalUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  try {
    const url = new URL(value, window.location.href);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch (_) {
    return null;
  }
}

function displayValue(value, nullLabel = "不明 / 未確認") {
  if (value === null || value === undefined || value === "") return nullLabel;
  if (Array.isArray(value)) return value.length ? value.join(", ") : "明示的に空";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function detail(title, rows, type, options = {}) {
  const badgeClass = options.badgeClass ? ` ${options.badgeClass}` : "";
  const noteClass = options.noteTone ? ` ${options.noteTone}` : "";
  const safeRows = rows.map(([label, value]) =>
    `<div class="row"><div class="label">${escapeHtml(label)}</div><div class="value">${escapeHtml(value)}</div></div>`
  ).join("");
  const note = options.note
    ? `<div class="note${noteClass}">${escapeHtml(options.note)}</div>`
    : "";
  const safeHref = safeExternalUrl(options.href);
  const externalLink = safeHref
    ? `<a class="detail-link" href="${escapeHtml(safeHref)}" target="_blank" rel="noopener noreferrer">公式詳細を開く</a>`
    : "";

  document.getElementById("details").innerHTML =
    `<span class="badge${badgeClass}">${escapeHtml(type)}</span>` +
    `<h2 class="detail-title">${escapeHtml(title)}</h2>` + safeRows + externalLink + note;
}

function shelterIcon() {
  return L.divIcon({
    className: "",
    html: '<div class="shelter-icon"><span>⌂</span></div>',
    iconSize: [30, 30],
    iconAnchor: [15, 29]
  });
}

function setStatus(message, tone = "normal") {
  const el = document.getElementById("status");
  el.textContent = message;
  el.dataset.tone = tone;
}

function setDatasetStatus(message, tone = "normal") {
  const el = document.getElementById("datasetStatus");
  el.textContent = message;
  el.dataset.tone = tone;
}

function updateDatasetChip(label, tone) {
  const chip = document.getElementById("datasetChip");
  chip.textContent = label;
  chip.className = `source-chip ${tone}`;
}

function updateCoverage(summary) {
  document.getElementById("recordCount").textContent = summary ? summary.records.length : "—";
  document.getElementById("mappedCount").textContent = summary ? summary.mappableRecords.length : "—";
  document.getElementById("missingCoordinateCount").textContent = summary ? summary.missingCoordinateRecords.length : "—";
}

function setMapAvailability(available, message = "") {
  const overlay = document.getElementById("mapUnavailable");
  const messageEl = document.getElementById("mapUnavailableMessage");
  overlay.hidden = available;
  if (!available) messageEl.textContent = message;
}

function showRegionWaitingDetail() {
  detail(
    currentRegion().label,
    [
      ["状態", "D RegionExport 未読込"],
      ["探索先", currentRegion().autoUrl],
      ["Contract", "RegionExport 0.9"]
    ],
    "地域切替",
    { note: "Eは確認できていない座標・境界を推測しません。" }
  );
}

function clearShelters() {
  shelterGroup.clearLayers();
  shelterBounds = null;
  currentShelterSummary = null;
  updateCoverage(null);
}

function renderReferenceBoundary() {
  boundaryGroup.clearLayers();
  boundaryBounds = null;

  const reference = window.HINANEX_REFERENCE_DATA;
  const boundary = reference?.boundary;
  if (!boundary?.features?.length) return false;

  const featureCode = boundary.features[0]?.properties?.municipalityCode;
  if (featureCode !== selectedRegionCode) return false;

  const layer = L.geoJSON(boundary, {
    pane: "boundaryPane",
    style: {
      color: "#2445dc",
      weight: 3,
      fillColor: "#ffffff",
      fillOpacity: 0.015
    },
    onEachFeature: (feature, leafletLayer) => leafletLayer.on("click", event => {
      L.DomEvent.stopPropagation(event);
      detail(
        feature.properties.name || currentRegion().label,
        [
          ["種類", "自治体境界"],
          ["地域", `${feature.properties.prefecture || ""}${feature.properties.name || ""}`],
          ["自治体コード", feature.properties.municipalityCode || selectedRegionCode],
          ["データ状態", "表示確認用fixture"]
        ],
        "境界fixture",
        {
          badgeClass: "reference",
          note: "この境界は表示確認用で、HINANEXの分析正本ではありません。"
        }
      );
    })
  }).addTo(boundaryGroup);

  boundaryBounds = layer.getBounds();
  return boundaryBounds.isValid();
}

function facilityTypeLabel(value) {
  if (value === "shelter") return "避難所";
  if (value === "supplementary_shelter") return "避難所補完施設";
  return displayValue(value);
}

function evidenceLabel(summary) {
  const first = summary.evidence[0];
  if (!first) return "Evidence 0件";
  const source = first.source_name || "名称未設定";
  const publisher = first.publisher ? ` / ${first.publisher}` : "";
  return `${source}${publisher}`;
}

function showDatasetOverview(summary, sourceLabel) {
  const missing = summary.missingCoordinateRecords.length;
  detail(
    summary.region.name,
    [
      ["Contract", `RegionExport ${summary.schemaVersion}`],
      ["DataRequirement", "shelter_location"],
      ["読込元", sourceLabel],
      ["records", `${summary.records.length}件`],
      ["地図表示", `${summary.mappableRecords.length}件`],
      ["座標欠損", `${missing}件`],
      ["Evidence", `${summary.evidence.length}件`],
      ["先頭Evidence", evidenceLabel(summary)],
      ...(summary.floodScenario ? [
        ["洪水Scenario（D原値）", summary.floodScenario.status],
        ["公式raw取得の状態", displayValue(summary.floodScenario.discoveryStatus)],
        ["Scenario元施設行", `${summary.floodScenario.recordCount}件`],
        ["洪水対応判定UNKNOWN", `${summary.floodScenario.unknownCount}件`]
      ] : [])
    ],
    "D RegionExport",
    {
      note: missing > 0
        ? "座標欠損recordは地図に描画していません。E側で住所から座標を推測・補完していません。"
        : "Dが正規化した座標のみを描画しています。E側で値を補完・推測していません。"
    }
  );
}

function renderShelterSummary(summary, sourceLabel) {
  shelterGroup.clearLayers();
  currentShelterSummary = summary;
  updateCoverage(summary);

  const latLngs = [];
  summary.mappableRecords.forEach(record => {
    latLngs.push([record.latitude, record.longitude]);
    L.marker([record.latitude, record.longitude], { icon: shelterIcon(), pane: "shelterPane" })
      .on("click", event => {
        L.DomEvent.stopPropagation(event);
        detail(
          record.name,
          [
            ["ID", record.id],
            ["種別", facilityTypeLabel(record.facility_type)],
            ["住所", displayValue(record.address)],
            ["行政区域", displayValue(record.administrative_area)],
            ["緯度", record.latitude.toFixed(7)],
            ["経度", record.longitude.toFixed(7)],
            ["対応災害", displayValue(record.supported_disasters)],
            ["収容人数", displayValue(record.capacity)],
            ["アクセシビリティ", displayValue(record.accessibility)],
            ...(summary.floodScenario?.byId.has(record.id) ? (() => {
              const fact = summary.floodScenario.byId.get(record.id);
              return [
                ["洪水Scenario（D原値）", fact.status],
                ["公式災害列", displayValue(fact.hazardScopeRaw)],
                ["公式rawの記号", displayValue(fact.officialStatusRaw)],
                ["利用階の原文", displayValue(fact.usableFloorRaw)],
                ["照合方式", displayValue(fact.joinStatus)],
                ["公式Source行", displayValue(fact.sourceRecordTrace)],
                ["Dの判定理由", displayValue(fact.reason)]
              ];
            })() : [])
          ],
          "D: shelter_location / raw facts",
          {
            href: summary.floodScenario?.byId.get(record.id)?.sourceUrl || record.detail_url,
            note: summary.floodScenario?.byId.has(record.id)
              ? "洪水Scenarioの状態は公式原文を追跡するためのD判定値です。UNKNOWNは危険・候補外ではありません。公式記号の意味、実際の開設、建物・経路の安全性は未確認です。"
              : "null は未確認 / 判定不能を意味します。E側で値を補完・推測していません。"
          }
        );
      })
      .addTo(shelterGroup);
  });

  shelterBounds = latLngs.length ? L.latLngBounds(latLngs) : null;
  setMapAvailability(
    Boolean(boundaryBounds?.isValid() || shelterBounds?.isValid()),
    `${summary.region.name} は座標付きrecordがないため、表示範囲を確定できません。E側で位置を推測しません。`
  );

  const missing = summary.missingCoordinateRecords.length;
  updateDatasetChip("D出力読込済", "ok");
  setDatasetStatus(
    `${sourceLabel}｜RegionExport ${summary.schemaVersion}｜records ${summary.records.length}件 / 地図表示 ${summary.mappableRecords.length}件 / 座標欠損 ${missing}件`,
    missing > 0 ? "warning" : "success"
  );
  setStatus(
    missing > 0
      ? `D避難所を表示中｜${missing}件は座標欠損のため地図非表示（件数は保持）`
      : `D避難所を${summary.mappableRecords.length}件表示中`,
    missing > 0 ? "warning" : "success"
  );

  showDatasetOverview(summary, sourceLabel);
  fitCurrentRegion();
}

function parseRegionExport(payload, sourceLabel) {
  const adapter = window.HINANEX_D_ADAPTER;
  if (!adapter) throw new Error("D RegionExport adapter is missing");
  const summary = adapter.extractShelterLocation(payload, selectedRegionCode);

  if (!summary.dataset) {
    clearShelters();
    currentShelterSummary = summary;
    updateCoverage(summary);
    updateDatasetChip("対象datasetなし", "warning");
    setDatasetStatus(`${sourceLabel}｜shelter_location dataset がありません`, "warning");
    setStatus("D出力内に shelter_location dataset がありません", "warning");
    detail(
      summary.region.name,
      [
        ["Contract", `RegionExport ${summary.schemaVersion}`],
        ["状態", "shelter_location datasetなし"],
        ["読込元", sourceLabel]
      ],
      "D RegionExport",
      { note: "E側では別datasetから避難所を推測しません。" }
    );
    return;
  }

  renderShelterSummary(summary, sourceLabel);
}


async function tryAutoLoad() {
  const config = currentRegion();
  const sequence = ++autoLoadSequence;

  if (autoLoadAbortController) autoLoadAbortController.abort();
  autoLoadAbortController = new AbortController();

  clearShelters();

  if (window.location.protocol === "file:") {
    updateDatasetChip("手動読込", "wait");
    setDatasetStatus(
      "file:// ではブラウザのorigin制約があるため自動fetchしません。HTTP起動するか、RegionExport JSONを選択してください。",
      "warning"
    );
    showRegionWaitingDetail();
    setStatus(`${config.label}｜D RegionExport は手動読込`, "warning");
    return;
  }

  updateDatasetChip("探索中", "wait");
  setDatasetStatus(`${config.label} のpipeline出力を探索しています…`);

  try {
    const response = await fetch(config.autoUrl, {
      cache: "no-store",
      signal: autoLoadAbortController.signal
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();

    if (sequence !== autoLoadSequence || config.code !== selectedRegionCode) return;
    parseRegionExport(payload, config.autoUrl);
  } catch (error) {
    if (error.name === "AbortError" || sequence !== autoLoadSequence) return;
    updateCoverage(null);
    updateDatasetChip("未読込", "wait");
    setDatasetStatus(
      `自動読込できませんでした（${error.message}）。${config.label} のRegionExport JSONを選択できます。`,
      "warning"
    );
    showRegionWaitingDetail();
    setStatus(`${config.label}｜D RegionExport 未読込`, "warning");
  }
}

function fitCurrentRegion() {
  if (boundaryBounds?.isValid()) {
    map.fitBounds(boundaryBounds, { padding: [26, 26], maxZoom: 14 });
    return true;
  }
  if (shelterBounds?.isValid()) {
    map.fitBounds(shelterBounds, { padding: [36, 36], maxZoom: 14 });
    return true;
  }
  return false;
}

function selectRegion(regionCode) {
  if (!REGION_CONFIGS[regionCode]) throw new Error(`Unsupported region: ${regionCode}`);
  selectedRegionCode = regionCode;
  document.getElementById("resetView").textContent = `${currentRegion().label}の表示範囲へ`;
  clearShelters();
  const hasBoundary = renderReferenceBoundary();
  document.getElementById("boundaryNote").textContent = hasBoundary
    ? "自治体境界（fixture）"
    : "自治体境界（fixtureなし）";
  document.getElementById("boundary").disabled = !hasBoundary;
  if (!hasBoundary) document.getElementById("boundary").checked = false;
  else document.getElementById("boundary").checked = true;
  if (hasBoundary && !map.hasLayer(boundaryGroup)) map.addLayer(boundaryGroup);
  setMapAvailability(
    hasBoundary,
    `${currentRegion().label} は境界fixtureがありません。Dの座標付きRegionExportを読み込むまで、地図位置を選択地域として扱いません。`
  );
  showRegionWaitingDetail();
  setStatus(`${currentRegion().label}｜D RegionExport を読み込みます`);
  tryAutoLoad();
  if (hasBoundary) fitCurrentRegion();
}

function bindToggle(id, layer) {
  document.getElementById(id).addEventListener("change", event => {
    if (event.target.checked) map.addLayer(layer);
    else map.removeLayer(layer);
  });
}

bindToggle("basemap", baseMap);
bindToggle("officialFlood", officialFloodLayer);
bindToggle("boundary", boundaryGroup);
bindToggle("shelter", shelterGroup);

document.getElementById("floodOpacity").addEventListener("input", event => {
  const percent = Number(event.target.value);
  officialFloodLayer.setOpacity(percent / 100);
  document.getElementById("floodOpacityValue").textContent = `${percent}%`;
});

document.getElementById("resetView").addEventListener("click", fitCurrentRegion);
document.getElementById("autoLoad").addEventListener("click", tryAutoLoad);
regionSelect.addEventListener("change", event => selectRegion(event.target.value));

document.getElementById("regionExportFile").addEventListener("change", async event => {
  const [file] = event.target.files || [];
  if (!file) return;

  updateDatasetChip("読込中", "wait");
  try {
    const payload = JSON.parse(await file.text());
    parseRegionExport(payload, file.name);
  } catch (error) {
    clearShelters();
    updateDatasetChip("読込失敗", "error");
    setDatasetStatus(`JSON読込失敗: ${error.message}`, "error");
    setStatus("D出力の読込に失敗しました", "error");
  } finally {
    event.target.value = "";
  }
});

map.on("click", event => {
  if (!map.hasLayer(officialFloodLayer)) return;
  const { lat, lng } = event.latlng;
  detail(
    "洪水浸水想定区域（想定最大規模）",
    [
      ["位置", `${lat.toFixed(6)}, ${lng.toFixed(6)}`],
      ["表示", "公的参照ラスタ"],
      ["想定", "想定最大規模"],
      ["地点属性", "Eでは推測しない"]
    ],
    "公的参照",
    {
      badgeClass: "reference",
      note: "ラスタ色から独自に危険度を推測せず、公式の表示をそのまま参照しています。洪水の分析ContractがDで追加された後、その属性を表示します。"
    }
  );
});

function reportExternalTileError(sourceName) {
  if (externalTileWarnings.has(sourceName)) return;
  externalTileWarnings.add(sourceName);
  setStatus(`外部タイル取得失敗: ${[...externalTileWarnings].join(" / ")}｜Dデータは利用可能`, "warning");
}

baseMap.on("tileerror", () => reportExternalTileError("背景地図"));
officialFloodLayer.on("tileerror", () => reportExternalTileError("公的洪水"));

try {
  selectRegion(selectedRegionCode);
} catch (error) {
  console.error(error);
  setStatus(`GIS初期化に失敗しました: ${error.message}`, "error");
}
