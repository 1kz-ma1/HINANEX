"use strict";
const fs = require("node:fs");
const path = require("node:path");
const wait = ms => new Promise(resolve => setTimeout(resolve, ms));

// Chrome can create this file before its contents are readable/complete.
// Keep the wait bounded; a timeout must still fail.
async function waitForDevToolsPort(profile, child, diagnostics, {
  readFile = fs.readFileSync, pause = wait, maxAttempts = 300,
} = {}) {
  const active = path.join(profile, "DevToolsActivePort");
  let lastRead = "not attempted";
  for (let i = 0; i < maxAttempts; i++) {
    if (child.exitCode !== null || child.signalCode !== null) throw Error("Chrome exited: " + diagnostics());
    try {
      const firstLine = readFile(active, "utf8").split("\n")[0].trim();
      const port = Number(firstLine);
      if (/^\d+$/.test(firstLine) && Number.isInteger(port) && port > 0 && port <= 65535) return port;
      lastRead = firstLine ? "invalid port" : "empty first line";
    } catch (error) {
      if (!["ENOENT", "EBUSY", "EPERM", "EACCES"].includes(error.code)) throw error;
      lastRead = error.code;
    }
    await pause(100);
  }
  throw Error("Chrome CDP startup timed out: " + diagnostics() +
    "\nDevToolsActivePort after " + maxAttempts + " reads: " + lastRead);
}

module.exports = {waitForDevToolsPort};
