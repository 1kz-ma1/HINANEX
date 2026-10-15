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

// Ensure the independent REAL-browser predeploy smoke remains syntactically
// runnable and follows the current GIS consumer copy after white-card changes.
// Chromium itself is deliberately NOT implied by this static CI validation.
for (const filename of ["demo_20261022_browser_smoke.js",
  "guided_tour_compare_browser_smoke.cjs"]) {
  const script = fs.readFileSync(path.join(__dirname, filename), "utf8");
  new vm.Script(script, { filename });
  assert.doesNotMatch(script, /includes\("D出力読込済"\)/,
    "browser smoke must follow the current dataset chip label");
}
const actualBrowserSmoke = fs.readFileSync(
  path.join(__dirname, "demo_20261022_browser_smoke.js"), "utf8");
assert.match(actualBrowserSmoke, /long point details must scroll in speech bubble/);
assert.match(actualBrowserSmoke, /anchored bubble must fit mobile width/);
assert.match(actualBrowserSmoke, /UI_TEST_ONLY/);


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
    value: id === "region" ? "13123" : id === "floodOpacity" ? "58" :
      id === "mapDDecisionFilter" ? "all" : "",
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
  const tilePane = {
    style: {scale:"",transformOrigin:"",transition:"",willChange:""},
    getBoundingClientRect() {return {left:0,top:0};}
  };
  panes.tilePane=tilePane;
  const mapPane = {
    style: {scale:"",transformOrigin:"",transition:"",willChange:""},
    getBoundingClientRect() { return {left:0,top:0}; }
  };
  const groups = [];
  const markers = [];
  const tiles = [];
  const popups = [];

  const map = {
    handlers: {},
    zoom: 13,
    overviewFitZoom: 4,
    container: { listeners: {},
      addEventListener(type, fn, options) {
        this.listeners[type] = {fn, options};
      } },
    viewportLimits: { south: 35.65, north: 35.8, west: 139.80, east: 139.96 },
    getBounds() {
      const b = this.viewportLimits;
      return {
        contains(coords) {
          return coords[0] >= b.south && coords[0] <= b.north &&
            coords[1] >= b.west && coords[1] <= b.east;
        }
      };
    },
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
    getCenter() { return this.lastView?.latlng || [35.704, 139.882]; },
    stop() { this.stopCalls = (this.stopCalls || 0) + 1; return this; },
    closePopup() {
      if (this.openedPopup) {
        this.lastClosedPopup = this.openedPopup;
        this.openedPopup = null;
        this.handlers.popupclose?.({ popup: this.lastClosedPopup });
      }
      return this;
    },
    flyToBounds(bounds, options) { this.lastFly = { bounds, options }; return this; },
    flyTo(latlng, zoom, options) {
      this.lastPointFly = { latlng, zoom, options };
      return this;
    },
    getZoom() { return this.zoom; },
    getMinZoom() { return this.minZoom ?? 2; },
    getMaxZoom() { return 18; },
    getContainer() { return this.container; },
    getSize() { return {x:1024,y:768}; },
    containerPointToLatLng() { return [35.704,139.882]; },
    getPanes() { return {mapPane,tilePane}; },
    mouseEventToContainerPoint(e) { return {x:e.clientX,y:e.clientY}; },
    setZoomAround(anchor, zoom, options) {
      this.zoomAroundCalls = [...(this.zoomAroundCalls || []), {anchor,zoom,options}];
      this.zoom = zoom;
      return this;
    },
    project(latlng, zoom) {
      // Web Mercator world pixels, deterministic independent of viewport.
      const world = 256 * Math.pow(2, zoom);
      const latRad = latlng[0] * Math.PI / 180;
      return {
        x: (latlng[1] + 180) / 360 * world,
        y: (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * world
      };
    },
    createPane(name) {
      panes[name] = {
        style:{scale:"",transformOrigin:"",transition:"",willChange:""},
        getBoundingClientRect() {return {left:0,top:0};}
      };
    },
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
    const parent = {
      ghosts: [],
      appendChild(ghost) { this.ghosts.push(ghost); ghost.parentElement=this; }
    };
    const node = {
      parentElement:parent,
      cloneNode() {
        return {
          style:{opacity:"",scale:"",transformOrigin:"",transition:""},
          classList:{add(){}},querySelectorAll(){return [];},
          setAttribute(){},removeAttribute(){},
          getBoundingClientRect(){return {left:0,top:0};},
          remove(){this.removed=true;}
        };
      }
    };
    const layer = {
      options,
      handlers: {},
      sourceParent: parent,
      getContainer() { return node; },
      isLoading() {return true;},
      addTo(target) { target.addLayer(this); return this; },
      setOpacity(value) { this.opacity = value; return this; },
      on(name, fn) { this.handlers[name] = fn; return this; },
      off(name, fn) { if (this.handlers[name]===fn) delete this.handlers[name];return this; }
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
    popup: options => {
      const bubble = {
        options,
        setLatLng(latlng) { this.anchor = latlng; return this; },
        setContent(content) { this.content = content; return this; },
        openOn(target) {
          target.closePopup();
          target.openedPopup = this;
          return this;
        }
      };
      popups.push(bubble);
      return bubble;
    },
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
    __tiles: tiles,
    __popups: popups
  };
}

function makeContext({ protocol, fetchImpl, href = null, discoveryOverride = null, geolocation = undefined, localStorage = undefined, ImageCtor = undefined }) {
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
    "mapDDecisionFilter", "mapDDecisionFilterStatus",
    "coordinateSearchForm", "coordinateSearchInput", "coordinateSearchButton",
    "coordinateSearchHelp", "coordinateSearchStatus", "externalFloodTileNotice",
    "mapFloodRefreshStatus",
    "gisLayout", "uiTabNormal", "uiTabScenario", "scenarioIntro",
    "toggleLeftPanel", "toggleRightPanel", "mapViewportDStatus"
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
    window: { location, history, localStorage, Image: ImageCtor },
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
  assert.match(fileCase.elements.status.textContent, /手動で読込/);

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
  assert.match(httpCase.elements.facilityDisplayModeDescription.textContent, /地域の避難施設/);
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
  assert.match(httpCase.elements.facilityDisplayModeDescription.textContent, /周辺で確認済みの公式掲載地点/);
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
  assert.equal(mapAsset[1], "flood-refresh-coverage-20261015-v1");
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
  assert.match(missingDCase.elements.datasetStatus.textContent, /地域の施設データを読み込めません/);
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
  // One compact white information card, with every original technical value
  // preserved under a native keyboard-accessible disclosure.
  const selectedCard = httpCase.elements.details.innerHTML;
  assert.match(selectedCard, /<span class="badge">地域の避難施設<\/span>/);
  assert.match(selectedCard, /class="place-card-summary"/);
  assert.match(selectedCard, /<details class="place-card-disclosure"><summary>詳しい情報を見る/);
  const topRows = selectedCard.split('<details class="place-card-disclosure">')[0];
  assert.doesNotMatch(topRows, /施設ID|緯度|経度|source_record_trace|出典の記録位置|UNKNOWN|D施設/);
  assert.match(topRows, /未判定/);
  assert.match(selectedCard, /出典の記録位置|施設ID/);
  assert.match(httpCase.elements.details.innerHTML, /2階以上/);
  assert.match(httpCase.elements.details.innerHTML, /資料に記載された災害種別/);
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

  assert.match(httpCase.elements.mapUnavailableMessage.textContent, /位置は推測しません/);
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
  // Presentation uses ONLY already C/HTTPS-accepted GSI skhb01 tiles.
  const gsiPresenterCase=makeContext({protocol:"http:",fetchImpl:async u=>
    String(u).includes("gsi_verified_tiles/") ? {ok:false,status:404} :
    String(u).includes("edogawa_flood_site_catalog.json") ? {ok:true,status:200,json:async()=>officialCatalog} :
    String(u).endsWith("edogawa.json") ? {ok:true,status:200,json:async()=>edogawa} :
    {ok:false,status:404}});
  await new Promise(r=>setTimeout(r,0));
  const gp=gsiPresenterCase.context.window.HINANEX_GSI_FLOOD_PRESENTER;
  // Simulates the supplied screenshot: map moved far west although Edogawa
  // is selected. Presenter must use an actual D source coordinate instead.
  gsiPresenterCase.L.__map.setView([35.4,138.7],8);
  const savedCenter=gsiPresenterCase.L.__map.getCenter();
  const result=await gp.begin();
  assert.deepEqual(Array.from(gsiPresenterCase.L.__map.lastPointFly.latlng),[35.70,139.88],
    "presentation origin must be a verified regional D point, never the map center");
  assert.equal(gsiPresenterCase.L.__map.lastPointFly.zoom,12);
  assert.equal(result.state,"ready");
  assert.equal(result.source,"GSI_SKHB01_FLOOD");
  assert.equal(result.rawDisaster1,1);
  assert.equal(result.total,1);
  assert.equal(result.partial,true);
  assert.equal(gsiPresenterCase.elements.facilityDisplayMode.value,"region");
  assert.equal(gp.show().state,"shown");
  assert.equal(gsiPresenterCase.elements.facilityDisplayMode.value,"nearby");
  assert.equal(gsiPresenterCase.L.__map.hasLayer(gsiPresenterCase.L.__groups[3]),true);
  const verifiedSite=gp.inspect();
  assert.equal(verifiedSite.disaster1Raw,1);
  assert.equal(verifiedSite.sourceTrace,"feature_index=0");
  assert.match(verifiedSite.sourceUrl,/cyberjapandata[.]gsi[.]go[.]jp\/xyz\/skhb01/);
  const dUnknown=gp.compareD();
  assert.equal(dUnknown.state,"separate-source");
  assert.equal(dUnknown.unclassified,2);
  assert.equal(dUnknown.joinedWithGSI,false);
  assert.equal(gsiPresenterCase.elements.facilityDisplayMode.value,"both");
  gp.end(true);
  assert.equal(gsiPresenterCase.elements.facilityDisplayMode.value,"region");
  assert.equal(gsiPresenterCase.L.__groups[3].items.length,0);
  assert.deepEqual(gsiPresenterCase.L.__map.getCenter(),savedCenter);
  const badCatalog={...officialCatalog,
    sites:officialCatalog.sites.map(s=>({...s,disaster1_raw:0}))};
  const noRegionalD=makeContext({protocol:"http:",fetchImpl:async u=>
    ({ok:false,status:404})});
  await new Promise(r=>setTimeout(r,0));
  const missingPoint=await noRegionalD.context.window.HINANEX_GSI_FLOOD_PRESENTER.begin();
  assert.equal(missingPoint.state,"unavailable");
  assert.equal(missingPoint.reason,"NO_REGION_SOURCE_POINT");
  assert.equal(noRegionalD.L.__map.lastPointFly,undefined,
    "without a regional source point, do not fly to a guessed location");
  const rejected=makeContext({protocol:"http:",fetchImpl:async u=>
    String(u).includes("gsi_verified_tiles/") ? {ok:false,status:404} :
    String(u).includes("edogawa_flood_site_catalog.json") ? {ok:true,status:200,json:async()=>badCatalog} :
    String(u).endsWith("edogawa.json") ? {ok:true,status:200,json:async()=>edogawa} :
    {ok:false,status:404}});
  await new Promise(r=>setTimeout(r,0));
  const rejectApi=rejected.context.window.HINANEX_GSI_FLOOD_PRESENTER;
  assert.equal((await rejectApi.begin()).state,"unavailable");
  assert.equal(rejected.L.__groups[3].items.length,0);
  rejectApi.end(true);
  console.log("Verified GSI flood presenter, D separation, and false-positive refusal: OK");

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
  acceptedPin.handlers.click({});
  assert.deepEqual(Array.from(acceptedCase.L.__map.openedPopup.anchor),
    [35.705, 139.89], "GSI official source point anchors its own bubble");
  assert.match(acceptedCase.L.__map.openedPopup.content, /洪水に関する公式掲載地点/);
  assert.match(acceptedCase.L.__map.openedPopup.options.className,
    /hinanex-place-popup place-bubble--mid/);
  // Resize at a new zoom without replacing the selected site/provenance.
  assert.equal(vm.runInContext("placePopupZoomTier(9)", acceptedCase.context),
    "place-bubble--far");
  assert.equal(vm.runInContext("placePopupZoomTier(12)", acceptedCase.context),
    "place-bubble--mid");
  assert.equal(vm.runInContext("placePopupZoomTier(15)", acceptedCase.context),
    "place-bubble--near");
  const preservedBubble = acceptedCase.L.__map.openedPopup;
  const classes = new Set(["hinanex-place-popup", "place-bubble--mid"]);
  let layoutUpdates = 0;
  preservedBubble.getElement = () => ({classList:{
    contains: name => classes.has(name),
    remove: (...names) => names.forEach(name => classes.delete(name)),
    add: name => classes.add(name)
  }});
  preservedBubble.update = () => {layoutUpdates += 1;};
  acceptedCase.L.__map.zoom = 15;
  vm.runInContext("updatePlacePopupZoom()", acceptedCase.context);
  assert.ok(classes.has("place-bubble--near"));
  assert.ok(!classes.has("place-bubble--mid"));
  assert.equal(layoutUpdates, 1);
  assert.strictEqual(acceptedCase.L.__map.openedPopup, preservedBubble);
  assert.doesNotMatch(acceptedCase.L.__map.openedPopup.content, /<unsafe>/);
  assert.match(acceptedCase.elements.details.innerHTML, /洪水に関する公式掲載地点/);
  assert.match(acceptedCase.elements.details.innerHTML, /place-card-disclosure/);
  assert.match(acceptedCase.elements.details.innerHTML, /公式の出典を確認/);
  assert.doesNotMatch(
    acceptedCase.elements.details.innerHTML.split('<details class="place-card-disclosure">')[0],
    /feature_index=0|raw行/, "raw source trace belongs in the collapsed detail section");
  assert.match(acceptedCase.elements.details.innerHTML, /安全性・現在の開設状況は確認できていません/);
  assert.doesNotMatch(acceptedCase.elements.details.innerHTML, /番号は表示順序/);
  // Selecting another pin replaces the first bubble; a blank map tap closes it.
  acceptedCase.L.__groups[1].items[0].handlers.click({});
  assert.match(acceptedCase.L.__map.openedPopup.content, /地域の避難施設/);
  assert.notEqual(acceptedCase.L.__map.openedPopup, acceptedCase.L.__popups[0]);
  acceptedCase.L.__map.handlers.click({
    latlng: {lat:35.7,lng:139.88}, originalEvent: {}
  });
  assert.equal(acceptedCase.L.__map.openedPopup, null,
    "blank-map click must dismiss, not replace with raster details");
  // The screenshot's boundary click is UI-only: show a compact label first,
  // keep its geographic click anchor and source/caveat under one disclosure.
  vm.runInContext(`detail("江戸川区", [
    ["種類", "自治体境界"], ["地域", "東京都江戸川区"],
    ["自治体コード", "13123"], ["データ状態", "表示確認用fixture"]
  ], "境界fixture", {
    anchor: [35.71, 139.88],
    note: "この境界は表示確認用で、分析の正本ではありません。"
  })`, acceptedCase.context);
  const boundaryPopup = acceptedCase.L.__map.openedPopup;
  assert.match(boundaryPopup.options.className, /place-bubble--boundary/);
  assert.match(boundaryPopup.content, /自治体境界（参考）/);
  assert.doesNotMatch(boundaryPopup.content, /<div class="place-card-summary"><div class="row">/);
  assert.equal((boundaryPopup.content.match(/<details class="place-card-disclosure">/g) || []).length, 1);
  assert.match(boundaryPopup.content, /13123/);
  assert.match(boundaryPopup.content, /表示確認用で、分析の正本ではありません/);
  assert.deepEqual(Array.from(boundaryPopup.anchor), [35.71,139.88]);
  const pageSource = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  assert.match(pageSource, /紫：公式掲載地点（安全性未判定/);
  assert.match(pageSource, /id="uiTabNormal"[^>]*role="tab"/);
  assert.match(pageSource, /id="uiTabScenario"[^>]*role="tab"/);
  assert.match(pageSource, /id="gisLayout"[^>]*role="tabpanel"/);
  assert.match(pageSource, /current_theme[.]css[?]v=gis-facility-drawer-20261009-v6/);
  assert.match(pageSource, /map_first[.]css[?]v=flood-refresh-status-20261015-v1/);
  assert.match(pageSource, /place_card[.]css[?]v=zoom-compact-popup-20261014-v1/);
  assert.match(pageSource,/id="mapFloodRefreshStatus"/);
  assert.match(pageSource,/map_first[.]css[?]v=flood-refresh-status-20261015-v1/);
  const floodCss=fs.readFileSync(path.resolve(__dirname,"../gis/css/map_first.css"),"utf8");
  assert.match(floodCss,/\\.map-flood-refresh-status\\[hidden\\]\\{display:none\\}/);
  assert.match(floodCss,/pointer-events:none/);
  assert.match(floodCss,/data-state="partial"/);

  const dPinCss = fs.readFileSync(path.resolve(__dirname, "../gis/css/style.css"), "utf8");
  assert.match(dPinCss, /\.leaflet-shelter-pane \.leaflet-marker-icon/);
  assert.match(dPinCss, /animation: hinanex-d-marker-appear 140ms ease-out both/);
  assert.match(dPinCss, /prefers-reduced-motion: reduce/);
  assert.doesNotMatch(dPinCss, /\.leaflet-marker-icon\s*\{\s*transform:scale/,
    "appearance may not resize/reproject source facility markers");
  assert.match(pageSource, /css\/style[.]css[?]v=d-marker-entrance-20261015-v1/);
  const cardCss = fs.readFileSync(path.resolve(__dirname, "../gis/css/place_card.css"), "utf8");
  assert.match(cardCss, /\.hinanex-place-popup \.leaflet-popup-content-wrapper/);
  assert.match(cardCss, /--place-width:188px/);
  assert.match(cardCss, /--place-width:260px/);
  assert.match(cardCss, /place-bubble--boundary/);
  assert.match(cardCss, /max-height:min\(var\(--place-height\),46dvh\)/);
  assert.match(cardCss, /display:none !important/,
    "fixed right-side information card must stay hidden");
  assert.match(cardCss, /place-card-disclosure/);
  assert.match(cardCss, /height:min\(22%,160px\);max-height:none;overflow:hidden/, "mobile demo must cap the card and clip overflow");
  assert.match(cardCss, /height:100%;max-height:none;overflow-y:auto/, "mobile card contents must scroll within the card");
  assert.match(cardCss, /calc\(100% - 144px - min\(22%,160px\)\)/, "mobile presenter must leave room above for its place card");
  assert.match(cardCss, /data-right-panel="closed"/);
  assert.match(pageSource, /地域の避難施設データ/);
  assert.doesNotMatch(pageSource, /D施設|地域D|DのUNKNOWN|CURRENT D SOURCE|GIS \/ RegionExport|CANDIDATE・EXCLUDED|UNKNOWN・資料不足|洪水Scenario/);

  assert.match(pageSource, /id="toggleLeftPanel"[^>]*aria-expanded="false"/);
  assert.match(pageSource, /id="toggleRightPanel"[^>]*aria-expanded="false"/);
  assert.match(pageSource, /id="gisLeftPanel"/);
  assert.match(pageSource, /gis-side-shell gis-side-shell--left/);
  assert.match(pageSource, /gis-side-shell gis-side-shell--right/);
  assert.match(pageSource, /aria-label="左メニューを開く"/);
  assert.match(pageSource, /aria-label="地点情報カードを閉じる"/);
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
  assert.match(sidebar, /未判定の施設情報を施設IDで照合/);
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
  assert.match(acceptedCase.elements.toggleDMarkers.textContent, /公式掲載地点だけ表示/);
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

  // Flood tile status never infers "no inundation" while loading.
  const floodNotice=clusterCase.elements.mapFloodRefreshStatus;
  const floodLayer=clusterCase.L.__tiles[1];
  vm.runInContext("beginFloodRefresh()",clusterCase.context);
  assert.equal(floodNotice.hidden,false);
  assert.equal(floodNotice.dataset.state,"loading");
  assert.match(floodNotice.textContent,/更新中/);
  assert.match(floodNotice.textContent,/浸水なし/);
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden,true);
  floodLayer.isLoading=()=>false;
  vm.runInContext("completeFloodRefresh()",clusterCase.context);
  assert.equal(floodNotice.hidden,true);
  floodLayer.isLoading=()=>true;
  vm.runInContext("beginFloodRefresh()",clusterCase.context);
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
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden,false);
  assert.equal(floodNotice.hidden,false);
  assert.equal(floodNotice.dataset.state,"partial");
  assert.match(floodNotice.textContent,/一部を確認できません/);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent,/浸水なし/);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent, /別データ/);
  // Later D status updates must not erase the independently visible raster warning.
  vm.runInContext('setStatus("D出力を更新しました", "success")', clusterCase.context);
  assert.match(clusterCase.elements.status.textContent, /D出力を更新/);
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden, false);
  assert.match(clusterCase.elements.externalFloodTileNotice.textContent, /公的洪水ラスタ/);
  assert.equal(clusterCase.elements.recordCount.textContent, 3);
  floodLayer.isLoading=()=>false;
  vm.runInContext("completeFloodRefresh()",clusterCase.context);
  assert.equal(floodNotice.dataset.state,"partial",
    "failed flood tile must not be overwritten by load-complete");
  vm.runInContext("beginFloodRefresh()",clusterCase.context);
  vm.runInContext("completeFloodRefresh()",clusterCase.context);
  assert.equal(floodNotice.hidden,true,
    "new successful batch clears transient banner, not failure history");
  assert.equal(clusterCase.elements.externalFloodTileNotice.hidden,false);
  vm.runInContext("beginFloodRefresh()",clusterCase.context);
  clusterCase.elements.officialFlood.checked=false;
  clusterCase.elements.officialFlood.listeners.change({
    target:clusterCase.elements.officialFlood
  });
  assert.equal(floodNotice.hidden,true);
  clusterCase.elements.officialFlood.checked=true;
  clusterCase.elements.officialFlood.listeners.change({
    target:clusterCase.elements.officialFlood
  });
  assert.equal(floodNotice.dataset.state,"loading");

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
  assert.match(html, /id="mapViewportDStatus"[^>]*role="status"/);
  assert.match(html, /id="mapSettingsPanel"[^>]*hidden/);
  assert.match(html, /id="mapSettingsToggle"[^>]*type="button"/);
  assert.match(html, /id="mapWheelSensitivity"[^>]*type="range"[^>]*min="0.5"[^>]*max="5"/);
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
        settings: { sensitivity: 3.75, style: "continuous" },
        getSettings() { return { ...this.settings }; },
        setSettings(changes) {
          this.settings = { ...this.settings, ...changes };
          return this.getSettings();
        },
        resetSettings() {
          this.settings = { sensitivity: 3.75, style: "continuous" };
          return this.getSettings();
        }
      }
    },
    Event: class { constructor(type) { this.type = type; } }
  };
  vm.createContext(facade);
  vm.runInContext(uiCode, facade, { filename: "map_first_ui.js" });
  assert.equal(gpsRequests, 0);
  assert.equal(nodes.mapWheelSensitivity.value, "3.75");
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
  assert.equal(nodes.mapWheelSensitivity.value, "3.75");
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

