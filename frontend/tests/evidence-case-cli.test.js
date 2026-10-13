import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtemp, readFile, writeFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const here = resolve(fileURLToPath(new URL(".", import.meta.url)));
const script = resolve(here, "../scripts/check-c-evidence-case.js");
const fixture = resolve(here, "../mock/shimokamata-evidence-ui-preview.json");

test("CLI accepts source-pinned educational C contract fixture without live-safety conclusions", () => {
  const result = spawnSync(process.execPath, [script, fixture], { encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /opening=UNKNOWN/);
  assert.match(result.stdout, /stages=3/);
  assert.match(result.stdout, /sources=4/);
});

test("CLI rejects tampered site-opening C export without printing source", async () => {
  const folder = await mkdtemp(resolve(tmpdir(), "hinanex-b-c-case-"));
  try {
    const file = resolve(folder, "tampered.json");
    const data = JSON.parse(await readFile(fixture, "utf8"));
    data.demo_states[2].current_operational_status = "OPEN";
    data.private_original_reply = "DO-NOT-PRINT-SECRET";
    await writeFile(file, JSON.stringify(data));
    const result = spawnSync(process.execPath, [script, file], { encoding: "utf8" });
    assert.equal(result.status, 1);
    assert.match(result.stderr, /REJECTED/);
    assert.doesNotMatch(result.stderr, /DO-NOT-PRINT-SECRET/);
  } finally {
    await rm(folder, { recursive: true, force: true });
  }
});
