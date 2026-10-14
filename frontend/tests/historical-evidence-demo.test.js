import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { validateEvidenceDeck } from "../src/historical-evidence-model.js";
const read = async () => JSON.parse(await readFile(new URL("../../validation/demo/2019_edogawa_evidence_cases.json", import.meta.url), "utf8"));
test("C-owned real report deck remains explicit about missing predictive approval", async () => {
  const d = validateEvidenceDeck(await read());
  assert.deepEqual(d.cases.map(c => c.id), ["trace", "abstain", "negative"]);
  assert.deepEqual(d.cases.map(c => c.track), ["T0", "T1", "T0_TEST"]);
  assert.equal(d.prediction_denominator, null);
  assert.equal(d.approved_actual_building_pairs, 0);
  assert.equal(d.cases[2].real_prediction_finding, null);
});
test("future prediction, synthetic MISMATCH or unsupported physical-site approval cannot be displayed", async () => {
  const raw = await read();
  for (const change of [
    d => { d.historical_prediction_approved = true; },
    d => { d.prediction_denominator = 66; },
    d => { d.approved_actual_building_pairs = 1; },
    d => { d.cases[0].result = "MATCH"; },
    d => { d.cases[1].result = "ABSTAIN"; },
    d => { d.cases[2].result = "MISMATCH"; },
    d => { d.cases[2].real_prediction_finding = "MISMATCH"; },
    d => { d.cases[0].source_ids = ["made_up"]; },
    d => { d.sources[0].official_url = "javascript:alert(1)"; },
    d => { d.cases.splice(1, 1); },
  ]) {
    const d = structuredClone(raw);
    change(d);
    assert.throws(() => validateEvidenceDeck(d), /C evidence contract/);
  }
});
test("standalone presenter view uses accessible buttons and read-only C data", async () => {
  const page = await readFile(new URL("../historical-evidence-demo.html", import.meta.url), "utf8");
  const controller = await readFile(new URL("../src/historical-evidence-demo.js", import.meta.url), "utf8");
  for (const id of ["trace", "abstain", "negative"]) assert.match(page, new RegExp('data-case-id="' + id + '"'));
  for (const id of ["playButton","pauseButton","nextButton","resetButton","sourceLinks","loadStatus","walkthrough"]) {
    assert.ok(page.includes('id="' + id + '"'));
  }
  assert.match(page, /実災害の予測成績ではありません/);
  assert.match(page, /合成負系テスト/);
  assert.match(controller, /response\.ok/);
  assert.match(controller, /aria-pressed/);
  assert.match(controller, /replaceChildren/);
  assert.doesNotMatch(controller, /\.innerHTML/);
  assert.match(controller, /stopClock\(\)/);
  assert.match(controller, /visibilitychange/);
});
