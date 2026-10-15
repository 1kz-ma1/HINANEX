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

// Target-first wheel zoom: coalesce a short gesture into one Leaflet target
// zoom rather than scheduling base-map image requests at passing zoom levels.
// Keep pinch and explicit zoom controls in Leaflet. Normal continuous wheel
// bursts instead resolve to one camera destination/animation per gesture.
// Sensitivity stays 3.75×. ?zoomFeel=native preserves the immediately previous
// target-first Leaflet handler; other historical A/B modes remain available.
const zoomFeelMode = new URL(window.location.href).searchParams.get("zoomFeel");
const previousZoomFeel = zoomFeelMode === "previous";
const slowZoomFeel = zoomFeelMode === "slow";
const progressiveZoomFeel = zoomFeelMode === "progressive";
const singleTargetWheel = !["native", "previous", "slow", "progressive"].includes(zoomFeelMode);
const legacyWheelPreview = zoomFeelMode === "preview135";
const legacyWholePanePreview = zoomFeelMode === "preview135" || zoomFeelMode === "wholePane";
// Persist only gesture preferences in this browser. Never persist map/GPS
// coordinates, source data, or disaster/safety assessments.
const GESTURE_PREF_KEY = "hinanex.gis.gesture.v2";
const LEGACY_GESTURE_PREF_KEY = "hinanex.gis.gesture.v1";
const DEFAULT_WHEEL_SENSITIVITY = 3.75;
// Enough to collect a short wheel burst before Leaflet's single target zoom;
// measured smoothness/latency still needs real-device visual acceptance.
const WHEEL_DEBOUNCE_MS = 135;
function normalizeWheelSensitivity(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return DEFAULT_WHEEL_SENSITIVITY;
  return Math.round(Math.max(0.5, Math.min(5, number)) * 4) / 4;
}
function normalizeZoomStyle(value) {
  return value === "steps" ? "steps" : "continuous";
}
function readGesturePrefs() {
  try {
    const current = JSON.parse(window.localStorage?.getItem(GESTURE_PREF_KEY) || "null");
    if (current && typeof current === "object") return {
      sensitivity: normalizeWheelSensitivity(current.sensitivity),
      style: normalizeZoomStyle(current.style)
    };
    const legacy = JSON.parse(window.localStorage?.getItem(LEGACY_GESTURE_PREF_KEY) || "null");
    if (legacy && typeof legacy === "object") {
      // The former default was 1.5. Users who never changed that baseline
      // should experience the newly requested 3.75 default after upgrading.
      // Deliberately customized wheel speeds/step style remain opt-in.
      const oldSensitivity = Number(legacy.sensitivity);
      return {
        sensitivity: oldSensitivity === 1.5
          ? DEFAULT_WHEEL_SENSITIVITY : normalizeWheelSensitivity(oldSensitivity),
        style: normalizeZoomStyle(legacy.style)
      };
    }
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
  wheelDebounceTime: slowZoomFeel ? 55 : previousZoomFeel ? 40
    : progressiveZoomFeel ? 80 : WHEEL_DEBOUNCE_MS,
  zoomAnimation: true,
  // A fast wheel burst may cover more than Leaflet's default 4 zoom levels;
  // allow a slightly larger transition before falling back to an instant jump.
  zoomAnimationThreshold: 5
}).setView([35.704, 139.882], 13);

// Instant visual feedback, deferred native tile resolution.
// Each ordinary wheel event only GPU-scales the *existing map pane*: no
// intermediate GSI or official flood raster requests, no new geographic facts.
// Once the wheel burst is quiet, commit one bounded Leaflet zoom at the same
// pointer anchor and remove the temporary visual transform in the same frame.
// Pinch, map controls, popup scrolling and explicitly stepped zoom stay native.
// Shorten only the custom preview's idle-to-commit delay: tile fetches can
// start sooner. Native wheel / stepped / pinch remain unchanged. The previous
// 135ms preview stays accessible for direct comparison.
const WHEEL_GESTURE_IDLE_MS = legacyWheelPreview ? 135 : 70;
const WHEEL_PREVIEW_TRANSITION_MS = legacyWheelPreview ? 65 : 40;
const MAX_WHEEL_PREVIEW_LEVELS = 2.75;
let pendingWheelPixels = 0;
let pendingWheelPoint = null;
let wheelGestureTimer = null;
let wheelPreview = null;
let wheelIntentStartedAt = null;

function singleTargetZoomChange(pixels) {
  const d = Math.abs(pixels) / (map.options.wheelPxPerZoomLevel * 4);
  const raw = Math.sign(pixels) * 4 * Math.log2(2 / (1 + Math.exp(-d)));
  return Math.max(-MAX_WHEEL_PREVIEW_LEVELS,
    Math.min(MAX_WHEEL_PREVIEW_LEVELS, raw));
}
function wheelDestinationZoom() {
  const base = map.getZoom();
  return Math.max(map.getMinZoom(),
    Math.min(map.getMaxZoom(), base + singleTargetZoomChange(pendingWheelPixels)));
}
// Scale geographic raster panes only; NEVER scale Leaflet marker, popup,
// boundary, control, tooltip or cluster panes with the image.
const RASTER_HOLD_MAX_MS = 1100;
const FLOOD_RASTER_HOLD_MAX_MS = 650;
const RASTER_FADE_MS = 120;
// Destination-only cache warm-up: at most eight already-authorized GSI
// background tiles per wheel burst. No intermediate zoom levels or hazard
// raster prefetch, no user GPS, no RegionExport changes.
const GSI_PREFETCH_MAX_TILES = 8;
const GSI_PREFETCH_PAUSE_MS = 28;
const GSI_PREFETCH_KEEP_MS = 1500;
const GSI_PREFETCH_ROOT = "https://cyberjapandata.gsi.go.jp/xyz/std";
let predictedTileTimer = null;
let predictedTileReleaseTimer = null;
let predictedTileImages = new Map();
let predictedTileZoom = null;
function clearPredictedTileTimer() {
  if (predictedTileTimer !== null) clearTimeout(predictedTileTimer);
  predictedTileTimer = null;
}
function discardPredictedTiles() {
  clearPredictedTileTimer();
  if (predictedTileReleaseTimer !== null) clearTimeout(predictedTileReleaseTimer);
  predictedTileReleaseTimer = null;
  predictedTileImages.clear();
  predictedTileZoom = null;
}
function predictedGsiTileCoords() {
  const point = pendingWheelPoint;
  if (!point || typeof map.containerPointToLatLng !== "function" ||
      typeof map.getSize !== "function") return [];
  const targetZoom = wheelDestinationZoom();
  if (!Number.isFinite(targetZoom)) return [];
  const z = Math.max(2, Math.min(18, Math.round(targetZoom)));
  const anchor = map.containerPointToLatLng(point);
  const projected = map.project(anchor,z);
  const size = map.getSize();
  if (!projected || !Number.isFinite(projected.x) ||
      !Number.isFinite(projected.y) || !size?.x || !size?.y) return [];
  const ratio = Math.pow(2,z-targetZoom);
  const left = projected.x-point.x*ratio;
  const top = projected.y-point.y*ratio;
  const right = left+size.x*ratio;
  const bottom = top+size.y*ratio;
  const maxIndex = Math.pow(2,z);
  const candidates = [];
  // Round only the selected final tile-zoom, never every crossed zoom.
  const xStart=Math.floor(left/256),xEnd=Math.floor(right/256);
  const yStart=Math.max(0,Math.floor(top/256));
  const yEnd=Math.min(maxIndex-1,Math.floor(bottom/256));
  for (let y=yStart;y<=yEnd;y++) for(let x=xStart;x<=xEnd;x++) {
    const normalizedX = ((x%maxIndex)+maxIndex)%maxIndex;
    const distance = Math.pow(x*256+128-(left+right)/2,2)
      + Math.pow(y*256+128-(top+bottom)/2,2);
    candidates.push({x:normalizedX,y,z,distance});
  }
  return candidates.sort((a,b)=>a.distance-b.distance)
    .slice(0,GSI_PREFETCH_MAX_TILES);
}
// Screen-complete target imagery handoff for significant zoom-outs.
// The old 8-tile warmup accelerates common requests but is not sufficient
// evidence that the whole destination viewport is covered. This grid is
// computed only at the *final* zoom, from Leaflet's projected source position.
// Do not repeat/extrapolate tiles beyond official Web-Mercator coverage.
const TARGET_COVER_MAX_TILES = 48;
const TARGET_COVER_WAIT_MS = 650;
const TARGET_COVER_HOLD_MS = 1300;
const TARGET_COVER_FADE_MS = 120;
let targetCoverGeneration = 0;
let targetCover = null;
function destinationTileGrid(point, targetZoom) {
  if (!point || !Number.isFinite(targetZoom) ||
      typeof map.containerPointToLatLng !== "function" ||
      typeof map.getSize !== "function") return null;
  const size = map.getSize();
  if (!(size?.x > 0 && size?.y > 0)) return null;
  const tileZoom = Math.max(2, Math.min(18, Math.round(targetZoom)));
  const geographicPoint = map.containerPointToLatLng(point);
  const projected = map.project(geographicPoint, tileZoom);
  if (!Number.isFinite(projected?.x) || !Number.isFinite(projected?.y)) return null;
  const ratio = Math.pow(2, tileZoom - targetZoom);
  const left = projected.x - point.x * ratio;
  const top = projected.y - point.y * ratio;
  const right = left + size.x * ratio;
  const bottom = top + size.y * ratio;
  const worldTileCount = Math.pow(2, tileZoom);
  const xStart = Math.floor(left / 256);
  const xEnd = Math.floor((right - 0.001) / 256);
  const yStart = Math.floor(top / 256);
  const yEnd = Math.floor((bottom - 0.001) / 256);
  const tileCount = (xEnd - xStart + 1) * (yEnd - yStart + 1);
  // Above/below world bounds, or extremely large screens: do not claim
  // geographic image coverage that the official map does not provide.
  if (tileCount < 1 || tileCount > TARGET_COVER_MAX_TILES ||
      yStart < 0 || yEnd >= worldTileCount) return null;
  const tiles = [];
  for (let y = yStart; y <= yEnd; y++) {
    for (let x = xStart; x <= xEnd; x++) {
      const wrappedX = ((x % worldTileCount) + worldTileCount) % worldTileCount;
      tiles.push({
        url: `${GSI_PREFETCH_ROOT}/${tileZoom}/${wrappedX}/${y}.png`,
        left: (x * 256 - left) / ratio,
        top: (y * 256 - top) / ratio,
        size: 256 / ratio
      });
    }
  }
  return {tiles, width:size.x, height:size.y};
}
function removeTargetCover() {
  if (!targetCover) return;
  clearTimeout(targetCover.timeout);
  targetCover.layer?.off?.("load", targetCover.finish);
  targetCover.node?.remove?.();
  targetCover = null;
}
function positionTargetCover() {
  if (!targetCover) return;
  const {node, pane} = targetCover;
  const a = map.getContainer()?.getBoundingClientRect?.();
  const p = pane.getBoundingClientRect?.();
  if (!a || !p) return;
  node.style.left = `${a.left - p.left}px`;
  node.style.top = `${a.top - p.top}px`;
}
function presentTargetCover(grid, images) {
  if (typeof document.createElement !== "function" ||
      typeof map.createPane !== "function") return false;
  let pane = map.getPane?.("wheelCoverPane");
  if (!pane) {
    map.createPane("wheelCoverPane");
    pane = map.getPane?.("wheelCoverPane");
  }
  if (!pane?.appendChild) return false;
  removeTargetCover();
  pane.style.zIndex = "205"; // above GSI base, BELOW official flood and points
  pane.style.pointerEvents = "none";
  const node = document.createElement("div");
  node.className = "hinanex-target-tile-cover";
  node.setAttribute("aria-hidden","true");
  Object.assign(node.style, {
    position:"absolute",width:`${grid.width}px`,height:`${grid.height}px`,
    overflow:"hidden",pointerEvents:"none",zIndex:"1"
  });
  // One decoded, authorized official tile per *distinct geographic tile*.
  // No stretching an unrelated old tile to fabricate new map coverage.
  for (let i=0; i<grid.tiles.length; i++) {
    const tile = grid.tiles[i];
    const img = document.createElement("img");
    Object.assign(img.style,{
      position:"absolute",left:`${tile.left}px`,top:`${tile.top}px`,
      width:`${tile.size}px`,height:`${tile.size}px`,
      maxWidth:"none",pointerEvents:"none"
    });
    img.alt = "";
    img.src = tile.url;
    node.appendChild(img);
  }
  pane.appendChild(node);
  const entry = {node,pane,layer:baseMap,timeout:null,finish:null};
  targetCover = entry;
  positionTargetCover();
  let finished = false;
  entry.finish = () => {
    if (finished) return;
    finished = true;
    entry.layer.off?.("load",entry.finish);
    clearTimeout(entry.timeout);
    node.style.transition = `opacity ${TARGET_COVER_FADE_MS}ms ease-out`;
    node.style.opacity = "0";
    entry.timeout = setTimeout(() => {
      if (targetCover === entry) removeTargetCover();
    }, TARGET_COVER_FADE_MS + 25);
  };
  entry.layer.on?.("load", entry.finish);
  entry.timeout = setTimeout(entry.finish, TARGET_COVER_HOLD_MS);
  return true;
}
function prepareTargetCover(point,targetZoom,generation,done) {
  // No source-safe complete atlas possible: retain normal Leaflet rendering,
  // never create filled/incorrect geographic imagery.
  const grid = targetZoom < map.getZoom() - 0.15 ?
    destinationTileGrid(point,targetZoom) : null;
  if (!grid || !grid.tiles.length ||
      typeof window.Image !== "function" ||
      typeof document.createElement !== "function") {
    done(false);
    return;
  }
  const images = grid.tiles.map(tile => {
    let image = predictedTileImages.get(tile.url);
    if (!image) {
      image = new window.Image();
      image.decoding = "async";
      predictedTileImages.set(tile.url,image);
      image.src = tile.url;
    }
    return image;
  });
  let complete = false;
  const finish = ok => {
    if (complete) return;
    complete = true;
    clearTimeout(timeout);
    for (const [img,loaded,failed] of listeners) {
      img.removeEventListener?.("load",loaded);
      img.removeEventListener?.("error",failed);
    }
    if (generation === targetCoverGeneration) {
      if (ok) presentTargetCover(grid,images);
      done(ok);
    }
  };
  const listeners = [];
  let awaiting = 0, failed = false;
  for (const image of images) {
    if (image.complete && image.naturalWidth > 0) continue;
    if (image.complete && image.naturalWidth === 0) {
      failed = true;break;
    }
    if (typeof image.addEventListener !== "function") {
      failed = true;break;
    }
    awaiting++;
    const loaded = () => { awaiting--; if (!awaiting) finish(!failed); };
    const error = () => {failed=true;finish(false);};
    image.addEventListener("load",loaded);
    image.addEventListener("error",error);
    listeners.push([image,loaded,error]);
  }
  const timeout = setTimeout(() => finish(false),TARGET_COVER_WAIT_MS);
  if (failed || !awaiting) finish(!failed);
}

