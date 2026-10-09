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

// A/B investigation: the prior 240px wheel setting felt unresponsive, while
// even 0.25 zoomSnap still rounded gestures into visible steps. Default to
// continuous (unsnapped) wheel/pinch zoom at the formerly responsive speed.
// ?zoomFeel=previous compares with 0.5-step/100px; ?zoomFeel=slow compares
// with the rejected 0.25-step/240px tuning. Neither touches source data.
const zoomFeelMode = new URL(window.location.href).searchParams.get("zoomFeel");
const previousZoomFeel = zoomFeelMode === "previous";
const slowZoomFeel = zoomFeelMode === "slow";
// Persist only gesture preferences in this browser. Never persist map/GPS
// coordinates, source data, or disaster/safety assessments.
const GESTURE_PREF_KEY = "hinanex.gis.gesture.v1";
const DEFAULT_WHEEL_SENSITIVITY = 1.5;
function normalizeWheelSensitivity(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return DEFAULT_WHEEL_SENSITIVITY;
  return Math.round(Math.max(0.5, Math.min(2.5, number)) * 4) / 4;
}
function normalizeZoomStyle(value) {
  return value === "steps" ? "steps" : "continuous";
}
function readGesturePrefs() {
  try {
    const stored = JSON.parse(window.localStorage?.getItem(GESTURE_PREF_KEY) || "null");
    if (stored && typeof stored === "object") return {
      sensitivity: normalizeWheelSensitivity(stored.sensitivity),
      style: normalizeZoomStyle(stored.style)
    };
  } catch (_) {
    // Private browsing/storage blocking must not disable map interaction.
  }
  return { sensitivity: DEFAULT_WHEEL_SENSITIVITY, style: "continuous" };
}
const savedGesturePrefs = readGesturePrefs();
let gesturePrefs = { ...savedGesturePrefs };
const map = L.map("map", {
  zoomControl: true,
  attributionControl: true,
  preferCanvas: true,
  // Retain historical A/B comparison query modes; settings take over once
  // the user explicitly changes a control.
  zoomSnap: slowZoomFeel ? 0.25 : previousZoomFeel ? 0.5
    : gesturePrefs.style === "steps" ? 0.5 : 0,
  zoomDelta: 0.5,
  wheelPxPerZoomLevel: slowZoomFeel ? 240 : previousZoomFeel ? 100
    : Math.round(100 / gesturePrefs.sensitivity),
  wheelDebounceTime: slowZoomFeel ? 55 : 40
}).setView([35.704, 139.882], 13);
function getGesturePrefs() {
  return { ...gesturePrefs };
}
function setGesturePrefs(changes) {
  gesturePrefs = {
    sensitivity: normalizeWheelSensitivity(
      changes.sensitivity === undefined ? gesturePrefs.sensitivity : changes.sensitivity
    ),
    style: normalizeZoomStyle(
      changes.style === undefined ? gesturePrefs.style : changes.style
    )
  };
  // Leaflet's wheel handler reads wheelPxPerZoomLevel from map.options for
  // each gesture; live changes don't need a map reload or a setView() call.
  map.options.wheelPxPerZoomLevel = Math.round(100 / gesturePrefs.sensitivity);
  map.options.zoomSnap = gesturePrefs.style === "steps" ? 0.5 : 0;
  map.options.wheelDebounceTime = 40;
  try { window.localStorage?.setItem(GESTURE_PREF_KEY, JSON.stringify(gesturePrefs)); }
  catch (_) { /* session-only fallback */ }
  return getGesturePrefs();
}
function resetGesturePrefs() {
  return setGesturePrefs({ sensitivity: DEFAULT_WHEEL_SENSITIVITY, style: "continuous" });
}
window.HINANEX_MAP_GESTURES = Object.freeze({
  getSettings: getGesturePrefs,
  setSettings: setGesturePrefs,
  resetSettings: resetGesturePrefs
});

map.createPane("officialFloodPane");
map.getPane("officialFloodPane").style.zIndex = 410;
map.createPane("boundaryPane");
map.getPane("boundaryPane").style.zIndex = 450;
map.createPane("shelterPane");
map.getPane("shelterPane").style.zIndex = 600;
map.createPane("referenceFootprintPane");
map.getPane("referenceFootprintPane").style.zIndex = 460;
map.createPane("referenceSitePane");
map.getPane("referenceSitePane").style.zIndex = 690;
map.createPane("referenceOriginPane");
map.getPane("referenceOriginPane").style.zIndex = 730;

const baseMap = L.tileLayer("https://cyberjapandata.gsi.go.jp/xyz/std/{z}/{x}/{y}.png", {
  // The overview minimum is set on the map itself based on its viewport.
  // Allow low-zoom GSI tiles so zooming out does not leave a blank basemap.
  minZoom: 2,
  maxZoom: 18,
  maxNativeZoom: 18,
  // Avoid additional bitmap swaps while the wheel gesture is still moving.
  // Only the rejected slow mode re-enables mid-animation basemap requests.
  // Official flood data is never hidden/changed to simulate smoothness.
  keepBuffer: 3,
  updateWhenZooming: slowZoomFeel,
  attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>'
}).addTo(map);

const officialFloodLayer = L.tileLayer(FLOOD_REFERENCE_URL, {
  pane: "officialFloodPane",
  minZoom: 2,
  maxZoom: 18,
  maxNativeZoom: 17,
  opacity: 0.58,
  keepBuffer: 3,
  updateWhenZooming: false,
  attribution: '出典：<a href="https://disaportal.gsi.go.jp/" target="_blank" rel="noopener">ハザードマップポータルサイト</a>'
}).addTo(map);

// Opt-in, local-only timing. ?debugMapPerf=1 logs tile-batch completion
// latency and visible D marker changes; no coordinates, network telemetry or
// persistent state is captured. Useful for desktop/mobile before-after QA.
const debugMapPerf = new URL(window.location.href).searchParams.get("debugMapPerf") === "1";
function perfTime() {
  return typeof performance !== "undefined" && performance.now
    ? performance.now() : Date.now();
}
if (debugMapPerf) {
  // Zoom duration is recorded without location coordinates or user events
  // being transmitted; this distinguishes rendering delay from sensitivity.
  let zoomStartedAt = null;
  map.on("zoomstart", () => { zoomStartedAt = perfTime(); });
  map.on("zoomend", () => {
    if (zoomStartedAt === null) return;
    console.info("[HINANEX map perf] zoom gesture", {
      durationMs: Math.round(perfTime() - zoomStartedAt),
      zoom: Number(map.getZoom().toFixed(2)),
      mode: zoomFeelMode || "continuous"
    });
    zoomStartedAt = null;
  });
  for (const [label, layer] of [["GSI basemap", baseMap], ["Official flood raster", officialFloodLayer]]) {
    let loadingSince = null;
    layer.on("loading", () => { loadingSince = perfTime(); });
    layer.on("load", () => {
      if (loadingSince === null) return;
      console.info("[HINANEX map perf] tile batch", {
        layer: label,
        durationMs: Math.round(perfTime() - loadingSince),
        zoom: map.getZoom()
      });
      loadingSince = null;
    });
  }
}

