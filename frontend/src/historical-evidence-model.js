const EXPECTED = [
  ["trace", "T0", "TECHNICAL_SOURCE_OUTPUT_CONSISTENCY", "C_MACHINE_TRACE_PASSED_HUMAN_PENDING"],
  ["abstain", "T1", "UNVERIFIED_PHYSICAL_SITE_NOT_EVALUABLE", "NOT_EVALUABLE"],
  ["negative", "T0_TEST", "SYNTHETIC_NEGATIVE_TEST_NOT_REAL_MISMATCH", "SYNTHETIC_INVALID_INPUT_REJECTED"],
];
const SOURCE_IDS = new Set(["school", "campus", "newsletter", "cross"]);
function check(ok, message) { if (!ok) throw new TypeError("C evidence contract: " + message); }
function validHttps(link) {
  if (typeof link !== "string") return false;
  try { return new URL(link).protocol === "https:"; } catch { return false; }
}
function validateEvidenceDeck(d) {
  check(d && typeof d === "object" && !Array.isArray(d), "invalid root");
  check(d.schema_id === "hinanex.c.midterm_explanation_cases.v0.1", "unsupported C schema");
  check(d.presentation_only === true && d.historical_replay_executed === false &&
    d.historical_prediction_approved === false && d.human_c_approved === false,
    "approval or predictive state cannot be displayed");
  check(d.prediction_denominator === null && d.prediction_numerator === null &&
    d.approved_actual_building_pairs === 0 && d.approved_historical_prediction_inputs === 0,
    "unsupported accuracy or building approval");
  check(d.t1_opening_prediction_accuracy === "NOT_EVALUABLE" && d.t2_hazard_prediction_accuracy === "NOT_RUN",
    "historical forecast promotion");
  check(d.verification_scope === "POST_EVENT_T0_SOURCE_OUTPUT_MACHINE_CHECKS_ONLY__HUMAN_REVIEW_PENDING",
    "unapproved C validation scope");
  check(Array.isArray(d.sources) && d.sources.length === 4, "source registry incomplete");
  check(new Set(d.sources.map(s => s.id)).size === 4 &&
    d.sources.every(s => SOURCE_IDS.has(s.id) && validHttps(s.machine_audit_url) &&
      (s.id === "cross" ? s.official_url === null : validHttps(s.official_url))), "untrusted or incomplete source");
  check(Array.isArray(d.cases) && d.cases.length === 3, "three read-only cases required");
  d.cases.forEach((c, index) => {
    const [id, track, kind, result] = EXPECTED[index];
    check(c && c.id === id && c.track === track && c.kind === kind && c.result === result,
      "case kind or result was reclassified");
    check(c.real_prediction_finding === null && Number.isInteger(c.seconds) && c.seconds === 25,
      "predicted result or replay duration changed");
    check(Array.isArray(c.source_ids) && c.source_ids.length > 0 &&
      c.source_ids.every(s => SOURCE_IDS.has(s)), "case source lineage missing");
    for (const k of ["label", "short_label", "question", "input_title", "input_text",
       "output_title", "output_text", "audit_title", "audit_text", "takeaway", "review_label"]) {
      check(typeof c[k] === "string" && c[k].trim().length > 0, "missing explanatory text: " + k);
    }
  });
  return d;
}
export { validateEvidenceDeck };
