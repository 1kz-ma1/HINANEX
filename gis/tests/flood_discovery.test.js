const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const assert = require("node:assert/strict");

const context = { window: {} };
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.resolve(__dirname, "../gis/js/flood_discovery.js"), "utf8"), context);
const { distanceMetres, discoverReferenceSites } = context.window.HINANEX_FLOOD_DISCOVERY;

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

const full = catalog(Array.from({ length: 10 }, (_, i) => site(String(i), 35.7 + i / 100, 139.9)));
const ranked = discoverReferenceSites(full, point);
assert.equal(ranked.status, "REFERENCE_ONLY");
assert.equal(ranked.total, 10);
assert.equal(ranked.sites.length, 5);
assert.equal(ranked.sites[0].distanceMetres, 0);
assert.equal(ranked.sites[0].name, "TEST_0");
assert.ok(ranked.sites[1].distanceMetres < ranked.sites[4].distanceMetres);
assert.match(ranked.message, /行くべき順ではありません/);
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
console.log("flood_discovery.test.js: OK");