const boundaryGroup = L.layerGroup().addTo(map);
const shelterGroup = L.layerGroup().addTo(map);
const referenceFootprintGroup = L.layerGroup().addTo(map);
const referenceSiteGroup = L.layerGroup().addTo(map);
L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

// Navigation-only overview: this rectangle approximates the visible Japanese
// archipelago from the southwest islands through Hokkaido. It is NOT a
// jurisdiction border, official hazard extent, data coverage or safety area.
// The outermost remote islands outside this frame are not all included.
const JAPAN_OVERVIEW_BOUNDS = L.latLngBounds([
  [24.0, 122.5],
  [45.8, 146.5]
]);
const OVERVIEW_TILE_MIN_ZOOM = 2;
const OVERVIEW_MAX_MIN_ZOOM = 6;
const OVERVIEW_VIEWPORT_PADDING = [32, 32];

function updateJapanOverviewMinimumZoom() {
  // getBoundsZoom returns the largest zoom level that fits the overview
  // bounds within the current map size. Recompute when a resize changes
  // that fit, instead of hard-coding desktop/mobile zoom levels.
  const fittedZoom = map.getBoundsZoom(
    JAPAN_OVERVIEW_BOUNDS, false, OVERVIEW_VIEWPORT_PADDING
  );
  if (!Number.isFinite(fittedZoom)) return;
  map.setMinZoom(Math.max(
    OVERVIEW_TILE_MIN_ZOOM,
    Math.min(OVERVIEW_MAX_MIN_ZOOM, Math.floor(fittedZoom))
  ));
}
updateJapanOverviewMinimumZoom();
map.on("resize", updateJapanOverviewMinimumZoom);

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
let facilityListQuery = "";
let facilityListPage = 0;
let selectedOrigin = null;
let choosingOrigin = false;
let originMarker = null;
let gpsRequestSequence = 0;
let verifiedFloodCatalog = null;
let catalogLoadSequence = 0;
let referenceFootprintBounds = null;
let referenceCandidateBounds = null;
let referenceCandidateLocations = [];
let displayMode = "region";

const externalTileWarnings = new Set();

// View tabs change presentation only. They must not reinitialize Leaflet,
// select a different region, refetch D/GSI, or alter GPS/origin/map state.
const viewTabs = {
  normal: document.getElementById("uiTabNormal"),
  scenario: document.getElementById("uiTabScenario")
};
const gisLayout = document.getElementById("gisLayout");
const scenarioIntro = document.getElementById("scenarioIntro");
let uiMode = "normal";

function setUiMode(mode, focusTab = false) {
  if (!Object.prototype.hasOwnProperty.call(viewTabs, mode)) return;
  uiMode = mode;
  gisLayout.setAttribute("data-ui-mode", mode);
  gisLayout.setAttribute("aria-labelledby", viewTabs[mode].id);
  scenarioIntro.hidden = mode !== "scenario";
  for (const [key, tab] of Object.entries(viewTabs)) {
    const selected = key === mode;
    tab.setAttribute("aria-selected", String(selected));
    tab.tabIndex = selected ? 0 : -1;
  }
  if (focusTab && typeof viewTabs[mode].focus === "function") viewTabs[mode].focus();
}

