const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const assert = require("node:assert/strict");

const context = { window: {} };
vm.createContext(context);
const read = name => fs.readFileSync(path.resolve(__dirname, "../gis/js", name), "utf8");
vm.runInContext(read("flood_discovery.js"), context);
vm.runInContext(read("reference_site_compare.js"), context);
const discovery = context.window.HINANEX_FLOOD_DISCOVERY;
const compare = context.window.HINANEX_REFERENCE_SITE_COMPARE;
assert.equal(compare.apiVersion, "gsi-reference-compare-20261020-v1");

const origin = { latitude: 35.7, longitude: 139.9 };
const url = "https://cyberjapandata.gsi.go.jp/xyz/skhb01/10/909/403.geojson";
function feature(index) {
  return {
    source_feature_key: url + "#feature_index=" + index,
    name_raw: index === 1 ? "<img src=x onerror=alert(1)>" : "TEST_GSI_" + index,
    address_raw: index === 1 ? null : "原文住所" + index,
    remarks_raw: "備考" + index,
    disaster1_raw: 1, search_context_region_code: "13123",
    latitude: 35.7 + index / 1000, longitude: 139.9,
    source_url: url, source_record_trace: "feature_index=" + index,
    source_raw_sha256: "a".repeat(64),
    designation_kind: "designated_emergency_evacuation_site",
    hazard_dataset: "GSI_SKHB01_FLOOD"
  };
}
const records = Array.from({ length: 3 }, (_, index) => feature(index));
const catalog = {
  catalog_kind: "flood_designated_emergency_site_reference",
  region_code: "13123", hazard: "flood", status: "REFERENCE_ONLY",
  source_status: "C_ACCEPTED", https_provenance_status: "MATCH",
  https_provenance_checked_at_utc: "2026-10-09T03:00:00+00:00",
  total_source_records: records.length,
  source_raw_sha256: "a".repeat(64), c_audit_reference: "TEST_ONLY",
  sites: records
};
const audited = discovery.discoverReferenceTiles([catalog], origin);
assert.equal(audited.status, "REFERENCE_ONLY");
const session = compare.createSession(audited);
assert.ok(session, "only vetted reference discovery can create a comparison session");
assert.equal(session.candidates().length, 3);
assert.equal(session.selected().length, 0);
assert.equal(session.coverage().partial, true);

const [a, b, c] = session.candidates();
assert.equal(session.toggle(a.id).ok, true);
assert.equal(session.toggle(b.id).ok, true);
assert.equal(session.selected().length, 2);
assert.equal(session.toggle(c.id).reason, "TWO_ONLY");
assert.equal(session.selected().length, 2);
assert.equal(session.toggle(b.id).ok, true);
assert.equal(session.selected().length, 1);
assert.equal(session.toggle(c.id).ok, true);
assert.equal(session.selected()[1].id, c.id);
assert.equal(session.toggle("not-in-verified-catalog").reason, "UNVERIFIED_SITE");
assert.equal(session.selected()[0].address, "原文住所0");
assert.equal(session.selected()[1].address, "原文住所2");
assert.ok(!Object.hasOwn(session.selected()[0], "safe"));
assert.ok(!Object.hasOwn(session.selected()[0], "recommended"));
assert.ok(!Object.hasOwn(session.selected()[0], "travelTime"));
assert.ok(Object.isFrozen(session.selected()[0]));

assert.equal(compare.createSession(null), null);
assert.equal(compare.createSession({ ...audited, status: "UNVERIFIED_SOURCE" }), null);
assert.equal(compare.createSession({ ...audited, sites: [] }), null);
assert.equal(compare.createSession({ ...audited, sites: [audited.sites[0]] }), null, "one vetted point is not enough for two-site comparison");
assert.equal(compare.createSession({ ...audited, verifiedTileKeys: [] }), null);
assert.equal(compare.createSession({ ...audited, sites: [...audited.sites, audited.sites[0]] }), null);
assert.equal(compare.createSession({ ...audited, sites: [{ ...audited.sites[0], id: "forged" }] }), null);
assert.equal(compare.createSession({ ...audited, sites: [{ ...audited.sites[0], sourceUrl: "https://fake.example/test" }] }), null);
assert.equal(compare.createSession({ ...audited, partialCoverage: false }), null);
assert.equal(compare.createSession({ ...audited, verifiedTileCount: 0 }), null);
assert.equal(compare.createSession({
  ...audited, sites: [{ ...audited.sites[0], distanceMetres: NaN }]
}), null);
assert.equal(discovery.discoverReferenceTiles([catalog], {
  latitude: 35.7, longitude: 140.1
}).status, "ORIGIN_OUTSIDE_SOURCE_TILE");

const html = fs.readFileSync(path.resolve(__dirname, "../gis/index.html"), "utf8");
const mapCode = read("map.js");
const css = fs.readFileSync(path.resolve(__dirname, "../gis/css/reference_site_compare.css"), "utf8");
for (const id of ["referenceCompareOpen", "referenceComparePanel", "referenceCompareTitle",
  "referenceCompareClose", "referenceCompareStatus", "referenceCompareChoices", "referenceCompareResult"]) {
  assert.equal((html.match(new RegExp('id="' + id + '"', "g")) || []).length, 1,
    "must include exactly one user control: " + id);
}
assert.match(html, /id="referenceCompareOpen"[^>]+hidden disabled/);
assert.match(html, /id="referenceComparePanel"[^>]+hidden/);
assert.match(html, /js\/reference_site_compare\.js\?v=gsi-reference-compare-20261020-v1/);
assert.match(html, /css\/reference_site_compare\.css\?v=gsi-reference-compare-20261020-v1/);
assert.ok(html.indexOf('js/reference_site_compare.js?') < html.indexOf('js/map.js?'));
assert.match(mapCode, /resetReferenceComparison\(\);\s+clearReferenceMap\(\)/);
assert.match(mapCode, /renderReferenceMap\(discovery\);\s+enableReferenceComparison\(discovery\)/);
assert.match(mapCode, /textContent = value/);
assert.match(mapCode, /comparisonElement\("a", "GSI公式GeoJSONの元データを確認/);
assert.match(mapCode, /link\.rel = "noopener noreferrer"/);
assert.match(css, /@media\(max-width:680px\)/);
assert.match(css, /\.reference-compare-header\{[^}]*position:sticky/);
assert.match(mapCode, /map\.closePopup\?\.\(\)/);
assert.match(mapCode, /const comparing = document\.getElementById\("referenceComparePanel"\)\?\.hidden === false/);
assert.match(html, /現在の開設・混雑・道路の安全性や自治体施設との同一性は検証していません/);
console.log("reference_site_compare.test.js: OK");