// Navigation-only min zoom uses Japan dimensions as a responsive reference,
// but stops closer (the second screenshot), intentionally allowing cropping.
// No municipality/source selection or map coordinates may change.
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
  const assertZoom = (actual, expected, reason) =>
    assert.ok(Math.abs(actual - expected) < 1e-9,
      reason + ": expected " + expected + ", got " + actual);
  assertZoom(map.minZoom, 4.6,
    "closer navigation limit should be 0.6 zoom above the former reference fit");
  // Round baseline is still responsive to desktop/panels/portrait. The
  // requested closer limit may intentionally crop the former full-Japan fit.
  map.overviewFitZoom = 4.85;
  map.handlers.resize();
  assertZoom(map.minZoom, 5.45, "near 200km rather than 300km scale");
  assert.ok(map.minZoom > map.overviewFitZoom,
    "the navigation-oriented floor no longer guarantees fitting all Japan");
  map.overviewFitZoom = 4.24;
  map.handlers.resize();
  assertZoom(map.minZoom, 4.7, "fractional viewport keeps its fit-derived baseline");
  map.overviewFitZoom = 4.55;
  map.handlers.resize();
  assertZoom(map.minZoom, 5.15, "fractional minZoom is not tied to tile integers");
  map.overviewFitZoom = 4;
  map.handlers.resize();
  assertZoom(map.minZoom, 4.6, "same reference fit has predictable +0.6 offset");
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
  assertZoom(map.minZoom, 3.6, "small portrait viewport retains responsive floor");
  map.overviewFitZoom = 5;
  map.handlers.resize();
  assertZoom(map.minZoom, 5.6, "wide viewport retains responsive floor");
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
  // Check a just-above-tile-floor fit and maximum-clamped large viewport.
  map.overviewFitZoom = 2.9;
  map.handlers.resize();
  assertZoom(map.minZoom, 3.45, "above tile floor with the new 0.6 closer scale");
  map.overviewFitZoom = 6.9;
  map.handlers.resize();
  assert.equal(map.minZoom, 6);
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
  assert.equal(L.__tiles[0].options.keepBuffer, 4);
  assert.equal(L.__tiles[1].options.keepBuffer, 3);
  assert.equal(L.__tiles[0].options.updateInterval, 220,
    "throttle mid-animation base-tile requests");
  assert.equal(L.__tiles[0].options.updateWhenZooming, false,
    "target-first view must skip intermediate basemap tile requests");
  assert.equal(L.__tiles[1].options.updateWhenZooming, false,
    "official flood raster retains lighter end-of-zoom tile loading");
  assert.equal(L.__tiles[0].options.minZoom, 2);
  assert.equal(L.__tiles[1].options.minZoom, 2);
  assert.equal(L.__map.getZoom(), 13);
  assert.ok(Math.abs(L.__map.minZoom - 4.6) < 1e-9,
    "navigation floor is closer without changing tile/gesture options");
  assert.match(mapCode, /new URL\(window\.location\.href\)\.searchParams\.get\("debugMapPerf"\) === "1"/);
  assert.match(mapCode, /\[HINANEX map perf\] tile batch/);
  assert.match(mapCode, /\[HINANEX map perf\] D markers/);
  assert.equal(L.__map.options.zoomSnap, 0,
    "continuous mode must not snap wheel and pinch gestures to discrete levels");
  assert.equal(L.__map.options.zoomDelta, 0.5, "+/- and keyboard remain half steps");
  assert.equal(L.__map.options.wheelPxPerZoomLevel, 27,
    "new baseline is 3.75x (2.5 times 1.5), unsnapped");
  assert.equal(L.__map.options.zoomSnap, 0);
  assert.equal(L.__map.options.wheelDebounceTime, 135,
    "batch rapid wheel input before one destination-focused zoom animation");
  assert.equal(L.__map.container.listeners.wheel.options.capture, true);
  assert.equal(L.__map.container.listeners.wheel.options.passive, false);
  assert.equal(L.__map.options.zoomAnimation, true);
  assert.equal(L.__map.options.zoomAnimationThreshold, 5);
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

  // Same 3.75× speed, old intermediate raster redraw policy: isolated A/B.
  const progressive = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=13123&zoomFeel=progressive",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(progressive.L.__map.options.wheelPxPerZoomLevel, 27);
  assert.equal(progressive.L.__map.options.wheelDebounceTime, 80);
  assert.equal(progressive.L.__map.options.zoomSnap, 0);
  assert.equal(progressive.L.__map.container.listeners.wheel, undefined,
    "progressive A/B variant retains Leaflet native wheel handler");
  assert.equal(progressive.L.__tiles[0].options.updateWhenZooming, true);
  assert.equal(progressive.L.__tiles[1].options.updateWhenZooming, false);
  assert.equal(progressive.L.__map.getZoom(), L.__map.getZoom());

  const native = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=13123&zoomFeel=native",
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(native.L.__map.options.wheelPxPerZoomLevel, 27);
  assert.equal(native.L.__map.options.wheelDebounceTime, 135);
  assert.equal(native.L.__map.container.listeners.wheel, undefined);
  assert.equal(native.L.__tiles[0].options.updateWhenZooming, false);

  // Compare new faster image-settling with precisely the same prior preview
  // implementation, wheel sensitivity and destination-only tile policy.
  const preview135 = makeContext({
    protocol: "http:",
    href: "http://test/gis/gis/?region=13123&zoomFeel=preview135",
    fetchImpl: async () => ({ok:false,status:404,json:async()=>({})})
  });
  assert.equal(vm.runInContext("WHEEL_GESTURE_IDLE_MS",preview135.context),135);
  assert.equal(vm.runInContext("WHEEL_PREVIEW_TRANSITION_MS",preview135.context),65);
  assert.equal(preview135.L.__map.options.wheelPxPerZoomLevel,27);
  assert.equal(preview135.L.__tiles[0].options.updateWhenZooming,false);
  assert.equal(preview135.L.__map.options.zoomSnap,0);
  assert.equal(typeof preview135.L.__map.container.listeners.wheel.fn,"function");

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


 // Capture-phase wheel input is combined into ONE public setZoomAround call,
 // not repeated calls per event. Non-wheel gestures and controls stay native.
 {
   const { L, context } = makeContext({
     protocol: "http:",
     fetchImpl: async () => ({ok:false,status:404,json:async()=>({})})
   });
   const map=L.__map, handler=map.container.listeners.wheel.fn;
   const mapPane=map.getPanes().mapPane;
   const tilePane=map.getPanes().tilePane;
   const floodPane=map.getPane("officialFloodPane");
   assert.equal(vm.runInContext("WHEEL_GESTURE_IDLE_MS",context),70,
     "new wheel image update starts 65ms earlier than prior preview");
   assert.equal(vm.runInContext("WHEEL_PREVIEW_TRANSITION_MS",context),40);
   assert.match(mapCode, /\[HINANEX map perf\] wheel intent-to-commit/);
   assert.equal(typeof handler, "function");
   const event = (deltaY, target={}) => ({
     deltaY, deltaMode:0, clientX:220, clientY:175, target,
     prevented: false, stopped:false,
     preventDefault() { this.prevented=true; },
     stopImmediatePropagation() { this.stopped=true; }
   });
   const e1=event(-24), e2=event(-24), e3=event(-24);
   handler(e1);handler(e2);handler(e3);
   assert.equal(e1.prevented,true);
   assert.equal(e1.stopped,true);
   assert.ok(Number(tilePane.style.scale)>1,
     "reuse background raster without scaling the geographic marker pane");
   assert.ok(Number(floodPane.style.scale)>1,
     "official flood raster follows the same preview geometry");
   assert.equal(mapPane.style.scale,"",
     "mapPane must not scale pins, cluster icons and location bubbles");
   assert.equal(tilePane.style.transition,"scale 40ms ease-out",
     "shorter preview transition must not delay visual response");
   assert.match(tilePane.style.transformOrigin, /220px 175px/);
   assert.equal(map.zoom,13, "preview must not change geographic map zoom");
   assert.equal(map.zoomAroundCalls?.length || 0,0,
     "no intermediate zoom on each wheel event");
   vm.runInContext("flushSingleTargetWheel()",context);
   assert.equal(tilePane.style.scale,"",
     "commit restores background layer CSS preview");
   assert.equal(floodPane.style.scale,"");
   assert.equal(mapPane.style.scale,"",
     "marker and popup panes remain unscaled throughout wheel gesture");
   assert.equal(L.__tiles[0].sourceParent.ghosts.length,1,
     "a read-only copy of rendered map tiles is preserved during final loading");
   assert.equal(L.__tiles[0].sourceParent.ghosts[0].removed,undefined);
   assert.equal(L.__tiles[1].sourceParent.ghosts.length,1);
   assert.equal(L.__tiles[1].sourceParent.ghosts[0].removed,true,
     "stale flood image must be discarded before geographic zoom changes");
   assert.equal(L.__tiles[0].sourceParent.ghosts[0].removed,undefined,
     "basemap's independently aligned old tiles may still be retained");
   assert.equal(tilePane.style.transformOrigin,"");
   assert.equal(map.zoomAroundCalls.length,1,
     "one gesture resolves to one animated destination");
   assert.equal(map.zoomAroundCalls[0].anchor.x,220);
   assert.equal(map.zoomAroundCalls[0].anchor.y,175);
   assert.ok(map.zoomAroundCalls[0].zoom>13);
   assert.ok(map.zoomAroundCalls[0].zoom<16,
     "limit preview scale so zoom raster stays manageable");
   assert.equal(map.zoomAroundCalls[0].options.animate,false,
     "a completed visual preview must not trigger a second animation");
   const firstTarget = map.zoomAroundCalls[0].zoom;
   handler(event(40));
   vm.runInContext("flushSingleTargetWheel()",context);
   assert.equal(map.zoomAroundCalls.length,2);
   assert.ok(map.zoomAroundCalls[1].zoom<firstTarget,
     "negative wheel intent returns toward the prior zoom");
   const pinch=event(-48);pinch.ctrlKey=true;handler(pinch);
   assert.equal(pinch.prevented,false,"trackpad pinch keeps native Leaflet handling");
   const popup=event(-48,{closest:()=>({})});handler(popup);
   assert.equal(popup.prevented,false,"popover scroll does not zoom map");
   // An explicit half-step preference remains under Leaflet's own handler.
   context.window.HINANEX_MAP_GESTURES.setSettings({style:"steps"});
   const stepped=event(-48);handler(stepped);
   assert.equal(stepped.prevented,false);
   assert.equal(map.zoomAroundCalls.length,2);
   // Competing drag cancels pending wheel rather than restoring stale camera.
   context.window.HINANEX_MAP_GESTURES.setSettings({style:"continuous"});
   handler(event(-32));
   assert.ok(Number(tilePane.style.scale)>1);
   map.handlers.dragstart();
   assert.equal(tilePane.style.scale,"");
   assert.equal(mapPane.style.scale,"");
   vm.runInContext("flushSingleTargetWheel()",context);
   assert.equal(map.zoomAroundCalls.length,2);

   // Minimum and maximum zoom are clamped by the map's effective bounds.
   context.window.HINANEX_MAP_GESTURES.setSettings({style:"continuous"});
   map.zoom=map.getMinZoom();
   handler(event(2000));
   vm.runInContext("flushSingleTargetWheel()",context);
   assert.equal(map.zoomAroundCalls.length,2);
   map.zoom=18;
   handler(event(-2000));
   vm.runInContext("flushSingleTargetWheel()",context);
   assert.equal(map.zoomAroundCalls.length,2);
 }


 // Prefetch only bounded, predicted *final* GSI basemap tiles. No flood
 // raster, invented destination or intermediate zoom pyramid is requested.
 {
   const images=[];
   class FakeImage {
     set src(url) {this.url=url;images.push(url);}
     get src() {return this.url;}
   }
   const {context,L}=makeContext({
     protocol:"http:",ImageCtor:FakeImage,
     fetchImpl:async()=>({ok:false,status:404,json:async()=>({})})
   });
   const ev={
     deltaY:-96,deltaMode:0,clientX:280,clientY:220,target:{},
     preventDefault(){},stopImmediatePropagation(){}
   };
   L.__map.container.listeners.wheel.fn(ev);
   const coords=vm.runInContext("predictedGsiTileCoords()",context);
   assert.ok(coords.length>0 && coords.length<=8);
   assert.equal(new Set(coords.map(x=>x.z)).size,1,
     "preload only ONE destination tile zoom, never crossed levels");
   assert.equal(coords[0].z,Math.round(vm.runInContext("wheelDestinationZoom()",context)));
   vm.runInContext("warmPredictedTiles()",context);
   assert.ok(images.length>0 && images.length<=8,
     "hard cap on extra tile requests per burst");
   assert.equal(new Set(images).size,images.length);
   assert.ok(images.every(url=>/^https:\/\/cyberjapandata[.]gsi[.]go[.]jp\/xyz\/std\/\d+\/\d+\/\d+[.]png$/.test(url)),
     "prefetch only exact official GSI background PNG URL");
   assert.ok(images.every(url=>!url.includes("flood")),
     "hazard raster cannot be speculative and stays a separate layer");
   vm.runInContext("warmPredictedTiles()",context);
   assert.equal(images.length,coords.length,"duplicate URLs reused in one burst");
   vm.runInContext("clearPendingWheel()",context);
   assert.equal(vm.runInContext("predictedTileImages.size",context),0);
 }

