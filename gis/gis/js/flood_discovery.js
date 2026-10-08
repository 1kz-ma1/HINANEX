(function () {
  "use strict";

  // Client-side *reference discovery*, not an evacuation safety/routing decision.
  // Location stays in this browser; nothing is posted to HINANEX services.
  const OFFICIAL_GSI = /^https:\/\/cyberjapandata\.gsi\.go\.jp\/xyz\/skhb01\/[0-9]+\/[0-9]+\/[0-9]+\.geojson$/;
  const LIMIT = 5;

  // GSI slippy tiles describe a geographic rectangle, not a municipality.
  // A single archived z/x/y tile cannot answer queries from arbitrary GPS
  // positions or prove the named municipality contains the facility.
  function containingTile(origin, zoom) {
    if (!Number.isInteger(zoom) || zoom < 0 || zoom > 20 ||
        Math.abs(origin.latitude) > 85.05112878) return null;
    const n = 2 ** zoom;
    const x = Math.floor((origin.longitude + 180) / 360 * n);
    const radians = origin.latitude * Math.PI / 180;
    const mercatorY = (1 - Math.asinh(Math.tan(radians)) / Math.PI) / 2;
    const y = Math.floor(mercatorY * n);
    return {
      x: Math.max(0, Math.min(n - 1, x)),
      y: Math.max(0, Math.min(n - 1, y))
    };
  }

  function officialTileKey(value) {
    const match = OFFICIAL_GSI.exec(value || "");
    if (!match) return null;
    const path = value.match(/\/skhb01\/(\d+)\/(\d+)\/(\d+)\.geojson$/);
    if (!path) return null;
    const [, z, x, y] = path.map(Number);
    const n = 2 ** z;
    if (z > 20 || x >= n || y >= n) return null;
    return { z, x, y };
  }

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
        // The D exporter introduced a separate official-HTTPS replay gate in #72.
        // A previously generated C-only JSON must no longer be displayable.
        catalog.https_provenance_status !== "MATCH" ||
        typeof catalog.https_provenance_checked_at_utc !== "string" ||
        !/^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|\\+00:00)$/.test(catalog.https_provenance_checked_at_utc) ||
        !Number.isFinite(Date.parse(catalog.https_provenance_checked_at_utc)) ||
        !Number.isInteger(catalog.total_source_records) ||
        catalog.total_source_records !== catalog.sites?.length ||
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
    // This v1 catalog producer accepts exactly one tile. A browser location
    // outside the tile must not receive arbitrary faraway reference sites.
    const tileKeys = new Set(catalog.sites.map(site => site.source_url));
    if (tileKeys.size !== 1 || sites.length === 0) return blocked;
    const sourceTile = officialTileKey(sites[0].sourceUrl);
    // A mislabeled or corrupted source row must not escape the audited tile.
    // Check every coordinate, not just the user's search origin.
    if (!sourceTile || sites.some(site => {
      const tile = containingTile(site, sourceTile.z);
      return !tile || tile.x !== sourceTile.x || tile.y !== sourceTile.y;
    })) return blocked;
    const originTile = containingTile(origin, sourceTile.z);
    if (!originTile || originTile.x !== sourceTile.x || originTile.y !== sourceTile.y) {
      return {
        status: "ORIGIN_OUTSIDE_SOURCE_TILE",
        sites: [],
        message: "指定地点は今回取得した公式データ1タイルの範囲外です。別地域の施設を近隣候補として表示しません。対象範囲の公式データ追加が必要です。"
      };
    }

    sites.sort((a, b) => a.distanceMetres - b.distanceMetres || a.id.localeCompare(b.id));
    return {
      status: "REFERENCE_ONLY",
      sites: sites.slice(0, LIMIT),
      total: sites.length,
      message: "取得した国土地理院の1タイル内の掲載地点を直線距離順に表示。江戸川区内の施設とは限らず、安全性・経路・開設状況・行くべき順ではありません。"
    };
  }

  window.HINANEX_FLOOD_DISCOVERY = { distanceMetres, discoverReferenceSites };
})();