for (const [mode, tab] of Object.entries(viewTabs)) {
  tab.addEventListener("click", () => setUiMode(mode));
  tab.addEventListener("keydown", event => {
    const keys = ["ArrowLeft", "ArrowRight", "Home", "End"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const next = event.key === "Home" ? "normal" :
      event.key === "End" ? "scenario" :
      event.key === "ArrowRight"
        ? (uiMode === "normal" ? "scenario" : "normal")
        : (uiMode === "scenario" ? "normal" : "scenario");
    setUiMode(next, true);
  });
}
setUiMode("normal");

// Independent panel visibility is presentation state, not a data or
// selection change. Controls stay outside the shrinking columns so either
// side can always be reopened, including when both sides are hidden.
for (const [side, buttonId] of [
  ["left", "toggleLeftPanel"],
  ["right", "toggleRightPanel"]
]) {
  const button = document.getElementById(buttonId);
  const stateAttribute = "data-" + side + "-panel";
  // Initialize from markup, and default to map-first closed rails if an
  // older cached HTML version omitted the state attribute.
  const initialClosed = gisLayout.getAttribute(stateAttribute) !== "open";
  gisLayout.setAttribute(stateAttribute, initialClosed ? "closed" : "open");
  button.setAttribute("aria-expanded", String(!initialClosed));
  const initialLabel = side === "left"
    ? (initialClosed ? "左メニューを開く" : "左メニューを閉じる")
    : (initialClosed ? "右詳細を開く" : "右詳細を閉じる");
  button.setAttribute("aria-label", initialLabel);
  button.setAttribute("title", initialLabel);
  button.addEventListener("click", () => {
    const collapsed = gisLayout.getAttribute(stateAttribute) !== "closed";
    gisLayout.setAttribute(stateAttribute, collapsed ? "closed" : "open");
    button.setAttribute("aria-expanded", String(!collapsed));
    // Preserve the inline SVG: updating textContent would destroy the icon.
    const label = side === "left"
      ? (collapsed ? "左メニューを開く" : "左メニューを閉じる")
      : (collapsed ? "右詳細を開く" : "右詳細を閉じる");
    button.setAttribute("aria-label", label);
    button.setAttribute("title", label);
    // Leaflet needs a viewport recalculation after its parent grid changes.
    // Explicit pan:false avoids repositioning the user-selected center.
    // No setView, fitBounds, region switch or C/D fetch is performed here.
    map.invalidateSize({ pan: false, animate: false });
  });
}

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
  // Map-first presentation only: background dataset summaries remain
  // collapsed, but a marker/origin/raster selection reveals the detail sheet.
  if (type !== "D RegionExport" && type !== "地域切替") {
    window.HINANEX_MAP_FIRST_UI?.showDetail?.();
  }
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

function renderFacilityList() {
  const model = window.HINANEX_FACILITY_LIST;
  if (!model) throw new Error("Facility list UI module is missing");
  const summary = currentShelterSummary;
  const panel = document.getElementById("facilityListPanel");
  if (!summary || panel.hidden) return;

  const result = model.filterFacilityRecords(summary, facilityListQuery, facilityListPage);
  facilityListPage = result.page;
  document.getElementById("facilityListCount").textContent =
    `取得施設 ${result.total}件 / 検索一致 ${result.matched}件（${result.first}〜${result.last}件を表示）`;
  document.getElementById("facilityListPage").textContent =
    `${result.page + 1} / ${result.pages}ページ`;
  document.getElementById("facilityListPrev").disabled = result.page === 0;
  document.getElementById("facilityListNext").disabled = result.page >= result.pages - 1;

  const cards = result.records.map(record => {
    const fact = summary.floodScenario?.byId.get(record.id);
    const fields = [
      ["施設ID", record.id],
      ["施設名（D原値）", record.name],
      ["住所（D原値）", record.address],
      ["行政区域（D原値）", record.administrative_area],
      ["施設区分（D原値）", record.facility_type],
      ["元データ記載の災害（適合性未検証）", record.supported_disasters],
      ["座標", record.hasCoordinates ? "Dに元座標あり" : "元データで未確認（推測表示なし）"],
      ["洪水Scenario（D原値）", fact?.status ?? "Scenario情報なし"],
      ["公式災害列（原文）", fact?.hazardScopeRaw],
      ["公式rawの記号", fact?.officialStatusRaw],
      ["利用階の原文", fact?.usableFloorRaw],
      ["照合方式", fact?.joinStatus],
      ["公式Source行", fact?.sourceRecordTrace],
      ["Dの判定理由", fact?.reason]
    ];
    const detailRows = fields.map(([label, value]) =>
      `<dt>${escapeHtml(label)}</dt><dd>${escapeHtml(displayValue(value))}</dd>`
    ).join("");
    const url = safeExternalUrl(fact?.sourceUrl || record.detail_url);
    const officialLink = url && url.startsWith("https:")
      ? `<a class="list-source" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">出典を開く</a>`
      : "";
    return `<details class="facility-list-card"><summary><strong>${escapeHtml(record.name)}</strong>` +
      `<small>${escapeHtml(displayValue(record.address))} / ${escapeHtml(displayValue(record.administrative_area))}</small>` +
      `</summary><dl>${detailRows}</dl>${officialLink}` +
      `<p class="list-note">地図上の位置・洪水時の安全性・開設は未検証です。raw記号やUNKNOWNから利用可否を判定しません。</p></details>`;
  });
  document.getElementById("facilityListResults").innerHTML =
    cards.length ? cards.join("") : '<div class="facility-list-empty">一致する施設はありません。検索語を変更してください。</div>';
}

function setFacilityListMode(summary) {
  const panel = document.getElementById("facilityListPanel");
  const overlay = document.getElementById("mapUnavailable");
  const active = Boolean(summary && summary.records.length && !summary.mappableRecords.length);
  panel.hidden = !active;
  overlay.className = active ? "map-unavailable has-facility-list" : "map-unavailable";
  document.getElementById("mapUnavailableTitle").textContent = active
    ? "位置は未確認ですが、施設一覧を検索できます"
    : "表示範囲を確定できません";
  // The list-only overlay physically covers the map. Do not offer an
  // impossible "click on map" task when none of this region's D records
  // has verified coordinates. The GPS and coordinate-search workflows
  // remain independent and keep their existing privacy/source semantics.
  const selectOriginButton = document.getElementById("selectOrigin");
  const mapOriginShortcut = document.getElementById("mapOriginShortcut");
  selectOriginButton.disabled = active;
  mapOriginShortcut.disabled = active;
  selectOriginButton.textContent = active
    ? "D施設の地図位置は未確認（地図選択不可）"
    : "地図から出発地点を指定";
  if (active) {
    choosingOrigin = false;
    updateMapOriginAction("選択地域のD施設は座標未確認です。施設一覧で名前・住所を確認してください。");
    if (!selectedOrigin) {
      document.getElementById("originStatus").textContent =
        "選択地域のD施設は地図位置を確認できません。地図をクリックして選択する操作は使えません。施設一覧を利用してください。";
    }
  }
  if (active) renderFacilityList();
}

const FLOOD_CATALOG_URL = "../../pipeline/data/output/edogawa_flood_site_catalog.json";
const VERIFIED_TILE_DIR = "../../pipeline/data/output/gsi_verified_tiles/";

function updateMapOriginAction(message, picking = false) {
  const button = document.getElementById("mapOriginShortcut");
  const status = document.getElementById("mapOriginShortcutStatus");
  button.setAttribute("aria-pressed", String(picking));
  button.textContent = picking ? "地図上の地点をクリック" : "地図をクリックして探索";
  status.textContent = message;
}

// A cached single-tile script may expose the old API without throwing during
// <script> evaluation. Fail CLOSED with actionable feedback instead of
// crashing the map when the newer controller calls missing functions.
const REQUIRED_DISCOVERY_VERSION = "gsi-z10-neighbors-20261009-v14";
function compatibleDiscoveryEngine() {
  const engine = window.HINANEX_FLOOD_DISCOVERY;
  return engine && engine.apiVersion === REQUIRED_DISCOVERY_VERSION &&
    typeof engine.discoverReferenceTiles === "function" &&
    typeof engine.nearbySourceTiles === "function" ? engine : null;
}


function clearReferenceMap() {
  referenceFootprintGroup.clearLayers();
  referenceSiteGroup.clearLayers();
  referenceFootprintBounds = null;
  referenceCandidateBounds = null;
  referenceCandidateLocations = [];
  const panel = document.getElementById("referenceMapSummary");
  panel.hidden = true;
  document.getElementById("referenceMapCoverage").textContent = "未探索";
  document.getElementById("referenceMapCount").textContent = "—";
}

function verifiedTileBounds(key) {
  const match = /^10\/(\d+)\/(\d+)$/.exec(key || "");
  if (!match) return null;
  const x = Number(match[1]), y = Number(match[2]);
  const n = 1024;
  if (!Number.isInteger(x) || !Number.isInteger(y) ||
      x < 0 || y < 0 || x >= n || y >= n) return null;
  const longitude = column => column / n * 360 - 180;
  const latitude = row => Math.atan(Math.sinh(Math.PI * (1 - 2 * row / n))) * 180 / Math.PI;
  return [
    [latitude(y + 1), longitude(x)],
    [latitude(y), longitude(x + 1)]
  ];
}

function updateDReferenceButton() {
  document.getElementById("toggleDMarkers").textContent =
    displayMode === "both" ? "周辺のGSIだけ表示" : "地域Dと比較";
}

function applyDisplayMode() {
  const showD = displayMode !== "nearby";
  const showGSI = displayMode !== "region";
  const shelterInput = document.getElementById("shelter");
  const boundaryInput = document.getElementById("boundary");
  const hasGsiEvidence = referenceFootprintBounds?.isValid() === true;
  const hasMappedD = (currentShelterSummary?.mappableRecords?.length || 0) > 0;
  const summaryPanel = document.getElementById("referenceMapSummary");
  // Hide GSI's legend and counts whenever GSI is not drawn. Preserve the
  // accepted in-memory evidence so toggling back does not trigger a re-fetch.
  summaryPanel.hidden = !showGSI || !hasGsiEvidence;

  // D, GSI, and municipality-fixture layers are independent. A newly selected
  // origin never changes the municipality or repurposes D as GSI reference.
  if (showD && shelterInput.checked) map.addLayer(shelterGroup);
  else map.removeLayer(shelterGroup);
  if (showD && boundaryInput.checked && boundaryBounds?.isValid()) map.addLayer(boundaryGroup);
  else map.removeLayer(boundaryGroup);
  if (showGSI) {
    map.addLayer(referenceFootprintGroup);
    map.addLayer(referenceSiteGroup);
  } else {
    map.removeLayer(referenceFootprintGroup);
    map.removeLayer(referenceSiteGroup);
  }

  shelterInput.disabled = !showD;
  boundaryInput.disabled = !showD || !boundaryBounds?.isValid();
  document.getElementById("facilityDisplayMode").value = displayMode;
  document.getElementById("facilityDisplayModeDescription").textContent =
    displayMode === "region"
      ? "選択地域のD施設を表示。GSIの照合結果は地図で非表示（再切替で復帰）。"
      : displayMode === "nearby"
        ? "選択地点周辺の検証済みGSI掲載地点だけを表示。安全性・開設は未判定。"
        : !hasMappedD
          ? "選択地域Dの位置情報が未読込・座標欠損のため比較範囲を表示できません。GSIは別データです。"
          : "選択地域D（緑）と選択地点周辺GSI（紫）を比較。異なる出典の情報です。";
  const focusButton = document.getElementById("focusReferenceTiles");
  focusButton.textContent = displayMode === "both"
    ? "緑と紫を一緒に見る" : "選択地点と5件を見る";
  focusButton.disabled = displayMode === "both" && !hasMappedD;
  updateDReferenceButton();
}

function setDisplayMode(mode) {
  if (!["region", "nearby", "both"].includes(mode)) return;
  displayMode = mode;
  if (mode === "both") document.getElementById("shelter").checked = true;
  applyDisplayMode();
}

// Never zoom to all 9 z10 tiles when the requested action is about nearby
// candidates. This bounds *only* the selected origin and at most five displayed
// GSI reference points, with an upper zoom limit; no hazard or travel routing.
function focusReferenceCandidates() {
  if (referenceCandidateBounds?.isValid()) {
    map.fitBounds(referenceCandidateBounds, { padding: [44, 44], maxZoom: 14 });
  }
}

function focusDisplayScope() {
  if (displayMode === "both") {
    // Two independent source sets can be geographically far apart. Fit the
    // selected origin / up to 5 certified GSI reference pins AND actual
    // coordinates from the chosen municipality's D RegionExport; never
    // infer facility location from its name, municipality, or tile coverage.
    const mappedD = currentShelterSummary?.mappableRecords || [];
    if (!mappedD.length || !referenceCandidateLocations.length) return;
    const points = [
      ...referenceCandidateLocations,
      ...mappedD.map(record => [record.latitude, record.longitude])
    ];
    map.fitBounds(L.latLngBounds(points), { padding: [38, 38], maxZoom: 13 });
    return;
  }
  if (displayMode === "nearby") focusReferenceCandidates();
}

function renderReferenceMap(discovery) {
  clearReferenceMap();
  // Only call after the *entire* raw source catalog is accepted and the user's
  // own tile is included. Unverified neighbors must not draw reassuring areas.
  const corners = [];
  for (const key of discovery.verifiedTileKeys || []) {
    const bounds = verifiedTileBounds(key);
    if (!bounds) {
      clearReferenceMap(); // fail-closed if engine/visual contracts diverge
      return;
    }
    corners.push(...bounds);
    L.rectangle(bounds, {
      pane: "referenceFootprintPane",
      color: "#7439aa", weight: 2, dashArray: "6 5",
      fillColor: "#7439aa", fillOpacity: 0.03, interactive: false
    }).addTo(referenceFootprintGroup);
  }
  if (!corners.length) return;
  referenceFootprintBounds = L.latLngBounds(corners);
  const nearbyPoints = selectedOrigin
    ? [[selectedOrigin.latitude, selectedOrigin.longitude]] : [];
  nearbyPoints.push(...discovery.sites.map(site => [site.latitude, site.longitude]));
  referenceCandidateLocations = nearbyPoints;
  referenceCandidateBounds = nearbyPoints.length ? L.latLngBounds(nearbyPoints) : null;

  // Five display pins, not 6,656. No lines, routing or safety ranking.
  discovery.sites.forEach(site => {
    const sourceLink = safeExternalUrl(site.sourceUrl);
    const popup = '<div class="reference-site-popup"><strong>GSI公式掲載地点（参考情報）</strong>' +
      '<p>' + escapeHtml(site.name) + '</p>' +
      '<p>直線距離：' + escapeHtml(site.distanceMetres.toLocaleString("ja-JP")) +
      'm（経路距離ではありません）</p>' +
      (sourceLink ? '<a href="' + escapeHtml(sourceLink) +
        '" target="_blank" rel="noopener noreferrer">原典タイル</a>' : '') +
      '<p>安全性・現在の開設・避難経路は未判定です。直線距離は安全性や優先度を表すものではありません。</p></div>';
    L.marker([site.latitude, site.longitude], {
      pane: "referenceSitePane", zIndexOffset: 1000,
      icon: L.divIcon({
        className: "",
        html: '<span class="reference-site-marker" aria-label="GSI公式掲載地点・安全性未判定"></span>',
        iconSize: [32, 32], iconAnchor: [16, 16]
      })
    }).bindPopup(popup).on("click", event => {
      L.DomEvent.stopPropagation(event);
      detail(site.name, [
        ["出典", "GSI skhb01 洪水指定緊急避難場所（参照のみ）"],
        ["直線距離（経路距離ではない）", site.distanceMetres + "m"],
        ["公式住所", displayValue(site.address)],
        ["公式備考", displayValue(site.remarks)],
        ["raw行", displayValue(site.trace)]
      ], "GSI公式掲載 / 未推奨", {
        href: site.sourceUrl,
        note: "国土地理院に掲載された場所の参考情報です。安全性・現在の開設状況・避難経路・自治体所属は確認できていません。"
      });
    }).addTo(referenceSiteGroup);
  });
  const panel = document.getElementById("referenceMapSummary");
  panel.hidden = false;
  document.getElementById("referenceMapCoverage").textContent =
    "検証済み " + discovery.verifiedTileCount + "/" + discovery.requestedTileCount + " タイル";
  document.getElementById("referenceMapCount").textContent =
    discovery.total.toLocaleString("ja-JP") + "件中 最大" + discovery.sites.length + "地点を地図表示";
  applyDisplayMode();
}

function renderReferenceDiscovery() {
  const result = document.getElementById("floodDiscoveryResults");
  clearReferenceMap();
  const engine = compatibleDiscoveryEngine();
  if (!engine) {
    result.textContent = "洪水指定場所の参照モジュールのバージョンが一致しません。ページを再読み込みしてください。古いJavaScriptやブラウザキャッシュの可能性があります（Ctrl+Shift+R）。";
    updateMapOriginAction("参照モジュールの読み込み不一致。Ctrl+Shift+Rで再読込。");
    return; // never turn unverified facilities into a result
  }
  const discovery = engine.discoverReferenceTiles(verifiedFloodCatalog, selectedOrigin, selectedRegionCode);
  if (discovery.status !== "REFERENCE_ONLY") {
    result.innerHTML = `<p class="reference-warning">${escapeHtml(discovery.message)}</p>`;
    if (!selectedOrigin) {
      updateMapOriginAction("ボタンを押してから地図上の地点をクリック", choosingOrigin);
    } else {
      updateMapOriginAction("地点の公式参考情報は未検証／範囲外。左の欄で詳細確認。");
    }
    return;
  }
  const cards = discovery.sites.map((site) => {
    const url = safeExternalUrl(site.sourceUrl);
    const urlEl = url
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">国土地理院の公式rawタイルを確認</a>`
      : "";
    return `<div class="reference-result"><strong>${escapeHtml(site.name)}</strong>` +
      `<span class="trace">公式住所：${escapeHtml(displayValue(site.address))}</span>` +
      `<span class="trace">公式備考：${escapeHtml(displayValue(site.remarks))}</span>` +
      `<span class="distance">直線距離：${escapeHtml(site.distanceMetres.toLocaleString("ja-JP"))}m（経路距離ではありません）</span>` +
      `<span class="trace">Source行：${escapeHtml(displayValue(site.trace))}</span>${urlEl}</div>`;
  }).join("");
  result.innerHTML = `<p>検証済み${discovery.verifiedTileCount}/${discovery.requestedTileCount}タイルの掲載地点：${discovery.total}件（自治体内の件数ではありません）。最大5件を参考表示。</p>` +
    `<p class="reference-warning">${escapeHtml(discovery.message)}</p>` +
    (cards || '<p>この照合済みデータ内に対象施設はありません。自治体の指定不存在は断定できません。</p>');
  renderReferenceMap(discovery);
  updateMapOriginAction("検証済み" + discovery.verifiedTileCount + "/" +
    discovery.requestedTileCount + "タイル・" + discovery.total +
    "掲載件数（左欄に参考結果）。避難先の推奨ではありません。");
}

function clearReferenceDiscovery() {
  gpsRequestSequence += 1; // ignore GPS callbacks from an earlier region
  catalogLoadSequence += 1; // stale async JSON may not update a different region
  choosingOrigin = false;
  selectedOrigin = null;
  verifiedFloodCatalog = null;
  if (originMarker) map.removeLayer(originMarker);
  originMarker = null;
  document.getElementById("originStatus").textContent = "位置は未選択です";
  document.getElementById("coordinateSearchInput").value = "";
  document.getElementById("coordinateSearchInput").setAttribute("aria-invalid", "false");
  document.getElementById("coordinateSearchStatus").textContent = "";
  document.getElementById("selectOrigin").disabled = false;
  document.getElementById("useGps").disabled = false;
  renderReferenceDiscovery();
}

async function loadFloodReferenceCatalog() {
  const sequence = ++catalogLoadSequence;
  verifiedFloodCatalog = null;
  renderReferenceDiscovery();
  updateMapOriginAction("指定地点周辺の検証済みデータを照合中…");
  const engine = compatibleDiscoveryEngine();
  const requestedOrigin = selectedOrigin;
  const requestedRegion = selectedRegionCode;
  if (!engine || !requestedOrigin || window.location.protocol === "file:") return;
  const keys = engine.nearbySourceTiles(requestedOrigin);
  if (!keys.length) return;

  // Each HTTP URL is derived from a coarse z10 cell, never exact GPS coords.
  // Missing tiles are NOT empty official data: they are unverified coverage.
  // Never fetch official raw GSI JSON directly from the browser.
  const responses = await Promise.all(keys.map(async key => {
    const [z, x, y] = key.split("/");
    const url = VERIFIED_TILE_DIR + requestedRegion + "/" + z + "-" + x + "-" + y + ".json";
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) return null;
      const catalog = await response.json();
      const expectedSource = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/" + key + ".geojson";
      // A substituted file at an expected tile path must fail the entire query.
      if (catalog?.sites?.[0]?.source_url !== expectedSource) return { invalid: true };
      return catalog;
    } catch (_) {
      return null;
    }
  }));

  if (sequence !== catalogLoadSequence ||
      requestedRegion !== selectedRegionCode || requestedOrigin !== selectedOrigin) return;
  const catalogs = responses.filter(Boolean);
  // Preserve the already user-accepted single-tile preview until a fresh
  // version is published at the new tile-scoped output path.
  if (!responses[0] && keys[0] === "10/909/403" && requestedRegion === "13123") {
    try {
      const legacy = await fetch(FLOOD_CATALOG_URL, { cache: "no-store" });
      if (legacy.ok) {
        const catalog = await legacy.json();
        catalogs.push(catalog);
      }
    } catch (_) { /* absence means unverifiable, not no shelters */ }
  }
  if (sequence !== catalogLoadSequence ||
      requestedRegion !== selectedRegionCode || requestedOrigin !== selectedOrigin) return;
  verifiedFloodCatalog = catalogs;
  renderReferenceDiscovery();
  if (displayMode === "nearby" && referenceCandidateBounds?.isValid()) {
    focusReferenceCandidates();
  }
}

