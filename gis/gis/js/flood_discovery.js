(function () {
  "use strict";

  // Client-side *reference discovery*, not an evacuation safety/routing decision.
  // Location stays in this browser; nothing is posted to HINANEX services.
  const OFFICIAL_GSI = /^https:\/\/cyberjapandata\.gsi\.go\.jp\/xyz\/skhb01\/[0-9]+\/[0-9]+\/[0-9]+\.geojson$/;
  const LIMIT = 5;

  function validNumber(value, low, high) {
    return typeof value === "number" && Number.isFinite(value) && value >= low && value <= high;
  }

  function distanceMetres(lat1, lon1, lat2, lon2) {
    const radians = degrees => degrees * Math.PI / 180;
    const a = Math.sin(radians(lat2 - lat1) / 2) ** 2 +
      Math.cos(radians(lat1)) * Math.cos(radians(lat2)) *
      Math.sin(radians(lon2 - lon1) / 2) ** 2;
    return Math.round(6371000 * 2 * Math.asin(Math.min(1, Math.sqrt(a))));
  }

  function discoverReferenceSites(catalog, origin) {
    const blocked = {
      status: "UNVERIFIED_SOURCE",
      sites: [],
      message: "公式の洪水指定情報は独立照合待ちです。既存施設のUNKNOWNを候補に変換しません。"
    };
    if (!validNumber(origin?.latitude, -90, 90) ||
        !validNumber(origin?.longitude, -180, 180)) {
      return { ...blocked, status: "NO_ORIGIN", message: "地図から出発地点を指定してください。" };
    }
    if (!catalog || catalog.status !== "REFERENCE_ONLY" ||
        catalog.source_status !== "C_ACCEPTED" ||
        catalog.catalog_kind !== "flood_designated_emergency_site_reference" ||
        catalog.hazard !== "flood" || catalog.region_code !== "13123" ||
        !Array.isArray(catalog.sites) ||
        !catalog.source_raw_sha256 || !catalog.c_audit_reference) {
      return blocked;
    }
    const ids = new Set();
    const sites = [];
    for (const site of catalog.sites) {
      if (!site || typeof site.source_feature_key !== "string" || !site.source_feature_key ||
          ids.has(site.source_feature_key) ||
          typeof site.name_raw !== "string" || !site.name_raw ||
          !validNumber(site.latitude, -90, 90) ||
          !validNumber(site.longitude, -180, 180) ||
          site.source_raw_sha256 !== catalog.source_raw_sha256 ||
          site.designation_kind !== "designated_emergency_evacuation_site" ||
          site.disaster1_raw !== 1 ||
          site.search_context_region_code !== catalog.region_code ||
          typeof site.source_record_trace !== "string" ||
          site.source_feature_key !== `${site.source_url}#${site.source_record_trace}` ||
          !/^feature_index=[0-9]+$/.test(site.source_record_trace) ||
          (site.address_raw != null && typeof site.address_raw !== "string") ||
          (site.remarks_raw != null && typeof site.remarks_raw !== "string") ||
          site.hazard_dataset !== "GSI_SKHB01_FLOOD" ||
          !OFFICIAL_GSI.test(site.source_url || "")) {
        return blocked; // reject the entire catalog, never silently skip bad rows
      }
      ids.add(site.source_feature_key);
      sites.push({
        id: site.source_feature_key,
        name: site.name_raw,
        address: site.address_raw,
        remarks: site.remarks_raw,
        distanceMetres: distanceMetres(origin.latitude, origin.longitude, site.latitude, site.longitude),
        sourceUrl: site.source_url,
        trace: site.source_record_trace,
        latitude: site.latitude,
        longitude: site.longitude
      });
    }
    sites.sort((a, b) => a.distanceMetres - b.distanceMetres || a.id.localeCompare(b.id));
    return {
      status: "REFERENCE_ONLY",
      sites: sites.slice(0, LIMIT),
      total: sites.length,
      message: "直線距離の近い順に公式掲載地点を表示。安全性・経路・開設状況・行くべき順ではありません。"
    };
  }

  window.HINANEX_FLOOD_DISCOVERY = { distanceMetres, discoverReferenceSites };
})();
