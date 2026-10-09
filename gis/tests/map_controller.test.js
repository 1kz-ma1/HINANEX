const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const assert = require("node:assert/strict");
const { URL } = require("node:url");

const root = path.resolve(__dirname, "../gis/js");
const adapterCode = fs.readFileSync(path.join(root, "d_region_adapter.js"), "utf8");
const facilityListCode = fs.readFileSync(path.join(root, "facility_list.js"), "utf8");
const mapCode = fs.readFileSync(path.join(root, "map.js"), "utf8");
const discoveryCode = fs.readFileSync(path.join(root, "flood_discovery.js"), "utf8");
const referenceCode = fs.readFileSync(path.join(root, "reference_data.js"), "utf8");

function payload(code, name, records) {
  return {
    region: { code, name },
    datasets: [{
      region_code: code,
      region_name: name,
      requirement_code: "shelter_location",
      records,
      evidence: [{ source_name: "D integration fixture", publisher: "HINANEX test" }],
      normalized_at: "2026-09-29T00:00:00Z"
    }],
    assessments: [],
    capabilities: [],
    gaps: [],
    recommendations: [],
    meta: {
      schema_version: "0.9",
      generated_at: "2026-09-29T00:00:00Z",
      dataset_count: 1,
      assessment_count: 0,
      capability_count: 0,
      gap_count: 0,
      recommendation_count: 0,
      evidence_count: 1
    }
  };
}

function record(id, name, latitude, longitude, detailUrl = null) {
  return {
    id,
    name,
    latitude,
    longitude,
    address: null,
    administrative_area: null,
    facility_type: "shelter",
    supported_disasters: null,
    accessibility: null,
    capacity: null,
    detail_url: detailUrl,
    notes: "integration fixture"
  };
}

function makeElement(id) {
  return {
    id,
    value: id === "region" ? "13123" : id === "floodOpacity" ? "58" : "",
    checked: true,
    disabled: false,
    hidden: true,
    textContent: "",
    innerHTML: "",
    className: "",
    dataset: {},
    files: [],
    listeners: {},
    attributes: {},
    setAttribute(name, value) { this.attributes[name] = String(value); },
    getAttribute(name) { return this.attributes[name]; },
    focus() { this.focusCount = (this.focusCount || 0) + 1; },
    addEventListener(name, fn) { this.listeners[name] = fn; }
  };
}

