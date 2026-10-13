import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { buildGisRegionUrl } from "../src/region-export-source.js";

const page = await readFile(fileURLToPath(new URL("../index.html", import.meta.url)), "utf8");
const app = await readFile(fileURLToPath(new URL("../src/app.js", import.meta.url)), "utf8");
const supported = ["13123", "15100", "23100"];

test("10/22 B demo keeps exactly the three approved presentation region selectors", () => {
  const buttons = [...page.matchAll(/<button\b[^>]*\bdata-region-code="(\d+)"[^>]*>/g)]
    .map((match) => match[1]);
  assert.deepEqual(buttons, supported);
  assert.match(page, /id="mapBackLink"/);
  assert.match(page, /href="\.\/evidence-case\.html"/);
  assert.match(page, /id="demoNotice"/);
});

test("10/22 B demo builds distinct GIS handoff URLs without implicit suitability", () => {
  for (const code of supported) {
    assert.equal(buildGisRegionUrl(code), "/gis/gis/?region=" + code);
  }
  assert.match(app, /mapBackLink\.href\s*=\s*buildGisRegionUrl/);
  assert.match(app, /demoNotice/);
});
