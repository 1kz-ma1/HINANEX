"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const {waitForDevToolsPort} = require("./helpers/chrome-active-port.cjs");
const running = () => ({exitCode:null, signalCode:null});
const ioError = code => Object.assign(Error(code), {code});

test("Chrome startup recovers from missing/locked/unfinished port file", async () => {
  const values = [ioError("ENOENT"), ioError("EBUSY"), ioError("EPERM"), ioError("EACCES"), "", "0\n", "bad\n", "12oops\n", "65536\n", "43210\n/devtools/browser/synthetic\n"];
  const delays = [];
  const port = await waitForDevToolsPort("synthetic-profile", running(), () => "synthetic diagnostics", {
    readFile(file, encoding) {
      assert.equal(file, path.join("synthetic-profile", "DevToolsActivePort"));
      assert.equal(encoding, "utf8");
      const value = values.shift();
      if (value instanceof Error) throw value;
      return value;
    },
    pause:async ms => {delays.push(ms);},
  });
  assert.equal(port, 43210);
  assert.deepEqual(delays, Array(9).fill(100));
  assert.equal(values.length, 0);
});

test("Chrome persistent port lock or malformed contents exhaust the original startup bound", async () => {
  for (const value of [ioError("EBUSY"), "", "NaN\n"]) {
    let reads = 0, elapsed = 0;
    await assert.rejects(waitForDevToolsPort("synthetic-profile", running(), () => "still starting", {
      readFile() {reads++; if (value instanceof Error) throw value; return value;},
      pause:async ms => {elapsed += ms;},
    }), /Chrome CDP startup timed out: still starting/);
    assert.equal(reads, 300);
    assert.equal(elapsed, 30000);
  }
});

test("Chrome unexpected port I/O error fails immediately without retry", async () => {
  const failure = ioError("EIO");
  let waits = 0;
  await assert.rejects(waitForDevToolsPort("synthetic-profile", running(), () => "", {
    readFile() {throw failure;}, pause:async () => {waits++;},
  }), error => error === failure);
  assert.equal(waits, 0);
});

test("Chrome exit during startup fails before trusting a stale port file", async () => {
  for (const child of [{exitCode:1,signalCode:null}, {exitCode:null,signalCode:"SIGTERM"}]) {
    await assert.rejects(waitForDevToolsPort("synthetic-profile", child, () => "synthetic early exit", {
      readFile() {assert.fail("Do not read a dead browser's port");},
      pause:async () => {assert.fail("Do not wait for a dead browser");},
    }), /Chrome exited: synthetic early exit/);
  }
  const child = running();
  let reads = 0;
  await assert.rejects(waitForDevToolsPort("synthetic-profile", child, () => "exit after lock", {
    readFile() {reads++; throw ioError("EBUSY");},
    pause:async () => {child.exitCode = 2;},
  }), /Chrome exited: exit after lock/);
  assert.equal(reads, 1);
});