function setReferenceOrigin(latitude, longitude) {
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
      Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    return;
  }
  choosingOrigin = false;
  gpsRequestSequence += 1; // chosen point supersedes any pending GPS request
  selectedOrigin = { latitude, longitude };
  // Keep the input reproducible for testers even when the source of the
  // selection was a map click or explicit geolocation permission.
  document.getElementById("coordinateSearchInput").value =
    latitude.toFixed(5) + ", " + longitude.toFixed(5);
  document.getElementById("coordinateSearchInput").setAttribute("aria-invalid", "false");
  document.getElementById("coordinateSearchStatus").textContent = "";
  // A new location request defaults to nearby GSI-only. The user can change
  // back to region D or combined without losing source-provenance semantics.
  setDisplayMode("nearby");
  if (originMarker) map.removeLayer(originMarker);
  originMarker = L.marker([latitude, longitude], {
    // Dedicated upper pane keeps the chosen point visible even if nearby
    // unranked GSI markers overlap it. Never conflate it with a safe shelter.
    pane: "referenceOriginPane",
    zIndexOffset: 1500,
    title: "探索の起点（避難先ではありません）",
    icon: L.divIcon({
      className: "",
      html: '<div class="reference-origin-marker" aria-label="探索の起点・避難先ではありません">◎</div>',
      iconSize: [36, 36],
      iconAnchor: [18, 18]
    })
  }).addTo(map);
  document.getElementById("originStatus").textContent =
    `選択した地点：${latitude.toFixed(5)}, ${longitude.toFixed(5)}（正確な座標は端末内だけで使用。タイルIDは配信サーバへ送信）`;
  // An explicit origin change supersedes the old right-hand raster-click or
  // facility detail. Neither the clicked point nor source tile proves risk.
  detail("選択した地点（公式掲載情報の探索起点）", [
    ["緯度・経度", latitude.toFixed(5) + ", " + longitude.toFixed(5)],
    ["表示内容", "GSIの検証済み公式掲載地点を参考探索"],
    ["照合結果", "地図の紫マーカー・左欄・検証済み範囲を確認"]
  ], "地点指定", {
    badgeClass: "reference",
    note: "この地点の浸水リスク・避難の安全性・開設状況・経路は評価していません。未検証タイルは掲載施設が存在しないことを意味しません。"
  });
  updateMapOriginAction("選択地点の公式参考情報を照合しています…");
  loadFloodReferenceCatalog();
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
  facilityListQuery = "";
  facilityListPage = 0;
  document.getElementById("facilityListSearch").value = "";
  setFacilityListMode(null);
  updateCoverage(null);
  applyDisplayMode();
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

