// UI facade only. Keep original D/GSI map logic, IDs and native controls.
(() => {
  const id = name => document.getElementById(name);
  const layout = id("gisLayout");
  const menuIds = ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"];
  const toolMenus = menuIds.map(id);
  const referenceDisclosure = id("referenceMapSummaryDisclosure");
  const referenceSummary = id("referenceMapSummary");
  const leftPanel = id("gisLeftPanel"), rightPanel = id("details");
  const dismissedMapClicks = new WeakSet();

  function isPanelOpen(side) {
    return layout.getAttribute("data-" + side + "-panel") === "open";
  }
  function closePanel(side) {
    if (!isPanelOpen(side)) return;
    id(side === "left" ? "toggleLeftPanel" : "toggleRightPanel").click();
  }
  function closeMenus(except = null) {
    for (const menu of toolMenus) if (menu !== except) menu.open = false;
  }
  function closeOtherSurfaces(except = null) {
    closeMenus(except);
    if (except !== leftPanel) closePanel("left");
    if (except !== rightPanel) closePanel("right");
    if (except !== referenceDisclosure) referenceDisclosure.open = false;
  }
  for (const menu of toolMenus) {
    menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      closeOtherSurfaces(menu);
    });
  }
  referenceDisclosure.addEventListener("toggle", () => {
    if (referenceDisclosure.open) closeOtherSurfaces(referenceDisclosure);
  });
  id("mapOpenAdvanced").addEventListener("click", () => {
    closeOtherSurfaces(leftPanel);
    if (!isPanelOpen("left")) id("toggleLeftPanel").click();
  });

  // Capture before Leaflet's map/marker click handler: a tap that dismisses a
  // sheet is not simultaneously interpreted as a new hazard reference tap.
  // A deliberate second tap can still inspect the map as before.
  document.addEventListener("click", event => {
    const target = event.target;
    const inOpenMenu = toolMenus.some(menu => menu.open && menu.contains(target));
    const inLeft = isPanelOpen("left") &&
      (leftPanel.contains(target) || id("toggleLeftPanel").contains(target));
    const inRight = isPanelOpen("right") &&
      (rightPanel.contains(target) || id("toggleRightPanel").contains(target));
    const inReference = !referenceSummary.hidden && referenceDisclosure.open &&
      referenceSummary.contains(target);
    if (inOpenMenu || inLeft || inRight || inReference) return;
    const wasOpen = toolMenus.some(menu => menu.open) ||
      isPanelOpen("left") || isPanelOpen("right") || referenceDisclosure.open;
    if (!wasOpen) return;
    if (event && typeof event === "object") dismissedMapClicks.add(event);
    closeOtherSurfaces();
  }, true);
  document.addEventListener("keydown", event => {
    if (event.key !== "Escape") return;
    const wasOpen = toolMenus.some(menu => menu.open) ||
      isPanelOpen("left") || isPanelOpen("right") || referenceDisclosure.open;
    if (!wasOpen) return;
    event.preventDefault();
    closeOtherSurfaces();
  });

  const region = id("region"), quickRegion = id("mapRegionQuickSelect");
  const forwardChange = target => target.dispatchEvent(new Event("change", { bubbles: true }));
  const synchronizeRegion = () => { quickRegion.value = region.value; };
  quickRegion.value = region.value;
  quickRegion.addEventListener("change", () => {
    region.value = quickRegion.value;
    forwardChange(region);
  });
  region.addEventListener("change", synchronizeRegion);

  function forwardChecked(proxyId, targetId) {
    const proxy = id(proxyId), target = id(targetId);
    const synchronize = () => {
      proxy.checked = target.checked;
      proxy.disabled = target.disabled;
    };
    synchronize();
    proxy.addEventListener("change", () => {
      target.checked = proxy.checked;
      forwardChange(target);
      synchronize();
    });
    target.addEventListener("change", synchronize);
    return synchronize;
  }
  const syncD = forwardChecked("mapShowShelter", "shelter");
  forwardChecked("mapShowFlood", "officialFlood");
  forwardChecked("mapShowBasemap", "basemap");
  const mode = id("facilityDisplayMode");
  mode.addEventListener("change", syncD);
  id("mapScenarioSelectOrigin").addEventListener("click", () => {
    id("selectOrigin").click();
    id("mapToolScenario").open = false;
  });
  id("mapLocateMe").addEventListener("click", () => {
    // The legacy GPS handler requests permission only from this user click.
    id("useGps").click();
  });
  const gpsFeedback = id("mapGpsFeedback");
  const originStatus = id("originStatus");
  // Geolocation failure was previously visible only in the hidden sidebar.
  // Mirror status on the map without storing or transmitting precise coords.
  if (typeof MutationObserver !== "undefined") {
    new MutationObserver(() => {
      const message = originStatus.textContent || "";
      const failure = /拒否|利用できません|取得できません|開始できません/.test(message);
      gpsFeedback.hidden = !failure;
      gpsFeedback.textContent = failure ? message : "";
    }).observe(originStatus, { childList: true, characterData: true, subtree: true });
  }

  function showDetail() {
    closeOtherSurfaces(rightPanel);
    layout.setAttribute("data-right-panel", "open");
    const button = id("toggleRightPanel");
    button.setAttribute("aria-expanded", "true");
    button.setAttribute("aria-label", "右詳細を閉じる");
    button.setAttribute("title", "右詳細を閉じる");
  }
  function showRasterWarning(message) {
    const notice = id("mapRasterNotice");
    notice.textContent = message;
    notice.hidden = false;
    const banner = id("mapRasterBanner");
    // Short but explicit map warning; the full original evidence remains in
    // the 災害情報 menu and in the persistent legacy status/evidence section.
    banner.textContent = "洪水情報の一部が未取得です（空白＝浸水なしではありません）";
    banner.title = message;
    banner.hidden = false;
  }
  window.HINANEX_MAP_FIRST_UI = Object.freeze({
    showDetail,
    showRasterWarning,
    wasDismissalClick(event) {
      return !!event && dismissedMapClicks.has(event);
    }
  });
})();