// Full target-zoom geographic coverage: verify layout in viewport pixels,
// no interpolated hazard/source features and a strict fallback for missing grid.
{
  const {context,L}=makeContext({
    protocol:"http:",
    fetchImpl:async()=>({ok:false,status:404,json:async()=>({})})
  });
  assert.equal(vm.runInContext("TARGET_COVER_MAX_TILES",context),48);
  assert.equal(vm.runInContext("TARGET_COVER_WAIT_MS",context),650);
  const points = [{x:16,y:18},{x:512,y:384},{x:1000,y:744}];
  for (const point of points) for (const zoom of [3,5,8,10,12]) {
    context.window.__targetPoint=point;
    context.window.__targetZoom=zoom;
    const grid=vm.runInContext(
      "destinationTileGrid(window.__targetPoint,window.__targetZoom)",context);
    assert.ok(grid,"target tile coverage should be computable for normal view");
    assert.ok(grid.tiles.length>0 && grid.tiles.length<=48);
    assert.equal(grid.width,1024);
    assert.equal(grid.height,768);
    assert.ok(Math.min(...grid.tiles.map(t=>t.left))<=0.01,
      "tile grid covers the left viewport edge");
    assert.ok(Math.max(...grid.tiles.map(t=>t.left+t.size))>=1023.99,
      "tile grid covers the right viewport edge");
    assert.ok(Math.min(...grid.tiles.map(t=>t.top))<=0.01);
    assert.ok(Math.max(...grid.tiles.map(t=>t.top+t.size))>=767.99);
    const zSet=new Set(grid.tiles.map(t=>Number(t.url.split("/")[5])));
    assert.equal(zSet.size,1,"only destination zoom tiles, never intermediates");
    assert.equal([...zSet][0],zoom);
    assert.ok(grid.tiles.every(t=>/^https:\/\/cyberjapandata[.]gsi[.]go[.]jp\/xyz\/std\/\d+\/\d+\/\d+[.]png$/.test(t.url)));
  }
  // Old-raster zoom-out preview must never visibly shrink loaded imagery
  // beyond its source screen-space bounds while waiting for target coverage.
  const viewport={left:0,top:0,right:1000,bottom:700};
  const origin={x:500,y:350};
  context.window.__coverage={left:-100,top:-90,right:1100,bottom:790};
  context.window.__viewport=viewport;
  context.window.__origin=origin;
  const clamped=vm.runInContext(
    "coverageLimitedScale(.25,window.__coverage,window.__origin,window.__viewport)",context);
  assert.ok(clamped>0.8 && clamped<=1,
    "old geographic coverage must not collapse to a small center rectangle");
  const ample=vm.runInContext(
    "coverageLimitedScale(.5,{left:-800,top:-800,right:1800,bottom:1600},window.__origin,window.__viewport)",context);
  assert.equal(ample,.5,"well-buffered old raster can still respond freely");
  const missing=vm.runInContext(
    "coverageLimitedScale(.25,{missing:true},window.__origin,window.__viewport)",context);
  assert.equal(missing,1,"unloaded raster cannot claim visual coverage");

  const originalSize=L.__map.getSize;
  L.__map.getSize=()=>({x:20000,y:12000});
  assert.equal(vm.runInContext("destinationTileGrid({x:5,y:5},10)",context),null,
    "over-budget display must fall back rather than synthesize coverage");
  L.__map.getSize=originalSize;
  // Test the DOM-only layer handoff without a map, raster or network provider.
  const elems=[];
  const createElement=tag=>{
    const obj={tag,style:{},children:[],className:"",removed:false,
      setAttribute(){},remove(){this.removed=true;},
      appendChild(child){this.children.push(child);}};
    elems.push(obj);
    return obj;
  };
  context.document.createElement=createElement;
  const pane={style:{},children:[],appendChild(child){this.children.push(child);},
    getBoundingClientRect(){return {left:0,top:0};}};
  L.__map.createPane=name=>{L.__map.coverPane=pane;};
  const existingPane=L.__map.getPane.bind(L.__map);
  L.__map.getPane=name=>name==="wheelCoverPane"?
    L.__map.coverPane:existingPane(name);
  const grid=vm.runInContext("destinationTileGrid({x:512,y:384},10)",context);
  context.window.__coverageGrid=grid;
  const presented=vm.runInContext(
    "presentTargetCover(window.__coverageGrid,[])",context);
  assert.equal(presented,true);
  assert.equal(pane.style.zIndex,"205",
    "complete backdrop must sit UNDER official flood and marker panes");
  assert.equal(pane.children.length,1);
  assert.equal(pane.children[0].children.length,grid.tiles.length,
    "use all exact official destination image URLs, not just 8 nearest");
  assert.ok(pane.children[0].children.every((img,i)=>
    img.src===grid.tiles[i].url && img.style.width.endsWith("px")));
  vm.runInContext("removeTargetCover()",context);
  assert.equal(pane.children[0].removed,true);
  assert.equal(vm.runInContext("targetCover",context),null);
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
  assert.deepEqual({ ...api.getSettings() }, { sensitivity: 3.75, style: "continuous" });
  assert.equal(first.L.__map.options.wheelPxPerZoomLevel, 27);
  const startView = first.L.__map.lastView;
  const minZoom = first.L.__map.minZoom;
  api.setSettings({ sensitivity: 2, style: "steps" });
  assert.equal(first.L.__map.options.wheelPxPerZoomLevel, 50);
  assert.equal(first.L.__map.options.zoomSnap, 0.5);
  assert.strictEqual(first.L.__map.lastView, startView);
  assert.equal(first.L.__map.minZoom, minZoom);
  assert.match(memory["hinanex.gis.gesture.v2"], /"sensitivity":2/);
  const reopened = makeGestureCase();
  assert.equal(reopened.L.__map.options.zoomSnap, 0.5);
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 50);
  reopened.context.window.HINANEX_MAP_GESTURES.setSettings({ sensitivity: 99, style: "invalid" });
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 20,
    "clamp unsafe extreme inputs to 5x");
  assert.equal(reopened.L.__map.options.zoomSnap, 0);
  reopened.context.window.HINANEX_MAP_GESTURES.resetSettings();
  assert.equal(reopened.L.__map.options.wheelPxPerZoomLevel, 27);
  assert.equal(reopened.L.__map.options.zoomSnap, 0);

  // Existing visitors with the previous *default* inherit the new
  // baseline; intentional earlier speed/step changes remain preserved.
  const legacyDefault = makeContext({
    protocol: "http:",
    localStorage: { getItem(k) {
      return k === "hinanex.gis.gesture.v1"
        ? '{"sensitivity":1.5,"style":"continuous"}' : null;
    }},
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(legacyDefault.L.__map.options.wheelPxPerZoomLevel, 27);
  const legacyCustom = makeContext({
    protocol: "http:",
    localStorage: { getItem(k) {
      return k === "hinanex.gis.gesture.v1"
        ? '{"sensitivity":2.25,"style":"steps"}' : null;
    }},
    fetchImpl: async () => ({ ok: false, status: 404, json: async () => ({}) })
  });
  assert.equal(legacyCustom.L.__map.options.wheelPxPerZoomLevel, 44);
  assert.equal(legacyCustom.L.__map.options.zoomSnap, 0.5);
  // v2 overrides v1 after an explicit change; values never modify map view.
  assert.equal(reopened.L.__map.options.wheelDebounceTime, 135);

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

// Viewport-based multi-region D markers: the *visible verified coordinates*
// drive what appears, not guessed municipality polygons, and do not pan.
(async () => {
  const received = [];
  const http = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const path = String(url);
      received.push(path);
      if (path.endsWith("edogawa.json")) return { ok: true, json: async () => edogawa };
      if (path.endsWith("niigata.json")) return { ok: true, json: async () => niigata };
      if (path.endsWith("nagoya.json")) return { ok: true, json: async () => nagoya };
      return { ok: false, status: 404 };
    }
  });
  const map = http.L.__map;
  const group = http.L.__groups[4];
  const pill = http.elements.mapViewportDStatus;
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(http.elements.region.value, "13123");
  const beforeView = map.lastView, beforeUrl = http.context.window.location.href;
  // The user scrolls Niigata into view; only real source positions may appear.
  map.viewportLimits = { south: 37.75, north: 38.25, west: 138.80, east: 139.50 };
  map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.equal(group.items.length, 1, "Niigata's verified coordinates appear without region-click");
  assert.equal(group.items[0].latlng[0], niigata.datasets[0].records[0].latitude);
  assert.equal(group.items[0].latlng[1], niigata.datasets[0].records[0].longitude);
  assert.match(pill.textContent, /新潟県 新潟市 1件/);
  assert.match(pill.textContent, /開設・安全性未判定/);
  assert.equal(pill.hidden, false);
  assert.strictEqual(map.lastView, beforeView, "panning does not reset chosen map view");
  assert.equal(http.context.window.location.href, beforeUrl, "no implicit region URL mutation");
  assert.equal(http.elements.region.value, "13123", "manual region remains a navigation shortcut");
  group.items[0].handlers.click({});
  assert.match(http.elements.details.innerHTML, /Niigata A/);
  assert.match(http.elements.details.innerHTML, /UNKNOWN/);
  const firstMarker = group.items[0];

  // Repeat pans/zoom inside the area: no further HTTP, same marker identity.
  map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.strictEqual(group.items[0], firstMarker);
  assert.equal(received.filter(url => url.endsWith("niigata.json")).length, 1);
  assert.equal(received.filter(url => url.endsWith("nagoya.json")).length, 1);
  map.zoom = 12.2;
  map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.equal(group.items.length, 1);
  // Pan away: extra-layer marker disappears. No claim that there are no sites.
  map.viewportLimits = { south: 34.9, north: 35.3, west: 136.7, east: 137.4 };
  map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.equal(group.items.length, 0);
  assert.match(pill.textContent, /未収録・未取得を含む/);
  assert.doesNotMatch(pill.textContent, /安全な地域|避難所が存在しない/);

  // The selected region still works as a manual shortcut, and must never
  // duplicate its source markers in the viewport-only overlay.
  http.elements.region.value = "15100";
  http.elements.region.listeners.change({ target: http.elements.region });
  await new Promise(resolve => setTimeout(resolve, 0));
  map.viewportLimits = { south: 37.75, north: 38.25, west: 138.80, east: 139.50 };
  map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.equal(group.items.length, 0, "selected Niigata D is rendered by its original layer");
  assert.equal(http.L.__groups[1].items.length, 1);
  assert.equal(http.elements.region.value, "15100");
  assert.match(pill.textContent, /新潟県 新潟市 1件/);

  // GSI-only mode must hide the independent D viewport layer.
  http.elements.facilityDisplayMode.value = "nearby";
  http.elements.facilityDisplayMode.listeners.change({ target: http.elements.facilityDisplayMode });
  assert.equal(map.hasLayer(group), false);
  assert.equal(pill.hidden, true);
  http.elements.facilityDisplayMode.value = "region";
  http.elements.facilityDisplayMode.listeners.change({ target: http.elements.facilityDisplayMode });
  assert.equal(map.hasLayer(group), true);

  const localFile = makeContext({
    protocol: "file:",
    fetchImpl: async () => { throw Error("file mode must not fetch"); }
  });
  localFile.L.__map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 155));
  assert.equal(localFile.L.__groups[4].items.length, 0);
  assert.match(localFile.elements.mapViewportDStatus.textContent, /未収録・未取得を含む/);
  console.log("viewport D navigation: OK");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