// This screen-pixel grid is visual decluttering only; not a facility location,
// coverage zone, opening-capacity aggregate, recommendation or safety ranking.
// Cluster coordinates are display centroids of original D coordinates.
function groupMappedDRecords(records, zoom, project) {
  if (zoom >= 13) return records.map(record => [record]);
  const width = zoom <= 10 ? 84 : 64;
  const cells = new Map();
  records.forEach(record => {
    const point = project([record.latitude, record.longitude], zoom);
    const key = Math.floor(point.x / width) + ":" + Math.floor(point.y / width);
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(record);
  });
  return [...cells.values()];
}

function drawIndividualDMarker(record, summary) {
    return L.marker([record.latitude, record.longitude], { icon: shelterIcon(), pane: "shelterPane" })
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
            ["元データ記載の災害（適合性未検証）", displayValue(record.supported_disasters)],
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
      });
}

// Layer objects are retained while their exact D-record membership stays the
// same across zoom steps. No location data is changed, and group centroids
// remain clearly labelled non-facility visual aggregates.
let visibleDMarkers = new Map();
let visibleDMarkerSummary = null;
let dRecordIndices = new Map();
// Quantize display-only cluster membership, never actual map zoom or D points.
// The same fractional wheel band should not recreate visual clusters.
let lastDMarkerZoomBucket = null;
function drawDClusterMarker(records) {
  const latitude = records.reduce((sum, record) => sum + record.latitude, 0) / records.length;
  const longitude = records.reduce((sum, record) => sum + record.longitude, 0) / records.length;
  const count = records.length;
  return L.marker([latitude, longitude], {
    pane: "shelterPane",
    title: "近接するD施設" + count + "件（地図表示用の集合、優先順位ではありません）",
    icon: L.divIcon({
      className: "",
      html: '<div class="d-facility-cluster" aria-label="近接するD施設' +
        count + '件を地図表示用にまとめています。安全性未判定">' +
        count.toLocaleString("ja-JP") + '</div>',
      iconSize: [42, 42],
      iconAnchor: [21, 21]
    })
  }).on("click", event => {
    L.DomEvent.stopPropagation(event);
    detail("D施設の表示上の集合（" + count + "件）", [
      ["件数", count + "件（地図上の重なりを軽減するための表示件数）"],
      ["対象", currentRegion().label + "のD RegionExport"],
      ["表示位置", "含まれる施設座標の平均値（実在する施設位置ではありません）"]
    ], "地図表示用クラスタ", {
      note: "この円の中心は避難場所ではありません。クリックで拡大すると個別施設の元データを確認できます。安全性・開設状況・経路・優先順位は未判定です。"
    });
    map.setView([latitude, longitude], Math.min(13, map.getZoom() + 2));
  });
}

