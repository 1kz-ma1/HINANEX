// UI facade only. Keep original D/GSI map logic, IDs and native controls.
(() => {
  const id = name => document.getElementById(name);
  const layout = id("gisLayout");
  const menuIds = ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"];
  for (const menuId of menuIds) {
    id(menuId).addEventListener("toggle", () => {
      if (!id(menuId).open) return;
      for (const other of menuIds) if (other !== menuId) id(other).open = false;
    });
  }

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
    banner.textContent = message;
    banner.hidden = false;
  }
  window.HINANEX_MAP_FIRST_UI = Object.freeze({ showDetail, showRasterWarning });
})();
