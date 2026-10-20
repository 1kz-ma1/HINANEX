(function () {
  "use strict";

  // Strictly a view over locations already accepted by E's flood_discovery.
  // The comparison never fetches, normalizes, joins or assesses shelter safety.
  const GSI_URL = /^https:\/\/cyberjapandata\.gsi\.go\.jp\/xyz\/skhb01\/10\/[0-9]+\/[0-9]+\.geojson$/;
  const LIMIT = 5;

  function validSite(site) {
    return site && typeof site.id === "string" &&
      typeof site.sourceUrl === "string" && GSI_URL.test(site.sourceUrl) &&
      typeof site.trace === "string" && /^feature_index=[0-9]+$/.test(site.trace) &&
      site.id === site.sourceUrl + "#" + site.trace &&
      typeof site.name === "string" && site.name.length > 0 &&
      (site.address === null || site.address === undefined || typeof site.address === "string") &&
      (site.remarks === null || site.remarks === undefined || typeof site.remarks === "string") &&
      typeof site.latitude === "number" && Number.isFinite(site.latitude) &&
      site.latitude >= -90 && site.latitude <= 90 &&
      typeof site.longitude === "number" && Number.isFinite(site.longitude) &&
      site.longitude >= -180 && site.longitude <= 180 &&
      Number.isSafeInteger(site.distanceMetres) && site.distanceMetres >= 0;
  }

  function createSession(discovery) {
    if (discovery?.status !== "REFERENCE_ONLY" ||
        !Array.isArray(discovery.sites) || discovery.sites.length < 1 ||
        discovery.sites.length > LIMIT ||
        !Array.isArray(discovery.verifiedTileKeys) ||
        discovery.verifiedTileKeys.length < 1 ||
        discovery.verifiedTileKeys.some(key => !/^10\/[0-9]+\/[0-9]+$/.test(key)) ||
        !Number.isInteger(discovery.verifiedTileCount) ||
        discovery.verifiedTileCount !== discovery.verifiedTileKeys.length ||
        !Number.isInteger(discovery.requestedTileCount) ||
        discovery.requestedTileCount < discovery.verifiedTileCount ||
        typeof discovery.partialCoverage !== "boolean" ||
        discovery.partialCoverage !== (discovery.verifiedTileCount !== discovery.requestedTileCount) ||
        discovery.sites.some(site => !validSite(site))) return null;

    const sites = discovery.sites.map(site => Object.freeze({
      id: site.id, name: site.name,
      address: site.address ?? null, remarks: site.remarks ?? null,
      sourceUrl: site.sourceUrl, trace: site.trace,
      distanceMetres: site.distanceMetres
    }));
    const known = new Map(sites.map(site => [site.id, site]));
    if (known.size !== sites.length) return null;
    let selectedIds = [];

    return Object.freeze({
      candidates() {
        return sites.map(site => Object.freeze({ ...site, selected: selectedIds.includes(site.id) }));
      },
      selected() {
        return selectedIds.map(id => known.get(id));
      },
      toggle(id) {
        if (!known.has(id)) return { ok: false, reason: "UNVERIFIED_SITE" };
        if (selectedIds.includes(id)) {
          selectedIds = selectedIds.filter(current => current !== id);
          return { ok: true, selected: selectedIds.length };
        }
        if (selectedIds.length >= 2) return { ok: false, reason: "TWO_ONLY" };
        selectedIds = [...selectedIds, id];
        return { ok: true, selected: selectedIds.length };
      },
      coverage() {
        return Object.freeze({
          verified: discovery.verifiedTileCount,
          requested: discovery.requestedTileCount,
          partial: discovery.partialCoverage,
        });
      }
    });
  }

  window.HINANEX_REFERENCE_SITE_COMPARE = Object.freeze({
    apiVersion: "gsi-reference-compare-20261020-v1",
    createSession
  });
})();