function renderDMarkers() {
  const startedAt = debugMapPerf ? perfTime() : 0;
  const summary = currentShelterSummary;
  if (summary !== visibleDMarkerSummary) {
    // A municipality/data refresh must never reuse stale markers or closures.
    shelterGroup.clearLayers();
    visibleDMarkers.clear();
    visibleDMarkerSummary = summary;
    lastDMarkerZoomBucket = null;
    dRecordIndices = new Map((summary?.mappableRecords || []).map((record, index) => [record, index]));
  }
  if (!summary?.mappableRecords?.length) {
    lastDMarkerZoomBucket = null;
    return;
  }
  const zoom = map.getZoom();
  // High detail uses source markers, always. At lower zoom levels fix the
  // visual-only grid within each integer zoom band to avoid flickering
  // centroid/cluster changes on every tiny fractional zoom delta.
  const zoomBucket = zoom >= 13 ? "individual" : Math.floor(zoom);
  if (zoomBucket === lastDMarkerZoomBucket) {
    if (debugMapPerf) {
      console.info("[HINANEX map perf] D grouping reused", { zoom, zoomBucket });
    }
    return;
  }
  const groupingZoom = zoom >= 13 ? zoom : zoomBucket;
  const batches = groupMappedDRecords(summary.mappableRecords, groupingZoom,
    (coordinate, level) => map.project(coordinate, level));
  const next = new Map();
  let added = 0;
  let removed = 0;
  // This key denotes *exact membership* within one loaded RegionExport.
  // Duplicate facility IDs are safe because identity is based on row index.
  for (const records of batches) {
    const key = records.map(record => dRecordIndices.get(record)).join(",");
    let marker = visibleDMarkers.get(key);
    if (!marker) {
      marker = records.length === 1
        ? drawIndividualDMarker(records[0], summary)
        : drawDClusterMarker(records);
      shelterGroup.addLayer(marker);
      added++;
    }
    next.set(key, marker);
  }
  for (const [key, marker] of visibleDMarkers) {
    if (next.has(key)) continue;
    shelterGroup.removeLayer(marker);
    removed++;
  }
  visibleDMarkers = next;
  lastDMarkerZoomBucket = zoomBucket;
  if (debugMapPerf) {
    console.info("[HINANEX map perf] D markers", {
      zoom, zoomBucket, visible: next.size, added, removed,
      durationMs: Math.round(perfTime() - startedAt)
    });
  }
}

