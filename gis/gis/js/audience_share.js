(() => {
  "use strict";
  // Static, locally rendered QR; QR payload and the text URL are identical.
  // Regenerated using Python qrcode, ECC M / four-module quiet zone.
  // 41x41 binary matrix; each row is 11 hex chars (44 bits, final 3 padded).
  const AUDIENCE_URL = "https://hinanex-staging.onrender.com/gis/gis/?demo=audience";
  const QR_HEX = "000000000000000000000000000000000000000000000fea0b93f80082d26720800ba3731ae800bae059ae800ba68922e8008247f8a0800feaaaabf80000dbca00000b763f425800c85cbb368005fb4e79d800ad480815800c76b425d800d9d254d50004ea27ab6000c1e98ce6000664a1c6e0003cf14bed8001e8b2e9a00034b368c80008beefd47000f522f1248002b7ea39b80054e589d48009329d2f880000afd38d000fedab1a800082a68f8f000ba512ffb800bac74b16800baa94836000827fe3dc800fefbed2a0000000000000000000000000000000000000000000000";
  const id = value => document.getElementById(value);
  const panel = id("mapSharePanel");
  const toggle = id("mapShareOpen");
  const status = id("mapShareStatus");
  const urlInput = id("mapShareURL");
  urlInput.value = AUDIENCE_URL;
  function renderQR() {
    const target = id("mapShareQR");
    if (target.firstChild) return;
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 41 41");
    svg.setAttribute("shape-rendering", "crispEdges");
    svg.setAttribute("aria-hidden", "true");
    const background = document.createElementNS(ns, "rect");
    background.setAttribute("width", "41");
    background.setAttribute("height", "41");
    background.setAttribute("fill", "#fff");
    svg.appendChild(background);
    let d = "";
    for (let y = 0; y < 41; y++) {
      const bits = parseInt(QR_HEX.slice(y * 11, (y + 1) * 11), 16).toString(2).padStart(44, "0");
      for (let x = 0; x < 41; x++) {
        if (bits[x] === "1") d += "M" + x + " " + y + "h1v1h-1z";
      }
    }
    const path = document.createElementNS(ns, "path");
    path.setAttribute("fill", "#000");
    path.setAttribute("d", d);
    svg.appendChild(path);
    target.appendChild(svg);
  }
  function closeOtherMapSurfaces() {
    for (const name of ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"]) id(name).open = false;
    id("referenceMapSummaryDisclosure").open = false;
    const layout = id("gisLayout");
    if (layout.getAttribute("data-left-panel") === "open") id("toggleLeftPanel").click();
    if (layout.getAttribute("data-right-panel") === "open") id("toggleRightPanel").click();
    if (!id("mapSettingsPanel").hidden) id("mapSettingsClose").click();
  }
  function setOpen(open) {
    panel.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) {
      closeOtherMapSurfaces();
      id("mapAudienceIntro").hidden = true;
      renderQR();
      status.textContent = "";
    }
  }
  toggle.addEventListener("click", () => setOpen(panel.hidden));
  id("mapShareClose").addEventListener("click", () => setOpen(false));
  id("mapShareCopy").addEventListener("click", async () => {
    try {
      if (!navigator.clipboard?.writeText) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(AUDIENCE_URL);
      status.textContent = "URLをコピーしました";
    } catch (_) {
      urlInput.focus();
      urlInput.select();
      status.textContent = "URLを選択しました。手動でコピーしてください";
    }
  });
  document.addEventListener("click", event => {
    if (panel.hidden || panel.contains(event.target) || toggle.contains(event.target)) return;
    setOpen(false);
  }, true);
  document.addEventListener("keydown", event => {
    if (event.key === "Escape" && !panel.hidden) {
      event.preventDefault();
      setOpen(false);
      toggle.focus();
    }
  });
  for (const name of ["mapToolScene", "mapToolScenario", "mapToolMarks", "mapToolHazards"]) {
    const menu = id(name);
    menu.addEventListener("toggle", () => { if (menu.open) setOpen(false); });
  }

  const intro = id("mapAudienceIntro");
  id("mapAudienceIntroClose").addEventListener("click", () => { intro.hidden = true; });
  id("mapAudienceIntroStart").addEventListener("click", () => {
    // A deliberate visitor action, not QR-driven autoplay or location access.
    // The single public MAIN DEMO owns its verified-source loading/fallback.
    intro.hidden = true;
    setOpen(false);
    id("mapGsiFloodDemoOpen").click();
  });
  const audienceMode = new URL(window.location.href).searchParams.get("demo") === "audience";
  // Each explicit visit or browser refresh of the distributed audience URL
  // is a new demonstration opportunity. Closing the card affects this loaded
  // document only; a later navigation or reload shows it again. No storage.
  intro.hidden = !audienceMode;
  // A visitor is never automatically GPS-tracked or autoplayed. This module
  // does not request geo permissions, infer safety or change the map camera.
})();