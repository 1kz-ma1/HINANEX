"use strict";
// Offline synthetic HTTP security regressions for F02 local Safari preview.
const test = require("node:test");
const assert = require("node:assert/strict");
const http = require("node:http");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { createPreviewServer } = require("../scripts/serve-f02-preview.cjs");

test("F02 local preview exposes only allowlisted assets and one D JSON on 127.0.0.1", async t => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), "hinanex-f02-preview-"));
  const data = path.join(temp, "synthetic-export.json");
  fs.writeFileSync(data, JSON.stringify({ fixture_only: true }));
  const server = createPreviewServer(data);
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  t.after(async () => {
    await new Promise(resolve => server.close(resolve));
    fs.rmSync(temp, { recursive: true, force: true });
  });
  const address = server.address();
  assert.equal(address.address, "127.0.0.1");
  const origin = "http://127.0.0.1:" + address.port;
  const html = await fetch(origin + "/frontend/f02.html");
  assert.equal(html.status, 200);
  assert.match(html.headers.get("content-security-policy"), /default-src 'none'/);
  assert.match(html.headers.get("content-security-policy"), /connect-src 'self'/);
  assert.equal(html.headers.get("referrer-policy"), "no-referrer");
  assert.match(await html.text(), /F02/);
  const dataResponse = await fetch(origin + "/pipeline/data/output/edogawa.json");
  assert.equal(dataResponse.status, 200);
  assert.deepEqual(await dataResponse.json(), { fixture_only: true });
  assert.equal((await fetch(origin + "/frontend/src/f02-page.js")).status, 200);
  for (const forbidden of [
    "/", "/.git/config", "/pipeline/data/raw/edogawa/20251211_hinanhokan.csv",
    "/pipeline/data/normalized/edogawa_shelters.json", "/frontend/index.html",
    "/frontend/../pipeline/data/raw/edogawa/20251211_hinanhokan.csv",
  ]) {
    assert.equal((await fetch(origin + forbidden)).status, 404,
      "Forbidden file should not be served: " + forbidden);
  }
  const post = await fetch(origin + "/frontend/f02.html", { method: "POST" });
  assert.equal(post.status, 405);
  const head = await fetch(origin + "/frontend/f02.html", { method: "HEAD" });
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  const invalidHost = await new Promise((resolve, reject) => {
    const request = http.get(origin + "/frontend/f02.html", {
      headers: { Host: "untrusted.example:" + address.port },
    }, response => { response.resume(); response.on("end", () => resolve(response.statusCode)); });
    request.on("error", reject);
  });
  assert.equal(invalidHost, 403, "Unexpected DNS-rebinding Host must be rejected");
});

test("F02 local preview refuses relative data paths", () => {
  assert.throws(() => createPreviewServer("../pipeline/data/output/edogawa.json"),
    /absolute local path/);
});
