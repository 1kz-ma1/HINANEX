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

  const map = {
    handlers: {},
    setView(latlng, zoom) { this.lastView = { latlng, zoom }; return this; },
    createPane(name) { panes[name] = { style: {} }; },
    getPane(name) { return panes[name]; },
    addLayer(layer) { mapLayers.add(layer); layer._onMap = true; return this; },
    removeLayer(layer) { mapLayers.delete(layer); layer._onMap = false; return this; },
    hasLayer(layer) { return mapLayers.has(layer); },
    fitBounds(bounds) { this.lastBounds = bounds; return this; },
    on(name, fn) { this.handlers[name] = fn; return this; }
  };

  function group() {
    const value = {
      items: [],
      addTo(target) { target.addLayer(this); return this; },
      addLayer(layer) { this.items.push(layer); return this; },
      clearLayers() { this.items = []; return this; }
    };
    groups.push(value);
    return value;
  }

  function tileLayer() {
    return {
      handlers: {},
      addTo(target) { target.addLayer(this); return this; },
      setOpacity(value) { this.opacity = value; return this; },
      on(name, fn) { this.handlers[name] = fn; return this; }
    };
  }

  function bounds(points) {
    return { points, isValid: () => Array.isArray(points) && points.length > 0 };
  }

  return {
    map: () => map,
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
    __panes: panes
  };
}

function makeContext({ protocol, fetchImpl, href = null, discoveryOverride = null, geolocation = undefined }) {
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
    "coordinateSearchHelp", "coordinateSearchStatus"
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
    window: { location, history },
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
  assert.equal(discoveryAsset[1], mapAsset[1], "map and discovery assets share a release version");
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
