// F05/B2 is a self-contained SYNTHETIC-ONLY comparison model.
// It MUST NOT be connected to real RegionExport, GPS, safety, or routing.
export const B2_STATUSES = Object.freeze(["CANDIDATE", "EXCLUDED", "UNKNOWN"]);
export const B2_FILTERS = Object.freeze(["ALL", ...B2_STATUSES]);
const STATUSES = new Set(B2_STATUSES);
const FILTERS = new Set(B2_FILTERS);
const text = v => typeof v === "string" && v.trim().length > 0;
const nullableText = v => v === null || text(v);
const normalize = v => v.normalize("NFKC").toLocaleLowerCase("ja-JP");

export function isB2Loopback(origin) {
  if (typeof origin !== "string") return false;
  try {
    const u = new URL(origin);
    return u.protocol === "http:" && !u.username && !u.password &&
      (u.hostname === "127.0.0.1" || u.hostname === "localhost" || u.hostname === "[::1]") &&
      u.origin === origin;
  } catch { return false; }
}

function stopped(state, message) {
  return Object.freeze({
    state, message, total: 0, counts: Object.freeze({CANDIDATE:0, EXCLUDED:0, UNKNOWN:0}),
    selected: () => [], choice: () => null, rows: () => [],
    setCriteria: () => ({ok:false, reason:state}),
    toggle: () => ({ok:false, reason:state}),
    choose: () => ({ok:false, reason:state}),
    clear: () => ({ok:false, reason:state})
  });
}

/**
 * Accepts only hardcoded synthetic records owned by the B2 prototype.
 * The D status names are copied verbatim as experiment labels; no status
 * calculation, source approval or real-data join exists in this module.
 */
export function createB2Session(snapshot) {
  if (snapshot === null || snapshot === undefined) {
    return stopped("NO_SCENARIO", "合成シナリオ未選択。候補ゼロとは異なります。");
  }
  if (snapshot?.kind === "SIMULATED_LOAD_ERROR" &&
      snapshot?.fixtureId === "synthetic-b2-load-error" &&
      snapshot?.syntheticOnly === true) {
    return stopped("LOAD_ERROR", "模擬データ取得失敗。前回の比較結果は再利用しません。");
  }
  if (snapshot?.kind !== "SYNTHETIC_FIXTURE" ||
      snapshot?.syntheticOnly !== true ||
      !text(snapshot.fixtureId) || !snapshot.fixtureId.startsWith("synthetic-b2-") ||
      snapshot?.hazardScope !== "SYNTHETIC_FLOOD" ||
      snapshot?.regionCode !== "TEST_ONLY" ||
      !text(snapshot.sourceId) || !snapshot.sourceId.startsWith("SYN-B2-") ||
      !Array.isArray(snapshot.records)) {
    return stopped("INVALID", "合成Fixtureの範囲・形式を検証できません。比較を停止しました。");
  }
  const seen = new Set();
  const safe = [];
  try {
    for (const r of snapshot.records) {
      if (!r || !text(r.id) || seen.has(r.id) || !text(r.name) ||
          !nullableText(r.address) || !STATUSES.has(r.status) ||
          !text(r.reason) || r.sourceId !== snapshot.sourceId ||
          r.hazardScope !== snapshot.hazardScope ||
          !text(r.sourceTrace) || !nullableText(r.rawValue) ||
          !Array.isArray(r.unknowns) || !r.unknowns.every(text) ||
          r.openStatus !== null || r.safetyVerified !== false) {
        throw new Error("Invalid synthetic row");
      }
      seen.add(r.id);
      safe.push(Object.freeze({
        id:r.id, name:r.name, address:r.address, status:r.status, reason:r.reason,
        sourceId:r.sourceId, sourceTrace:r.sourceTrace, hazardScope:r.hazardScope,
        rawValue:r.rawValue, unknowns:Object.freeze([...r.unknowns]),
        openStatus:null, safetyVerified:false
      }));
    }
  } catch {
    return stopped("INVALID", "合成FixtureのID・出典・記号の整合が取れません。表示を停止しました。");
  }
  const rows = Object.freeze(safe);
  const counts = Object.freeze({
    CANDIDATE: rows.filter(r=>r.status === "CANDIDATE").length,
    EXCLUDED: rows.filter(r=>r.status === "EXCLUDED").length,
    UNKNOWN: rows.filter(r=>r.status === "UNKNOWN").length
  });
  let query = "", filter = "ALL", ids = [], choiceId = null;
  const visible = () => rows.filter(r =>
    (filter === "ALL" || r.status === filter) &&
    normalize([r.name, r.address ?? ""].join(" ")).includes(normalize(query.trim()))
  );
  const clearSelection = () => { ids = []; choiceId = null; };
  return Object.freeze({
    state:rows.length ? "READY" : "EMPTY_DATASET",
    message: rows.length ? "合成Fixtureを表示しています。現在の災害・施設指定を表しません。" :
      "合成Fixtureは0件です。通信失敗や条件一致0件とは区別します。",
    sourceId:snapshot.sourceId, fixtureId:snapshot.fixtureId, hazardScope:snapshot.hazardScope,
    total:rows.length, counts,
    rows: () => Object.freeze([...visible()]),
    selected: () => Object.freeze(ids.map(id=>rows.find(r=>r.id === id))),
    choice: () => rows.find(r=>r.id === choiceId) ?? null,
    setCriteria(nextQuery, nextFilter) {
      if (typeof nextQuery !== "string" || !FILTERS.has(nextFilter)) {
        return {ok:false, reason:"INVALID_CRITERIA"};
      }
      if (query !== nextQuery || filter !== nextFilter) {
        query = nextQuery; filter = nextFilter; clearSelection();
      }
      return {ok:true};
    },
    toggle(id) {
      if (!visible().some(r=>r.id === id)) return {ok:false, reason:"NOT_VISIBLE"};
      if (ids.includes(id)) ids = ids.filter(x=>x !== id);
      else if (ids.length >= 2) return {ok:false, reason:"TWO_MAX"};
      else ids = [...ids, id];
      choiceId = null;
      return {ok:true, count:ids.length};
    },
    choose(id) {
      if (ids.length !== 2 || !ids.includes(id)) return {ok:false, reason:"COMPARE_TWO_FIRST"};
      choiceId = id;
      return {ok:true, id};
    },
    clear() { clearSelection(); return {ok:true}; }
  });
}
