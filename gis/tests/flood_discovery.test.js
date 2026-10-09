const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const assert = require("node:assert/strict");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, "../gis/js/flood_discovery.js"), "utf8"), context);
const { distanceMetres, discoverReferenceSites, discoverReferenceTiles, sourceTileKey, nearbySourceTiles } = context.window.HINANEX_FLOOD_DISCOVERY;

const point = { latitude: 35.7, longitude: 139.9 };
function site(id, lat, lon) {
  return {
    source_feature_key: `https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson#feature_index=${id}`, name_raw: `TEST_${id}`, address_raw: "TEST address", remarks_raw: null,
    disaster1_raw: 1, search_context_region_code: "13123", latitude: lat, longitude: lon,
    source_url: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson",
    source_record_trace: `feature_index=${id}`, source_raw_sha256: "a".repeat(64),
    designation_kind: "designated_emergency_evacuation_site",
    hazard_dataset: "GSI_SKHB01_FLOOD"
  };
}
function catalog(sites) {
  return {
    catalog_kind: "flood_designated_emergency_site_reference",
    region_code: "13123", hazard: "flood",
    status: "REFERENCE_ONLY", source_status: "C_ACCEPTED",
    https_provenance_status: "MATCH",
    https_provenance_checked_at_utc: "2026-10-09T03:00:00+00:00",
    total_source_records: sites.length,
    source_raw_sha256: "a".repeat(64),
    c_audit_reference: "C-TEST",
    sites
  };
}
assert.equal(distanceMetres(35, 139, 35, 139), 0);
assert.ok(distanceMetres(35, 139, 35.01, 139) > 1000);
assert.equal(discoverReferenceSites(null, point).status, "UNVERIFIED_SOURCE");
assert.equal(discoverReferenceSites(catalog([site("0", 35.7, 139.9)]), null).status, "NO_ORIGIN");
assert.equal(discoverReferenceSites({ ...catalog([site("0", 35.7, 139.9)]), source_status: "PENDING" }, point).sites.length, 0);
assert.equal(discoverReferenceSites({ ...catalog([site("0", 35.7, 139.9)]), region_code: "15100" }, point).sites.length, 0);

// Old, C-only catalog JSON must fail closed even if all site rows look valid.
const acceptedWithoutReplay = catalog([site("0", 35.7, 139.9)]);
for (const unproven of [
  { ...acceptedWithoutReplay, https_provenance_status: undefined },
  { ...acceptedWithoutReplay, https_provenance_status: "PENDING" },
  { ...acceptedWithoutReplay, https_provenance_checked_at_utc: null },
  { ...acceptedWithoutReplay, https_provenance_checked_at_utc: "2026-10-09T03:00:00" },
  { ...acceptedWithoutReplay, total_source_records: 2 }
]) {
  assert.equal(discoverReferenceSites(unproven, point).status, "UNVERIFIED_SOURCE");
  assert.equal(discoverReferenceSites(unproven, point).sites.length, 0);
}

const full = catalog(Array.from({ length: 10 }, (_, i) => site(String(i), 35.7 + i / 1000, 139.9)));
const ranked = discoverReferenceSites(full, point);
assert.equal(ranked.status, "REFERENCE_ONLY");
assert.equal(ranked.total, 10);
assert.equal(ranked.sites.length, 5);
assert.equal(ranked.sites[0].distanceMetres, 0);
assert.equal(ranked.sites[0].name, "TEST_0");
assert.ok(ranked.sites[1].distanceMetres < ranked.sites[4].distanceMetres);
assert.match(ranked.message, /距離は安全性を示さず/);
assert.doesNotMatch(ranked.message, /行くべき順|推奨順位|ランキング/);
assert.match(ranked.message, /江戸川区内の施設とは限らず/);
// The official source is ONE GSI tile, not the entire municipality. A GPS
// fix beyond its coverage must not return misleading distant "nearest" sites.
const outside = discoverReferenceSites(full, { latitude: 35.7, longitude: 140.1 });
assert.equal(outside.status, "ORIGIN_OUTSIDE_SOURCE_TILE");
assert.equal(outside.sites.length, 0);
assert.match(outside.message, /範囲外/);
assert.equal(discoverReferenceSites(full, { latitude: 36.1, longitude: 139.9 }).status, "ORIGIN_OUTSIDE_SOURCE_TILE");
assert.equal(discoverReferenceSites(full, { latitude: 35.7, longitude: 139.9 }).status, "REFERENCE_ONLY");
// A single source URL is insufficient if a row's coordinates fall outside it.
// Fail closed instead of returning a cross-tile record as a nearby facility.
assert.equal(discoverReferenceSites(catalog([site("0", 35.7, 139.9), site("1", 35.7, 140.1)]), point).status, "UNVERIFIED_SOURCE");
assert.equal(discoverReferenceSites(catalog([site("0", 35.7, 139.9), site("1", 35.7, 140.1)]), point).sites.length, 0);

