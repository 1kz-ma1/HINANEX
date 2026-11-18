/* F01: a separate, read-only hazard information entry over the existing GIS.
 * Reuse the existing official raster and region controls. No hazard inference,
 * new requests, GPS collection, shelter assessment, or persistence.
 */
(() => {
  "use strict";
  const get = name => document.getElementById(name);
  const panel = get("hazardGuidePanel");
  const openButton = get("hazardGuideOpen");
  const closeButton = get("hazardGuideClose");
  const regionInput = get("hazardGuideRegion");
  const floodInput = get("hazardGuideFlood");
  const status = get("hazardGuideStatus");
  const region = get("region");
  const flood = get("officialFlood");
  if (!panel || !openButton || !closeButton || !regionInput || !floodInput ||
      !status || !region || !flood) return;

  const knownRegions = new Set(["13123", "15100", "23100"]);
  const tools = ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"];
  const warning = get("mapRasterBanner");
  const refresh = get("mapFloodRefreshStatus");
  const previousError = get("externalFloodTileNotice");

  // Changing the region never certifies that the map viewport or new raster
  // has changed. Do not carry an old area's tile-result label into the new one.
  let lastRegion = region.value;
  let regionStatusStale = false;

  function getStatus() {
    if (!knownRegions.has(region.value)) {
      return "地域未確認：選択した地域を確認できません。以前の取得結果は表示しません。";
    }
    if (!flood.checked) {
      return "非表示：洪水浸水想定レイヤーは非表示です。取得を要求していない状態であり、非表示は「浸水なし」を意味しません。";
    }
    if (regionStatusStale) {
      return "地域切替後：以前の表示範囲の画像取得結果は引き継ぎません。現在の地図タイルの全域取得・対応範囲・最新性は確認済みではありません。";
    }
    if (refresh?.dataset?.state === "partial") {
      return "画像取得失敗を検知しました。通信失敗・配信対象外・ブラウザ制限など原因は未確認です。空白は「浸水なし」を意味しません。";
    }
    if (refresh?.dataset?.state === "loading") {
      return "取得中：公的洪水画像を更新中です。まだ取得を確認できない部分があり、空白は「浸水なし」を意味しません。";
    }
    if (warning?.dataset?.partial === "true" || previousError?.hidden === false) {
      return "過去の閲覧範囲で画像取得失敗を検知しました。現在の表示範囲での取得成功・対象外・通信状況は未確認です。空白は「浸水なし」を意味しません。";
    }
    return "取得状態未確認：洪水レイヤーを表示する設定です。地図タイルの全域取得・対応範囲・最新性は確認済みではありません。未取得と対象外を混同しないでください。";
  }

  function synchronize() {
    if (region.value !== lastRegion) {
      lastRegion = region.value;
      regionStatusStale = true;
    }
    regionInput.value = knownRegions.has(region.value) ? region.value : "";
    floodInput.checked = !!flood.checked;
    status.textContent = getStatus();
  }

  function setOpen(visible) {
    panel.hidden = !visible;
    openButton.setAttribute("aria-expanded", String(visible));
    if (!visible) return;
    // Avoid stacked sheets without modifying any hazard or facility state.
    for (const name of tools) {
      const node = get(name);
      if (node) node.open = false;
    }
    for (const name of ["mapEvidencePanel", "mapTourPanel", "mapSharePanel", "mapSettingsPanel"]) {
      const other = get(name);
      if (other && !other.hidden) {
        const close = get({
          mapEvidencePanel: "mapEvidenceClose",
          mapTourPanel: "mapTourClose",
          mapSharePanel: "mapShareClose",
          mapSettingsPanel: "mapSettingsClose"
        }[name]);
        close?.click();
      }
    }
    synchronize();
    regionInput.focus();
  }

  // The opener is inside a <details> menu that closes when F01 opens.
  // After the sheet closes, return focus to the visible menu summary instead.
  function returnFocus() {
    const menu = get("mapToolHazards");
    const visibleSummary = menu && !menu.open ? menu.querySelector?.("summary") : null;
    (visibleSummary || openButton).focus();
  }
  openButton.addEventListener("click", () => setOpen(panel.hidden));
  closeButton.addEventListener("click", () => {
    setOpen(false);
    returnFocus();
  });
  regionInput.addEventListener("change", () => {
    if (!knownRegions.has(regionInput.value) || regionInput.value === region.value) return;
    region.value = regionInput.value;
    region.dispatchEvent(new Event("change", { bubbles: true }));
    synchronize();
  });
  floodInput.addEventListener("change", () => {
    if (flood.checked === floodInput.checked) return;
    flood.checked = floodInput.checked;
    flood.dispatchEvent(new Event("change", { bubbles: true }));
    synchronize();
  });
  region.addEventListener("change", synchronize);
  flood.addEventListener("change", () => {
    // A deliberate re-enable starts a new tile attempt through the existing
    // map controller. No previous-area result is treated as current evidence.
    if (flood.checked) regionStatusStale = false;
    synchronize();
  });
  document.addEventListener("keydown", event => {
    if (panel.hidden || event.key !== "Escape") return;
    event.preventDefault();
    setOpen(false);
    returnFocus();
  });
  document.addEventListener("click", event => {
    if (panel.hidden || panel.contains(event.target) || openButton.contains(event.target)) return;
    setOpen(false);
  }, true);
  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(records => {
      // Clear the region switch guard only for a newly observed raster load.
      // A pre-existing partial/error flag is not evidence for the new region.
      if (regionStatusStale && refresh?.dataset?.state === "loading" &&
          records.some(record => record.target === refresh &&
            record.type === "attributes" && record.attributeName === "data-state")) {
        regionStatusStale = false;
      }
      if (!panel.hidden) synchronize();
    });
    if (refresh) observer.observe(refresh, {
      attributes: true, attributeFilter: ["data-state", "hidden"],
      childList: true, characterData: true, subtree: true
    });
    if (warning) observer.observe(warning, {
      attributes: true, attributeFilter: ["data-partial"]
    });
    if (previousError) observer.observe(previousError, {
      attributes: true, attributeFilter: ["hidden"],
      childList: true, characterData: true, subtree: true
    });
  }
  synchronize();
})();