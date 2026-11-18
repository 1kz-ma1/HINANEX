"use strict";
const fs = require("node:fs");
const path = require("node:path");
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Chrome can create this file before its contents are readable/complete.
// Preserve the existing 300 x 100ms bound; a timeout must still fail.
async function waitForDevToolsPort(profile, child, diagnostics, {
  readFile = fs.readFileSync, pause = wait,
} = {}) {
  const active = path.join(profile, "DevToolsActivePort");
  for (let i = 0; i < 300; i++) {
    if (child.exitCode !== null || child.signalCode !== null) throw Error("Chrome exited: " + diagnostics());
    try {
      const firstLine = readFile(active, "utf8").split("\n")[0].trim();
      const port = Number(firstLine);
      if (/^\d+$/.test(firstLine) && Number.isInteger(port) && port > 0 && port <= 65535) return port;
    } catch (error) {
      if (!["ENOENT", "EBUSY", "EPERM", "EACCES"].includes(error.code)) throw error;
    }
    await pause(100);
  }
  throw Error("Chrome CDP startup timed out: " + diagnostics());
}

module.exports = {waitForDevToolsPort};
