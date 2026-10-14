(() => {
  "use strict";
  const id = key => document.getElementById(key);
  const panel = id("mapEvidencePanel"), openButton = id("mapEvidenceOpen");
  if (!panel || !openButton) return;
  const toolMenus = ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"].map(id);
  function display(idValue, fallback) {
    const node = id(idValue);
    return node?.textContent?.trim() || fallback;
  }
  function refresh() {
    id("mapEvidenceRegion").textContent =
      id("region").selectedOptions?.[0]?.textContent?.trim() ||
      ({ "13123": "東京都 江戸川区", "15100": "新潟県 新潟市",
         "23100": "愛知県 名古屋市" }[id("region").value] || "選択地域を確認できません");
    const records = display("recordCount", "—");
    const mapped = display("mappedCount", "—");
    const missing = display("missingCoordinateCount", "—");
    const chip = display("datasetChip", "未読込");
    const loaded = !["—", "未読込"].includes(records);
    id("mapEvidenceD").textContent = loaded
      ? chip + "｜" + records + "件（選択中の地域のみ）"
      : chip + "｜件数未確認";
    id("mapEvidenceCoordinate").textContent = loaded
      ? "座標あり " + mapped + "件／座標未確認 " + missing + "件"
      : "元座標を確認できていません";
    // GSI displayed counts are ONLY the verified tiles around an explicitly
    // selected reference location. Never confuse with 地域の施設データ counts.
    const gsiPanel = id("referenceMapSummary");
    id("mapEvidenceGSI").textContent = gsiPanel?.hidden
      ? "地点未指定・未照合、または掲載を確認できない範囲"
      : display("referenceMapCoverage", "照合状況未確認") + "｜" +
        display("referenceMapCount", "件数未確認") +
        "（選択地点周辺の照合済み範囲のみ）";
    const flood = id("officialFlood");
    const rasterError = id("mapRasterBanner");
    id("mapEvidenceFlood").textContent = !flood.checked
      ? "非表示（危険なしという意味ではありません）"
      : rasterError?.hidden === false
        ? "表示中／一部のタイルが未取得（空白＝浸水なしではありません）"
        : "表示中（タイル全域の取得・精度・安全性は保証しません）";
    const viewport = id("mapViewportDStatus");
    id("mapEvidenceViewport").textContent = viewport?.textContent?.trim()
      ? "閲覧範囲の表示状態：" + viewport.textContent.trim()
      : "閲覧範囲の追加地域の避難施設は未確認です。未表示は施設なしを意味しません。";
  }
  function setOpen(open) {
    panel.hidden = !open;
    openButton.setAttribute("aria-expanded", String(open));
    if (!open) return;
    for (const menu of toolMenus) menu.open = false;
    // A viewer can inspect the status without losing the current map view.
    if (!id("mapSharePanel").hidden) id("mapShareClose").click();
    if (!id("mapTourPanel").hidden) id("mapTourClose").click();
    if (!id("mapSettingsPanel").hidden) id("mapSettingsClose").click();
    const layout = id("gisLayout");
    if (layout.getAttribute("data-left-panel") === "open") id("toggleLeftPanel").click();
    if (layout.getAttribute("data-right-panel") === "open") id("toggleRightPanel").click();
    id("referenceMapSummaryDisclosure").open = false;
    refresh();
  }
  openButton.addEventListener("click", () => setOpen(panel.hidden));
  id("mapEvidenceClose").addEventListener("click", () => setOpen(false));
  for (const menu of toolMenus) menu.addEventListener("toggle", () => {
    if (menu.open && !panel.hidden) setOpen(false);
  });
  for (const key of ["mapShareOpen", "mapTourOpen", "mapSettingsToggle",
    "toggleLeftPanel", "toggleRightPanel"]) {
    id(key).addEventListener("click", () => {
      if (!panel.hidden) setOpen(false);
    });
  }
  document.addEventListener("click", event => {
    if (panel.hidden || panel.contains(event.target) || openButton.contains(event.target)) return;
    setOpen(false);
  }, true);
  document.addEventListener("keydown", event => {
    if (panel.hidden || event.key !== "Escape") return;
    event.preventDefault();
    setOpen(false);
    openButton.focus();
  });
  if (typeof MutationObserver !== "undefined") {
    const observer = new MutationObserver(() => {
      if (!panel.hidden) refresh();
    });
    for (const key of ["recordCount", "mappedCount", "missingCoordinateCount",
      "datasetChip", "referenceMapCoverage", "referenceMapCount",
      "mapRasterBanner", "mapViewportDStatus"]) {
      const node = id(key);
      if (node) observer.observe(node, {
        childList: true, characterData: true, subtree: true,
        ...(key === "mapRasterBanner"
          ? { attributes: true, attributeFilter: ["hidden"] } : {})
      });
    }
  }
  id("region").addEventListener("change", () => { if (!panel.hidden) refresh(); });
  id("officialFlood").addEventListener("change", () => { if (!panel.hidden) refresh(); });
})();