map.on("zoomend", renderDMarkers);

function renderShelterSummary(summary, sourceLabel) {
  currentShelterSummary = summary;
  updateCoverage(summary);
  applyDisplayMode(); // if D arrives after GSI, update comparison availability

  // Keep bounds based on ALL verified D positions, never on cluster-centroid
  // display points (which are not actual facility locations).
  const latLngs = summary.mappableRecords.map(record => [record.latitude, record.longitude]);
  renderDMarkers();

  shelterBounds = latLngs.length ? L.latLngBounds(latLngs) : null;
  const listOnly = summary.records.length > 0 && summary.mappableRecords.length === 0;
  setMapAvailability(
    !listOnly && Boolean(boundaryBounds?.isValid() || shelterBounds?.isValid()),
    `${summary.region.name} は座標付きrecordがないため、表示範囲を確定できません。E側で位置を推測しません。`
  );
  setFacilityListMode(listOnly ? summary : null);

  const missing = summary.missingCoordinateRecords.length;
  updateDatasetChip("D出力読込済", "ok");
  setDatasetStatus(
    `${sourceLabel}｜RegionExport ${summary.schemaVersion}｜records ${summary.records.length}件 / 地図表示 ${summary.mappableRecords.length}件 / 座標欠損 ${missing}件`,
    missing > 0 ? "warning" : "success"
  );
  setStatus(
    listOnly
      ? `座標未確認のため施設一覧を表示中（${summary.records.length}件）。安全・開設状況は判定していません。`
      : missing > 0
        ? `D避難所を表示中｜${missing}件は座標欠損のため地図非表示（件数は保持）`
        : `D避難所を${summary.mappableRecords.length}件表示中`,
    missing > 0 ? "warning" : "success"
  );

  showDatasetOverview(summary, sourceLabel);
  // A delayed D JSON response must not pan back to the municipality after
  // the user has explicitly selected a different origin for GSI discovery.
  if (displayMode === "region") fitCurrentRegion();
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
      `D RegionExportを読み込めませんでした（${error.message}）。${config.label} のJSONを選択するか、元のworktreeのpipeline/data/outputからコピーしてください。GSI公式地点探索は別データなので利用できます。`,
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
  clearReferenceDiscovery();
  document.getElementById("resetView").textContent = `${currentRegion().label}の表示範囲へ`;
  clearShelters();
  const hasBoundary = renderReferenceBoundary();
  document.getElementById("boundaryNote").textContent = hasBoundary
    ? "自治体境界（fixture）"
    : "自治体境界（fixtureなし）";
  document.getElementById("boundary").disabled = !hasBoundary;
  if (!hasBoundary) document.getElementById("boundary").checked = false;
  else document.getElementById("boundary").checked = true;
  setDisplayMode("region");
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
document.getElementById("boundary").addEventListener("change", applyDisplayMode);
document.getElementById("shelter").addEventListener("change", applyDisplayMode);
document.getElementById("facilityDisplayMode").addEventListener("change", event => {
  setDisplayMode(event.target.value);
  if (displayMode === "nearby") focusReferenceCandidates();
});
document.getElementById("focusReferenceTiles").addEventListener("click", focusDisplayScope);
document.getElementById("toggleDMarkers").addEventListener("click", () => {
  setDisplayMode(displayMode === "both" ? "nearby" : "both");
});

document.getElementById("floodOpacity").addEventListener("input", event => {
  const percent = Number(event.target.value);
  officialFloodLayer.setOpacity(percent / 100);
  document.getElementById("floodOpacityValue").textContent = `${percent}%`;
});

document.getElementById("facilityListSearch").addEventListener("input", event => {
  facilityListQuery = event.target.value;
  facilityListPage = 0;
  renderFacilityList();
});
document.getElementById("facilityListPrev").addEventListener("click", () => {
  if (facilityListPage > 0) facilityListPage -= 1;
  renderFacilityList();
});
document.getElementById("facilityListNext").addEventListener("click", () => {
  facilityListPage += 1;
  renderFacilityList();
});

// Coordinate input is a local test-navigation control, not geocoding and
// not evidence that an official reference site exists at the selected point.
function parseCoordinatePair(value) {
  if (typeof value !== "string") return null;
  const parts = value.trim().replace(/[，、]/g, ",").split(",");
  const decimal = /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/;
  if (parts.length !== 2 || parts.some(part => !decimal.test(part.trim()))) return null;
  const [latitude, longitude] = parts.map(part => Number(part.trim()));
  if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
      Math.abs(latitude) > 85.05112878 || longitude < -180 || longitude > 180) return null;
  return { latitude, longitude };
}