const otherTile = {
  ...site("99", 35.7, 139.9),
  source_url: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/910/403.geojson",
  source_feature_key: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/910/403.geojson#feature_index=99"
};
assert.equal(discoverReferenceSites(catalog([site("0", 35.7, 139.9), otherTile]), point).status, "UNVERIFIED_SOURCE");

for (const bad of [
  { latitude: null }, { latitude: NaN }, { longitude: 190 },
  { source_url: "https://untrusted.example/x" },
  { source_url: "https://cyberjapandata.gsi.go.jp/xyz/skhb04/10/909/403.geojson" },
  { source_raw_sha256: "b".repeat(64) }, { hazard_dataset: "NIIGATA_ODS" },
  { designation_kind: "designated_shelter" }, { disaster1_raw: 0 }
]) {
  const result = discoverReferenceSites(catalog([{ ...site("0", 35.7, 139.9), ...bad }]), point);
  assert.equal(result.status, "UNVERIFIED_SOURCE");
  assert.equal(result.sites.length, 0);
}
assert.equal(discoverReferenceSites(catalog([site("0", 35.7, 139.9), site("0", 35.8, 139.9)]), point).sites.length, 0);

assert.equal(sourceTileKey(point), "10/909/403");
assert.equal(sourceTileKey({ latitude: 35.7, longitude: 140.1 }), "10/910/403");
assert.equal(sourceTileKey({ latitude: 90, longitude: 140.1 }), null);
assert.equal(nearbySourceTiles(point).length, 9);
assert.equal(nearbySourceTiles(point)[0], "10/909/403");
assert.ok(nearbySourceTiles(point).includes("10/910/403"));

const multiOriginOnly = discoverReferenceTiles([full], point);
assert.equal(multiOriginOnly.status, "REFERENCE_ONLY");
assert.equal(multiOriginOnly.total, 10);
assert.match(multiOriginOnly.message, /距離は安全性を表さず/);
assert.doesNotMatch(multiOriginOnly.message, /行くべき順|推奨順位|ランキング/);
assert.equal(multiOriginOnly.verifiedTileCount, 1);
assert.equal(multiOriginOnly.partialCoverage, true);
assert.match(multiOriginOnly.message, /未検証タイル/);

const eastSite = {
  ...site("0", 35.7, 140.1),
  source_url: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/910/403.geojson",
  source_feature_key: "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/910/403.geojson#feature_index=0",
  source_raw_sha256: "b".repeat(64)
};
const eastCatalog = {
  ...catalog([eastSite]), source_raw_sha256: "b".repeat(64),
  c_audit_reference: "C-EAST"
};
const nextTile = { latitude: 35.7, longitude: 140.1 };
const multiEast = discoverReferenceTiles([eastCatalog, full], nextTile);
assert.equal(multiEast.status, "REFERENCE_ONLY");
assert.equal(multiEast.total, 11);
assert.equal(multiEast.sites[0].id, eastSite.source_feature_key);
assert.equal(multiEast.verifiedTileCount, 2);
assert.equal(discoverReferenceTiles([full], nextTile).status, "ORIGIN_OUTSIDE_SOURCE_TILE");
assert.equal(discoverReferenceTiles([eastCatalog], point).status, "ORIGIN_OUTSIDE_SOURCE_TILE");

// A tampered secondary tile blocks ALL returned results, not only that tile.
// Validating from the source-tile center avoids rejecting adjacent entries
// just because the user currently stands in another tile.
for (const badEast of [
  { ...eastCatalog, https_provenance_status: "PENDING" },
  { ...eastCatalog, source_raw_sha256: "c".repeat(64) },
  { ...eastCatalog, sites: [ { ...eastSite, latitude: 35.7, longitude: 139.9 } ] }
]) {
  assert.equal(discoverReferenceTiles([full, badEast], point).status, "UNVERIFIED_SOURCE");
  assert.equal(discoverReferenceTiles([full, badEast], point).sites.length, 0);
}
assert.equal(discoverReferenceTiles([full, full], point).status, "UNVERIFIED_SOURCE");
assert.equal(discoverReferenceTiles([full, eastCatalog], point, "15100").status, "UNVERIFIED_SOURCE");
assert.equal(discoverReferenceTiles(null, point).status, "UNVERIFIED_SOURCE");
assert.equal(discoverReferenceTiles([full], null).status, "NO_ORIGIN");

console.log("flood_discovery.test.js: OK");