function makeLeafletStub() {
  const mapLayers = new Set();
  const panes = {};
  const groups = [];
  const markers = [];
  const tiles = [];

  const map = {
    handlers: {},
    zoom: 13,
    overviewFitZoom: 4,
    getBoundsZoom(bounds, inside, padding) {
      this.overviewFitArgs = { bounds, inside, padding };
      return this.overviewFitZoom;
    },
    setMinZoom(value) {
      this.minZoom = value;
      this.minZoomCalls = [...(this.minZoomCalls || []), value];
      return this;
    },
    setView(latlng, zoom) { this.lastView = { latlng, zoom }; this.zoom = zoom; return this; },
    getZoom() { return this.zoom; },
    project(latlng, zoom) {
      // Web Mercator world pixels, deterministic independent of viewport.
      const world = 256 * Math.pow(2, zoom);
      const latRad = latlng[0] * Math.PI / 180;
      return {
        x: (latlng[1] + 180) / 360 * world,
        y: (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * world
      };
    },
    createPane(name) { panes[name] = { style: {} }; },
    getPane(name) { return panes[name]; },
    addLayer(layer) { mapLayers.add(layer); layer._onMap = true; return this; },
    removeLayer(layer) { mapLayers.delete(layer); layer._onMap = false; return this; },
    hasLayer(layer) { return mapLayers.has(layer); },
    fitBounds(bounds) { this.lastBounds = bounds; return this; },
    invalidateSize(options) { this.invalidateCalls = [...(this.invalidateCalls || []), options]; return this; },
    on(name, fn) { this.handlers[name] = fn; return this; }
  };

  function group() {
    const value = {
      items: [],
      addTo(target) { target.addLayer(this); return this; },
      addLayer(layer) {
        if (!this.items.includes(layer)) this.items.push(layer);
        return this;
      },
      removeLayer(layer) {
        this.items = this.items.filter(item => item !== layer);
        return this;
      },
      clearLayers() { this.items = []; return this; }
    };
    groups.push(value);
    return value;
  }

  function tileLayer(_url, options) {
    const layer = {
      options,
      handlers: {},
      addTo(target) { target.addLayer(this); return this; },
      setOpacity(value) { this.opacity = value; return this; },
      on(name, fn) { this.handlers[name] = fn; return this; }
    };
    tiles.push(layer);
    return layer;
  }

  function bounds(points) {
    return { points, isValid: () => Array.isArray(points) && points.length > 0 };
  }

  return {
    map: (_id, options) => { map.options = options; return map; },
    tileLayer,
    layerGroup: group,
    control: { scale: () => ({ addTo: () => ({}) }) },
    divIcon: value => value,
    marker: (latlng, options) => {
      const marker = {
        latlng, options,
        handlers: {},
        bindPopup(content) { this.popupHtml = content; return this; },
        on(name, fn) { this.handlers[name] = fn; return this; },
        addTo(target) { target.addLayer(this); return this; }
      };
      markers.push(marker);
      return marker;
    },
    rectangle: (bounds, options) => ({
      bounds, options,
      addTo(target) { target.addLayer(this); return this; }
    }),
    geoJSON: (data, options) => ({
      data,
      options,
      addTo(target) { target.addLayer(this); return this; },
      getBounds: () => ({ isValid: () => true })
    }),
    latLngBounds: bounds,
    DomEvent: { stopPropagation: () => {} },
    __map: map,
    __groups: groups,
    __markers: markers,
    __panes: panes,
    __tiles: tiles
  };
}

function makeContext({ protocol, fetchImpl, href = null, discoveryOverride = null, geolocation = undefined, localStorage = undefined }) {
  const ids = [
    "map", "mapUnavailable", "mapUnavailableMessage", "details", "status", "region",
    "basemap", "officialFlood", "boundary", "boundaryNote", "shelter", "floodOpacity",
    "floodOpacityValue", "resetView", "regionExportFile", "autoLoad", "recordCount",
    "mappedCount", "missingCoordinateCount", "datasetStatus", "datasetChip",
    "mapUnavailableTitle", "facilityListPanel", "facilityListSearch",
    "facilityListCount", "facilityListResults", "facilityListPrev", "facilityListNext",
    "facilityListPage", "scenarioHazard", "selectOrigin", "useGps",
    "originStatus", "floodDiscoveryResults", "mapOriginShortcut", "mapOriginShortcutStatus",
    "referenceMapSummary", "referenceMapCoverage", "referenceMapCount",
    "focusReferenceTiles", "toggleDMarkers", "facilityDisplayMode", "facilityDisplayModeDescription",
    "coordinateSearchForm", "coordinateSearchInput", "coordinateSearchButton",
    "coordinateSearchHelp", "coordinateSearchStatus", "externalFloodTileNotice",
    "gisLayout", "uiTabNormal", "uiTabScenario", "scenarioIntro",
    "toggleLeftPanel", "toggleRightPanel"
  ];
  const elements = Object.fromEntries(ids.map(id => [id, makeElement(id)]));
  const L = makeLeafletStub();
  const location = { protocol, href: href ?? `${protocol}//test/gis/gis/index.html` };
  if (protocol === "file:" && !href) location.href = "file:///tmp/HINANEX/gis/gis/index.html";
  const history = {
    calls: [],
    replaceState(_state, _title, nextUrl) {
      this.calls.push(nextUrl);
      location.href = new URL(nextUrl, location.href).href;
    }
  };

  const context = {
    window: { location, history, localStorage },
    document: { getElementById: id => elements[id] },
    navigator: geolocation === undefined ? undefined : { geolocation },
    L,
    fetch: fetchImpl,
    AbortController,
    URL,
    console,
    setTimeout,
    clearTimeout
  };
  context.window.window = context.window;
  vm.createContext(context);
  vm.runInContext(referenceCode, context, { filename: "reference_data.js" });
  vm.runInContext(adapterCode, context, { filename: "d_region_adapter.js" });
  vm.runInContext(facilityListCode, context, { filename: "facility_list.js" });
  vm.runInContext(discoveryOverride === null ? discoveryCode : discoveryOverride, context, { filename: "flood_discovery.js" });
  vm.runInContext(mapCode, context, { filename: "map.js" });
  return { context, elements, L, history };
}

const edogawa = payload("13123", "東京都江戸川区", [
  record("e1", "Edogawa A", 35.70, 139.88, "https://example.invalid/a"),
  record("e2", "Edogawa B", 35.72, 139.90, "javascript:alert(1)")
]);
const niigata = payload("15100", "新潟県新潟市", [
  record("n1", "Niigata A", 37.90, 139.02)
]);
niigata.scenarios = [{
  scenario_id: "flood_shelter_selection",
  region_code: "15100",
  status: "UNKNOWN",
  requirement_assessment: { discovery_status: "AVAILABLE" },
  facility_results: [{
    facility_id: "n1",
    status: "UNKNOWN",
    reason: "ODSの公式記号の意味は確認中",
    fact: {
      facility_id: "n1",
      hazard_scope_raw: "災害種別_洪水",
      official_status_raw: "2階以上",
      usable_floor_raw: "2階以上",
      source_record_trace: "csv_row=2",
      join_status: "DIRECT_SAME_SOURCE",
      source_url: "https://example.test/niigata.csv"
    }
  }]
}];
const nagoya = payload("23100", "愛知県名古屋市", [
  record("g1", "Nagoya A", null, null),
  record("g2", '<img src=x onerror="alert(1)">', null, null)
]);
nagoya.datasets[0].records[0].address = "名古屋市中区丸の内";
nagoya.datasets[0].records[0].administrative_area = "中区";
nagoya.scenarios = [{
  scenario_id: "flood_shelter_selection",
  region_code: "23100",
  status: "UNKNOWN",
  requirement_assessment: { discovery_status: "AVAILABLE" },
  facility_results: [
    {
      facility_id: "g1", status: "UNKNOWN",
      reason: "名古屋市の洪水・内水統合列は洪水のみの確定意味ではない",
      fact: {
        facility_id: "g1", official_status_raw: "洪水・内水",
        usable_floor_raw: null, hazard_scope_raw: "洪水・内水",
        join_status: "DIRECT_SAME_SOURCE",
        source_record_trace: "file=test.xls;sheet=0;excel_row=5",
        source_url: "https://example.test/nagoya.xls"
      }
    },
    {
      facility_id: "g2", status: "UNKNOWN", reason: "",
      fact: {
        facility_id: "g2", official_status_raw: null,
        usable_floor_raw: null, hazard_scope_raw: "洪水・内水",
        join_status: "DIRECT_SAME_SOURCE",
        source_record_trace: "file=test.xls;sheet=0;excel_row=6",
        source_url: "javascript:alert(1)"
      }
    }
  ]
}];

(async () => {
  // file://: the old browser-origin warning is avoided by never attempting auto-fetch.
  let fileFetchCalls = 0;
  const fileCase = makeContext({
    protocol: "file:",
    fetchImpl: async () => { fileFetchCalls += 1; throw new Error("must not fetch"); }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(fileFetchCalls, 0);
  assert.match(fileCase.elements.datasetStatus.textContent, /file:\/\//);
  assert.match(fileCase.elements.status.textContent, /手動読込/);

  // Two independent UI tabs operate on ONE map, never on two data pipelines.
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-ui-mode"), "normal");
  assert.equal(fileCase.elements.gisLayout.getAttribute("aria-labelledby"), "uiTabNormal");
  assert.equal(fileCase.elements.uiTabNormal.getAttribute("aria-selected"), "true");
  assert.equal(fileCase.elements.uiTabScenario.getAttribute("aria-selected"), "false");
  assert.equal(fileCase.elements.scenarioIntro.hidden, true);
  const fileMap = fileCase.L.__map;
  fileCase.elements.uiTabScenario.listeners.click();
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-ui-mode"), "scenario");
  assert.equal(fileCase.elements.gisLayout.getAttribute("aria-labelledby"), "uiTabScenario");
  assert.equal(fileCase.elements.uiTabScenario.getAttribute("aria-selected"), "true");
  assert.equal(fileCase.elements.uiTabScenario.tabIndex, 0);
  assert.equal(fileCase.elements.uiTabNormal.tabIndex, -1);
  assert.equal(fileCase.elements.scenarioIntro.hidden, false);
  assert.strictEqual(fileCase.L.__map, fileMap);
  let preventedTabScroll = false;
  fileCase.elements.uiTabScenario.listeners.keydown({
    key: "ArrowLeft", preventDefault() { preventedTabScroll = true; }
  });
  assert.equal(preventedTabScroll, true);
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-ui-mode"), "normal");
  assert.equal(fileCase.elements.uiTabNormal.focusCount, 1);
  fileCase.elements.uiTabNormal.listeners.keydown({key: "End", preventDefault() {}});
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-ui-mode"), "scenario");
  fileCase.elements.uiTabScenario.listeners.keydown({key: "Home", preventDefault() {}});
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-ui-mode"), "normal");
  assert.equal(fileFetchCalls, 0, "tabs may not load even D/GSI data in file mode");
  // Start in map-first: rails are collapsed so the map fills the viewport.
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-left-panel"), "closed");
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-right-panel"), "closed");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("aria-expanded"), "false");
  assert.equal(fileCase.elements.toggleRightPanel.getAttribute("aria-expanded"), "false");
  fileCase.elements.toggleLeftPanel.listeners.click();
  fileCase.elements.toggleRightPanel.listeners.click();
  // Exclude the initial map-first setup from the legacy four-toggle invariant.
  fileCase.L.__map.invalidateCalls = [];
  // Collapse controls remain visible in the header even with both panels closed.
  // It is only a viewport size notification; never move the map or refetch.
  const boundsBeforeCollapse = fileMap.lastBounds;
  const zoomBeforeCollapse = fileMap.getZoom();
  fileCase.elements.toggleLeftPanel.listeners.click();
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-left-panel"), "closed");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("aria-expanded"), "false");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("aria-label"), "左メニューを開く");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("title"), "左メニューを開く");
  fileCase.elements.toggleRightPanel.listeners.click();
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-right-panel"), "closed");
  assert.equal(fileCase.elements.toggleRightPanel.getAttribute("aria-expanded"), "false");
  assert.equal(fileCase.elements.toggleRightPanel.getAttribute("aria-label"), "右詳細を開く");
  fileCase.elements.toggleLeftPanel.listeners.click();
  fileCase.elements.toggleRightPanel.listeners.click();
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-left-panel"), "open");
  assert.equal(fileCase.elements.gisLayout.getAttribute("data-right-panel"), "open");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("aria-expanded"), "true");
  assert.equal(fileCase.elements.toggleRightPanel.getAttribute("aria-expanded"), "true");
  assert.equal(fileCase.elements.toggleLeftPanel.getAttribute("aria-label"), "左メニューを閉じる");
  assert.equal(fileCase.elements.toggleRightPanel.getAttribute("aria-label"), "右詳細を閉じる");
  assert.equal(fileMap.invalidateCalls.length, 4);
  assert.equal(fileMap.invalidateCalls.every(args => args.pan === false && args.animate === false), true);
  assert.strictEqual(fileMap.lastBounds, boundsBeforeCollapse);
  assert.equal(fileMap.getZoom(), zoomBeforeCollapse);
  assert.strictEqual(fileCase.L.__map, fileMap);
  assert.equal(fileFetchCalls, 0);

  // HTTP: D RegionExport is loaded and counts are reflected in UI state.
  const byUrl = { edogawa, niigata, nagoya };
  const httpCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const key = Object.keys(byUrl).find(candidate => String(url).includes(`${candidate}.json`));
      if (!key) return { ok: false, status: 404, json: async () => ({}) };
      return { ok: true, status: 200, json: async () => byUrl[key] };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(httpCase.elements.recordCount.textContent, 2);
  assert.equal(httpCase.elements.mappedCount.textContent, 2);
  assert.equal(httpCase.elements.missingCoordinateCount.textContent, 0);
  assert.match(httpCase.elements.status.textContent, /2件表示中/);
  assert.match(httpCase.elements.resetView.textContent, /東京都 江戸川区/);
  assert.equal(httpCase.elements.selectOrigin.disabled, false);
  assert.equal(httpCase.elements.facilityDisplayMode.value, "region");
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[1]), true);
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[3]), false);
  assert.match(httpCase.elements.facilityDisplayModeDescription.textContent, /選択地域のD施設/);
  assert.equal(httpCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "false");
  assert.match(httpCase.elements.mapOriginShortcutStatus.textContent, /地図/);
  assert.match(httpCase.elements.floodDiscoveryResults.innerHTML, /地図から出発地点/);

  // Exact numeric-coordinate search is available by Enter/form submission,
  // not only by an imprecise manual map click. Invalid values must not
  // change the selected origin, map viewport, mode or make HTTP requests.
  let coordinateFetchCount = 0;
  const coordinateCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      coordinateFetchCount += 1;
      if (String(url).endsWith("edogawa.json")) {
        return { ok: true, status: 200, json: async () => edogawa };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  const initialView = coordinateCase.L.__map.lastView;
  const initialCount = coordinateFetchCount;
  for (const invalid of ["", "35.70", "35.70,", ",140.10", "35.7,140.1,20",
                         "nan,140", "35north,139", "90,140", "-90,140",
                         "35.7,181", "35.7,-181", "1e2,139"]) {
    const control = coordinateCase.elements.coordinateSearchInput;
    control.value = invalid;
    let prevented = false;
    coordinateCase.elements.coordinateSearchForm.listeners.submit({
      preventDefault() { prevented = true; }
    });
    assert.equal(prevented, true, invalid + " must prevent native navigation");
    assert.equal(control.getAttribute("aria-invalid"), "true");
    assert.match(coordinateCase.elements.coordinateSearchStatus.textContent, /入力を確認/);
    assert.match(coordinateCase.elements.originStatus.textContent, /未選択/);
    assert.equal(coordinateCase.elements.facilityDisplayMode.value, "region");
    assert.strictEqual(coordinateCase.L.__map.lastView, initialView);
    assert.equal(coordinateFetchCount, initialCount, "invalid origin cannot make requests");
  }
  coordinateCase.elements.coordinateSearchInput.value = " 35.70， 140.10 ";
  coordinateCase.elements.coordinateSearchForm.listeners.submit({ preventDefault() {} });
  assert.equal(coordinateCase.elements.coordinateSearchInput.getAttribute("aria-invalid"), "false");
  assert.equal(coordinateCase.elements.coordinateSearchInput.value, "35.70000, 140.10000");
  assert.match(coordinateCase.elements.coordinateSearchStatus.textContent, /指定座標へ移動/);
  assert.match(coordinateCase.elements.originStatus.textContent, /35.70000, 140.10000/);
  assert.equal(coordinateCase.elements.facilityDisplayMode.value, "nearby");
  assert.equal(coordinateCase.L.__map.lastView.zoom, 12);
  assert.equal(coordinateCase.L.__map.lastView.latlng[0], 35.7);
  assert.equal(coordinateCase.L.__map.lastView.latlng[1], 140.1);
  assert.match(coordinateCase.elements.details.innerHTML, /35.70000, 140.10000/);
  assert.match(coordinateCase.elements.details.innerHTML, /この地点の浸水リスク/);
  assert.doesNotMatch(coordinateCase.elements.details.innerHTML, /洪水浸水想定区域（想定最大規模）/);
  assert.doesNotMatch(coordinateCase.context.window.location.href, /lat=|lon=|origin=/);
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.ok(coordinateFetchCount > initialCount);
  assert.match(coordinateCase.elements.floodDiscoveryResults.innerHTML, /未検証|独立照合待ち/);
  // The same form can move to a second source cell without changing region.
  coordinateCase.elements.coordinateSearchInput.value = "35.70、139.90";
  coordinateCase.elements.coordinateSearchForm.listeners.submit({ preventDefault() {} });
  assert.match(coordinateCase.elements.originStatus.textContent, /35.70000, 139.90000/);
  assert.equal(coordinateCase.L.__map.lastView.latlng[1], 139.9);
  await new Promise(resolve => setTimeout(resolve, 0));
  // A region change clears the old origin and field instead of reusing stale GPS data.
  coordinateCase.elements.region.value = "15100";
  coordinateCase.elements.region.listeners.change({ target: coordinateCase.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(coordinateCase.elements.coordinateSearchInput.value, "");
  assert.equal(coordinateCase.elements.coordinateSearchStatus.textContent, "");
  assert.equal(coordinateCase.elements.facilityDisplayMode.value, "region");
  assert.match(coordinateCase.context.window.location.href, /[?]region=15100$/);
  assert.equal(coordinateCase.history.calls.length, 1);
  assert.doesNotMatch(coordinateCase.context.window.location.href, /35.7|139.9|140.1/);

  // User action selects a point; missing C-accepted catalog never promotes
  // existing Edogawa shelter_location records into safe/approved candidates.
  httpCase.elements.mapOriginShortcut.listeners.click();
  assert.equal(httpCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "true");
  assert.match(httpCase.elements.mapOriginShortcutStatus.textContent, /地点指定モード/);
  assert.match(httpCase.elements.originStatus.textContent, /地図上/);
  httpCase.L.__map.handlers.click({ latlng: { lat: 35.700, lng: 139.880 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(httpCase.elements.facilityDisplayMode.value, "nearby");
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[1]), false);
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[0]), false);
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[3]), true);
  assert.equal(httpCase.elements.shelter.disabled, true);
  assert.match(httpCase.elements.facilityDisplayModeDescription.textContent, /周辺の検証済みGSI/);
  assert.match(httpCase.elements.originStatus.textContent, /端末内だけ/);
  assert.equal(httpCase.elements.coordinateSearchInput.value, "35.70000, 139.88000");
  assert.match(httpCase.elements.details.innerHTML, /35.70000, 139.88000/);
  assert.match(httpCase.elements.details.innerHTML, /地点指定/);
  assert.doesNotMatch(httpCase.elements.details.innerHTML, /この地点は安全です/);
  assert.match(httpCase.elements.floodDiscoveryResults.innerHTML, /独立照合待ち/);
  assert.match(httpCase.elements.mapOriginShortcutStatus.textContent, /未検証/);
  assert.equal(httpCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "false");
  assert.doesNotMatch(httpCase.elements.floodDiscoveryResults.innerHTML, /Edogawa A/);
  assert.equal(httpCase.elements.referenceMapSummary.hidden, true);
  assert.equal(httpCase.L.__groups[2].items.length, 0);
  assert.equal(httpCase.L.__groups[3].items.length, 0);
  // A missing source never restores unrelated D pins into GSI-only scope.
  httpCase.elements.facilityDisplayMode.value = "region";
  httpCase.elements.facilityDisplayMode.listeners.change({ target: httpCase.elements.facilityDisplayMode });
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[1]), true);
  assert.equal(httpCase.L.__map.hasLayer(httpCase.L.__groups[3]), false);
  assert.equal(httpCase.elements.shelter.disabled, false);
  // Geolocation permission or API absence must not cause a crash.
  httpCase.elements.useGps.listeners.click();
  assert.match(httpCase.elements.originStatus.textContent, /緯度・経度/);
  assert.match(httpCase.elements.coordinateSearchStatus.textContent, /GPSを使わず/);
  assert.equal(httpCase.elements.coordinateSearchInput.focusCount, 1);

  // Explicit user GPS permission outcome: refusal should preserve the map
  // and lead back to the numeric coordinate field, even after a pending request.
  const gpsCallbacks = [];
  const gpsCase = makeContext({
    protocol: "http:",
    geolocation: {
      getCurrentPosition(success, error, opts) {
        gpsCallbacks.push({ success, error, opts });
      }
    },
    fetchImpl: async url => String(url).includes("edogawa.json")
      ? { ok: true, status: 200, json: async () => edogawa }
      : { ok: false, status: 404, json: async () => ({}) }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(gpsCallbacks.length, 0, "geolocation must never start without explicit click");
  gpsCase.elements.useGps.listeners.click();
  assert.equal(gpsCallbacks.length, 1);
  assert.equal(gpsCallbacks[0].opts.enableHighAccuracy, false);
  assert.equal(gpsCallbacks[0].opts.timeout, 10000);
  assert.match(gpsCase.elements.originStatus.textContent, /許可を確認/);
  const originalGpsView = gpsCase.L.__map.lastView;
  gpsCallbacks[0].error({ code: 1, message: "denied" });
  assert.match(gpsCase.elements.originStatus.textContent, /拒否/);
  assert.match(gpsCase.elements.originStatus.textContent, /緯度・経度/);
  assert.match(gpsCase.elements.coordinateSearchStatus.textContent, /GPSを使わず/);
  assert.equal(gpsCase.elements.coordinateSearchInput.focusCount, 1);
  assert.equal(gpsCase.elements.facilityDisplayMode.value, "region");
  assert.strictEqual(gpsCase.L.__map.lastView, originalGpsView);

  // Invalid coordinates from a broken GPS provider are not treated as a
  // valid origin; no fallback to a guessed nearby location.
  gpsCase.elements.useGps.listeners.click();
  gpsCallbacks[1].success({ coords: { latitude: NaN, longitude: 139.9 } });
  assert.match(gpsCase.elements.originStatus.textContent, /座標を利用できません/);
  assert.equal(gpsCase.elements.facilityDisplayMode.value, "region");

  // A new explicit form choice supersedes an earlier pending GPS response.
  gpsCase.elements.useGps.listeners.click();
  gpsCase.elements.coordinateSearchInput.value = "35.70,140.10";
  gpsCase.elements.coordinateSearchForm.listeners.submit({ preventDefault() {} });
  assert.equal(gpsCase.elements.facilityDisplayMode.value, "nearby");
  assert.match(gpsCase.elements.originStatus.textContent, /35.70000, 140.10000/);
  gpsCallbacks[2].success({ coords: { latitude: 35.7, longitude: 139.9 } });
  gpsCallbacks[2].error({ code: 1 });
  assert.match(gpsCase.elements.originStatus.textContent, /35.70000, 140.10000/);
  assert.equal(gpsCase.elements.coordinateSearchInput.value, "35.70000, 140.10000");

  // A newly requested and granted GPS position is drawn in its own top pane.
  gpsCase.elements.useGps.listeners.click();
  gpsCallbacks[3].success({ coords: { latitude: 35.70, longitude: 139.90 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(gpsCase.elements.originStatus.textContent, /35.70000, 139.90000/);
  assert.equal(gpsCase.L.__map.lastView.zoom, 12);
  assert.equal(gpsCase.elements.coordinateSearchInput.value, "35.70000, 139.90000");
  assert.equal(gpsCase.elements.facilityDisplayMode.value, "nearby");
  const activeGpsMarker = gpsCase.L.__markers.at(-1);
  assert.equal(activeGpsMarker.options.pane, "referenceOriginPane");
  assert.equal(gpsCase.L.__panes.referenceOriginPane.style.zIndex, 730);
  assert.equal(gpsCase.L.__panes.referenceSitePane.style.zIndex, 690);
  assert.equal(activeGpsMarker.options.icon.iconSize[0], 36);
  assert.match(activeGpsMarker.options.icon.html, /避難先ではありません/);
  assert.doesNotMatch(gpsCase.context.window.location.href, /origin=|lat=|lon=/);
  gpsCase.elements.useGps.listeners.click();
  gpsCase.elements.region.value = "23100";
  gpsCase.elements.region.listeners.change({ target: gpsCase.elements.region });
  gpsCallbacks[4].success({ coords: { latitude: 35.7, longitude: 139.9 } });
  assert.equal(gpsCase.elements.coordinateSearchInput.value, "");
  assert.equal(gpsCase.elements.facilityDisplayMode.value, "region");

  // Real browsers can load cached single-tile discovery JS with a fresh map.js.
  // Their method signatures differ: report a module/version mismatch instead
  // of throwing TypeError on initial region selection or on map click.
  const pageHtml = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const discoveryAsset = pageHtml.match(new RegExp("js/flood_discovery[.]js[?]v=([A-Za-z0-9_-]+)"));
  const mapAsset = pageHtml.match(new RegExp("js/map[.]js[?]v=([A-Za-z0-9_-]+)"));
  assert.ok(discoveryAsset, "flood_discovery.js needs a versioned URL");
  assert.ok(mapAsset, "map.js needs a versioned URL");
  // UI-only map changes bust the consumer asset without changing the
  // accepted discovery API. Assert compatibility by both embedded signatures,
  // not by equating unrelated HTTP cache tags.
  assert.equal(discoveryAsset[1], "gsi-z10-neighbors-20261009-v14");
  assert.equal(mapAsset[1], "cluster-stable-20261009-v5");
  assert.match(discoveryCode, new RegExp('apiVersion: "' + discoveryAsset[1] + '"'));
  assert.match(mapCode, new RegExp('REQUIRED_DISCOVERY_VERSION = "' + discoveryAsset[1] + '"'));
  const oldScriptCase = makeContext({
    protocol: "http:",
    discoveryOverride: "window.HINANEX_FLOOD_DISCOVERY = { discoverReferenceSites: function () {} };",
    fetchImpl: async url => ({ ok: true, status: 200, json: async () => edogawa })
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(oldScriptCase.elements.floodDiscoveryResults.textContent, /バージョンが一致しません/);
  oldScriptCase.elements.selectOrigin.listeners.click();
  oldScriptCase.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.9 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(oldScriptCase.elements.floodDiscoveryResults.textContent, /再読み込み/);
  assert.equal(oldScriptCase.elements.floodDiscoveryResults.innerHTML, "");
  assert.equal(oldScriptCase.elements.recordCount.textContent, 2);

  const noScriptCase = makeContext({
    protocol: "http:",
    discoveryOverride: "",
    fetchImpl: async url => ({ ok: true, status: 200, json: async () => edogawa })
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(noScriptCase.elements.floodDiscoveryResults.textContent, /バージョンが一致しません/);
  assert.equal(noScriptCase.elements.recordCount.textContent, 2);

  // GIS must explain a missing ignored RegionExport without disabling
  // the independent official GSI discovery origin picker or hiding the map.
  const missingDCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      if (String(url).includes("edogawa.json")) return { ok: false, status: 404 };
      return { ok: false, status: 404 };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(missingDCase.elements.datasetStatus.textContent, /D RegionExportを読み込めません/);
  assert.match(missingDCase.elements.datasetStatus.textContent, /GSI公式地点探索は別データ/);
  assert.equal(missingDCase.elements.mapOriginShortcut.disabled, false);
  assert.equal(missingDCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "false");
  missingDCase.elements.mapOriginShortcut.listeners.click();
  assert.equal(missingDCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "true");
  missingDCase.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.9 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(missingDCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "false");
  assert.match(missingDCase.elements.originStatus.textContent, /35.70000/);

  // Frontend -> GIS deep link: a supported region query selects that region before auto-load.
  const queryCase = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=15100",
    fetchImpl: async url => {
      assert.match(String(url), /niigata\.json$/);
      return { ok: true, status: 200, json: async () => niigata };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(queryCase.elements.region.value, "15100");
  assert.equal(queryCase.history.calls.length, 0); // initial deep-link unchanged
  assert.equal(queryCase.elements.recordCount.textContent, 1);
  assert.match(queryCase.elements.resetView.textContent, /新潟県 新潟市/);

  // Unsupported query values are ignored safely and keep the HTML default region.
  const invalidQueryCase = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=99999",
    fetchImpl: async url => {
      assert.match(String(url), /edogawa\.json$/);
      return { ok: true, status: 200, json: async () => edogawa };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(invalidQueryCase.elements.region.value, "13123");
  assert.equal(invalidQueryCase.elements.recordCount.textContent, 2);
  assert.match(invalidQueryCase.elements.resetView.textContent, /東京都 江戸川区/);

  // Non-http(s) detail URLs are not rendered as clickable links.
  const shelterGroup = httpCase.L.__groups[1];
  shelterGroup.items[1].handlers.click({});
  assert.doesNotMatch(httpCase.elements.details.innerHTML, /javascript:/i);
  assert.doesNotMatch(httpCase.elements.details.innerHTML, /detail-link/);

  // Region switch: Niigata uses its D coordinates instead of retaining Edogawa state.
  httpCase.elements.region.value = "15100";
  httpCase.elements.region.listeners.change({ target: httpCase.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(httpCase.elements.recordCount.textContent, 1);
  assert.equal(httpCase.elements.mappedCount.textContent, 1);
  assert.equal(httpCase.elements.missingCoordinateCount.textContent, 0);
  assert.equal(httpCase.elements.mapUnavailable.hidden, true);
  assert.match(httpCase.elements.resetView.textContent, /新潟県 新潟市/);
  // Existing shelter markers remain ordinary location points. Clicking shows
  // only the Source's raw floor wording and D UNKNOWN, never flood safety.
  const niigataMarker = httpCase.L.__groups[1].items[0];
  niigataMarker.handlers.click({});
  assert.match(httpCase.elements.details.innerHTML, /2階以上/);
  assert.match(httpCase.elements.details.innerHTML, /元データ記載の災害（適合性未検証）/);
  assert.match(httpCase.elements.details.innerHTML, /UNKNOWN/);
  assert.match(httpCase.elements.details.innerHTML, /安全性|安全/);
  assert.doesNotMatch(httpCase.elements.details.innerHTML, /javascript:/i);

  // Nagoya currently has no machine-readable coordinates: keep records, show 0 markers,
  // and cover the map instead of inventing a center/geocoding the addresses.
  httpCase.elements.region.value = "23100";
  httpCase.elements.region.listeners.change({ target: httpCase.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(httpCase.elements.recordCount.textContent, 2);
  assert.equal(httpCase.elements.mappedCount.textContent, 0);
  assert.equal(httpCase.elements.missingCoordinateCount.textContent, 2);
  assert.equal(httpCase.elements.mapUnavailable.hidden, false);
  httpCase.elements.facilityDisplayMode.value = "both";
  httpCase.elements.facilityDisplayMode.listeners.change({ target: httpCase.elements.facilityDisplayMode });
  assert.equal(httpCase.elements.focusReferenceTiles.disabled, true);
  assert.match(httpCase.elements.facilityDisplayModeDescription.textContent, /座標欠損/);
  httpCase.elements.facilityDisplayMode.value = "region";
  httpCase.elements.facilityDisplayMode.listeners.change({ target: httpCase.elements.facilityDisplayMode });

  assert.match(httpCase.elements.mapUnavailableMessage.textContent, /位置を推測しません/);
  assert.equal(httpCase.elements.facilityListPanel.hidden, false);
  assert.equal(httpCase.elements.mapUnavailable.className, "map-unavailable has-facility-list");
  assert.match(httpCase.elements.mapUnavailableTitle.textContent, /施設一覧を検索できます/);
  assert.equal(httpCase.elements.selectOrigin.disabled, true,
    "a map click must not be offered under the coordinate-less Nagoya list overlay");
  assert.equal(httpCase.elements.mapOriginShortcut.disabled, true);
  assert.match(httpCase.elements.selectOrigin.textContent, /地図位置は未確認/);
  assert.match(httpCase.elements.originStatus.textContent, /施設一覧を利用/);
  assert.equal(httpCase.elements.useGps.disabled, false,
    "independent GPS workflow remains available and unchanged");
  const blockedOriginStatus = httpCase.elements.originStatus.textContent;
  httpCase.elements.selectOrigin.listeners.click();
  httpCase.elements.mapOriginShortcut.listeners.click();
  assert.equal(httpCase.elements.originStatus.textContent, blockedOriginStatus);
  assert.equal(httpCase.elements.mapOriginShortcut.getAttribute("aria-pressed"), "false");
  assert.match(httpCase.elements.facilityListCount.textContent, /取得施設 2件 \/ 検索一致 2件/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /Nagoya A/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /名古屋市中区丸の内/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /洪水・内水/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /UNKNOWN/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /file=test.xls/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /<details class="facility-list-card">/);
  // Arbitrary source text is rendered escaped and unsafe links are not opened.
  assert.match(httpCase.elements.facilityListResults.innerHTML, /&lt;img src=x onerror=/);
  assert.doesNotMatch(httpCase.elements.facilityListResults.innerHTML, /<img src=x onerror=/);
  assert.doesNotMatch(httpCase.elements.facilityListResults.innerHTML, /href="javascript:/);

  httpCase.elements.facilityListSearch.value = "中区 丸の内";
  httpCase.elements.facilityListSearch.listeners.input({
    target: httpCase.elements.facilityListSearch
  });
  assert.match(httpCase.elements.facilityListCount.textContent, /検索一致 1件/);
  assert.match(httpCase.elements.facilityListResults.innerHTML, /Nagoya A/);
  assert.doesNotMatch(httpCase.elements.facilityListResults.innerHTML, /&lt;img/);
  httpCase.elements.facilityListSearch.value = "見つからない";
  httpCase.elements.facilityListSearch.listeners.input({
    target: httpCase.elements.facilityListSearch
  });
  assert.match(httpCase.elements.facilityListResults.innerHTML, /一致する施設はありません/);

  // Switching to a mapped region clears stale query and hides the list.
  httpCase.elements.region.value = "15100";
  httpCase.elements.region.listeners.change({ target: httpCase.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(httpCase.elements.facilityListPanel.hidden, true);
  assert.equal(httpCase.elements.facilityListSearch.value, "");
  assert.equal(httpCase.elements.mapUnavailableTitle.textContent, "表示範囲を確定できません");
  assert.equal(httpCase.elements.selectOrigin.disabled, false);
  assert.equal(httpCase.elements.mapOriginShortcut.disabled, false);
  assert.equal(httpCase.elements.selectOrigin.textContent, "地図から出発地点を指定");
  assert.equal(httpCase.elements.mappedCount.textContent, 1);
  // A region with no verified coordinates must not visually expose the
  // previously selected municipality's basemap through a translucent mask.
  const css = fs.readFileSync(path.resolve(__dirname, "../gis/css/style.css"), "utf8");
  assert.match(css, /\.map-unavailable\{[^}]*background:#f4f8fc;/);
  assert.doesNotMatch(css, /\.map-unavailable\{[^}]*background:rgba\(/);

  // An explicitly C-accepted catalog can be inspected as *reference only*;
  // neither it nor distance sorting imply current opening or safe routing.
  const officialCatalog = {
    catalog_kind: "flood_designated_emergency_site_reference",
    region_code: "13123", hazard: "flood",
    status: "REFERENCE_ONLY", source_status: "C_ACCEPTED",
    https_provenance_status: "MATCH",
    https_provenance_checked_at_utc: "2026-10-09T03:00:00+00:00",
    total_source_records: 1,
    source_raw_sha256: "a".repeat(64), c_audit_reference: "C-TEST",
    sites: [{
      source_feature_key: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson#feature_index=0",
      name_raw: "<unsafe> TEST official place", address_raw: "TEST address",
      remarks_raw: null, disaster1_raw: 1, search_context_region_code: "13123",
      latitude: 35.705, longitude: 139.89,
      source_url: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson",
      source_record_trace: "feature_index=0",
      source_raw_sha256: "a".repeat(64),
      designation_kind: "designated_emergency_evacuation_site",
      hazard_dataset: "GSI_SKHB01_FLOOD"
    }]
  };
  const acceptedCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => String(url).includes("gsi_verified_tiles/")
      ? { ok: false, status: 404, json: async () => ({}) }
      : String(url).includes("edogawa_flood_site_catalog.json")
      ? { ok: true, status: 200, json: async () => officialCatalog }
      : { ok: true, status: 200, json: async () => edogawa }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  acceptedCase.elements.selectOrigin.listeners.click();
  acceptedCase.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.88 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(acceptedCase.elements.floodDiscoveryResults.innerHTML, /直線距離/);
  assert.match(acceptedCase.elements.mapOriginShortcutStatus.textContent, /検証済み/);
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, false);
  assert.match(acceptedCase.elements.referenceMapCoverage.textContent, /1\/9/);
  assert.match(acceptedCase.elements.referenceMapCount.textContent, /最大1地点/);
  assert.equal(acceptedCase.L.__groups[2].items.length, 1); // verified GSI tile outline
  assert.equal(acceptedCase.L.__groups[3].items.length, 1); // purple numbered pin, not D
  const acceptedPin = acceptedCase.L.__groups[3].items[0];
  assert.ok(acceptedPin.options.icon.html.includes("reference-site-marker"));
  assert.match(acceptedPin.options.icon.html, /aria-label="GSI公式掲載地点・安全性未判定"/);
  assert.doesNotMatch(acceptedPin.options.icon.html, />[1-5]<|GSI公式掲載参考地点[1-5]/);
  assert.match(acceptedPin.popupHtml, /GSI公式掲載地点（参考情報）/);
  assert.doesNotMatch(acceptedPin.popupHtml, /GSI公式掲載（参考\s*[0-9]|番号は|順位/);
  assert.ok(acceptedPin.popupHtml.includes("未判定"));
  assert.ok(acceptedPin.popupHtml.includes("&lt;unsafe&gt;"));
  assert.ok(!acceptedPin.popupHtml.includes("<unsafe>"));
  acceptedPin.handlers.click({});
  assert.match(acceptedCase.elements.details.innerHTML, /GSI公式掲載/);
  assert.match(acceptedCase.elements.details.innerHTML, /未推奨/);
  assert.doesNotMatch(acceptedCase.elements.details.innerHTML, /番号は表示順序/);
  const pageSource = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  assert.match(pageSource, /紫：公式掲載地点（安全性未判定/);
  assert.match(pageSource, /id="uiTabNormal"[^>]*role="tab"/);
  assert.match(pageSource, /id="uiTabScenario"[^>]*role="tab"/);
  assert.match(pageSource, /id="gisLayout"[^>]*role="tabpanel"/);
  assert.match(pageSource, /current_theme[.]css[?]v=gis-facility-drawer-20261009-v6/);
  assert.match(pageSource, /map_first[.]css[?]v=map-first-20261009-v4/);
  assert.match(pageSource, /id="toggleLeftPanel"[^>]*aria-expanded="false"/);
  assert.match(pageSource, /id="toggleRightPanel"[^>]*aria-expanded="false"/);
  assert.match(pageSource, /id="gisLeftPanel"/);
  assert.match(pageSource, /gis-side-shell gis-side-shell--left/);
  assert.match(pageSource, /gis-side-shell gis-side-shell--right/);
  assert.match(pageSource, /aria-label="左メニューを開く"/);
  assert.match(pageSource, /aria-label="右詳細を開く"/);
  assert.equal((pageSource.match(/id="map"/g) || []).length, 1);
  assert.equal((pageSource.match(/id="toggleLeftPanel"/g) || []).length, 1);
  assert.equal((pageSource.match(/id="toggleRightPanel"/g) || []).length, 1);
  assert.ok(pageSource.indexOf('gis-side-shell--left') < pageSource.indexOf('<main class="map-wrap">'));
  assert.ok(pageSource.indexOf('<main class="map-wrap">') < pageSource.indexOf('gis-side-shell--right'));
  assert.ok(pageSource.indexOf('id="toggleRightPanel"') < pageSource.indexOf('id="details"'),
    "right rail control must survive replacing the dynamic details innerHTML");
  assert.doesNotMatch(pageSource.slice(pageSource.indexOf('<nav'), pageSource.indexOf('</nav>')), /gis-panel-controls/,
    "panel toggles must not remain as text buttons in the top tab bar");
  assert.match(pageSource, /<svg[^>]*viewBox="0 0 24 24"/);
  assert.match(pageSource, /aria-controls="details"/);
  assert.match(pageSource, /探索の流れ（操作ボタンではありません）/);
  assert.match(pageSource, /操作は下の地点指定ボタンや地図上の入力欄/);
  assert.doesNotMatch(pageSource, /<button[^>]*>地域を確認<\/button>/);
  // Sidebar keeps the existing real controls, state and raster limitations;
  // an optional details disclosure only hides expert controls, never source status.
  const sidebar = pageSource.slice(
    pageSource.indexOf('<aside class="left"'),
    pageSource.indexOf('<main class="map-wrap">')
  );
  const sections = [
    'id="sidebarRegionTitle"',
    'id="sidebarExploreTitle"',
    'id="sidebarStatusTitle"',
    'id="sidebarDataTitle"',
    'id="sidebarLayersTitle"'
  ];
  for (let i = 1; i < sections.length; i += 1) {
    assert.ok(sidebar.indexOf(sections[i - 1]) < sidebar.indexOf(sections[i]),
      "task-first order is region -> origin -> status -> D -> layers");
  }
  for (const id of [
    "region", "resetView", "selectOrigin", "useGps", "originStatus",
    "floodDiscoveryResults", "status", "externalFloodTileNotice",
    "datasetChip", "datasetStatus", "recordCount", "mappedCount",
    "missingCoordinateCount", "officialFlood", "shelter", "basemap",
    "boundary", "floodOpacity", "regionExportFile", "autoLoad", "scenarioHazard"
  ]) {
    assert.equal((sidebar.match(new RegExp('id="' + id + '"', "g")) || []).length, 1,
      "sidebar must preserve exactly one existing element: " + id);
  }
  for (const panelId of ["sourceDisclosure", "dataDisclosure", "layerDisclosure", "legendDisclosure"]) {
    assert.match(sidebar, new RegExp('<details[^>]*id="' + panelId + '"[^>]*>'),
      "advanced settings are native keyboard-accessible details");
    assert.doesNotMatch(sidebar, new RegExp('<details[^>]*id="' + panelId + '"[^>]*\\bopen\\b'),
      "advanced controls must start closed");
  }
  assert.ok(sidebar.indexOf('id="externalFloodTileNotice"') <
    sidebar.indexOf('id="dataDisclosure"'), "raster warning cannot be hidden inside D advanced controls");
  assert.ok(sidebar.indexOf('id="externalFloodTileNotice"') <
    sidebar.indexOf('id="layerDisclosure"'), "raster warning cannot be hidden in layer options");
  assert.match(sidebar, /安全な避難先や現在の開設状況を保証しません/);
  assert.match(sidebar, /座標未確認/);
  assert.match(sidebar, /UNKNOWNを施設IDで照合/);
  const theme = fs.readFileSync(path.resolve(__dirname, "../gis/css/current_theme.css"), "utf8");
  assert.match(theme, /--bg:#07131e/);
  assert.match(theme, /--cyan:#4ed7dc/);
  assert.match(theme, /\.scenario-intro\[hidden\]\{display:none\}/);
  assert.match(theme, /\.scenario-intro \.scenario-steps li\{/);
  assert.match(theme, /cursor:default/);
  assert.match(theme, /--gis-left-track:0px/);
  assert.match(theme, /--gis-right-track:0px/);
  assert.match(theme, /\.layout>\.gis-side-shell--left\{grid-column:1;grid-row:1\}/);
  assert.match(theme, /\.layout>\.map-wrap\{grid-column:2;grid-row:1/);
  assert.match(theme, /\.layout>\.gis-side-shell--right\{grid-column:3;grid-row:1\}/);
  assert.match(theme, /--gis-left-width:44px/);
  assert.match(theme, /--gis-right-width:44px/);
  assert.match(theme, /\.layout\[data-left-panel="closed"\]>.gis-side-shell--left>.left\{display:none\}/);
  assert.match(theme, /\.layout\[data-right-panel="closed"\]>.gis-side-shell--right>.right\{display:none\}/);
  assert.match(theme, /\.layout\[data-left-panel="closed"\]>.map-wrap\{grid-column:2;grid-row:1\}/);
  assert.match(theme, /\.layout\[data-left-panel="closed"\]>.map-wrap\{grid-column:1;grid-row:2\}/);
  assert.match(theme, /\.gis-panel-toggle svg\{display:block/);
  // Restore usable vertical map area without reverting the successful
  // fixed central map grid and both 44px collapsible icon rails.
  assert.match(theme, /height:clamp\(390px,calc\(100dvh - 204px\),900px\)/);
  assert.match(theme, /height:clamp\(410px,calc\(100dvh - 215px\),760px\)/);
  assert.doesNotMatch(theme, /height:clamp\(420px,calc\(100dvh - 242px\),760px\)/);
  assert.match(theme, /height:clamp\(370px,60dvh,620px\)/,
    "mobile map behavior is intentionally unchanged");
  assert.match(theme, /\.layout>\.map-wrap\{grid-column:2;grid-row:1/,
    "expanded map must retain the dedicated middle column");
  assert.match(theme, /#map\{height:100%;min-height:0\}/);
  assert.doesNotMatch(theme, /(?:#map|\.leaflet-tile)[^\{]*\{[^}]*\bfilter\s*:/,
    "official imagery must never be filtered or inverted in the dark theme");
  assert.match(theme, /\.map-unavailable\{background:var\(--surface\)/,
    "unlocated facility overlay must stay opaque under dark palette");
  assert.doesNotMatch(pageSource, /紫の番号|reference-legend-sample">1/);
  const cssSource = fs.readFileSync(path.resolve(__dirname, "../gis/css/style.css"), "utf8");
  assert.match(cssSource, /reference-site-marker::after/);
  assert.equal(acceptedCase.elements.facilityDisplayMode.value, "nearby");
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), false);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[3]), true);
  assert.equal(acceptedCase.L.__map.lastBounds.points.length, 2); // origin + one vetted GSI site
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, false);
  assert.equal(acceptedCase.elements.focusReferenceTiles.disabled, false);
  assert.match(acceptedCase.elements.focusReferenceTiles.textContent, /選択地点と5件/);
  acceptedCase.elements.toggleDMarkers.listeners.click(); // explicitly compare
  assert.equal(acceptedCase.elements.facilityDisplayMode.value, "both");
  assert.equal(acceptedCase.elements.shelter.checked, true);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), true);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[3]), true);
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, false);
  assert.equal(acceptedCase.elements.focusReferenceTiles.disabled, false);
  assert.match(acceptedCase.elements.focusReferenceTiles.textContent, /緑と紫を一緒に見る/);
  const originalFocus = acceptedCase.L.__map.lastBounds;
  acceptedCase.elements.focusReferenceTiles.listeners.click();
  assert.notStrictEqual(acceptedCase.L.__map.lastBounds, originalFocus);
  assert.equal(acceptedCase.L.__map.lastBounds.points.length, 4, 
    "comparison fits clicked origin + certified GSI pin + both D coordinates");
  assert.equal(acceptedCase.L.__map.lastBounds.points[0][0], 35.7);
  assert.equal(acceptedCase.L.__map.lastBounds.points[0][1], 139.88);
  assert.match(acceptedCase.elements.toggleDMarkers.textContent, /周辺/);
  acceptedCase.elements.toggleDMarkers.listeners.click();
  assert.equal(acceptedCase.elements.facilityDisplayMode.value, "nearby");
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), false);
  // D scope temporarily hides GSI drawing, but accepted evidence stays in memory.
  acceptedCase.elements.facilityDisplayMode.value = "region";
  acceptedCase.elements.facilityDisplayMode.listeners.change({ target: acceptedCase.elements.facilityDisplayMode });
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), true);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[3]), false);
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, true,
    "D-only must not display an unrelated GSI summary or legend");
  assert.equal(acceptedCase.L.__groups[3].items.length, 1,
    "C accepted source remains cached but not visible");
  acceptedCase.elements.facilityDisplayMode.value = "nearby";
  acceptedCase.elements.facilityDisplayMode.listeners.change({ target: acceptedCase.elements.facilityDisplayMode });
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), false);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[3]), true);
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, false);
  assert.equal(acceptedCase.elements.referenceMapCoverage.textContent.includes("1/9"), true,
    "cached accepted source restored without confusing D as GSI");
  acceptedCase.elements.focusReferenceTiles.listeners.click();
  assert.ok(acceptedCase.L.__map.lastBounds?.points?.length);
  assert.equal(acceptedCase.L.__map.lastBounds.points.length, 2);
  const sharedMap = acceptedCase.L.__map;
  const currentBounds = sharedMap.lastBounds;
  const sourceCount = acceptedCase.L.__groups[3].items.length;
  const compareValue = acceptedCase.elements.facilityDisplayMode.value;
  const referenceDetails = acceptedCase.elements.referenceMapCount.textContent;
  const originCopy = acceptedCase.elements.coordinateSearchInput.value;
  acceptedCase.elements.uiTabScenario.listeners.click();
  acceptedCase.elements.uiTabNormal.listeners.click();
  acceptedCase.elements.uiTabScenario.listeners.click();
  assert.strictEqual(acceptedCase.L.__map, sharedMap, "the Leaflet instance is shared");
  assert.strictEqual(sharedMap.lastBounds, currentBounds,
    "tab only switches UI, never triggers map navigation");
  assert.equal(acceptedCase.L.__groups[3].items.length, sourceCount);
  assert.equal(acceptedCase.elements.facilityDisplayMode.value, compareValue);
  assert.equal(acceptedCase.elements.referenceMapCount.textContent, referenceDetails);
  assert.equal(acceptedCase.elements.coordinateSearchInput.value, originCopy,
    "tab switch must not clear the selected coordinate origin");
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, false);
  assert.equal(acceptedCase.elements.region.value, "13123");
  assert.match(acceptedCase.elements.floodDiscoveryResults.innerHTML, /距離は安全性を表さず/);
  assert.doesNotMatch(acceptedCase.elements.floodDiscoveryResults.innerHTML, /行くべき順|推奨順位|ランキング/);
  assert.match(acceptedCase.elements.floodDiscoveryResults.innerHTML, /&lt;unsafe&gt;/);
  assert.doesNotMatch(acceptedCase.elements.floodDiscoveryResults.innerHTML, /<unsafe>/);
  assert.doesNotMatch(acceptedCase.elements.floodDiscoveryResults.innerHTML, /Edogawa A/);
  assert.match(acceptedCase.elements.floodDiscoveryResults.innerHTML, /国土地理院の公式raw/);
  acceptedCase.elements.region.value = "15100";
  acceptedCase.elements.region.listeners.change({ target: acceptedCase.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(acceptedCase.elements.selectOrigin.disabled, false);
  assert.equal(acceptedCase.elements.facilityDisplayMode.value, "region");
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[1]), true);
  assert.equal(acceptedCase.L.__map.hasLayer(acceptedCase.L.__groups[3]), false);
  assert.doesNotMatch(acceptedCase.elements.floodDiscoveryResults.innerHTML, /&lt;unsafe&gt;/);
  assert.equal(acceptedCase.elements.referenceMapSummary.hidden, true);
  assert.equal(acceptedCase.L.__groups[2].items.length, 0);
  assert.equal(acceptedCase.L.__groups[3].items.length, 0);


  // HTTP integration: origin tile plus an independently verified adjacent
  // official tile are combined only when the exact cell files are served.
  const neighborSource = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/910/403.geojson";
  const neighborCatalog = {
    ...officialCatalog,
    source_raw_sha256: "b".repeat(64),
    c_audit_reference: "C-SECOND-TILE",
    sites: [{
      ...officialCatalog.sites[0],
      source_feature_key: neighborSource + "#feature_index=0",
      source_url: neighborSource,
      name_raw: "EAST_NEIGHBOR_ONLY",
      latitude: 35.7, longitude: 140.1,
      source_raw_sha256: "b".repeat(64)
    }]
  };
  const multiCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const path = String(url);
      if (path.includes("gsi_verified_tiles/13123/10-909-403.json")) {
        return { ok: true, status: 200, json: async () => officialCatalog };
      }
      if (path.includes("gsi_verified_tiles/13123/10-910-403.json")) {
        return { ok: true, status: 200, json: async () => neighborCatalog };
      }
      if (path.includes("gsi_verified_tiles/")) {
        return { ok: false, status: 404, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => edogawa };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  multiCase.elements.selectOrigin.listeners.click();
  multiCase.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.9 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.match(multiCase.elements.floodDiscoveryResults.innerHTML, /検証済み2\/9タイル/);
  assert.match(multiCase.elements.floodDiscoveryResults.innerHTML, /EAST_NEIGHBOR_ONLY/);
  assert.match(multiCase.elements.floodDiscoveryResults.innerHTML, /未検証タイル/);
  assert.match(multiCase.elements.floodDiscoveryResults.innerHTML, /直線距離/);
  assert.equal(multiCase.L.__groups[2].items.length, 2);
  assert.equal(multiCase.L.__groups[3].items.length, 2);
  assert.match(multiCase.elements.referenceMapCoverage.textContent, /2\/9/);
  multiCase.elements.facilityDisplayMode.value = "both";
  multiCase.elements.facilityDisplayMode.listeners.change({ target: multiCase.elements.facilityDisplayMode });
  assert.equal(multiCase.elements.referenceMapSummary.hidden, false);
  assert.equal(multiCase.elements.focusReferenceTiles.disabled, false);
  multiCase.elements.focusReferenceTiles.listeners.click();
  assert.equal(multiCase.L.__map.lastBounds.points.length, 5,
    "2 independently accepted GSI pins + origin + 2 D coordinates");
  assert.equal(multiCase.L.__map.lastBounds.points.some(p => p[1] === 140.1), true,
    "distant accepted GSI source is included in comparison viewport");
  multiCase.elements.facilityDisplayMode.value = "region";
  multiCase.elements.facilityDisplayMode.listeners.change({ target: multiCase.elements.facilityDisplayMode });
  assert.equal(multiCase.elements.referenceMapSummary.hidden, true);
  multiCase.elements.facilityDisplayMode.value = "nearby";
  multiCase.elements.facilityDisplayMode.listeners.change({ target: multiCase.elements.facilityDisplayMode });
  assert.equal(multiCase.elements.referenceMapSummary.hidden, false);

  assert.equal(multiCase.elements.facilityDisplayMode.value, "nearby");
  assert.equal(multiCase.L.__map.hasLayer(multiCase.L.__groups[1]), false);
  assert.equal(multiCase.L.__map.hasLayer(multiCase.L.__groups[3]), true);
  assert.equal(multiCase.L.__map.lastBounds.points.length, 3); // origin + two GSI sites

  // Delayed regional D load must not move the map away from an explicitly
  // selected nearby GSI origin/candidate view.
  let finishD;
  const lateDCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const request = String(url);
      if (request.includes("/edogawa.json")) {
        return new Promise(resolve => { finishD = resolve; });
      }
      if (request.includes("gsi_verified_tiles/13123/10-909-403.json")) {
        return { ok: true, status: 200, json: async () => officialCatalog };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(typeof finishD, "function");
  lateDCase.elements.mapOriginShortcut.listeners.click();
  lateDCase.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.9 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(lateDCase.elements.facilityDisplayMode.value, "nearby");
  const selectedBounds = lateDCase.L.__map.lastBounds;
  assert.equal(selectedBounds.points.length, 2);
  finishD({ ok: true, status: 200, json: async () => edogawa });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.strictEqual(lateDCase.L.__map.lastBounds, selectedBounds,
    "a delayed D load may not replace the origin-based viewport");
  assert.equal(lateDCase.L.__map.hasLayer(lateDCase.L.__groups[1]), false);
  assert.equal(lateDCase.elements.recordCount.textContent, 2);

  // D-only visual aggregation at low zoom: counts represent actual
  // D RegionExport mappableRecords, never evidence of safe facilities.
  const closeD = payload("13123", "東京都江戸川区", [
    record("cluster-1", "FIRST original D site", 35.70, 139.88),
    record("cluster-2", "SECOND original D site", 35.7001, 139.8801),
    record("cluster-3", "THIRD original D site", 35.7002, 139.8802)
  ]);
  const clusterCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => String(url).includes("gsi_verified_tiles/")
      ? { ok: false, status: 404, json: async () => ({}) }
      : { ok: true, status: 200, json: async () => closeD }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(clusterCase.elements.recordCount.textContent, 3);
  assert.equal(clusterCase.elements.mappedCount.textContent, 3);
  assert.equal(clusterCase.L.__groups[1].items.length, 3,
    "zoom 13 keeps all precise D source markers");
  const at13 = [...clusterCase.L.__groups[1].items];
  const afterFirstRender = clusterCase.L.__markers.length;
  clusterCase.L.__map.zoom = 13.5;
  clusterCase.L.__map.handlers.zoomend();
  assert.deepEqual(clusterCase.L.__groups[1].items, at13,
    "fractional zoom 13.5 reuses unchanged individual D markers");
  clusterCase.L.__map.zoom = 14;
  clusterCase.L.__map.handlers.zoomend();
  assert.deepEqual(clusterCase.L.__groups[1].items, at13,
    "zoom 13 to 14 must reuse individual marker objects");
  assert.equal(clusterCase.L.__markers.length, afterFirstRender,
    "no additional DOM markers created for unchanged membership");
  clusterCase.L.__map.zoom = 15.75;
  clusterCase.L.__map.handlers.zoomend();
  assert.deepEqual(clusterCase.L.__groups[1].items, at13,
    "source D markers stay reusable at every fractional high-detail zoom");
  clusterCase.L.__map.zoom = 9.5;
  clusterCase.L.__map.handlers.zoomend();
  assert.equal(clusterCase.L.__groups[1].items.length, 1,
    "fractional zoom 9.5 preserves visual clustering of true D coordinates");
  clusterCase.L.__map.zoom = 9;
  clusterCase.L.__map.handlers.zoomend();
  assert.equal(clusterCase.L.__groups[1].items.length, 1,
    "zoomed out actual nearby D source coordinates aggregate into a single visual circle");
  const oneCluster = clusterCase.L.__groups[1].items[0];
  const afterClusterBuild = clusterCase.L.__markers.length;
  const originalProject = clusterCase.L.__map.project;
  let projectionCalls = 0;
  clusterCase.L.__map.project = function(...args) {
    projectionCalls++;
    return originalProject.apply(this, args);
  };
  clusterCase.L.__map.zoom = 9.75;
  clusterCase.L.__map.handlers.zoomend();
  assert.equal(projectionCalls, 0,
    "same fractional zoom band reuses the previous visual D grouping");
  assert.strictEqual(clusterCase.L.__groups[1].items[0], oneCluster);
  clusterCase.L.__map.zoom = 10;
  clusterCase.L.__map.handlers.zoomend();
  assert.ok(projectionCalls > 0,
    "crossing an integer zoom band recalculates the D cluster grid");
  assert.strictEqual(clusterCase.L.__groups[1].items[0], oneCluster,
    "low-zoom visual cluster remains the same marker across identical membership");
  assert.equal(clusterCase.L.__markers.length, afterClusterBuild,
    "same visual group never regenerates an icon");
  clusterCase.L.__map.zoom = 9;
  clusterCase.L.__map.handlers.zoomend();
  assert.strictEqual(clusterCase.L.__groups[1].items[0], oneCluster);
  assert.match(oneCluster.options.icon.html, /d-facility-cluster/);
  assert.match(oneCluster.options.icon.html, />3<\/div>/);
  assert.match(oneCluster.options.icon.html, /安全性未判定/);
  assert.doesNotMatch(oneCluster.options.icon.html, /reference-site-marker/);
  oneCluster.handlers.click({});
  assert.match(clusterCase.elements.details.innerHTML, /3件/);
  assert.match(clusterCase.elements.details.innerHTML, /実在する施設位置ではありません/);
  assert.equal(clusterCase.L.__map.lastView.zoom, 11);
  // A zoom change regenerates the display without touching the original D row count.
  clusterCase.L.__map.zoom = 13;
  clusterCase.L.__map.handlers.zoomend();
  assert.equal(clusterCase.L.__groups[1].items.length, 3);
  const originalDMarker = clusterCase.L.__groups[1].items[0];
  originalDMarker.handlers.click({});
  assert.match(clusterCase.elements.details.innerHTML, /FIRST original D site/);
  assert.equal(clusterCase.elements.mappedCount.textContent, 3);
  // Hiding the D layer while the user examines GSI never transforms D into purple.
  clusterCase.elements.facilityDisplayMode.value = "nearby";
  clusterCase.elements.facilityDisplayMode.listeners.change({
    target: clusterCase.elements.facilityDisplayMode
  });
  assert.equal(clusterCase.L.__map.hasLayer(clusterCase.L.__groups[1]), false);
  clusterCase.L.__map.zoom = 9;
  clusterCase.L.__map.handlers.zoomend();
  assert.equal(clusterCase.L.__groups[1].items.length, 1);
  assert.equal(clusterCase.L.__map.hasLayer(clusterCase.L.__groups[1]), false);
  clusterCase.elements.facilityDisplayMode.value = "region";
  clusterCase.elements.facilityDisplayMode.listeners.change({
    target: clusterCase.elements.facilityDisplayMode
  });
  assert.equal(clusterCase.L.__map.hasLayer(clusterCase.L.__groups[1]), true);
  assert.equal(clusterCase.L.__groups[1].items.length, 1);
  // Exact same coordinates were used to calculate the D display centroid.
  assert.ok(Math.abs(clusterCase.L.__groups[1].items[0].latlng[0] - 35.7001) < 0.00000001);
  assert.ok(Math.abs(clusterCase.L.__groups[1].items[0].latlng[1] - 139.8801) < 0.00000001);

  // External flood raster availability is separate from certified GSI
  // skhb01 shelter reference coverage. Tileerror does not prove HTTP404,
  // zero inundation, missing shelters or lack of D RegionExport.
  clusterCase.L.__tiles[1].handlers.tileerror({
    tile: { src: "https://disaportaldata.gsi.go.jp/raster/01_flood_l2_shinsuishin_data/10/909/403.png" }
  });
  assert.match(clusterCase.elements.status.textContent, /外部タイルの一部/);
  assert.match(clusterCase.elements.status.textContent, /公的洪水ラスタ/);
  assert.match(clusterCase.elements.status.textContent, /浸水の有無・安全性は判定できません/);
  assert.doesNotMatch(clusterCase.elements.status.textContent, /Dデータは利用可能|浸水なし|安全な避難先/);
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden, false);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent, /浸水なし/);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent, /別データ/);
  // Later D status updates must not erase the independently visible raster warning.
  vm.runInContext('setStatus("D出力を更新しました", "success")', clusterCase.context);
  assert.match(clusterCase.elements.status.textContent, /D出力を更新/);
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden, false);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent, /公的洪水ラスタ/);
  assert.equal(clusterCase.elements.recordCount.textContent, 3);

  // A wrong tile file on the correct static path is NOT a permitted fallback.
  const substituted = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const path = String(url);
      if (path.includes("gsi_verified_tiles/13123/10-909-403.json")) {
        return { ok: true, status: 200, json: async () => neighborCatalog };
      }
      if (path.includes("gsi_verified_tiles/")) {
        return { ok: false, status: 404, json: async () => ({}) };
      }
      return { ok: true, status: 200, json: async () => edogawa };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  substituted.elements.selectOrigin.listeners.click();
  substituted.L.__map.handlers.click({ latlng: { lat: 35.7, lng: 139.9 } });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.doesNotMatch(substituted.elements.floodDiscoveryResults.innerHTML, /EAST_NEIGHBOR_ONLY/);
  assert.match(substituted.elements.floodDiscoveryResults.innerHTML, /独立照合待ち|未検証/);
  assert.equal(substituted.elements.referenceMapSummary.hidden, true);
  assert.equal(substituted.L.__groups[2].items.length, 0);
  assert.equal(substituted.L.__groups[3].items.length, 0);

  // A slow response from the previously selected region must not overwrite the new region.
  const pending = {};
  const raceCase = makeContext({
    protocol: "http:",
    fetchImpl: url => new Promise(resolve => { pending[String(url)] = resolve; })
  });
  raceCase.elements.region.value = "15100";
  raceCase.elements.region.listeners.change({ target: raceCase.elements.region });
  pending["../../pipeline/data/output/niigata.json"]({
    ok: true, status: 200, json: async () => niigata
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(raceCase.elements.recordCount.textContent, 1);
  assert.match(raceCase.elements.status.textContent, /1件表示中/);

  pending["../../pipeline/data/output/edogawa.json"]({
    ok: true, status: 200, json: async () => edogawa
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(raceCase.elements.recordCount.textContent, 1);
  assert.match(raceCase.elements.resetView.textContent, /新潟県 新潟市/);

  console.log("map_controller.test.js: OK");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});


// Map-first toolbar semantics, future navigation and responsive positioning.
// Actual DOM gesture/visual behavior requires a separate browser check.
{
  const html = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const css = fs.readFileSync(path.resolve(__dirname, "../gis/css/map_first.css"), "utf8");
  for (const menu of ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"]) {
    assert.match(html, new RegExp('id="' + menu + '"'));
  }
  for (const [label, planned] of [["地図",false],["やること",true],["マイ情報",true],["設定",false]]) {
    assert.ok(html.includes("<span>" + label + "</span>"));
    if (planned) assert.match(html, /今後実装予定/);
  }
  assert.match(html, /id="mapLocateMe"[^>]*type="button"/);
  assert.match(html, /id="mapSettingsPanel"[^>]*hidden/);
  assert.match(html, /id="mapSettingsToggle"[^>]*type="button"/);
  assert.match(html, /id="mapWheelSensitivity"[^>]*type="range"[^>]*min="0.5"[^>]*max="2.5"/);
  assert.match(html, /id="mapZoomStyle"/);
  assert.match(css, /\.map-settings-sheet\[hidden\]\{display:none\}/);
  assert.match(css, /\.map-locate-button\{[\s\S]*?right:16px;bottom:18px/);
  assert.match(css, /\.hinanex-bottom-nav\{[\s\S]*?position:fixed;bottom:0/);
  assert.match(css, /\.layout>\.gis-side-shell--right\s*\{[\s\S]*?bottom:0/);
  assert.match(html, /id="mapOpenAdvanced"[^>]*type="button"/);
  assert.match(html, /id="referenceMapSummaryDisclosure"/);
  assert.match(css, /\.layout\[data-left-panel="closed"\]>.gis-side-shell--left\{display:none\}/);
  assert.match(html, /id="mapRegionQuickSelect"/);
  assert.match(html, /id="mapShowShelter"[^>]*type="checkbox"/);
  assert.match(html, /id="mapShowFlood"[^>]*type="checkbox"/);
  assert.match(html, /id="mapShowBasemap"[^>]*type="checkbox"/);
  assert.match(html, /災害後シミュレーション／避難経路シミュレーションは今後実装予定/);
  for (const id of ["coordinateSearchForm","coordinateSearchInput","mapOriginShortcut","facilityDisplayMode","useGps","mapLocateMe"]) {
    assert.equal((html.match(new RegExp('id="' + id + '"', "g")) || []).length,1,id + " must have one instance");
  }
  assert.doesNotMatch(css, /(?:#map|\.leaflet-tile)[^\{]*\{[^}]*\bfilter\s*:/);
}

// Verify the map-first UI facade actually forwards choices to the existing
// D/GSI controls and never requests GPS until the locate button is clicked.
{
  const uiCode = fs.readFileSync(path.resolve(__dirname, "../gis/js/map_first_ui.js"), "utf8");
  const uiIds = ["gisLayout", "toggleRightPanel", "region", "mapRegionQuickSelect",
    "mapShowShelter", "shelter", "mapShowFlood", "officialFlood", "mapShowBasemap",
    "basemap", "facilityDisplayMode", "mapScenarioSelectOrigin", "selectOrigin",
    "mapLocateMe", "useGps", "mapGpsFeedback", "originStatus", "mapRasterNotice", "mapRasterBanner",
    "mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards",
    "mapOpenAdvanced", "toggleLeftPanel", "gisLeftPanel", "details",
    "referenceMapSummary", "referenceMapSummaryDisclosure",
    "mapSettingsPanel", "mapSettingsToggle", "mapSettingsClose",
    "mapWheelSensitivity", "mapWheelSensitivityValue", "mapZoomStyle", "mapGestureReset"];
  const nodes = Object.fromEntries(uiIds.map(id => {
    const node = makeElement(id);
    // Browser EventTarget allows multiple handlers; the legacy simple stub
    // overwrites by name, so wrap listeners for the facade integration test.
    const callbacks = {};
    node.addEventListener = function(name, callback) {
      (callbacks[name] ||= []).push(callback);
      this.listeners[name] = event => callbacks[name].forEach(fn => fn(event));
    };
    node.dispatchEvent = function(event) {
      this.listeners[event.type]?.({ target: this });
      return true;
    };
    node.click = function() { this.listeners.click?.({ target: this }); };
    return [id, node];
  }));
  // Fake a native DOM contains() and the existing GIS panel toggle
  // controller; these are presentation-only, not data-fetch events.
  for (const node of Object.values(nodes)) {
    node.contains = target => target === node;
  }
  nodes.referenceMapSummary.hidden = true;
  nodes.mapSettingsPanel.hidden = true;
  nodes.gisLayout.setAttribute("data-left-panel", "closed");
  nodes.gisLayout.setAttribute("data-right-panel", "closed");
  const captured = {};
  nodes.toggleLeftPanel.addEventListener("click", () => {
    const open = nodes.gisLayout.getAttribute("data-left-panel") !== "open";
    nodes.gisLayout.setAttribute("data-left-panel", open ? "open" : "closed");
  });
  nodes.toggleRightPanel.addEventListener("click", () => {
    const open = nodes.gisLayout.getAttribute("data-right-panel") !== "open";
    nodes.gisLayout.setAttribute("data-right-panel", open ? "open" : "closed");
    nodes.toggleRightPanel.setAttribute("aria-expanded", String(open));
  });
  nodes.region.value = "13123";
  let regionChanges = 0, gpsRequests = 0, originRequests = 0;
  nodes.region.addEventListener("change", () => { regionChanges += 1; });
  nodes.useGps.addEventListener("click", () => { gpsRequests += 1; });
  nodes.selectOrigin.addEventListener("click", () => { originRequests += 1; });
  const facade = {
    document: {
      getElementById: id => nodes[id],
      addEventListener(type, handler) { captured[type] = handler; }
    },
    window: {
      HINANEX_MAP_GESTURES: {
        settings: { sensitivity: 1.5, style: "continuous" },
        getSettings() { return { ...this.settings }; },
        setSettings(changes) {
          this.settings = { ...this.settings, ...changes };
          return this.getSettings();
        },
        resetSettings() {
          this.settings = { sensitivity: 1.5, style: "continuous" };
          return this.getSettings();
        }
      }
    },
    Event: class { constructor(type) { this.type = type; } }
  };
  vm.createContext(facade);
  vm.runInContext(uiCode, facade, { filename: "map_first_ui.js" });
  assert.equal(gpsRequests, 0);
  assert.equal(nodes.mapWheelSensitivity.value, "1.5");
  assert.equal(nodes.mapZoomStyle.value, "continuous");
  nodes.mapRegionQuickSelect.value = "15100";
  nodes.mapRegionQuickSelect.listeners.change();
  assert.equal(nodes.region.value, "15100");
  assert.equal(regionChanges, 1);
  nodes.region.value = "23100";
  nodes.region.listeners.change({ target: nodes.region });
  assert.equal(nodes.mapRegionQuickSelect.value, "23100");

  nodes.mapShowShelter.checked = false;
  nodes.mapShowShelter.listeners.change();
  assert.equal(nodes.shelter.checked, false);
  nodes.mapShowFlood.checked = false;
  nodes.mapShowFlood.listeners.change();
  assert.equal(nodes.officialFlood.checked, false);
  nodes.mapShowBasemap.checked = false;
  nodes.mapShowBasemap.listeners.change();
  assert.equal(nodes.basemap.checked, false);

  nodes.mapToolScenario.open = true;
  nodes.mapToolScenario.listeners.toggle();
  nodes.mapToolScene.open = true;
  nodes.mapToolScene.listeners.toggle();
  assert.equal(nodes.mapToolScenario.open, false, "only one toolbar menu opens");

  nodes.mapToolScenario.open = true;
  nodes.mapScenarioSelectOrigin.click();
  assert.equal(originRequests, 1);
  assert.equal(nodes.mapToolScenario.open, false);

  nodes.mapLocateMe.click();
  assert.equal(gpsRequests, 1, "locate forwards exactly one explicit click");

  facade.window.HINANEX_MAP_FIRST_UI.showDetail();
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "open");
  assert.equal(nodes.toggleRightPanel.getAttribute("aria-expanded"), "true");
  facade.window.HINANEX_MAP_FIRST_UI.showRasterWarning("タイル未取得");
  assert.equal(nodes.mapRasterNotice.hidden, false);
  assert.equal(nodes.mapRasterNotice.textContent, "タイル未取得");
  assert.equal(nodes.mapRasterBanner.hidden, false);
  assert.match(nodes.mapRasterBanner.textContent, /空白＝浸水なしではありません/);
  assert.equal(nodes.mapRasterBanner.title, "タイル未取得");

  // Opening a different top menu closes the active detail sheet.
  nodes.mapToolScene.open = true;
  nodes.mapToolScene.listeners.toggle();
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "closed");
  assert.equal(nodes.mapToolScene.open, true);

  // Another menu replaces the previous one; clicking within it keeps it open.
  nodes.mapToolMarks.open = true;
  nodes.mapToolMarks.listeners.toggle();
  assert.equal(nodes.mapToolScene.open, false);
  captured.click({ target: nodes.mapToolMarks });
  assert.equal(nodes.mapToolMarks.open, true);

  // Outside click dismisses all, is recorded for Leaflet click suppression,
  // and never modifies map or provider data.
  const outsideTap = { target: {}, type: "click" };
  captured.click(outsideTap);
  assert.equal(nodes.mapToolMarks.open, false);
  assert.equal(facade.window.HINANEX_MAP_FIRST_UI.wasDismissalClick(outsideTap), true);

  nodes.mapToolHazards.open = true;
  nodes.mapToolHazards.listeners.toggle();
  let escapePrevented = false;
  captured.keydown({ key: "Escape", preventDefault() { escapePrevented = true; } });
  assert.equal(escapePrevented, true);
  assert.equal(nodes.mapToolHazards.open, false);

  // The old floating side tile disappears; advanced controls remain
  // accessible through the Scene menu and dismiss on outside click.
  nodes.mapToolScene.open = true;
  nodes.mapToolScene.listeners.toggle();
  nodes.mapOpenAdvanced.click();
  assert.equal(nodes.gisLayout.getAttribute("data-left-panel"), "open");
  assert.equal(nodes.mapToolScene.open, false);
  captured.click({ target: {}, type: "click" });
  assert.equal(nodes.gisLayout.getAttribute("data-left-panel"), "closed");

  // A GSI summary is a compact disclosure, never a second large sheet.
  nodes.referenceMapSummary.hidden = false;
  nodes.referenceMapSummaryDisclosure.open = true;
  nodes.referenceMapSummaryDisclosure.listeners.toggle();
  facade.window.HINANEX_MAP_FIRST_UI.showDetail();
  assert.equal(nodes.referenceMapSummaryDisclosure.open, false);
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "open");
  captured.click({ target: nodes.details });
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "open");
  captured.click({ target: nodes.toggleRightPanel });
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "open",
    "close button is not pre-emptively toggled by outside-click capture");
  captured.click({ target: {}, type: "click" });
  assert.equal(nodes.gisLayout.getAttribute("data-right-panel"), "closed");
  assert.equal(facade.window.HINANEX_MAP_FIRST_UI.wasDismissalClick(null), false);

  // The future Settings slot is now an active map-only preference sheet.
  nodes.mapSettingsToggle.click();
  assert.equal(nodes.mapSettingsPanel.hidden, false);
  assert.equal(nodes.mapSettingsToggle.getAttribute("aria-expanded"), "true");
  nodes.mapWheelSensitivity.value = "2";
  nodes.mapWheelSensitivity.listeners.input({ target: nodes.mapWheelSensitivity });
  assert.equal(facade.window.HINANEX_MAP_GESTURES.settings.sensitivity, "2");
  assert.equal(nodes.mapWheelSensitivityValue.textContent, "2倍");
  nodes.mapZoomStyle.value = "steps";
  nodes.mapZoomStyle.listeners.change({ target: nodes.mapZoomStyle });
  assert.equal(facade.window.HINANEX_MAP_GESTURES.settings.style, "steps");
  captured.click({ target: nodes.mapSettingsPanel });
  assert.equal(nodes.mapSettingsPanel.hidden, false,
    "tapping within settings should not dismiss or change the map");
  nodes.mapGestureReset.click();
  assert.equal(nodes.mapWheelSensitivity.value, "1.5");
  assert.equal(nodes.mapZoomStyle.value, "continuous");
  nodes.mapToolMarks.open = true;
  nodes.mapToolMarks.listeners.toggle();
  assert.equal(nodes.mapSettingsPanel.hidden, true,
    "opening map layer controls dismisses the settings surface");

  nodes.mapSettingsToggle.click();
  const dismissSettings = { target: {}, type: "click" };
  captured.click(dismissSettings);
  assert.equal(nodes.mapSettingsPanel.hidden, true);
  assert.equal(facade.window.HINANEX_MAP_FIRST_UI.wasDismissalClick(dismissSettings), true);

  nodes.mapSettingsToggle.click();
  captured.keydown({ key: "Escape", preventDefault() {} });
  assert.equal(nodes.mapSettingsPanel.hidden, true);
  nodes.mapSettingsToggle.click();
  nodes.mapSettingsClose.click();
  assert.equal(nodes.mapSettingsPanel.hidden, true);
}

// The expert analytics/evidence route stays a standalone page, not a
// modal, iframe or map-state-changing SPA navigation.
{
  const page = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const styles = fs.readFileSync(path.resolve(__dirname, "../gis/css/map_first.css"), "utf8");
  const header = page.slice(page.indexOf('<header class="header">'), page.indexOf("</header>"));
  assert.match(header, /<a class="header-evidence-link" href="\.\.\/\.\.\/frontend\/" target="_blank" rel="noopener noreferrer"/);
  assert.match(header, /aria-label="分析・根拠を別タブで開く"/);
  assert.match(header, />分析・根拠 <span aria-hidden="true">↗<\/span><\/a>/);
  assert.equal((page.match(/class="header-evidence-link"/g) || []).length, 1);
  assert.doesNotMatch(header, /<iframe|<dialog|onclick=/i);
  assert.match(styles, /\.header-evidence-link:focus-visible/);
  assert.match(styles, /@media\(max-width:680px\)[\s\S]*?\.header-evidence-link\{min-height:44px/);
}

// Navigation-only minimum zoom must keep the Japanese archipelago overview
// on-screen, without changing the selected region or guessing data locations.
{
  const { L, elements } = makeContext({
    protocol: "http:",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  const map = L.__map;
  assert.deepEqual(Array.from(map.overviewFitArgs.bounds.points, item => [...item]), [
    [24.0, 122.5], [45.8, 146.5]
  ]);
  assert.equal(map.overviewFitArgs.inside, false);
  assert.deepEqual(Array.from(map.overviewFitArgs.padding), [32, 32]);
  assert.equal(map.minZoom, 4, "minimum is derived from overview fit, not a hard-coded world view");
  assert.equal(map.zoom, 13, "initial city zoom remains unchanged");
  assert.equal(map.lastView.zoom, 13);
  assert.equal(elements.region.value, "13123", "municipality selection is unchanged");
  assert.equal(L.__tiles.length >= 2, true);
  assert.equal(mapCode.includes('minZoom: 2,'), true,
    "basemap tile range must allow the computed small-screen overview level");

  // Emulate rotating from short landscape to tall portrait and very large
  // desktops, without changing the user's map center/zoom when not needed.
  map.overviewFitZoom = 3;
  map.handlers.resize();
  assert.equal(map.minZoom, 3);
  map.overviewFitZoom = 5;
  map.handlers.resize();
  assert.equal(map.minZoom, 5);
  map.overviewFitZoom = 11;
  map.handlers.resize();
  assert.equal(map.minZoom, 6, "limit min-zoom escalation on very large canvases");
  map.overviewFitZoom = 1;
  map.handlers.resize();
  assert.equal(map.minZoom, 2, "respect actual raster/basemap tile lower bound");
  const callsBeforeInvalid = map.minZoomCalls.length;
  map.overviewFitZoom = Number.NaN;
  map.handlers.resize();
  assert.equal(map.minZoomCalls.length, callsBeforeInvalid,
    "invalid viewport size must not override the previous minimum");
  assert.equal(map.zoom, 13, "resizing does not reset current detailed view");

  // Leaflet handles +/- zoom, wheel and touch pinch using the same minZoom.
  assert.match(mapCode, /map\.setMinZoom\(/);
  assert.doesNotMatch(mapCode, /map\.setView\(\[[^\]]*\],\s*[345]\)/);
}

// Tile scheduling and opt-in diagnostics: do not silently disable the official
// flood raster or infer that a missing tile means safe/no inundation.
{
  const { L } = makeContext({
    protocol: "http:",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  for (const tile of L.__tiles.slice(0, 2)) {
    assert.equal(tile.options.keepBuffer, 3);
  }
  assert.equal(L.__tiles[0].options.updateWhenZooming, false,
    "avoid mid-gesture bitmap swaps in the responsive mode");
  assert.equal(L.__tiles[1].options.updateWhenZooming, false,
    "official flood raster retains lighter end-of-zoom tile loading");
  assert.equal(L.__tiles[0].options.minZoom, 2);
  assert.equal(L.__tiles[1].options.minZoom, 2);
  assert.equal(L.__map.getZoom(), 13);
  assert.equal(L.__map.minZoom, 4, "Japan overview minimum zoom unchanged");
  assert.match(mapCode, /new URL\(window\.location\.href\)\.searchParams\.get\("debugMapPerf"\) === "1"/);
  assert.match(mapCode, /\[HINANEX map perf\] tile batch/);
  assert.match(mapCode, /\[HINANEX map perf\] D markers/);
  assert.equal(L.__map.options.zoomSnap, 0,
    "continuous mode must not snap wheel and pinch gestures to discrete levels");
  assert.equal(L.__map.options.zoomDelta, 0.5, "+/- and keyboard remain half steps");
  assert.equal(L.__map.options.wheelPxPerZoomLevel, 67,
    "new default is 1.5x, but map remains unsnapped");
  assert.equal(L.__map.options.zoomSnap, 0);
  assert.equal(L.__map.options.wheelDebounceTime, 40, "restore default debounce");
  assert.equal(L.__map.options.preferCanvas, true, "renderer is unchanged");
  assert.match(mapCode, /\[HINANEX map perf\] zoom gesture/);
  assert.match(mapCode, /HINANEX_MAP_GESTURES/);

  const old = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=13123&zoomFeel=previous",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(old.L.__map.options.zoomSnap, 0.5,
    "QA query restores previous zoom snap");
  assert.equal(old.L.__map.options.wheelPxPerZoomLevel, 100);
  assert.equal(old.L.__map.options.wheelDebounceTime, 40);
  assert.equal(old.L.__tiles[0].options.updateWhenZooming, false);
  assert.equal(old.L.__tiles[1].options.updateWhenZooming, false);
  assert.equal(old.L.__map.minZoom, L.__map.minZoom,
    "both versions retain Japan zoom floor");
  assert.equal(old.L.__map.getZoom(), L.__map.getZoom(),
    "same municipality zoom for fair comparisons");

  const slow = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=13123&zoomFeel=slow",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(slow.L.__map.options.zoomSnap, 0.25,
    "rejected slow mode remains available for controlled comparison");
  assert.equal(slow.L.__map.options.zoomDelta, 0.5);
  assert.equal(slow.L.__map.options.wheelPxPerZoomLevel, 240);
  assert.equal(slow.L.__map.options.wheelDebounceTime, 55);
  assert.equal(slow.L.__tiles[0].options.updateWhenZooming, true);
  assert.equal(slow.L.__tiles[1].options.updateWhenZooming, false);
  assert.equal(slow.L.__map.minZoom, L.__map.minZoom,
    "slow and responsive modes respect the same Japan min zoom");
  assert.equal(slow.L.__map.getZoom(), L.__map.getZoom());
}

// Gesture settings are opt-in, persistent only in this browser, and never
// modify location/region/official data. Storage errors degrade gracefully.
{
  const memory = {};
  const storage = {
    getItem(key) { return memory[key] ?? null; },
    setItem(key, value) { memory[key] = value; }
  };
  const makeGestureCase = () => makeContext({
    protocol: "http:", localStorage: storage,
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  const first = makeGestureCase();
  const api = first.context.window.HINANEX_MAP_GESTURES;
  assert.deepEqual({ ...api.getSettings() }, { sensitivity: 1.5, style: "continuous" });
  assert.equal(first.L.__map.options.wheelPxPerZoomLevel, 67);
  const startView = first.L.__map.lastView;
  const minZoom = first.L.__map.minZoom;
  api.setSettings({ sensitivity: 2, style: "steps" });
  assert.equal(first.L.__map.options.wheelPxPerZoomLevel, 50);
  assert.equal(first.L.__map.options.zoomSnap, 0.5);
  assert.strictEqual(first.L.__map.lastView, startView);
  assert.equal(first.L.__map.minZoom, minZoom);
  assert.match(memory["hinanex.gis.gesture.v1"], /"sensitivity":2/);
  const reopened = makeGestureCase();
  assert.equal(reopened.L.__map.options.zoomSnap, 0.5);
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 50);
  reopened.context.window.HINANEX_MAP_GESTURES.setSettings({ sensitivity: 99, style: "invalid" });
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 40,
    "clamp unsafe extreme inputs to 2.5x");
  assert.equal(reopened.L.__map.options.zoomSnap, 0);
  reopened.context.window.HINANEX_MAP_GESTURES.resetSettings();
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 67);
  assert.equal(reopened.L.__map.options.zoomSnap, 0);

  const blocked = makeContext({
    protocol: "http:",
    localStorage: { getItem() { throw Error("storage blocked"); },
      setItem() { throw Error("storage blocked"); } },
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(blocked.L.__map.options.zoomSnap, 0);
  assert.equal(blocked.context.window.HINANEX_MAP_GESTURES.setSettings({ sensitivity: 1.75 }).sensitivity, 1.75);
  assert.equal(blocked.L.__map.options.wheelPxPerZoomLevel, 57);
}

// Fractional zoom optimizes only visual cluster presentation, not source
// coordinates, hazard semantics or the minimum overview zoom.
{
  assert.match(mapCode, /const zoomBucket = zoom >= 13 \? "individual" : Math\.floor\(zoom\)/);
  assert.match(mapCode, /const groupingZoom = zoom >= 13 \? zoom : zoomBucket/);
  assert.match(mapCode, /lastDMarkerZoomBucket = null;/);
  assert.match(mapCode, /\[HINANEX map perf\] D grouping reused/);
}
