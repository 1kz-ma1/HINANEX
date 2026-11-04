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

  function getStatus() {
    if (!flood.checked) return "洪水浸水想定レイヤーは非表示です。非表示は「浸水なし」を意味しません。";
    if (refresh?.dataset?.state === "partial" ||
        warning?.dataset?.partial === "true" ||
        previousError?.hidden === false) {
      return "公的洪水画像の取得失敗を検知しました（過去の閲覧範囲を含みます）。現在の範囲を含め、空白は「浸水なし」と判断できません。";
    }
    if (refresh?.dataset?.state === "loading") {
      return "公的洪水画像を更新中です。地図の空白は「浸水なし」を意味しません。";
    }
    return "洪水レイヤーを表示する設定です。地図タイルの全域取得・対応範囲・最新性は確認済みではありません。";
  }

  function synchronize() {
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

  openButton.addEventListener("click", () => setOpen(panel.hidden));
  closeButton.addEventListener("click", () => {
    setOpen(false);
    openButton.focus();
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
  flood.addEventListener("change", synchronize);
  document.addEventListener("keydown", event => {
    if (panel.hidden || event.key !== "Escape") return;
    event.preventDefault();
    setOpen(false);
    openButton.focus();
  });
  document.addEventListener("click", event => {
    if (panel.hidden || panel.contains(event.target) || openButton.contains(event.target)) return;
    setOpen(false);
  }, true);
  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(() => {
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