function warmPredictedTiles() {
  predictedTileTimer = null;
  // The browser must use the *same* GSI URL and image request mode as the
  // existing Leaflet TileLayer for shared HTTP caching.
  const ImageCtor = window.Image;
  if (typeof ImageCtor !== "function") return;
  const coords = predictedGsiTileCoords();
  if (!coords.length || (predictedTileZoom !== null &&
      predictedTileZoom !== coords[0].z)) return;
  if (predictedTileZoom === null) predictedTileZoom = coords[0].z;
  let started=0;
  for(const tile of coords) {
    if(predictedTileImages.size>=GSI_PREFETCH_MAX_TILES)break;
    const url = `${GSI_PREFETCH_ROOT}/${tile.z}/${tile.x}/${tile.y}.png`;
    if(predictedTileImages.has(url))continue;
    const image = new ImageCtor();
    image.decoding="async";
    predictedTileImages.set(url,image);
    image.src=url;
    started++;
  }
  if(debugMapPerf && started)
    console.info("[HINANEX map perf] destination tile prefetch",
      {count:started,total:predictedTileImages.size});
}
function schedulePredictedTileWarmup() {
  clearPredictedTileTimer();
  if(predictedTileImages.size>=GSI_PREFETCH_MAX_TILES)return;
  predictedTileTimer=setTimeout(warmPredictedTiles,GSI_PREFETCH_PAUSE_MS);
}
function keepPredictedTileCache() {
  clearPredictedTileTimer();
  if(predictedTileReleaseTimer!==null)clearTimeout(predictedTileReleaseTimer);
  predictedTileReleaseTimer=setTimeout(()=>{
    predictedTileImages.clear();
    predictedTileZoom=null;
    predictedTileReleaseTimer=null;
  },GSI_PREFETCH_KEEP_MS);
}

let retainedRaster = [];
let committingWheelZoom = false;
function discardRetainedRaster() {
  for (const entry of retainedRaster.splice(0)) {
    clearTimeout(entry.maxTimer);
    clearTimeout(entry.fadeTimer);
    entry.layer?.off?.("load", entry.release);
    entry.ghost?.remove?.();
  }
}
function rasterTargets() {
  if (legacyWholePanePreview) {
    const pane = map.getPanes?.().mapPane;
    return pane ? [{pane, layer:null, legacy:true}] : [];
  }
  return [
    {pane:map.getPane?.("tilePane") || map.getPanes?.().tilePane,layer:baseMap},
    {pane:map.getPane?.("officialFloodPane"),layer:officialFloodLayer,flood:true}
  ].filter(item => item.pane?.style);
}
function copyRenderedRaster(layer) {
  const source = layer?.getContainer?.();
  if (!source?.cloneNode || !source.parentElement) return null;
  // Clones only already displayed, verified raster layers. No marker clones,
  // simulated risk colors, CSS text, or new tile URL construction.
  const ghost = source.cloneNode(true);
  ghost.removeAttribute?.("id");
  ghost.querySelectorAll?.("[id]").forEach(el => el.removeAttribute("id"));
  ghost.setAttribute?.("aria-hidden","true");
  ghost.classList?.add("hinanex-raster-retained");
  ghost.style.pointerEvents = "none";
  ghost.style.userSelect = "none";
  ghost.style.zIndex = "999";
  source.parentElement.appendChild(ghost);
  return ghost;
}
function restoreWheelPreview() {
  if (!wheelPreview) return [];
  const previews = wheelPreview.targets;
  for (const {pane,original} of previews) {
    pane.style.scale = original.scale;
    pane.style.transformOrigin = original.transformOrigin;
    pane.style.transition = original.transition;
    pane.style.willChange = original.willChange;
  }
  wheelPreview = null;
  return previews;
}
function clearPendingWheel() {
  targetCoverGeneration++;
  removeTargetCover();
  if (wheelGestureTimer !== null) clearTimeout(wheelGestureTimer);
  wheelGestureTimer = null;
  restoreWheelPreview().forEach(({ghost}) => ghost?.remove?.());
  pendingWheelPixels = 0;
  pendingWheelPoint = null;
  wheelIntentStartedAt = null;
  discardRetainedRaster();
  discardPredictedTiles();
}
// For zoom-outs, old loaded tiles do not necessarily cover newly exposed
// geography. Limit the cosmetic shrink to coverage actually present, while
// waiting for the full, geographically correct destination atlas.
function oldRasterCoverage() {
  const container = baseMap?.getContainer?.();
  const tiles = container?.querySelectorAll?.("img.leaflet-tile-loaded");
  if (!tiles) return null;
  const boxes = Array.from(tiles).map(el => el.getBoundingClientRect?.())
    .filter(rect => rect && rect.width > 0 && rect.height > 0);
  if (!boxes.length) return {missing:true};
  return {
    left:Math.min(...boxes.map(r=>r.left)),
    top:Math.min(...boxes.map(r=>r.top)),
    right:Math.max(...boxes.map(r=>r.right)),
    bottom:Math.max(...boxes.map(r=>r.bottom))
  };
}
function coverageLimitedScale(wanted, coverage, origin, viewport) {
  if (!(wanted < 1) || !coverage || !viewport || !origin) return wanted;
  if (coverage.missing) return 1;
  // This is a conservative rectangular screen-envelope bound. The loaded
  // image grid may have internal holes; full final coverage still requires
  // the actual destination atlas, not this rough preview limit.
  const covers = scale =>
    origin.x+(coverage.left-origin.x)*scale <= viewport.left+1 &&
    origin.x+(coverage.right-origin.x)*scale >= viewport.right-1 &&
    origin.y+(coverage.top-origin.y)*scale <= viewport.top+1 &&
    origin.y+(coverage.bottom-origin.y)*scale >= viewport.bottom-1;
  if (!covers(1)) return 1;
  if (covers(wanted)) return wanted;
  let low=wanted, high=1;
  for(let i=0;i<14;i++){
    const mid=(low+high)/2;
    if(covers(mid)) high=mid; else low=mid;
  }
  return high;
}

