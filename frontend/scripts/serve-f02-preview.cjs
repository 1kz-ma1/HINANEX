#!/usr/bin/env node
"use strict";
// F02 local-only, read-only preview for Safari/VoiceOver manual review.
// This server serves ONLY the F02 consumer assets and one generated D JSON.
// It does not certify shelter status, safety, official provenance or publication.
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { spawnSync } = require("node:child_process");

const repoRoot = path.resolve(__dirname, "../..");
const allowedAssets = Object.freeze({
  "/frontend/f02.html": { filename: "frontend/f02.html", type: "text/html; charset=utf-8" },
  "/frontend/f02.css": { filename: "frontend/f02.css", type: "text/css; charset=utf-8" },
  "/frontend/src/f02-page.js": { filename: "frontend/src/f02-page.js", type: "text/javascript; charset=utf-8" },
  "/frontend/src/f02-shelter-reference.js": { filename: "frontend/src/f02-shelter-reference.js", type: "text/javascript; charset=utf-8" },
  "/frontend/src/region-export-loader.js": { filename: "frontend/src/region-export-loader.js", type: "text/javascript; charset=utf-8" },
  "/frontend/src/region-export-source.js": { filename: "frontend/src/region-export-source.js", type: "text/javascript; charset=utf-8" },
});

function createPreviewServer(dataFile) {
  if (typeof dataFile !== "string" || !path.isAbsolute(dataFile)) {
    throw new TypeError("F02 preview dataFile must be an absolute local path");
  }
  const server = http.createServer((req, res) => {
    const address = server.address();
    const host = address ? "127.0.0.1:" + address.port : "";
    // Require an exact loopback Host, including port, to limit DNS rebinding.
    if (req.headers.host !== host) {
      res.writeHead(403, { "Cache-Control": "no-store" });
      res.end("Invalid local Host");
      return;
    }
    if (req.method !== "GET" && req.method !== "HEAD") {
      res.writeHead(405, { Allow: "GET, HEAD", "Cache-Control": "no-store" });
      res.end();
      return;
    }
    let pathname;
    try {
      pathname = new URL(req.url, "http://127.0.0.1").pathname;
    } catch {
      res.writeHead(400, { "Cache-Control": "no-store" });
      res.end();
      return;
    }
    const asset = allowedAssets[pathname];
    const isData = pathname === "/pipeline/data/output/edogawa.json";
    if (!asset && !isData) {
      res.writeHead(404, { "Cache-Control": "no-store" });
      res.end("Not served");
      return;
    }
    // No URL-derived filesystem path is ever resolved or opened.
    const filePath = isData ? dataFile : path.resolve(repoRoot, asset.filename);
    const contentType = isData ? "application/json; charset=utf-8" : asset.type;
    let body;
    try {
      body = fs.readFileSync(filePath);
    } catch {
      res.writeHead(503, { "Cache-Control": "no-store" });
      res.end("F02 preview asset unavailable");
      return;
    }
    res.writeHead(200, {
      "Content-Type": contentType,
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      "Referrer-Policy": "no-referrer",
      "X-Frame-Options": "DENY",
      "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    });
    if (req.method === "HEAD") {
      res.end();
    } else {
      res.end(body);
    }
  });
  return server;
}

function main() {
  const dataFile = path.resolve(process.env.F02_REAL_EXPORT_PATH ||
    path.join(repoRoot, "pipeline/data/output/edogawa.json"));
  const checker = path.resolve(__dirname, "check-f02-real-export.js");
  const gate = spawnSync(process.execPath, [checker, dataFile], {
    encoding: "utf8",
    timeout: 15000,
    maxBuffer: 1048576,
  });
  if (gate.error || gate.status !== 0) {
    process.stderr.write("F02_PREVIEW_BLOCKED: local D JSON did not pass consumer structural gate\n");
    if (gate.stderr) process.stderr.write(gate.stderr + "\n");
    if (gate.error) process.stderr.write(String(gate.error) + "\n");
    process.exitCode = 1;
    return;
  }
  const server = createPreviewServer(dataFile);
  server.once("error", error => {
    process.stderr.write("F02_PREVIEW_ERROR: " + error.message + "\n");
    process.exitCode = 1;
  });
  server.listen(0, "127.0.0.1", () => {
    const port = server.address().port;
    process.stdout.write(
      "F02_PREVIEW_LOCAL_ONLY: http://127.0.0.1:" + port + "/frontend/f02.html\n" +
      "Only F02 assets and the locally generated D JSON are accessible. No public binding.\n" +
      "NOT_APPROVED: real-world facility identity, flood suitability, open status, and publication.\n" +
      "Press Ctrl+C to stop this preview.\n"
    );
  });
  process.on("SIGINT", () => server.close(() => process.exit(0)));
  process.on("SIGTERM", () => server.close(() => process.exit(0)));
}

if (require.main === module) main();
module.exports = { createPreviewServer };