// The map scale change is intentionally small and purely presentational:
// exact D/GSI/official raster semantics are not modified by a minZoom setter.
{
  assert.match(mapCode, /const NAVIGATION_CLOSEUP_ZOOM_OFFSET = 0\.6/);
  assert.match(mapCode, /tightFitZoom \+ NAVIGATION_CLOSEUP_ZOOM_OFFSET/);
  assert.doesNotMatch(mapCode, /map\.setView\(\[24\.0,\s*122\.5\]/);
}


// Audience QR and on-device access must remain a controlled, view-only GIS
// presentation surface: never auto-request GPS or start a scenario tour.
{
  const page = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const shareSource = fs.readFileSync(path.resolve(__dirname, "../gis/js/audience_share.js"), "utf8");
  const styles = fs.readFileSync(path.resolve(__dirname, "../gis/css/map_first.css"), "utf8");
  const audienceURL = "https://hinanex-staging.onrender.com/gis/gis/?demo=audience";
  assert.match(page, /id="mapShareOpen"[^>]*aria-controls="mapSharePanel"/);
  assert.match(page, /id="mapSharePanel"[^>]*hidden/);
  assert.match(page, /id="mapShareURL"[^>]*readonly value="https:\/\/hinanex-staging\.onrender\.com\/gis\/gis\/\?demo=audience"/);
  assert.match(page, /id="mapAudienceIntro"[^>]*hidden/);
  assert.match(page, /js\/audience_share[.]js[?]v=audience-share-20261010-v1/);
  assert.match(page, /css\/map_first[.]css[?]v=flood-refresh-status-20261015-v1/);
  assert.match(styles, /\.map-share-panel\[hidden\],\.map-audience-intro\[hidden\]\{display:none\}/);
  assert.match(shareSource, /const AUDIENCE_URL = "https:\/\/hinanex-staging\.onrender\.com\/gis\/gis\/\?demo=audience"/);
  assert.doesNotMatch(shareSource, /geolocation|getCurrentPosition|flyTo|map\.setView|fetch\(|sendBeacon|XMLHttpRequest|<iframe/);

  function harness(href, store = new Map()) {
    const nodes = new Map(), listeners = {};
    function makeNode(key) {
      const attrs = new Map();
      const node = {
        key, hidden: false, open: false, children: [], listeners: {},
        appendChild(child) { this.children.push(child); return child; },
        get firstChild() { return this.children[0] || null; },
        setAttribute(name, value) { attrs.set(name, String(value)); },
        getAttribute(name) {
          if (key === "gisLayout" && name.startsWith("data-")) return "closed";
          return attrs.get(name) || null;
        },
        addEventListener(type, callback) { this.listeners[type] = callback; },
        contains(target) { return this === target; },
        click() { this.listeners.click?.({ target: this }); },
        focus() { this.wasFocused = true; },
        select() { this.wasSelected = true; }
      };
      return node;
    }
    const element = id => {
      if (!nodes.has(id)) nodes.set(id, makeNode(id));
      return nodes.get(id);
    };
    for (const id of ["mapSharePanel", "mapAudienceIntro", "mapSettingsPanel"]) element(id).hidden = true;
    const location = { href };
    const sessionStorage = {
      getItem(k) { return store.get(k) ?? null; },
      setItem(k, v) { store.set(k, v); }
    };
    const document = {
      getElementById: element,
      createElementNS(_ns, type) { return makeNode(type); },
      addEventListener(name, fn) { listeners[name] = fn; }
    };
    const window = { location, sessionStorage };
    const navigator = { clipboard: { async writeText(v) { window.copied = v; } } };
    vm.runInNewContext(shareSource, { document, window, navigator, URL, console });
    return { element, window, listeners, store };
  }
  const h = harness("https://hinanex-staging.onrender.com/gis/gis/");
  h.element("mapShareOpen").click();
  assert.equal(h.element("mapSharePanel").hidden, false);
  assert.equal(h.element("mapShareOpen").getAttribute("aria-expanded"), "true");
  assert.equal(h.element("mapShareURL").value, audienceURL);
  const svg = h.element("mapShareQR").firstChild;
  assert.equal(svg.getAttribute("viewBox"), "0 0 41 41");
  assert.equal(svg.children.length, 2, "in-page SVG QR requires no third-party image service");
  assert.equal((svg.children[1].getAttribute("d").match(/M/g) || []).length, 575,
    "locally encoded URL has the expected dark QR modules");
  assert.equal(h.element("mapSharePanel").hidden, false);
  const outside = { target: {} };
  h.listeners.click(outside);
  assert.equal(h.element("mapSharePanel").hidden, true);
  assert.equal(h.element("mapShareOpen").getAttribute("aria-expanded"), "false");
  h.element("mapShareOpen").click();
  h.listeners.keydown({ key: "Escape", preventDefault() { this.prevented = true; } });
  assert.equal(h.element("mapSharePanel").hidden, true);
  assert.equal(h.element("mapShareOpen").wasFocused, true);
  h.element("mapShareOpen").click();
  h.element("mapToolMarks").open = true;
  h.element("mapToolMarks").listeners.toggle();
  assert.equal(h.element("mapSharePanel").hidden, true,
    "opening another map control closes the sharing card");

  const v1 = harness(audienceURL);
  assert.equal(v1.element("mapAudienceIntro").hidden, false,
    "audience URL shows a one-time, dismissible guide");
  assert.equal(v1.element("mapSharePanel").hidden, true,
    "visitors never see a presenter sharing panel automatically");
  assert.equal(v1.element("mapShareQR").children.length, 0,
    "QR is generated only on an explicit sharing click");
  v1.element("mapAudienceIntroClose").click();
  assert.equal(v1.element("mapAudienceIntro").hidden, true);
  const v2 = harness(audienceURL, v1.store);
  assert.equal(v2.element("mapAudienceIntro").hidden, true,
    "the same browser session does not repeatedly interrupt exploration");

  const b = harness("https://hinanex-staging.onrender.com/gis/gis/?demo=audience", new Map());
  assert.equal(b.element("mapAudienceIntro").hidden, false);
  assert.equal(b.element("mapSharePanel").hidden, true);
}

// 10/22 guided presentation tour API uses only actual source coordinates;
// it never silently changes selected municipality, D UNKNOWN, GPS or URL.
(async () => {
  const requests = [];
  const tourCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      requests.push(String(url));
      if (String(url).endsWith("edogawa.json")) return { ok: true, json: async () => edogawa };
      if (String(url).endsWith("niigata.json")) return { ok: true, json: async () => niigata };
      if (String(url).endsWith("nagoya.json")) return { ok: true, json: async () => nagoya };
      return { ok: false, status: 404 };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  const tour = tourCase.context.window.HINANEX_PRESENTATION_TOUR;
  assert.ok(tour, "GIS exposes a small presenter-only camera API");
  const view = tourCase.L.__map.lastView;
  const region = tourCase.elements.region.value;
  const url = tourCase.context.window.location.href;
  tour.begin();
  const openingStop = await tour.focus("13123", true, true);
  assert.equal(openingStop.state, "mapped");
  assert.equal(openingStop.focus, "source-example");
  assert.equal(tourCase.L.__map.lastPointFly.zoom, 14,
    "first tour stop zooms into an actual D coordinate rather than the initial regional overview");
  assert.equal(tourCase.L.__map.lastPointFly.latlng[0], edogawa.datasets[0].records[0].latitude);
  assert.equal(tourCase.L.__map.lastPointFly.latlng[1], edogawa.datasets[0].records[0].longitude);
  const niigataStop = await tour.focus("15100", true);
  assert.equal(niigataStop.state, "mapped");
  assert.equal(niigataStop.mapped, 1);
  assert.equal(tourCase.L.__map.lastFly.options.maxZoom, 12);
  assert.equal(tourCase.L.__map.lastFly.options.duration, 1.25);
  assert.equal(tourCase.elements.region.value, region, "tour does not switch manual municipality");
  assert.equal(tourCase.context.window.location.href, url, "tour does not rewrite location");
  const lastFly = tourCase.L.__map.lastFly;
  const nagoyaStop = await tour.focus("23100", true);
  assert.equal(nagoyaStop.state, "unlocated");
  assert.equal(nagoyaStop.mapped, 0);
  assert.equal(nagoyaStop.total, 2, "the source exists but is not geocoded");
  assert.strictEqual(tourCase.L.__map.lastFly, lastFly,
    "unlocated city must not fabricate a camera destination");
  assert.equal(requests.filter(x => x.endsWith("niigata.json")).length, 1);
  tour.halt();
  assert.ok(tourCase.L.__map.stopCalls > 0);
  tour.end(true);
  assert.equal(tourCase.L.__map.lastView.zoom, view.zoom);
  assert.strictEqual(tourCase.L.__map.lastView.latlng, view.latlng,
    "stopping restores the pre-tour map location");
  assert.equal(tourCase.L.__map.minZoom > 4, true,
    "closeup zoom-out floor remains intact");

  let releaseNiigata;
  const lateCase = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      if (String(url).endsWith("niigata.json")) {
        return new Promise(resolve => { releaseNiigata = resolve; });
      }
      if (String(url).endsWith("edogawa.json")) return { ok: true, json: async () => edogawa };
      return { ok: false, status: 404 };
    }
  });
  const lateTour = lateCase.context.window.HINANEX_PRESENTATION_TOUR;
  lateTour.begin();
  const pendingFocus = lateTour.focus("15100", true);
  lateTour.halt();
  releaseNiigata({ ok: true, json: async () => niigata });
  const stale = await pendingFocus;
  assert.equal(stale.state, "cancelled", "in-flight data cannot move a paused demo");
  assert.equal(lateCase.L.__map.lastFly, undefined);
  lateTour.end(false);

  const viewSource = fs.readFileSync(path.resolve(__dirname, "../gis/js/guided_tour.js"), "utf8");
  const html = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const css = fs.readFileSync(path.resolve(__dirname, "../gis/css/map_first.css"), "utf8");
  assert.match(html, /id="mapTourPanel"[^>]*hidden/);
  assert.match(html, /id="mapTourOpen"[^>]*aria-controls="mapTourPanel"/);
  assert.match(html, /js\/guided_tour[.]js[?]v=interactive-presenter-20261014-v1/);
  assert.match(html, /災害予測や避難推奨ではありません/);
  assert.match(viewSource, /mapTourPause/);
  assert.match(viewSource, /prefers-reduced-motion: reduce/);
  assert.match(viewSource, /pointerdown", "wheel", "touchstart"/);
  assert.match(viewSource, /state === "paused"/);
  assert.match(css, /\.map-tour-panel\[hidden\]\{display:none\}/);
  assert.doesNotMatch(viewSource, /getCurrentPosition|geolocation|sendBeacon|setInterval/);
  console.log("Presenter guided tour sources and cancellation: OK");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

// A map move may already be downloading Niigata by the time the presenter
// clicks Start. The tour MUST await that in-flight request: previously
// fetchViewportDOnce returned immediately and the UI said "unavailable".
(async () => {
  let releaseNiigata;
  let niigataRequests = 0;
  const h = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      const u = String(url);
      if (u.endsWith("edogawa.json")) return { ok: true, json: async () => edogawa };
      if (u.endsWith("nagoya.json")) return { ok: true, json: async () => nagoya };
      if (u.endsWith("niigata.json")) {
        niigataRequests++;
        return new Promise(resolve => { releaseNiigata = resolve; });
      }
      return { ok: false, status: 404 };
    }
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  // Triggers normal viewport fetching, which is still in progress.
  h.L.__map.handlers.moveend();
  await new Promise(resolve => setTimeout(resolve, 150));
  assert.equal(niigataRequests, 1);
  const api = h.context.window.HINANEX_PRESENTATION_TOUR;
  api.begin();
  let finished = false;
  const focus = api.focus("15100", true).then(result => {
    finished = true; return result;
  });
  await new Promise(resolve => setTimeout(resolve, 0));
  assert.equal(finished, false,
    "presenter must not skip a region while viewport discovery is still fetching");
  assert.equal(niigataRequests, 1,
    "a concurrent presenter step reuses the existing download");
  releaseNiigata({ ok: true, json: async () => niigata });
  const result = await focus;
  assert.equal(result.state, "mapped");
  assert.equal(result.mapped, 1);
  assert.equal(h.L.__map.lastFly.options.duration, 1.25);
  assert.equal(niigataRequests, 1);
  api.end(false);
  console.log("Concurrent presenter and viewport RegionExport download: OK");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});


// On-map evidence view must separate selected-region D source metrics from
// viewport D points and explicitly verified GSI/official raster status.
{
  const html = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
  const style = fs.readFileSync(path.resolve(__dirname, "../gis/css/map_first.css"), "utf8");
  const source = fs.readFileSync(path.resolve(__dirname, "../gis/js/evidence_sheet.js"), "utf8");
  assert.match(html, /id="mapEvidenceOpen"[^>]*aria-controls="mapEvidencePanel"/);
  assert.match(html, /id="mapEvidencePanel"[^>]*hidden/);
  assert.match(html, /js\/evidence_sheet[.]js[?]v=evidence-sheet-20261010-v1/);
  assert.match(html, /css\/map_first[.]css[?]v=flood-refresh-status-20261015-v1/);
  assert.match(html, /地域の避難施設と国土地理院の公式掲載地点は別情報源/);
  assert.match(style, /\.map-evidence-panel\[hidden\]\{display:none\}/);
  assert.doesNotMatch(source, /fetch\(|getCurrentPosition|geolocation|setView\(|flyTo|sendBeacon/);
  assert.doesNotMatch(source, /innerHTML\s*=/,
    "all source-derived values must be textContent, never injected HTML");

  const nodes = new Map(), documentListeners = {};
  function elem(name) {
    if (nodes.has(name)) return nodes.get(name);
    const attrs = new Map();
    const element = {
      id: name, hidden: false, open: false, textContent: "",
      checked: true, value: "", listeners: {},
      setAttribute(key, value) { attrs.set(key, String(value)); },
      getAttribute(key) {
        if (name === "gisLayout" && key.startsWith("data-")) return "closed";
        return attrs.get(key);
      },
      addEventListener(type, cb) { this.listeners[type] = cb; },
      click() { this.listeners.click?.({ target: this }); },
      contains(target) { return target === this; },
      focus() { this.focused = true; }
    };
    nodes.set(name, element);
    return element;
  }
  elem("mapEvidencePanel").hidden = true;
  elem("mapSettingsPanel").hidden = true;
  elem("mapSharePanel").hidden = true;
  elem("mapTourPanel").hidden = true;
  elem("referenceMapSummary").hidden = true;
  elem("mapRasterBanner").hidden = true;
  elem("region").value = "13123";
  elem("recordCount").textContent = "152";
  elem("mappedCount").textContent = "152";
  elem("missingCoordinateCount").textContent = "0";
  elem("datasetChip").textContent = "D出力読込済";
  elem("officialFlood").checked = true;
  elem("mapViewportDStatus").textContent = "表示範囲のD施設：東京都 江戸川区 50件";
  const document = {
    getElementById: elem,
    addEventListener(name, cb) { documentListeners[name] = cb; }
  };
  vm.runInNewContext(source, { document, console }, { filename: "evidence_sheet.js" });
  elem("mapEvidenceOpen").click();
  assert.equal(elem("mapEvidencePanel").hidden, false);
  assert.equal(elem("mapEvidenceOpen").getAttribute("aria-expanded"), "true");
  assert.match(elem("mapEvidenceRegion").textContent, /東京都 江戸川区/);
  assert.match(elem("mapEvidenceD").textContent, /152件（選択中の地域のみ）/);
  assert.match(elem("mapEvidenceCoordinate").textContent, /座標あり 152件/);
  assert.match(elem("mapEvidenceGSI").textContent, /未照合/);
  assert.match(elem("mapEvidenceFlood").textContent, /タイル全域の取得・精度/);
  assert.match(elem("mapEvidenceViewport").textContent, /50件/);

  // Only a selected-point reference with verified GSI tiles is described
  // as such; it is never conflated with D/municipal coverage.
  elem("referenceMapSummary").hidden = false;
  elem("referenceMapCoverage").textContent = "検証済み 2/4 タイル";
  elem("referenceMapCount").textContent = "119件中 最大5地点";
  elem("region").value = "15100";
  elem("region").listeners.change();
  assert.match(elem("mapEvidenceRegion").textContent, /新潟県 新潟市/);
  assert.match(elem("mapEvidenceGSI").textContent, /検証済み 2\/4 タイル/);
  assert.match(elem("mapEvidenceGSI").textContent, /選択地点周辺の照合済み範囲のみ/);
  elem("recordCount").textContent = "—";
  elem("datasetChip").textContent = "未読込";
  elem("officialFlood").checked = false;
  elem("officialFlood").listeners.change();
  assert.match(elem("mapEvidenceD").textContent, /件数未確認/);
  assert.match(elem("mapEvidenceFlood").textContent, /非表示/);
  elem("officialFlood").checked = true;
  elem("mapRasterBanner").hidden = false;
  elem("officialFlood").listeners.change();
  assert.match(elem("mapEvidenceFlood").textContent, /一部のタイルが未取得/);

  // Menu exclusivity, outside click and keyboard escape must work.
  elem("mapToolMarks").open = true;
  elem("mapToolMarks").listeners.toggle();
  assert.equal(elem("mapEvidencePanel").hidden, true);
  elem("mapEvidenceOpen").click();
  assert.equal(elem("mapToolMarks").open, false);
  documentListeners.click({ target: {} });
  assert.equal(elem("mapEvidencePanel").hidden, true);
  elem("mapEvidenceOpen").click();
  let prevented = false;
  documentListeners.keydown({ key: "Escape", preventDefault() { prevented = true; } });
  assert.equal(prevented, true);
  assert.equal(elem("mapEvidencePanel").hidden, true);
  assert.equal(elem("mapEvidenceOpen").focused, true);
  console.log("On-map evidence statuses and menu dismissal: OK");
}


// GIS may DISPLAY the exact D scenario classification on a pin, but E must
// never infer flood eligibility from raw symbols, supported_disasters or GSI.
(async () => {
  const marked = payload("13123", "東京都江戸川区", [
    record("f1", "D source candidate", 35.7000, 139.8800),
    record("f2", "D source excluded", 35.7001, 139.8801),
    record("f3", "D source unknown", 35.7002, 139.8802)
  ]);
  // Synthetic assessment statuses are provided by a fixture; the map must
  // NOT compute them. Official production exports remain all UNKNOWN.
  marked.scenarios = [{
    scenario_id: "flood_shelter_selection",
    region_code: "13123",
    status: "DEGRADED",
    requirement_assessment: { discovery_status: "PARTIAL" },
    facility_results: [
      { facility_id:"f1", status:"CANDIDATE", fact:{facility_id:"f1",official_status_raw:null} },
      { facility_id:"f2", status:"EXCLUDED", fact:{facility_id:"f2",official_status_raw:null} },
      { facility_id:"f3", status:"UNKNOWN", fact:{facility_id:"f3",official_status_raw:"○"} }
    ]
  }];
  const test = makeContext({
    protocol: "http:",
    fetchImpl: async url => {
      if (String(url).endsWith("edogawa.json"))
        return { ok:true, status:200, json:async () => marked };
      return { ok:false, status:404 };
    }
  });
  await new Promise(r => setTimeout(r, 0));
  const markers = test.L.__groups[1], filter = test.elements.mapDDecisionFilter;
  assert.equal(filter.value, "all");
  assert.equal(markers.items.length, 3);
  assert.match(markers.items[0].options.icon.html, /d-status-candidate/);
  assert.match(markers.items[1].options.icon.html, /d-status-excluded/);
  assert.match(markers.items[2].options.icon.html, /d-status-unknown/);
  assert.doesNotMatch(markers.items[0].options.icon.html, /安全な避難先|開設中/);
  assert.match(test.elements.mapDDecisionFilterStatus.textContent, /2件が分類済み／1件が未判定/);
  const sourceCount = test.elements.recordCount.textContent;
  const originView = test.L.__map.lastView;
  filter.value = "classified";
  filter.listeners.change({target:filter});
  assert.equal(markers.items.length, 2);
  assert.ok(markers.items.every(m => /d-status-(candidate|excluded)/.test(m.options.icon.html)));
  assert.equal(test.elements.recordCount.textContent, sourceCount, "filter cannot alter D dataset count");
  assert.strictEqual(test.L.__map.lastView, originView, "filter cannot recenter user's map");
  filter.value = "unclassified";
  filter.listeners.change({target:filter});
  assert.equal(markers.items.length, 1);
  assert.match(markers.items[0].options.icon.html, /d-status-unknown/);
  markers.items[0].handlers.click({});
  assert.match(test.elements.details.innerHTML, /洪水対応分類/);
  assert.match(test.elements.details.innerHTML, /未判定/);
  filter.value = "all";
  filter.listeners.change({target:filter});
  assert.equal(markers.items.length, 3);

  test.L.__map.zoom = 9;
  test.L.__map.handlers.zoomend();
  assert.equal(markers.items.length, 1, "mixed statuses may visually cluster at low zoom");
  assert.match(markers.items[0].options.icon.html, /d-status-mixed/);
  assert.match(markers.items[0].options.icon.html, /分類済み2件・未判定1件/);
  filter.value = "classified";
  filter.listeners.change({target:filter});
  assert.equal(markers.items.length, 1);
  assert.match(markers.items[0].options.icon.html, /d-status-classified/);
  filter.value = "unclassified";
  filter.listeners.change({target:filter});
  assert.equal(markers.items.length, 1);
  assert.match(markers.items[0].options.icon.html, /d-status-unknown/);

  // Existing real-source-shaped fixture has no accepted per-site Scenario.
  // No data -> UNKNOWN, not a positive candidate nor a zero-site claim.
  const noDecision = makeContext({
    protocol:"http:",
    fetchImpl: async url => String(url).endsWith("edogawa.json")
      ? {ok:true, status:200, json:async () => edogawa}
      : {ok:false,status:404}
  });
  await new Promise(r => setTimeout(r, 0));
  noDecision.elements.mapDDecisionFilter.value = "classified";
  noDecision.elements.mapDDecisionFilter.listeners.change({});
  assert.equal(noDecision.L.__groups[1].items.length, 0);
  assert.match(noDecision.elements.mapDDecisionFilterStatus.textContent, /この出典には判定済み施設がありません/);
  assert.match(noDecision.elements.mapDDecisionFilterStatus.textContent, /避難施設が存在しないという意味ではありません/);
  assert.equal(noDecision.elements.recordCount.textContent, 2);
  assert.equal(noDecision.L.__groups[3].items.length, 0, "no GSI marks may be fabricated");

  // Auto-discovered D from a different region obeys the same filter but is
  // still NOT turned into GSI's independently verified purple markers.
  const other = payload("15100","新潟県新潟市",[
    record("n1","Niigata classified",37.9,139.02),
    record("n2","Niigata unknown",37.9001,139.0201)
  ]);
  other.scenarios = [{
    scenario_id:"flood_shelter_selection",region_code:"15100",status:"DEGRADED",
    facility_results:[
      {facility_id:"n1",status:"EXCLUDED",fact:{facility_id:"n1"}},
      {facility_id:"n2",status:"UNKNOWN",fact:{facility_id:"n2"}}
    ]
  }];
  const moving = makeContext({
    protocol:"http:",
    fetchImpl: async url => String(url).endsWith("edogawa.json")
      ? {ok:true,status:200,json:async () => edogawa}
      : String(url).endsWith("niigata.json")
        ? {ok:true,status:200,json:async () => other}
        : {ok:false,status:404}
  });
  await new Promise(r => setTimeout(r, 0));
  moving.L.__map.zoom = 13;
  moving.L.__map.viewportLimits = {south:37.75,north:38.2,west:138.9,east:139.25};
  moving.L.__map.handlers.moveend();
  await new Promise(r => setTimeout(r, 155));
  assert.equal(moving.L.__groups[4].items.length, 2);
  moving.elements.mapDDecisionFilter.value = "classified";
  moving.elements.mapDDecisionFilter.listeners.change({});
  assert.equal(moving.L.__groups[4].items.length, 1);
  assert.match(moving.L.__groups[4].items[0].options.icon.html, /d-status-excluded/);
  assert.match(moving.elements.mapViewportDStatus.textContent, /絞込中/);
  assert.equal(moving.L.__groups[3].items.length, 0);

  const page = fs.readFileSync(path.resolve(__dirname,"../gis/index.html"),"utf8");
  const css = fs.readFileSync(path.resolve(__dirname,"../gis/css/map_first.css"),"utf8");
  assert.match(page,/id="mapDDecisionFilter"/);
  assert.match(page,/value="classified"/);
  assert.match(page,/value="unclassified"/);
  assert.match(page,/zoom-compact-popup-20261014-v1/);
  assert.match(css,/\.shelter-icon\.d-status-unknown/);
  assert.match(css,/\.d-facility-cluster\.d-status-mixed/);
  console.log("D flood assessment display-only filter and legend: OK");
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});

// Run the new data-safe three-case playback comparison checks in the existing
// required GIS controller CI job without modifying shared workflow ownership.
require("./guided_tour_compare.test.js");

// Presenter regression on actual D adapter + Leaflet-stub marker membership.
(async()=>{
 const d=payload("13123","東京都江戸川区",[
   record("f1","東小学校",35.70,139.88,"https://example.invalid/f1"),
   record("f2","西小学校",35.71,139.89),
   record("f3","中央体育館",35.72,139.90)
 ]);
 const t=makeContext({protocol:"http:",fetchImpl:async u=>String(u).endsWith("edogawa.json")
   ? {ok:true,status:200,json:async()=>d} : {ok:false,status:404}});
 await new Promise(r=>setTimeout(r,0));
 const api=t.context.window.HINANEX_FACILITY_PRESENTER;
 const markers=t.L.__groups[1],before=t.L.__map.getCenter();
 assert.equal(markers.items.length,3);
 const loaded=await api.begin();
 assert.equal(loaded.state,"ready");
 assert.equal(loaded.mapped,3);
 assert.equal(loaded.matches,2);
 assert.equal(loaded.classified,0);
 assert.match(loaded.criterion,/小学校/);
 api.apply();
 assert.equal(markers.items.length,2,"real marker group must be filtered");
 assert.equal(t.elements.recordCount.textContent,3,"never modify total source count");
 const f=api.inspect();
 assert.match(f.name,/小学校/);
 assert.match(f.criterionValue,/小学校/);
 assert.equal(f.decision,"UNKNOWN");
 assert.equal(t.L.__map.lastPointFly.zoom,14);
 api.end(true);
 assert.equal(markers.items.length,3,"restore real D layer");
 assert.deepEqual(t.L.__map.getCenter(),before);
 assert.equal(t.L.__groups[3].items.length,0,"no fabricated GSI markers");
 const s=payload("13123","東京都江戸川区",[
   record("a1","A",35.70,139.88),record("a2","B",35.71,139.89),
   record("a3","C",35.72,139.90)
 ]);
 s.scenarios=[{scenario_id:"flood_shelter_selection",region_code:"13123",status:"DEGRADED",
   facility_results:[
     {facility_id:"a1",status:"CANDIDATE",fact:{facility_id:"a1",official_status_raw:"○",source_record_trace:"row 1"}},
     {facility_id:"a2",status:"EXCLUDED",fact:{facility_id:"a2",official_status_raw:"×"}},
     {facility_id:"a3",status:"UNKNOWN",fact:{facility_id:"a3"}}
   ]}];
 const v=makeContext({protocol:"http:",fetchImpl:async u=>String(u).endsWith("edogawa.json")
   ? {ok:true,status:200,json:async()=>s} : {ok:false,status:404}});
 await new Promise(r=>setTimeout(r,0));
 const api2=v.context.window.HINANEX_FACILITY_PRESENTER;
 const cls=await api2.begin();
 assert.equal(cls.criterionKind,"classification");
 assert.equal(cls.matches,2);
 api2.apply();
 assert.equal(v.L.__groups[1].items.length,2);
 assert.equal(api2.inspect().sourceTrace,"row 1");
 api2.end(false);
 const no=payload("13123","東京都江戸川区",[
   record("z1","A",35.70,139.88),record("z2","B",35.71,139.89)
 ]);
 const u=makeContext({protocol:"http:",fetchImpl:async url=>String(url).endsWith("edogawa.json")
   ? {ok:true,status:200,json:async()=>no} : {ok:false,status:404}});
 await new Promise(r=>setTimeout(r,0));
 assert.equal((await u.context.window.HINANEX_FACILITY_PRESENTER.begin()).state,"no-distinguishing-condition");
 u.context.window.HINANEX_FACILITY_PRESENTER.end();
 console.log("E condition-based D facility presenter true marker filter and source matching: OK");
})().catch(e=>{console.error(e);process.exitCode=1;});
require("./filter_demo.test.js");
require("./gsi_flood_demo.test.js");