function updateWheelPreview(event) {
  if (!wheelPreview) {
    discardRetainedRaster();
    const targets = [];
    for (const item of rasterTargets()) {
      const pane = item.pane;
      if (!pane?.style || !("scale" in pane.style) ||
          !pane.getBoundingClientRect) continue;
      const rect = pane.getBoundingClientRect();
      const x = Number(event.clientX) - rect.left;
      const y = Number(event.clientY) - rect.top;
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
      const original = {
        scale:pane.style.scale,transformOrigin:pane.style.transformOrigin,
        transition:pane.style.transition,willChange:pane.style.willChange
      };
      const ghost = item.legacy ? null : copyRenderedRaster(item.layer);
      targets.push({...item,ghost,original});
      pane.style.transformOrigin = `${x}px ${y}px`;
      pane.style.transition = `scale ${WHEEL_PREVIEW_TRANSITION_MS}ms ease-out`;
      pane.style.willChange = "scale";
    }
    if (!targets.length) return; // Unsupported CSS scale: safe native commit.
    const viewport = map.getContainer()?.getBoundingClientRect?.();
    wheelPreview = {
      targets,
      coverage:oldRasterCoverage(),
      viewport,
      origin:{x:Number(event.clientX),y:Number(event.clientY)}
    };
  }
  const change = wheelDestinationZoom() - map.getZoom();
  const wanted = Math.pow(2,change);
  const displayed = coverageLimitedScale(wanted,
    wheelPreview.coverage,wheelPreview.origin,wheelPreview.viewport);
  const visualScale = String(Number(displayed.toFixed(5)));
  for (const {pane} of wheelPreview.targets) pane.style.scale = visualScale;
}
function retainUntilRasterReady(previews) {
  for (const item of previews) {
    const {ghost,pane,layer,flood} = item;
    if (!ghost || !layer) continue;
    // Preserve the current raster frame while Leaflet commits geographic zoom.
    // A ghost is scoped to its original *raster* pane, underneath real markers.
    const before = ghost.getBoundingClientRect?.();
    ghost.style.scale = pane.style.scale || "1";
    ghost.style.transformOrigin = pane.style.transformOrigin;
    // Do not leave stale official imagery over updated hazard tiles indefinitely.
    const entry = {ghost,layer,release:null,maxTimer:null,fadeTimer:null};
    let released = false;
    entry.release = () => {
      if (released) return;
      released = true;
      layer.off?.("load",entry.release);
      clearTimeout(entry.maxTimer);
      ghost.style.transition = `opacity ${RASTER_FADE_MS}ms ease-out`;
      ghost.style.opacity = "0";
      entry.fadeTimer = setTimeout(() => {
        ghost.remove?.();
        retainedRaster = retainedRaster.filter(value=>value!==entry);
      },RASTER_FADE_MS+20);
    };
    entry.maxTimer = setTimeout(entry.release,
      flood ? FLOOD_RASTER_HOLD_MAX_MS : RASTER_HOLD_MAX_MS);
    layer.on?.("load",entry.release);
    retainedRaster.push(entry);
    // Reconcile the old pane's Leaflet translation after setZoomAround. An
    // optional pre-commit bounding box is retained for the following tick.
    entry.before = before;
  }
}
function alignRetainedRaster() {
  for (const entry of retainedRaster) {
    const before=entry.before;
    const after=entry.ghost?.getBoundingClientRect?.();
    if (!before || !after) continue;
    const dx=before.left-after.left,dy=before.top-after.top;
    if (Number.isFinite(dx)&&Number.isFinite(dy))
      entry.ghost.style.translate = `${dx}px ${dy}px`;
    // Cached tiles may already have completed synchronously.
    setTimeout(() => {
      if (!entry.layer?.isLoading?.()) entry.release();
    },90);
  }
}
function flushSingleTargetWheel() {
  if (wheelGestureTimer !== null) clearTimeout(wheelGestureTimer);
  wheelGestureTimer = null;
  const point = pendingWheelPoint;
  const targetZoom = wheelDestinationZoom();
  const startedAt = wheelIntentStartedAt;
  const generation = ++targetCoverGeneration;
  // Begin official final-level downloads BEFORE replacing old imagery.
  // On slow/no coverage, fall back to the existing bounded Leaflet path.
  prepareTargetCover(point,targetZoom,generation,covered => {
    if (generation !== targetCoverGeneration) return;
    wheelIntentStartedAt = null;
    keepPredictedTileCache();
    const previews = wheelPreview?.targets || [];
    const scales = previews.map(({pane}) => pane.style.scale);
    const origins = previews.map(({pane}) => pane.style.transformOrigin);
    restoreWheelPreview();
    pendingWheelPixels = 0;
    pendingWheelPoint = null;
    if (!point || Math.abs(targetZoom - map.getZoom()) < 0.001) {
      previews.forEach(({ghost}) => ghost?.remove?.());
      removeTargetCover();
      return;
    }
    previews.forEach((item,i) => {
      if (item.ghost) {
        item.ghost.style.scale = scales[i];
        item.ghost.style.transformOrigin = origins[i];
        // A complete, geographically aligned destination grid replaces the
        // old BACKGROUND clone. Flood uses its independent source/cap.
        if (covered && item.layer === baseMap) {
          item.ghost.remove?.();
          item.ghost = null;
        }
        // An old flood image belongs to the *prior geographic view*. Never
        // retain it through the new Leaflet zoom, where colors might appear
        // at an incorrect coordinate. Show a visible "updating / unverified"
        // state until official tile loading settles instead.
        if (item.flood) {
          item.ghost.remove?.();
          item.ghost = null;
        }
      }
    });
    retainUntilRasterReady(previews);
    committingWheelZoom = true;
    try { map.setZoomAround(point,targetZoom,{animate:false}); }
    finally { committingWheelZoom = false; }
    positionTargetCover();
    alignRetainedRaster();
    if (debugMapPerf && startedAt !== null) {
      console.info("[HINANEX map perf] wheel intent-to-commit",{
        delayMs:Math.round(perfTime()-startedAt),
        idleMs:WHEEL_GESTURE_IDLE_MS,
        fullTargetCover:covered,
        mode:zoomFeelMode || "preview-fast"
      });
    }
  });
}
function captureSingleTargetWheel(event) {
  if (!singleTargetWheel || gesturePrefs.style === "steps" ||
      event.ctrlKey || event.metaKey) return;
  if (event.target?.closest?.(
    ".leaflet-popup, .leaflet-control, .map-settings-sheet, " +
    "input, select, textarea, [data-wheel-scroll]")) return;
  const rawDelta = Number(event.deltaY);
  if (!Number.isFinite(rawDelta) || rawDelta === 0) return;
  event.preventDefault();
  event.stopImmediatePropagation?.();
  const scale = event.deltaMode === 1 ? 20 : event.deltaMode === 2 ? 60 : 1;
  if (!pendingWheelPoint) {
    // New gesture, new bounded budget. Previous prefetched images have already
    // served (or expired) and must not prevent warmup at another destination.
    discardPredictedTiles();
    // A new independent gesture invalidates any old base-map cover. Otherwise
    // a stale, fully opaque atlas would hide the next instantaneous preview.
    removeTargetCover();
    pendingWheelPoint = map.mouseEventToContainerPoint(event);
    wheelIntentStartedAt = perfTime();
  }
  targetCoverGeneration++;
  pendingWheelPixels += -rawDelta * scale;
  updateWheelPreview(event);
  schedulePredictedTileWarmup();
  if (wheelGestureTimer !== null) clearTimeout(wheelGestureTimer);
  wheelGestureTimer = setTimeout(flushSingleTargetWheel, WHEEL_GESTURE_IDLE_MS);
}
if (singleTargetWheel) {
  map.getContainer().addEventListener("wheel", captureSingleTargetWheel, {
    capture: true, passive: false
  });
  // If another camera gesture begins before the wheel settles, discard the
  // stale preview instead of overwriting the newer move with an old zoom.
  map.on("dragstart", clearPendingWheel);
  map.on("zoomstart", () => {
    if (!committingWheelZoom) clearPendingWheel();
  });
}
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
  map.options.wheelDebounceTime = WHEEL_DEBOUNCE_MS;
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

const baseMap = L.tileLayer(GSI_PREFETCH_ROOT + "/{z}/{x}/{y}.png", {
  // The overview minimum is set on the map itself based on its viewport.
  // Allow low-zoom GSI tiles so zooming out does not leave a blank basemap.
  minZoom: 2,
  maxZoom: 18,
  maxNativeZoom: 18,
  // Avoid the intermediate raster/tile work during a rapid zoom gesture.
  // Leaflet scales the available imagery, then requests the target zoom's
  // official tiles. Old progressive mode is available for A/B diagnostics.
  // The flood layer is never hidden and retains its separate source.
  keepBuffer: previousZoomFeel ? 3 : 4,
  updateWhenZooming: slowZoomFeel || progressiveZoomFeel,
  updateInterval: 220,
  attribution: '<a href="https://maps.gsi.go.jp/development/ichiran.html" target="_blank" rel="noopener">地理院タイル</a>'
}).addTo(map);

