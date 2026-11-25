/* F06 / static official-information directory.
 * These are verified external entrypoints, NOT an emergency-information feed.
 * No API, GPS, geocoding, personal storage, status polling or safety inference.
 */
(() => {
  "use strict";
  const get = id => document.getElementById(id);
  const panel = get("officialAlertsPanel");
  const opener = get("officialAlertsOpen");
  const closer = get("officialAlertsClose");
  const region = get("region");
  const regionName = get("officialAlertsRegionName");
  const regionNote = get("officialAlertsRegionNote");
  const local = get("officialAlertsLocalLink");
  if (!panel || !opener || !closer || !region || !regionName || !regionNote || !local) return;

  // Checked against publishers' own sites on 2026-11-04. Page availability
  // and the existence or absence of a current alert are NOT checked by HINANEX.
  const directory = Object.freeze({
    "13123": Object.freeze({
      name: "東京都 江戸川区", label: "江戸川区防災ポータルを開く",
      href: "https://bosai.city.edogawa.tokyo.jp/"
    }),
    "15100": Object.freeze({
      name: "新潟県 新潟市", label: "新潟市 防災・緊急情報を開く",
      href: "https://www.city.niigata.lg.jp/kurashi/bosai/index.html"
    }),
    "23100": Object.freeze({
      name: "愛知県 名古屋市", label: "名古屋市 防災ポータルを開く",
      href: "https://www.city.nagoya.jp/bousaiportal/index.html"
    })
  });

  function synchronize() {
    const item = Object.prototype.hasOwnProperty.call(directory, region.value)
      ? directory[region.value] : null;
    regionName.textContent = item ? item.name : "未対応の地域";
    if (item) {
      local.href = item.href;
      local.textContent = item.label;
      local.hidden = false;
      regionNote.textContent = "選択中の地域に対応する自治体の公式入口です。外部サイトで対象地域と発表内容・発表時刻を確認してください。";
    } else {
      local.hidden = true;
      local.removeAttribute("href");
      local.textContent = "";
      regionNote.textContent = "この地域向けの自治体リンクは未登録です。自治体公式情報を別途確認してください。未登録は警報なしや自治体が発信していないことを意味しません。";
    }
  }

  function focusReturn() {
    const hazards = get("mapToolHazards");
    const visible = hazards && !hazards.open && hazards.querySelector
      ? hazards.querySelector("summary") : null;
    (visible || opener).focus();
  }

  function setOpen(visible) {
    panel.hidden = !visible;
    opener.setAttribute("aria-expanded", String(visible));
    if (!visible) return;
    // Avoid overlapping separate GIS information panels.
    for (const id of ["mapToolScene","mapToolScenario","mapToolMarks","mapToolHazards"]) {
      const tool = get(id);
      if (tool) tool.open = false;
    }
    for (const [id,buttonId] of [
      ["hazardGuidePanel","hazardGuideClose"],
      ["mapEvidencePanel","mapEvidenceClose"],
      ["mapTourPanel","mapTourClose"],
      ["mapSharePanel","mapShareClose"],
      ["mapSettingsPanel","mapSettingsClose"]
    ]) {
      const other = get(id);
      if (other && !other.hidden) get(buttonId)?.click();
    }
    synchronize();
    closer.focus();
  }

  opener.addEventListener("click", () => setOpen(panel.hidden));
  closer.addEventListener("click", () => {
    setOpen(false);
    focusReturn();
  });
  region.addEventListener("change", synchronize);
  document.addEventListener("keydown", event => {
    if (panel.hidden || event.key !== "Escape") return;
    event.preventDefault();
    setOpen(false);
    focusReturn();
  });
  document.addEventListener("click", event => {
    if (panel.hidden || panel.contains(event.target) || opener.contains(event.target)) return;
    setOpen(false);
  }, true);
  // Browser history restoration can change the existing map's selected region.
  window.addEventListener("pageshow", synchronize);
  synchronize();
})();