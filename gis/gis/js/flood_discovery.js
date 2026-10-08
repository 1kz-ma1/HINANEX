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

  function discoverReferenceSites(catalog, origin, expectedRegionCode = "13123") {
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
        !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$/.test(catalog.https_provenance_checked_at_utc) ||
        !Number.isFinite(Date.parse(catalog.https_provenance_checked_at_utc)) ||
        !Number.isInteger(catalog.total_source_records) ||
        catalog.total_source_records !== catalog.sites?.length ||
        catalog.catalog_kind !== "flood_designated_emergency_site_reference" ||
        catalog.hazard !== "flood" || catalog.region_code !== expectedRegionCode ||
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


  // GSI skhb01 data tiles use z=10. Only C-vetted local JSON is fetched.
  const REFERENCE_ZOOM = 10;
  function sourceTileKey(origin) {
    if (!validNumber(origin?.latitude, -85.05112878, 85.05112878) ||
        !validNumber(origin?.longitude, -180, 180)) return null;
    const tile = containingTile(origin, REFERENCE_ZOOM);
    return tile ? REFERENCE_ZOOM + "/" + tile.x + "/" + tile.y : null;
  }
  function nearbySourceTiles(origin) {
    const key = sourceTileKey(origin);
    if (!key) return [];
    const parts = key.split("/");
    const x = Number(parts[1]), y = Number(parts[2]), n = 2 ** REFERENCE_ZOOM;
    const items = [key];
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dy) continue;
        const nextY = y + dy;
        if (nextY < 0 || nextY >= n) continue;
        items.push(REFERENCE_ZOOM + "/" + ((x + dx + n) % n) + "/" + nextY);
      }
    }
    return items;
  }
  function tileCenter(tile) {
    const n = 2 ** tile.z;
    return {
      longitude: (tile.x + 0.5) / n * 360 - 180,
      latitude: Math.atan(Math.sinh(Math.PI * (1 - 2 * (tile.y + 0.5) / n))) * 180 / Math.PI
    };
  }
  function discoverReferenceTiles(catalogs, origin, regionCode = "13123") {
    const blocked = {
      status: "UNVERIFIED_SOURCE", sites: [],
      message: "公式の洪水指定情報は独立照合待ちです。避難場所が存在しないことを意味しません。"
    };
    const originKey = sourceTileKey(origin);
    if (!originKey) return {
      ...blocked, status: "NO_ORIGIN", message: "有効な出発地点を地図から選択してください。"
    };
    if (!["13123", "15100", "23100"].includes(regionCode) ||
        !Array.isArray(catalogs) || catalogs.length > 9) return blocked;
    const permittedKeys = new Set(nearbySourceTiles(origin));
    const seenTiles = new Set(), seenSites = new Set(), sites = [];
    for (const catalog of catalogs) {
      const firstUrl = catalog?.sites?.[0]?.source_url;
      const tile = officialTileKey(firstUrl);
      const key = tile && tile.z + "/" + tile.x + "/" + tile.y;
      if (!key || !permittedKeys.has(key) || seenTiles.has(key) ||
          tile.z !== REFERENCE_ZOOM || catalog.region_code !== regionCode) return blocked;
      // validate every record with its own tile center, not user position
      const accepted = discoverReferenceSites(catalog, tileCenter(tile), regionCode);
      if (accepted.status !== "REFERENCE_ONLY") return blocked;
      seenTiles.add(key);
      for (const raw of catalog.sites) {
        if (seenSites.has(raw.source_feature_key)) return blocked;
        seenSites.add(raw.source_feature_key);
        sites.push({
          id: raw.source_feature_key,
          name: raw.name_raw, address: raw.address_raw, remarks: raw.remarks_raw,
          sourceUrl: raw.source_url, trace: raw.source_record_trace,
          latitude: raw.latitude, longitude: raw.longitude,
          distanceMetres: distanceMetres(origin.latitude, origin.longitude, raw.latitude, raw.longitude)
        });
      }
    }
    // A verified neighboring tile never substitutes for the origin tile.
    if (!seenTiles.has(originKey)) return {
      ...blocked, status: "ORIGIN_OUTSIDE_SOURCE_TILE",
      message: "指定地点のGSIタイルはまだ独立検証・配信されていません。周辺の参考地点も表示しません。"
    };
    sites.sort((a, b) => a.distanceMetres - b.distanceMetres || a.id.localeCompare(b.id));
    const partial = seenTiles.size !== permittedKeys.size;
    return {
      status: "REFERENCE_ONLY", sites: sites.slice(0, LIMIT), total: sites.length,
      verifiedTileCount: seenTiles.size, requestedTileCount: permittedKeys.size,
      partialCoverage: partial,
      message: "公式指定場所を検証済み" + seenTiles.size + "タイル内で直線距離順に参考表示。" +
        (partial ? "周辺の未検証タイルがあるため、地域全体の最寄り順や網羅性は保証しません。" : "") +
        " 自治体所属・安全性・経路・開設状況は未認定で、行くべき順ではありません。"
    };
  }

  window.HINANEX_FLOOD_DISCOVERY = { distanceMetres, discoverReferenceSites, sourceTileKey, nearbySourceTiles, discoverReferenceTiles };
})();