const officialFloodLayer = L.tileLayer(FLOOD_REFERENCE_URL, {
  pane: "officialFloodPane",
  minZoom: 2,
  maxZoom: 18,
  maxNativeZoom: 17,
  opacity: 0.58,
  // Retain a slightly wider native Leaflet tile cache through fast zooms.
  // Leaflet alone keeps each official raster tile at its real coordinates;
  // the old flood clone is never overlaid after the geographic view changes.
  keepBuffer: 4,
  // Larger verified hazard-raster requests are delayed until zoom end so
  // the faster base map never triggers a flood-tile network storm.
  updateWhenZooming: false,
  attribution: '出典：<a href="https://disaportal.gsi.go.jp/" target="_blank" rel="noopener">ハザードマップポータルサイト</a>'
}).addTo(map);

// Official flood imagery has independent loading/coverage semantics.
// A blank or temporarily missing raster never means "no inundation".
// Keep this local map status separate from D facility records and the
// persistent source-error banner. Do NOT keep old flood PNGs misregistered
// after committing a different geographic zoom.
const floodRefreshStatus = document.getElementById("mapFloodRefreshStatus");
let floodRefreshSequence = 0;
let floodRefreshPending = false;
let floodRefreshErrors = 0;
let floodRefreshCheck = null;
function floodRasterEnabled() {
  return map.hasLayer(officialFloodLayer) &&
    document.getElementById("officialFlood")?.checked !== false;
}
function showFloodRefresh(state) {
  if (!floodRefreshStatus) return;
  if (!floodRasterEnabled() || state === "ready") {
    floodRefreshStatus.hidden = true;
    floodRefreshStatus.textContent = "";
    delete floodRefreshStatus.dataset.state;
    return;
  }
  floodRefreshStatus.hidden = false;
  floodRefreshStatus.dataset.state = state;
  floodRefreshStatus.textContent = state === "partial"
    ? "洪水参照画像の一部を確認できません。未表示・空白は「浸水なし」を意味しません。"
    : "公的洪水画像を更新中です。表示されない場所も「浸水なし」とは判断できません。";
}
function beginFloodRefresh() {
  if (!floodRasterEnabled()) {
    showFloodRefresh("ready");
    return;
  }
  floodRefreshSequence++;
  floodRefreshPending = true;
  floodRefreshErrors = 0;
  if (floodRefreshCheck !== null) clearTimeout(floodRefreshCheck);
  floodRefreshCheck = null;
  showFloodRefresh("loading");
}
function completeFloodRefresh() {
  if (!floodRefreshPending || !floodRasterEnabled()) {
    showFloodRefresh("ready");
    return;
  }
  if (officialFloodLayer.isLoading?.()) return;
  floodRefreshPending = false;
  showFloodRefresh(floodRefreshErrors > 0 ? "partial" : "ready");
}
function settleFloodRefreshSoon() {
  const sequence = floodRefreshSequence;
  if (floodRefreshCheck !== null) clearTimeout(floodRefreshCheck);
  floodRefreshCheck = setTimeout(() => {
    floodRefreshCheck = null;
    if (sequence === floodRefreshSequence) completeFloodRefresh();
  }, 100);
}
officialFloodLayer.on("loading", beginFloodRefresh);
officialFloodLayer.on("load", () => {
  // A resolved Leaflet batch means requests stopped; it does not certify
  // completeness of official hazard coverage, merely readiness of this view.
  settleFloodRefreshSoon();
});
map.on("zoomstart", beginFloodRefresh);
map.on("zoomend", settleFloodRefreshSoon);
map.on("layerremove", event => {
  if (event.layer === officialFloodLayer) {
    floodRefreshSequence++;
    floodRefreshPending = false;
    showFloodRefresh("ready");
  }
});
map.on("layeradd", event => {
  if (event.layer === officialFloodLayer) beginFloodRefresh();
});

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
      mode: zoomFeelMode || "target-first"
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
// Additional D records seen during map navigation. Kept independent from the
// selected municipality, its full-source records, and verified GSI layers.
const viewportDGroup = L.layerGroup().addTo(map);
L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

// Navigation-only zoom scale reference: approximate Japanese archipelago
// dimensions. The user prefers the closer map scale over an all-Japan fit.
// This is NOT a jurisdiction border, data coverage or disaster safety area;
// the outer edges of Japan may be cropped at the minimum zoom.
const JAPAN_OVERVIEW_BOUNDS = L.latLngBounds([
  [24.0, 122.5],
  [45.8, 146.5]
]);
const OVERVIEW_TILE_MIN_ZOOM = 2;
const OVERVIEW_MAX_MIN_ZOOM = 6;
const OVERVIEW_VIEWPORT_PADDING = [32, 32];
// Keep responsive minimum-zoom sizing, but stop zooming out around the
// closer, 200 km scale-bar reference from the user's second screenshot
// rather than demanding the full Japan rectangle fit. At the same viewport,
// +0.6 zoom is roughly 1.5x the rendered map scale (300 km -> 200 km).
const OVERVIEW_MIN_ZOOM_STEPS_PER_LEVEL = 4;
const NAVIGATION_CLOSEUP_ZOOM_OFFSET = 0.6;