document.getElementById("coordinateSearchForm").addEventListener("submit", event => {
  event.preventDefault();
  const input = document.getElementById("coordinateSearchInput");
  const feedback = document.getElementById("coordinateSearchStatus");
  const location = parseCoordinatePair(input.value);
  if (!location) {
    input.setAttribute("aria-invalid", "true");
    feedback.textContent =
      "入力を確認してください。緯度, 経度の順に10進数で入力（例：35.70, 140.10）。" +
      "緯度は-85.05112878～85.05112878、経度は-180～180です。";
    return; // Never move the marker, change source mode or request a tile.
  }
  setReferenceOrigin(location.latitude, location.longitude);
  // Always visibly navigate to the requested position, even where the C
  // reference tile is unpublished and the discovery appropriately fails closed.
  map.setView([location.latitude, location.longitude], 12);
  feedback.textContent = "指定座標へ移動しました。公式掲載情報は照合結果を確認してください。";
});

function beginSelectingOrigin() {
  if (!document.getElementById("facilityListPanel").hidden) return;
  choosingOrigin = true;
  document.getElementById("originStatus").textContent = "地図上の出発地点をクリックしてください。";
  updateMapOriginAction("地点指定モード：地図を1回クリック", true);
}
document.getElementById("selectOrigin").addEventListener("click", beginSelectingOrigin);
document.getElementById("mapOriginShortcut").addEventListener("click", beginSelectingOrigin);
function suggestManualOriginAfterGpsFailure(message) {
  document.getElementById("originStatus").textContent = message +
    " 地図上の「緯度・経度で地点を指定」から手動で探索できます。";
  document.getElementById("coordinateSearchStatus").textContent =
    "GPSを使わず、緯度・経度を入力して「座標で探索」を押せます。";
  const input = document.getElementById("coordinateSearchInput");
  if (typeof input.focus === "function") input.focus();
}

document.getElementById("useGps").addEventListener("click", () => {
  const requestId = ++gpsRequestSequence;
  if (typeof navigator === "undefined" || !navigator.geolocation) {
    suggestManualOriginAfterGpsFailure("この環境では位置情報を利用できません。");
    return;
  }
  document.getElementById("originStatus").textContent = "位置情報の許可を確認しています…";
  try {
    navigator.geolocation.getCurrentPosition(
      position => {
        if (requestId !== gpsRequestSequence) return;
        const latitude = position?.coords?.latitude;
        const longitude = position?.coords?.longitude;
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
            Math.abs(latitude) > 85.05112878 || Math.abs(longitude) > 180) {
          suggestManualOriginAfterGpsFailure("取得した位置情報の座標を利用できません。");
          return;
        }
        setReferenceOrigin(latitude, longitude);
        map.setView([latitude, longitude], 12);
      },
      () => {
        if (requestId !== gpsRequestSequence) return;
        suggestManualOriginAfterGpsFailure("位置情報が拒否されたか、取得できませんでした。");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }
    );
  } catch (_) {
    if (requestId === gpsRequestSequence) {
      suggestManualOriginAfterGpsFailure("位置情報の取得を開始できませんでした。");
    }
  }
});

document.getElementById("resetView").addEventListener("click", fitCurrentRegion);
document.getElementById("autoLoad").addEventListener("click", tryAutoLoad);
regionSelect.addEventListener("change", event => {
  selectRegion(event.target.value);
  // Keep the deep-link's municipality consistent with the visible dropdown.
  // Only explicit region changes update the URL; map/GPS/coordinate queries
  // remain private and must never be serialized to a query parameter.
  if (window.location.protocol !== "file:" &&
      typeof window.history?.replaceState === "function") {
    try {
      const url = new URL(window.location.href);
      url.searchParams.set("region", selectedRegionCode);
      window.history.replaceState(null, "", url.pathname + url.search + url.hash);
    } catch (_) {
      // Unsupported browser history must not stop the D/GSI region selection.
    }
  }
});

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
  if (choosingOrigin) {
    setReferenceOrigin(event.latlng.lat, event.latlng.lng);
    return;
  }
  // A background tap used to dismiss another panel should never instantly
  // reopen a raster information sheet on that very same click.
  if (window.HINANEX_MAP_FIRST_UI?.wasDismissalClick?.(event.originalEvent)) return;
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

const externalTileSampleCounts = new Map();
function reportExternalTileError(sourceName, event) {
  // Leaflet's tileerror event is not an HTTP status / proof of no flood.
  // The official raster specification limits geography and native zoom
  // 2–17; log URL samples for DevTools Network without guessing a cause.
  const samples = externalTileSampleCounts.get(sourceName) || 0;
  if (samples < 3) {
    const failedUrl = String(event?.tile?.currentSrc || event?.tile?.src || "");
    console.warn("[HINANEX] 外部タイルの一部を表示できません", {
      source: sourceName,
      tileUrl: /^https:\/\/(cyberjapandata|disaportaldata)\.gsi\.go\.jp\//.test(failedUrl) ? failedUrl : "(URL不明)",
      detail: "HTTP status / 範囲外 / ブラウザ制限はNetworkで個別確認"
    });
    externalTileSampleCounts.set(sourceName, samples + 1);
  }
  if (sourceName === "公的洪水ラスタ") {
    // D load/region navigation may later overwrite the generic status line.
    // Preserve an independent and visible fail-closed notice near the raster
    // toggle; it applies to observed missing imagery only, NOT to shelters.
    const rasterNotice = document.getElementById("externalFloodTileNotice");
    rasterNotice.hidden = false;
    rasterNotice.textContent =
      "公的洪水ラスタの一部を取得できません。空白や未表示は「浸水なし」を意味しません。施設のD・GSI掲載情報とは別データです。";
    window.HINANEX_MAP_FIRST_UI?.showRasterWarning?.(rasterNotice.textContent);
  }
  if (externalTileWarnings.has(sourceName)) return;
  externalTileWarnings.add(sourceName);
  setStatus(
    "外部タイルの一部が表示できません：" + [...externalTileWarnings].join(" / ") +
    "。浸水の有無・安全性は判定できません。公的洪水ラスタとD/GSI施設情報は別系統です（原因はNetworkで確認）。",
    "warning"
  );
}

baseMap.on("tileerror", event => reportExternalTileError("背景地図", event));
officialFloodLayer.on("tileerror", event => reportExternalTileError("公的洪水ラスタ", event));

try {
  selectRegion(selectedRegionCode);
} catch (error) {
  console.error(error);
  setStatus(`GIS初期化に失敗しました: ${error.message}`, "error");
}