function updateJapanOverviewMinimumZoom() {
  // getBoundsZoom returns the largest zoom level that fits the overview
  // bounds within the current map size. Recompute when a resize changes
  // that fit, instead of hard-coding desktop/mobile zoom levels.
  const fittedZoom = map.getBoundsZoom(
    JAPAN_OVERVIEW_BOUNDS, false, OVERVIEW_VIEWPORT_PADDING
  );
  if (!Number.isFinite(fittedZoom)) return;
  // Derive a responsive baseline from Japan dimensions, then intentionally
  // zoom in ~0.6 more levels for navigation. Unlike the former all-Japan-fit
  // rule, Hokkaido/Kyushu/remote islands can be offscreen at this limit.
  // Never recenter the map: only constrain how far a user can zoom out.
  const tightFitZoom = Math.min(
    fittedZoom,
    Math.floor(fittedZoom * OVERVIEW_MIN_ZOOM_STEPS_PER_LEVEL) /
      OVERVIEW_MIN_ZOOM_STEPS_PER_LEVEL + 0.1
  );
  map.setMinZoom(Math.max(
    OVERVIEW_TILE_MIN_ZOOM,
    Math.min(OVERVIEW_MAX_MIN_ZOOM,
      tightFitZoom + NAVIGATION_CLOSEUP_ZOOM_OFFSET)
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

// All source enums and raw values remain unchanged; these are presentation labels.
const PLACE_KIND_LABELS = Object.freeze({
  "D: shelter_location / raw facts": "地域の避難施設",
  "D RegionExport": "地域の施設情報",
  "GSI公式掲載 / 未推奨": "洪水に関する公式掲載地点",
  "地図表示用クラスタ": "近接する施設",
  "境界fixture": "自治体境界（参考）",
  "公的参照": "公的な洪水情報"
});
const PLACE_FIELD_LABELS = Object.freeze({
  "ID": "施設ID", "raw行": "元データの記録位置",
  "施設名（D原値）": "施設名（元データ）",
  "住所（D原値）": "住所（元データ）",
  "行政区域（D原値）": "行政区域（元データ）",
  "施設区分（D原値）": "施設区分（元データ）",
  "公式災害列（原文）": "公式資料の災害区分（原文）",
  "公式Source行": "出典の記録位置",
  "公式rawの記号": "公式資料の記号",
  "公式災害列": "公式資料の災害区分",
  "洪水Scenario（D原値）": "洪水対応の確認状態",
  "Dの判定理由": "判定の根拠",
  "元データ記載の災害（適合性未検証）": "資料に記載された災害種別",
  "照合方式": "情報の照合方法",
  "Contract": "データ形式"
});
const PLACE_PRIORITY_FIELDS = new Set([
  "住所", "公式住所", "種別", "洪水対応分類",
  "直線距離（経路距離ではない）", "件数", "表示", "位置", "状態"
]);
// A selected source point owns one popup; its scale follows zoom, not data
// semantics. Leaflet retains the popup's geographic anchor across pan/zoom.
const PLACE_POPUP_TIERS = ["place-bubble--far", "place-bubble--mid", "place-bubble--near"];
function placePopupZoomTier(zoom) {
  return zoom < 11 ? PLACE_POPUP_TIERS[0] :
    zoom < 14 ? PLACE_POPUP_TIERS[1] : PLACE_POPUP_TIERS[2];
}
let activePlacePopup = null;
function updatePlacePopupZoom() {
  const popup = activePlacePopup;
  const element = popup?.getElement?.();
  if (!element?.classList) return;
  const tier = placePopupZoomTier(map.getZoom());
  if (element.classList.contains(tier)) return;
  element.classList.remove(...PLACE_POPUP_TIERS);
  element.classList.add(tier);
  // Leaflet remeasures the bubble after its width changes, preserving
  // its attachment point without replacing/closing the selected content.
  popup.update?.();
}
map.on("zoomend", updatePlacePopupZoom);

// Leaflet anchors a bubble to the selected point; #details is a hidden template.
function detail(title, rows, type, options = {}) {
  const badgeClass = options.badgeClass ? " " + options.badgeClass : "";
  const noteClass = options.noteTone ? " " + options.noteTone : "";
  const prominent = rows.filter(row => PLACE_PRIORITY_FIELDS.has(row[0])).slice(0, 2);
  // A boundary is a display fixture, not a selectable facility. Keep its
  // default bubble to the name/type only, with all raw fields one tap away.
  const summaryRows = type === "境界fixture" ? [] :
    prominent.length ? prominent : rows.slice(0, 2);
  const extraRows = rows.filter(row => !summaryRows.includes(row));
  const renderRows = entries => entries.map(([label, value]) =>
    `<div class="row"><div class="label">${escapeHtml(PLACE_FIELD_LABELS[label] || label)}</div>` +
    `<div class="value">${escapeHtml(displayValue(value))}</div></div>`
  ).join("");
  const note = options.note
    ? `<p class="note${noteClass}">${escapeHtml(options.note)}</p>` : "";
  // A single disclosure avoids two large actions occupying the map. Original
  // evidence, caution notes and technical/source rows remain accessible.
  const disclosure = extraRows.length || note
    ? `<details class="place-card-disclosure"><summary>` +
      (extraRows.length ? `詳しい情報を見る（${extraRows.length}項目）` :
        "注意事項と確認範囲") +
      `</summary><div class="place-card-extra">${renderRows(extraRows)}${note}</div></details>`
    : "";
  const safeHref = safeExternalUrl(options.href);
  const externalLink = safeHref
    ? `<a class="detail-link" href="${escapeHtml(safeHref)}" target="_blank" rel="noopener noreferrer">公式の出典を確認 ↗</a>`
    : "";
  const showSafetyCaveat = type === "D: shelter_location / raw facts" ||
    type === "GSI公式掲載 / 未推奨";
  const caution = showSafetyCaveat
    ? `<p class="place-card-caution">安全性・現在の開設状況は確認できていません。${type === "D: shelter_location / raw facts" ? "洪水対応の未判定は危険・対応不可を意味しません。" : ""}</p>`
    : "";
  const visibleType = PLACE_KIND_LABELS[type] || type;
  document.getElementById("details").innerHTML =
    `<span class="badge${badgeClass}">${escapeHtml(visibleType)}</span>` +
    `<h2 class="detail-title">${escapeHtml(title)}</h2>` +
    `<div class="place-card-summary">${renderRows(summaryRows)}</div>` +
    caution + externalLink + disclosure;
  if (options.anchor && typeof L.popup === "function") {
    const isBoundary = type === "境界fixture";
    const zoomTier = placePopupZoomTier(map.getZoom());
    const popup = L.popup({
      className: "hinanex-place-popup " + zoomTier +
        (isBoundary ? " place-bubble--boundary" : ""),
      closeButton: true, autoPan: true,
      autoPanPaddingTopLeft: [16, 82],
      autoPanPaddingBottomRight: [16, 76], maxWidth: 285
    }).setLatLng(options.anchor)
      .setContent(document.getElementById("details").innerHTML);
    popup.openOn(map);
    activePlacePopup = popup;
    window.HINANEX_MAP_FIRST_UI?.showDetail?.();
  } else if (options.anchor && typeof L.popup !== "function") {
    // For offline controller fixtures without real Leaflet popup primitives.
    window.HINANEX_MAP_FIRST_UI?.showDetail?.();
  }
}
map.on("popupclose", event => {
  if (!event?.popup || event.popup === activePlacePopup) activePlacePopup = null;
  document.getElementById("gisLayout")?.setAttribute("data-right-panel", "closed");
  document.getElementById("toggleRightPanel")?.setAttribute("aria-expanded", "false");
});
function shelterIcon(decision = "UNKNOWN") {
  const safeClass = decision === "CANDIDATE" ? "d-status-candidate" :
    decision === "EXCLUDED" ? "d-status-excluded" : "d-status-unknown";
  return L.divIcon({
    className: "",
    html: '<div class="shelter-icon ' + safeClass + '" aria-label="洪水対応分類：' +
      (decision === "CANDIDATE" ? "候補として分類済み（安全性未判定）" :
        decision === "EXCLUDED" ? "対象外として分類済み（危険性未判定）" :
        "未判定（安全性未判定）") + '"><span>⌂</span></div>',
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
      ["座標", record.hasCoordinates ? "元データに座標あり" : "元データで未確認（推測表示なし）"],
      ["洪水Scenario（D原値）", fact?.status ?? "判定情報なし"],
      ["公式災害列（原文）", fact?.hazardScopeRaw],
      ["公式rawの記号", fact?.officialStatusRaw],
      ["利用階の原文", fact?.usableFloorRaw],
      ["照合方式", fact?.joinStatus],
      ["公式Source行", fact?.sourceRecordTrace],
      ["Dの判定理由", fact?.reason]
    ];
    const detailRows = fields.map(([label, value]) =>
      `<dt>${escapeHtml(PLACE_FIELD_LABELS[label] || label)}</dt><dd>${escapeHtml(displayValue(value))}</dd>`
    ).join("");
    const url = safeExternalUrl(fact?.sourceUrl || record.detail_url);
    const officialLink = url && url.startsWith("https:")
      ? `<a class="list-source" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">出典を開く</a>`
      : "";
    return `<details class="facility-list-card"><summary><strong>${escapeHtml(record.name)}</strong>` +
      `<small>${escapeHtml(displayValue(record.address))} / ${escapeHtml(displayValue(record.administrative_area))}</small>` +
      `</summary><dl>${detailRows}</dl>${officialLink}` +
      `<p class="list-note">地図上の位置・洪水時の安全性・開設は未検証です。元資料の記号や未判定の情報から利用可否を判断しません。</p></details>`;
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
    ? "施設の地図位置は未確認（地図選択不可）"
    : "地図から出発地点を指定";
  if (active) {
    choosingOrigin = false;
    updateMapOriginAction("選択地域の施設は座標未確認です。施設一覧で名前・住所を確認してください。");
    if (!selectedOrigin) {
      document.getElementById("originStatus").textContent =
        "選択地域の施設の地図位置を確認できません。地図をクリックして選択する操作は使えません。施設一覧を利用してください。";
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
    displayMode === "both" ? "公式掲載地点だけ表示" : "地域の避難施設と比較";
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
  if (showD && shelterInput.checked) {
    map.addLayer(shelterGroup);
    map.addLayer(viewportDGroup);
  } else {
    map.removeLayer(shelterGroup);
    map.removeLayer(viewportDGroup);
  }
  const viewportBadge = document.getElementById("mapViewportDStatus");
  if (viewportBadge) viewportBadge.hidden =
    !showD || !shelterInput.checked || !summaryPanel.hidden;
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
      ? "地域の避難施設を表示。公式掲載地点の確認結果は地図で非表示（再切替で復帰）。"
      : displayMode === "nearby"
        ? "選択地点周辺で確認済みの公式掲載地点だけを表示。安全性・開設は未判定。"
        : !hasMappedD
          ? "地域施設の位置情報が未読込・座標欠損のため比較範囲を表示できません。GSIは別データです。"
          : "地域の避難施設（緑）と公式掲載地点（紫）を比較。異なる出典の情報です。";
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
    L.marker([site.latitude, site.longitude], {
      pane: "referenceSitePane", zIndexOffset: 1000,
      icon: L.divIcon({
        className: "",
        html: '<span class="reference-site-marker" aria-label="GSI公式掲載地点・安全性未判定"></span>',
        iconSize: [32, 32], iconAnchor: [16, 16]
      })
    }).on("click", event => {
      L.DomEvent.stopPropagation(event);
      detail(site.name, [
        ["出典", "GSI skhb01 洪水指定緊急避難場所（参照のみ）"],
        ["直線距離（経路距離ではない）", site.distanceMetres + "m"],
        ["公式住所", displayValue(site.address)],
        ["公式備考", displayValue(site.remarks)],
        ["raw行", displayValue(site.trace)]
      ], "GSI公式掲載 / 未推奨", {
        anchor: [site.latitude, site.longitude],
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
    anchor: [latitude, longitude],
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
      ["状態", "地域の施設情報は未読込"],
      ["探索先", currentRegion().autoUrl],
      ["Contract", "RegionExport 0.9"]
    ],
    "地域切替",
    { note: "Eは確認できていない座標・境界を推測しません。" }
  );
}

function clearShelters() {
  // On data replacement an old point bubble must never masquerade as a new record.
  map.closePopup?.();
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
          anchor: event.latlng,
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
        ["洪水対応が未判定", `${summary.floodScenario.unknownCount}件`]
      ] : [])
    ],
    "D RegionExport",
    {
      note: missing > 0
        ? "座標を確認できない施設は地図に表示していません。住所から位置を推測していません。"
        : "元データにある座標だけを表示しています。未確認の位置を推測していません。"
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

// A D Scenario's exact-ID facility status is NOT an actual safety rating.
function dFloodDecision(summary, record) {
  const status = summary?.floodScenario?.byId.get(record.id)?.status;
  return status === "CANDIDATE" || status === "EXCLUDED" ? status : "UNKNOWN";
}
function dRecordVisible(summary, record) {
  if (presenterFilterIds && summary === currentShelterSummary &&
      !presenterFilterIds.has(record.id)) return false;
  const filter = document.getElementById("mapDDecisionFilter").value;
  const status = dFloodDecision(summary, record);
  return filter === "classified" ? status !== "UNKNOWN" :
    filter === "unclassified" ? status === "UNKNOWN" : true;
}
function updateDDecisionFilterStatus(summary) {
  const el = document.getElementById("mapDDecisionFilterStatus");
  const records = summary?.mappableRecords || [];
  const classified = records.filter(item => dFloodDecision(summary, item) !== "UNKNOWN").length;
  const unknown = records.length - classified;
  const filter = document.getElementById("mapDDecisionFilter").value;
  const shown = filter === "classified" ? classified :
    filter === "unclassified" ? unknown : records.length;
  el.textContent = !summary ? "選択地域の施設データ未読込。0件と断定できません。" :
    "選択地域の座標付き施設：" + classified + "件が分類済み／" +
    unknown + "件が未判定。現在 " + shown + "件を表示対象。" +
    (filter === "classified" && !classified
      ? " この出典には判定済み施設がありません。避難施設が存在しないという意味ではありません。"
      : "") +
    " 座標なし施設は別途一覧で確認してください。";
}
function drawIndividualDMarker(record, summary) {
    const decision = dFloodDecision(summary, record);
    return L.marker([record.latitude, record.longitude], { icon: shelterIcon(decision), pane: "shelterPane" })
      .on("click", event => {
        L.DomEvent.stopPropagation(event);
        detail(
          record.name,
          [
            ["ID", record.id],
            ["洪水対応分類", decision === "UNKNOWN" ? "未判定" :
              decision === "CANDIDATE" ? "候補として分類済み" :
              "対象外として分類済み"],
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
            anchor: [record.latitude, record.longitude],
            href: summary.floodScenario?.byId.get(record.id)?.sourceUrl || record.detail_url,
            note: summary.floodScenario?.byId.has(record.id)
              ? "洪水対応の確認状態は、出典を追える形で記録したものです。未判定は危険・候補外を意味しません。公式記号の意味、実際の開設、建物・経路の安全性は未確認です。"
              : "空欄は未確認または判定できない情報です。値を推測で埋めていません。"
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
function drawDClusterMarker(records, regionLabel = currentRegion().label,
                            summary = currentShelterSummary) {
  const states = records.map(record => dFloodDecision(summary, record));
  const classified = states.filter(s => s !== "UNKNOWN").length;
  const unknown = states.length - classified;
  const className = unknown === states.length ? "d-status-unknown" :
    classified === states.length ? "d-status-classified" : "d-status-mixed";
  const latitude = records.reduce((sum, record) => sum + record.latitude, 0) / records.length;
  const longitude = records.reduce((sum, record) => sum + record.longitude, 0) / records.length;
  const count = records.length;
  return L.marker([latitude, longitude], {
    pane: "shelterPane",
    title: "近接する施設" + count + "件（地図表示用の集合、優先順位ではありません）",
    icon: L.divIcon({
      className: "",
      html: '<div class="d-facility-cluster ' + className +
        '" aria-label="近接する施設' + count + '件。洪水対応分類済み' + classified +
        '件・未判定' + unknown + '件。地図表示用の集合、安全性未判定">' +
        count.toLocaleString("ja-JP") + '</div>',
      iconSize: [42, 42],
      iconAnchor: [21, 21]
    })
  }).on("click", event => {
    L.DomEvent.stopPropagation(event);
    detail("施設の表示上の集合（" + count + "件）", [
      ["件数", count + "件（地図上の重なりを軽減するための表示件数）"],
      ["対象", regionLabel + "の施設データ"],
      ["表示位置", "含まれる施設座標の平均値（実在する施設位置ではありません）"],
      ["洪水対応分類", "分類済み " + classified + "件／未判定 " + unknown + "件"]
    ], "地図表示用クラスタ", {
      anchor: [latitude, longitude],
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
  updateDDecisionFilterStatus(summary);
  if (!summary?.mappableRecords?.length) {
    lastDMarkerZoomBucket = null;
    return;
  }
  const visibleRecords = summary.mappableRecords.filter(record => dRecordVisible(summary, record));
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
  const batches = groupMappedDRecords(visibleRecords, groupingZoom,
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
        : drawDClusterMarker(records, currentRegion().label, summary);
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

// D locations across all three *known* RegionExport files are considered
// only after the user navigates the map. This is not municipality inference:
// a visible coordinate is an observed D point, and an absent coordinate or
// absent file never means an area has no shelters or is safe.
const viewportDCache = new Map();
const viewportDLoading = new Set();
const viewportDInFlight = new Map();
const viewportDFailed = new Set();
let viewportDMarkers = new Map();
let viewportDTimer = null;
let viewportTriggered = false;

function rememberViewportD(code, summary) {
  if (!REGION_CONFIGS[code] || !summary) return;
  viewportDCache.set(code, {
    summary,
    indices: new Map(summary.mappableRecords.map((record, index) => [record, index]))
  });
  viewportDFailed.delete(code);
}

function renderViewportD() {
  const badge = document.getElementById("mapViewportDStatus");
  const bounds = map.getBounds();
  if (!bounds || typeof bounds.contains !== "function") return;
  const start = debugMapPerf ? perfTime() : 0;
  const zoom = map.getZoom();
  const next = new Map();
  const counts = [];
  let activeTotal = 0;
  for (const config of Object.values(REGION_CONFIGS)) {
    const item = viewportDCache.get(config.code);
    const summary = config.code === selectedRegionCode
      ? currentShelterSummary : item?.summary;
    if (!summary) continue;
    const visible = summary.mappableRecords.filter(record =>
      bounds.contains([record.latitude, record.longitude]) &&
      dRecordVisible(summary, record));
    if (visible.length) counts.push(config.label + " " + visible.length + "件");
    activeTotal += visible.length;
    // The selected municipality already owns its marker layer; avoid
    // duplicates while preserving its full RegionExport detail/list state.
    if (config.code === selectedRegionCode || !item || !visible.length) continue;
    const groupingZoom = zoom >= 13 ? zoom : Math.floor(zoom);
    const batches = groupMappedDRecords(visible, groupingZoom,
      (coordinate, level) => map.project(coordinate, level));
    for (const records of batches) {
      const key = config.code + ":" +
        records.map(record => item.indices.get(record)).join(",");
      let marker = viewportDMarkers.get(key);
      if (!marker) {
        marker = records.length === 1
          ? drawIndividualDMarker(records[0], summary)
          : drawDClusterMarker(records, config.label, summary);
        viewportDGroup.addLayer(marker);
      }
      next.set(key, marker);
    }
  }
  for (const [key, marker] of viewportDMarkers) {
    if (!next.has(key)) viewportDGroup.removeLayer(marker);
  }
  viewportDMarkers = next;
  const loading = viewportDLoading.size;
  const failures = viewportDFailed.size;
  badge.textContent = activeTotal
    ? "表示範囲の避難施設：" + counts.join(" / ") + "（開設・安全性未判定）"
    : "表示範囲：座標を確認できた施設は未表示（未収録・未取得を含む）";
  if (document.getElementById("mapDDecisionFilter").value !== "all") {
    badge.textContent += "｜洪水対応分類で絞込中（非表示＝施設なしではありません）";
  }
  if (loading) badge.textContent += "｜他地域の施設データ確認中";
  if (failures) badge.textContent += "｜未取得 " + failures + "地域";
  // A second official GSI legend has priority on small screens.
  badge.hidden = !viewportTriggered || displayMode === "nearby" ||
    !document.getElementById("shelter").checked ||
    !document.getElementById("referenceMapSummary").hidden;
  if (debugMapPerf) console.info("[HINANEX map perf] viewport D", {
    zoom, visibleSourcePoints: activeTotal, otherRegionMarkers: next.size,
    durationMs: Math.round(perfTime() - start)
  });
}

function fetchViewportDOnce(config) {
  // Both normal viewport discovery and presenter tour use this provider.
  // A second consumer MUST await the existing in-flight request rather than
  // treating "currently fetching" as "unavailable" and skipping the tour.
  if (viewportDCache.has(config.code) || viewportDFailed.has(config.code)) {
    return Promise.resolve();
  }
  const existing = viewportDInFlight.get(config.code);
  if (existing) return existing;
  viewportDLoading.add(config.code);
  const request = (async () => {
    try {
      const response = await fetch(config.autoUrl, { cache: "force-cache" });
      if (!response.ok) throw new Error("RegionExport unavailable");
      const payload = await response.json();
      const adapter = window.HINANEX_D_ADAPTER;
      if (!adapter) throw new Error("D adapter missing");
      const summary = adapter.extractShelterLocation(payload, config.code);
      rememberViewportD(config.code, summary);
    } catch (_) {
      // Unknown is never converted into a claim about shelter availability.
      viewportDFailed.add(config.code);
    } finally {
      viewportDLoading.delete(config.code);
      viewportDInFlight.delete(config.code);
      if (viewportTriggered) renderViewportD();
    }
  })();
  viewportDInFlight.set(config.code, request);
  return request;
}

function updateViewportD() {
  viewportTriggered = true;
  // Fetch is lazy and once per verified RegionExport URL, NEVER per pixel of
  // pan/zoom; it does not change selectedRegionCode or the current map view.
  if (window.location.protocol !== "file:") {
    for (const config of Object.values(REGION_CONFIGS)) {
      if (config.code !== selectedRegionCode) fetchViewportDOnce(config);
    }
  }
  renderViewportD();
}
function scheduleViewportD() {
  if (viewportDTimer !== null) clearTimeout(viewportDTimer);
  viewportDTimer = setTimeout(() => {
    viewportDTimer = null;
    updateViewportD();
  }, 120);
}
map.on("moveend", scheduleViewportD);


// Presenter-only source-attribute filter. This is an exact subset of the
// selected D RegionExport, never a new hazard/eligibility calculation.
let presenterFilterIds = null;
let presenterFilterSession = null;
let presenterFilterEpoch = 0;
function presenterChooseCondition(summary) {
  const all = summary.mappableRecords || [];
  if (all.length < 2) return null;
  const classified = all.filter(r => dFloodDecision(summary, r) !== "UNKNOWN");
  if (classified.length && classified.length < all.length) return {
    kind: "classification", value: "洪水対応の分類結果がある施設",
    label: "洪水対応が分類済み", records: classified
  };
  // If D has no approved scenario decisions (common in production), show
  // an honest *source-text* filter rather than inventing a flood-safe result.
  for (const word of ["小学校", "中学校", "高等学校", "体育館", "公民館", "公園"]) {
    const matching = all.filter(r => r.name.includes(word));
    if (matching.length && matching.length < all.length) return {
      kind: "name", value: word, label: "施設名に「" + word + "」を含む",
      records: matching
    };
  }
  for (const key of ["facility_type", "administrative_area"]) {
    const groups = new Map();
    for (const record of all) {
      const value = record[key];
      if (typeof value !== "string" || !value.trim()) continue;
      if (!groups.has(value)) groups.set(value, []);
      groups.get(value).push(record);
    }
    const possible = [...groups].filter(([,set]) => set.length < all.length);
    if (possible.length) {
      possible.sort((a,b) => b[1].length - a[1].length || a[0].localeCompare(b[0]));
      const [value,records] = possible[0];
      return {
        kind:key, value,
        label:(key === "facility_type" ? "施設区分（元データ）" : "行政区域（元データ）")+
          "が「"+value+"」",records
      };
    }
  }
  return null; // No useful subset: don't fake a filter or a count.
}
window.HINANEX_FACILITY_PRESENTER = Object.freeze({
  async begin() {
    if (presenterFilterSession) return {state:"busy"};
    const epoch = ++presenterFilterEpoch;
    const filterControl = document.getElementById("mapDDecisionFilter");
    const shelterControl = document.getElementById("shelter");
    const session = {
      epoch, code: selectedRegionCode,
      center: map.getCenter(), zoom: map.getZoom(),
      filter: filterControl.value, shelter: shelterControl.checked, mode:displayMode,
      summary:null, condition:null
    };
    presenterFilterSession = session;
    const config = currentRegion();
    if (!currentShelterSummary && window.location.protocol !== "file:") {
      await fetchViewportDOnce(config);
    }
    if (epoch !== presenterFilterEpoch || presenterFilterSession !== session)
      return {state:"cancelled"};
    const summary = currentShelterSummary ||
      viewportDCache.get(config.code)?.summary || null;
    if (!summary?.dataset || summary.region.code !== config.code ||
        !Array.isArray(summary.mappableRecords) || !summary.mappableRecords.length)
      return {state:"unavailable",region:config.label};
    if (summary !== currentShelterSummary) {
      // Validated D adapter output, shared with the ordinary GIS view.
      renderShelterSummary(summary, "地域の施設データ（発表用確認）");
    }
    const condition = presenterChooseCondition(summary);
    session.summary=summary;
    session.condition=condition;
    filterControl.value="all";
    shelterControl.checked=true;
    setDisplayMode("region");
    presenterFilterIds=null;
    lastDMarkerZoomBucket=null;
    renderDMarkers();
    const sourceLocations=summary.mappableRecords;
    const bounds=L.latLngBounds(sourceLocations.map(r=>[r.latitude,r.longitude]));
    if (bounds.isValid()) {
      if (typeof map.flyToBounds==="function")
        map.flyToBounds(bounds,{padding:[64,64],maxZoom:12,duration:1.2});
      else map.fitBounds(bounds,{padding:[64,64],maxZoom:12});
    }
    const classified=sourceLocations.filter(r=>dFloodDecision(summary,r)!=="UNKNOWN").length;
    return {
      state:condition?"ready":"no-distinguishing-condition", region:config.label,
      sourceTotal:summary.records.length, mapped:sourceLocations.length,
      missing:summary.missingCoordinateRecords.length,
      classified,unknown:sourceLocations.length-classified,
      criterion:condition?.label || null,criterionKind:condition?.kind || null,
      matches:condition?.records.length || 0
    };
  },
  apply() {
    const s=presenterFilterSession;
    if (!s?.summary || !s.condition || selectedRegionCode !== s.code)
      return {state:"unavailable"};
    presenterFilterIds=new Set(s.condition.records.map(r=>r.id));
    lastDMarkerZoomBucket=null;
    renderDMarkers(); // Existing D markers, source coordinates, normal clustering.
    const points=s.condition.records.map(r=>[r.latitude,r.longitude]);
    const bounds=L.latLngBounds(points);
    if(bounds.isValid()){
      if(typeof map.flyToBounds==="function")
        map.flyToBounds(bounds,{padding:[55,55],maxZoom:13,duration:1.1});
      else map.fitBounds(bounds,{padding:[55,55],maxZoom:13});
    }
    return {state:"filtered",matches:s.condition.records.length,
      mapped:s.summary.mappableRecords.length,criterion:s.condition.label};
  },
  inspect() {
    const s=presenterFilterSession;
    if (!s?.summary || !s.condition || selectedRegionCode !== s.code)
      return {state:"unavailable"};
    const record=s.condition.records[0];
    // Actual selected D-record coordinates only; not a recommended destination.
    if (typeof map.flyTo==="function")
      map.flyTo([record.latitude,record.longitude],14,{duration:1.1});
    else map.setView([record.latitude,record.longitude],14,{animate:false});
    const fact=s.summary.floodScenario?.byId.get(record.id) || null;
    const criterionValue=s.condition.kind==="classification" ?
      dFloodDecision(s.summary,record) :
      s.condition.kind==="name" ? record.name :
      record[s.condition.kind];
    return {
      state:"inspected",name:record.name,
      criterion:s.condition.label,kind:s.condition.kind,criterionValue,
      decision:dFloodDecision(s.summary,record),
      facilityType:record.facility_type,administrativeArea:record.administrative_area,
      rawSymbol:fact?.officialStatusRaw ?? null,
      rawFloor:fact?.usableFloorRaw ?? null,
      sourceTrace:fact?.sourceRecordTrace ?? null,
      reason:fact?.reason ?? null,
      sourceUrl:safeExternalUrl(fact?.sourceUrl || record.detail_url) || null
    };
  },
  halt(){ if(typeof map.stop==="function")map.stop(); },
  end(restore=true) {
    const s=presenterFilterSession;
    presenterFilterEpoch++;
    if(typeof map.stop==="function")map.stop();
    presenterFilterSession=null;
    presenterFilterIds=null;
    if(!s)return;
    document.getElementById("mapDDecisionFilter").value=s.filter;
    document.getElementById("shelter").checked=s.shelter;
    setDisplayMode(s.mode);
    lastDMarkerZoomBucket=null;
    renderDMarkers();
    if(restore)map.setView(s.center,s.zoom,{animate:false});
  }
});


// GSI official-flood presenter: skhb01 and raw disaster1=1 are prevalidated
// by the existing E discovery engine. This is not a D safety classification.
let gsiPresenterSession = null;
let gsiPresenterEpoch = 0;
window.HINANEX_GSI_FLOOD_PRESENTER = Object.freeze({
  async begin() {
    if (gsiPresenterSession) return {state:"busy"};
    const center=map.getCenter();
    // A presentation must not take an arbitrary zoomed-out map center as a
    // "source origin" for the currently selected municipality. Choose an
    // actual D record coordinate solely as geographic context, not as a
    // recommended shelter or evidence of a GSI/D building identity.
    const sourceSummary=currentShelterSummary?.region.code===selectedRegionCode
      ? currentShelterSummary : viewportDCache.get(selectedRegionCode)?.summary;
    const sourcePoint=sourceSummary?.mappableRecords?.[0] || null;
    const origin=selectedOrigin || (sourcePoint && {
      latitude:sourcePoint.latitude,longitude:sourcePoint.longitude
    });
    if(!origin)return {state:"unavailable",reason:"NO_REGION_SOURCE_POINT"};
    const engine=compatibleDiscoveryEngine();
    if(!engine||!engine.sourceTileKey(origin))return {state:"unavailable",reason:"origin"};
    const token=++gsiPresenterEpoch;
    const session={
      token,center,zoom:map.getZoom(),mode:displayMode,
      origin:selectedOrigin,catalog:verifiedFloodCatalog,
      originalDetail:document.getElementById("details").innerHTML,
      originalOriginLabel:document.getElementById("originStatus").textContent,
      originalCoord:document.getElementById("coordinateSearchInput").value,
      sourceCode:selectedRegionCode,
      sites:null,discovery:null
    };
    gsiPresenterSession=session;
    selectedOrigin={latitude:origin.latitude,longitude:origin.longitude};
    setDisplayMode("region"); // start with D as context; GSI appears at the source-switch scene.
    if(!session.origin) {
      // The map in the user's screenshot was in the western mountains while
      // the selected region was Edogawa. Start the story where the verified D
      // record actually is, without manufacturing a hazard or GSI location.
      if(typeof map.flyTo==="function")
        map.flyTo([origin.latitude,origin.longitude],12,{duration:1.1});
      else map.setView([origin.latitude,origin.longitude],12,{animate:false});
    }
    await loadFloodReferenceCatalog();
    if(token!==gsiPresenterEpoch||gsiPresenterSession!==session)return {state:"cancelled"};
    const d=engine.discoverReferenceTiles(verifiedFloodCatalog,selectedOrigin,selectedRegionCode);
    if(d.status!=="REFERENCE_ONLY"||!d.total||!d.sites.length){
      return {state:"unavailable",reason:d.status,message:d.message};
    }
    session.sites=d.sites;
    session.discovery=d;
    // GSI data has been validated but stays hidden until the demo applies the flood designation.
    return {
      state:"ready", source:"GSI_SKHB01_FLOOD", rawDisaster1:1,
      label:"洪水に対応する指定緊急避難場所（GSI skhb01）",
      total:d.total,shown:d.sites.length,
      verifiedTiles:d.verifiedTileCount,requestedTiles:d.requestedTileCount,
      partial:d.partialCoverage,firstName:d.sites[0].name,
      sourceUrl:d.sites[0].sourceUrl
    };
  },
  show() {
    const s=gsiPresenterSession;
    if(!s?.discovery||s.sourceCode!==selectedRegionCode)return {state:"unavailable"};
    setDisplayMode("nearby");
    focusReferenceCandidates();
    return {state:"shown",count:s.discovery.total,shown:s.sites.length,
      partial:s.discovery.partialCoverage};
  },
  inspect() {
    const s=gsiPresenterSession;
    if(!s?.discovery||s.sourceCode!==selectedRegionCode)return {state:"unavailable"};
    const item=s.sites[0]; // existing strictly verified, non-recommended record
    if(typeof map.flyTo==="function")
      map.flyTo([item.latitude,item.longitude],14,{duration:1.2});
    else map.setView([item.latitude,item.longitude],14,{animate:false});
    const sourceUrl=safeExternalUrl(item.sourceUrl);
    return {
      state:"inspected",name:item.name,address:item.address,remarks:item.remarks,
      sourceTrace:item.trace,sourceUrl,disaster1Raw:1,
      designation:"洪水の指定緊急避難場所（公式掲載）",
      tileCount:s.discovery.verifiedTileCount,requestedTiles:s.discovery.requestedTileCount,
      // Source tiles do not establish a municipality or current opening status.
      municipalityVerified:false,openingVerified:false,safeRouteVerified:false
    };
  },
  compareD() {
    const s=gsiPresenterSession;
    if(!s?.discovery)return {state:"unavailable"};
    const d=currentShelterSummary;
    if(!d||d.region.code!==selectedRegionCode||!d.dataset)
      return {state:"unavailable",reason:"D RegionExport not loaded"};
    const mapped=d.mappableRecords.length;
    const unclassified=d.mappableRecords.filter(r=>dFloodDecision(d,r)==="UNKNOWN").length;
    setDisplayMode("both"); // green D and purple GSI remain distinct sources
    return {state:"separate-source",source:"D RegionExport",total:d.records.length,
      mapped,missing:d.missingCoordinateRecords.length,unclassified,
      classified:mapped-unclassified,joinedWithGSI:false};
  },
  halt(){if(typeof map.stop==="function")map.stop();},
  end(restore=true) {
    const s=gsiPresenterSession;
    gsiPresenterEpoch++;
    catalogLoadSequence++; // supersede any verified-tile HTTP still pending
    if(typeof map.stop==="function")map.stop();
    gsiPresenterSession=null;
    if(!s)return;
    selectedOrigin=s.origin;
    verifiedFloodCatalog=s.catalog;
    document.getElementById("originStatus").textContent=s.originalOriginLabel;
    document.getElementById("coordinateSearchInput").value=s.originalCoord;
    document.getElementById("details").innerHTML=s.originalDetail;
    renderReferenceDiscovery();
    setDisplayMode(s.mode);
    if(restore)map.setView(s.center,s.zoom,{animate:false});
  }
});

// Presentation-only map tour API. This does not select another municipality,
// alter Scenario contracts, imply data coverage, or infer unlocated facilities.
// It can only focus on *actual mappable source points* from RegionExport.
let tourSavedView = null;
let tourRequestGeneration = 0;
async function focusPresentationTourRegion(code, animate = true, focusFirstVerifiedPoint = false) {
  const generation = tourRequestGeneration;
  const config = REGION_CONFIGS[code];
  if (!config) return { state: "unsupported", region: code, mapped: 0, total: 0 };
  if (!viewportDCache.has(code) && window.location.protocol !== "file:") {
    await fetchViewportDOnce(config);
  }
  // A presenter may stop/pause while awaiting HTTP. Never allow stale data
  // completion to move the map after the manual interaction takes control.
  if (generation !== tourRequestGeneration) return {
    state: "cancelled", region: config.label, mapped: 0, total: 0
  };
  const summary = viewportDCache.get(code)?.summary ||
    (code === selectedRegionCode ? currentShelterSummary : null);
  if (!summary) return {
    state: "unavailable", region: config.label, mapped: 0, total: 0
  };
  const locations = summary.mappableRecords;
  if (!locations.length) return {
    state: "unlocated", region: config.label,
    mapped: 0, total: summary.records.length
  };
  const bounds = L.latLngBounds(locations.map(item => [item.latitude, item.longitude]));
  if (!bounds.isValid()) return {
    state: "unlocated", region: config.label,
    mapped: 0, total: summary.records.length
  };
  viewportTriggered = true;
  renderViewportD();
  // The first stop starts on the user's already-selected Edogawa region:
  // focusing its entire extent barely moves the camera. Explicitly focus
  // the first *verified source point* to make the presenter tour visibly
  // start; this is an example record, NEVER a recommended shelter.
  if (focusFirstVerifiedPoint) {
    const point = locations[0];
    const center = [point.latitude, point.longitude];
    if (animate && typeof map.flyTo === "function") {
      map.flyTo(center, 14, { duration: 1.25 });
    } else {
      map.setView(center, 14, { animate: false });
    }
  } else {
    const viewOptions = { padding: [48, 48], maxZoom: 12 };
    if (animate && typeof map.flyToBounds === "function") {
      map.flyToBounds(bounds, { ...viewOptions, duration: 1.25 });
    } else {
      map.fitBounds(bounds, { ...viewOptions, animate: false });
    }
  }
  return {
    state: "mapped", region: config.label,
    mapped: locations.length, total: summary.records.length,
    focus: focusFirstVerifiedPoint ? "source-example" : "source-bounds"
  };
}
window.HINANEX_PRESENTATION_TOUR = Object.freeze({
  begin() {
    tourRequestGeneration++;
    tourSavedView = { center: map.getCenter(), zoom: map.getZoom() };
  },
  focus: focusPresentationTourRegion,
  halt() {
    tourRequestGeneration++;
    if (typeof map.stop === "function") map.stop();
  },
  end(restore = true) {
    tourRequestGeneration++;
    if (typeof map.stop === "function") map.stop();
    if (restore && tourSavedView) {
      map.setView(tourSavedView.center, tourSavedView.zoom, { animate: false });
    }
    tourSavedView = null;
  }
});

function renderShelterSummary(summary, sourceLabel) {
  currentShelterSummary = summary;
  rememberViewportD(selectedRegionCode, summary);
  updateCoverage(summary);
  applyDisplayMode(); // if D arrives after GSI, update comparison availability

  // Keep bounds based on ALL verified D positions, never on cluster-centroid
  // display points (which are not actual facility locations).
  const latLngs = summary.mappableRecords.map(record => [record.latitude, record.longitude]);
  renderDMarkers();
  if (viewportTriggered) renderViewportD();

  shelterBounds = latLngs.length ? L.latLngBounds(latLngs) : null;
  const listOnly = summary.records.length > 0 && summary.mappableRecords.length === 0;
  setMapAvailability(
    !listOnly && Boolean(boundaryBounds?.isValid() || shelterBounds?.isValid()),
    `${summary.region.name}には座標を確認できる施設がなく、地図上の範囲を確定できません。位置は推測しません。`
  );
  setFacilityListMode(listOnly ? summary : null);

  const missing = summary.missingCoordinateRecords.length;
  updateDatasetChip("施設データ読込済", "ok");
  setDatasetStatus(
    `${sourceLabel}｜施設データ形式 ${summary.schemaVersion}｜取得 ${summary.records.length}件 / 地図に表示 ${summary.mappableRecords.length}件 / 位置未確認 ${missing}件`,
    missing > 0 ? "warning" : "success"
  );
  setStatus(
    listOnly
      ? `座標未確認のため施設一覧を表示中（${summary.records.length}件）。安全・開設状況は判定していません。`
      : missing > 0
        ? `避難施設を表示中｜${missing}件は座標欠損のため地図非表示（件数は保持）`
        : `避難施設を${summary.mappableRecords.length}件表示中`,
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
    updateDatasetChip("施設データ未確認", "warning");
    setDatasetStatus(`${sourceLabel}｜避難施設データが見つかりません`, "warning");
    setStatus("この地域の施設情報を確認できません", "warning");
    detail(
      summary.region.name,
      [
        ["Contract", `RegionExport ${summary.schemaVersion}`],
        ["状態", "避難施設データを確認できません"],
        ["読込元", sourceLabel]
      ],
      "D RegionExport",
      { note: "不足した施設情報を別の資料から推測して補っていません。" }
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
      "file:// で開いているため、ブラウザの制限により自動取得できません。HTTPサーバー経由で開くか、施設データ（JSON）を選択してください。",
      "warning"
    );
    showRegionWaitingDetail();
    setStatus(`${config.label}｜地域の施設情報は手動で読込`, "warning");
    return;
  }

  updateDatasetChip("探索中", "wait");
  setDatasetStatus(`${config.label} の施設データを探しています…`);

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
      `地域の施設データを読み込めませんでした（${error.message}）。${config.label} のJSONを選択するか、提供元の施設データを読み込んでください。GSI公式地点探索は別データなので利用できます。`,
      "warning"
    );
    showRegionWaitingDetail();
    setStatus(`${config.label}｜地域の施設情報は未読込`, "warning");
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
  // Switching the manual region is still a deliberate shortcut; viewport D
  // points from other confirmed sources remain independent and do not pan.
  if (viewportTriggered) renderViewportD();
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
    `${currentRegion().label} は境界fixtureがありません。座標付きの施設データを読み込むまで、地図位置を選択地域として扱いません。`
  );
  showRegionWaitingDetail();
  setStatus(`${currentRegion().label}｜地域の施設情報を読み込みます`);
  tryAutoLoad();
  if (hasBoundary) fitCurrentRegion();
  if (viewportTriggered) renderViewportD();
}

function bindToggle(id, layer) {
  document.getElementById(id).addEventListener("change", event => {
    if (event.target.checked) map.addLayer(layer);
    else map.removeLayer(layer);
    if (layer === officialFloodLayer) {
      if (event.target.checked) beginFloodRefresh();
      else {
        floodRefreshSequence++;
        floodRefreshPending = false;
        showFloodRefresh("ready");
      }
    }
  });
}

bindToggle("basemap", baseMap);
bindToggle("officialFlood", officialFloodLayer);
document.getElementById("boundary").addEventListener("change", applyDisplayMode);
document.getElementById("shelter").addEventListener("change", applyDisplayMode);
document.getElementById("mapDDecisionFilter").addEventListener("change", () => {
  // Zoom-band reuse is only valid for the same selected classification filter.
  // Keep source data, viewport bounds and GSI layers exactly as they were.
  lastDMarkerZoomBucket = null;
  renderDMarkers();
  if (viewportTriggered) renderViewportD();
});
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
  map.closePopup?.();
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
    setStatus("施設データの読込に失敗しました", "error");
  } finally {
    event.target.value = "";
  }
});

map.on("click", event => {
  if (choosingOrigin) {
    setReferenceOrigin(event.latlng.lat, event.latlng.lng);
    return;
  }
  // A blank-map tap dismisses the selection; official raster remains available
  // in the 災害情報 evidence view, not as a competing floating card.
  map.closePopup?.();
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
    floodRefreshErrors++;
    if (floodRasterEnabled()) {
      floodRefreshPending = true;
      showFloodRefresh("partial");
    }
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
