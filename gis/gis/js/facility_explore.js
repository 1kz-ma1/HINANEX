(function () {
  "use strict";
  // Read-only GIS consumer of D RegionExport; not a disaster-safety assessment.
  const VALID = new Set(["CANDIDATE", "EXCLUDED", "UNKNOWN"]);
  const PAGE_SIZE = 20;

  function sourceLink(value) {
    if (value == null || value === "") return null;
    if (typeof value !== "string") throw new Error("Invalid source URL");
    let parsed;
    try { parsed = new URL(value); } catch { throw new Error("Invalid source URL"); }
    if (parsed.protocol !== "https:" || !parsed.hostname || parsed.username ||
        parsed.password || /[\u0000-\u001f]/.test(value)) {
      throw new Error("Untrusted source URL");
    }
    return parsed.href;
  }

  function createSession(summary) {
    if (!summary || !summary.dataset) {
      return { state: "NO_DATASET", message: "地域の施設データは未取得です。施設が存在しないという意味ではありません。" };
    }
    if (!summary.floodScenario) {
      return { state: "NO_SCENARIO", message: "洪水の評価情報を確認できません。施設の安全性や適合性は判断できません。" };
    }
    const original = summary.records;
    const facts = summary.floodScenario.byId;
    if (!summary.region?.code || !Array.isArray(original) ||
        (typeof facts?.get !== "function" || typeof facts?.has !== "function" ||
          typeof facts?.size !== "number") || facts.size !== original.length) {
      return { state: "INVALID", message: "地域と洪水評価の施設対応を確認できません。比較を停止しました。" };
    }
    const known = new Set();
    const rows = [];
    const counts = { CANDIDATE: 0, EXCLUDED: 0, UNKNOWN: 0 };
    try {
      for (const record of original) {
        if (!record || typeof record.id !== "string" || !record.id.trim() ||
            known.has(record.id) || typeof record.name !== "string" || !record.name.trim()) {
          throw new Error("Invalid or duplicate facility identity");
        }
        known.add(record.id);
        const fact = facts.get(record.id);
        if (!fact || !VALID.has(fact.status) ||
            typeof fact.reason !== "string" || typeof fact.hazardScopeRaw !== "string" ||
            !["DIRECT_SAME_SOURCE", "UNVERIFIED"].includes(fact.joinStatus)) {
          throw new Error("Invalid scenario fact");
        }
        const url = sourceLink(fact.sourceUrl);
        if (fact.status !== "UNKNOWN" && (
            fact.joinStatus !== "DIRECT_SAME_SOURCE" ||
            fact.hazardScopeRaw !== "災害種別_洪水" ||
            typeof fact.officialStatusRaw !== "string" || !fact.officialStatusRaw.trim() ||
            typeof fact.sourceRecordTrace !== "string" || !fact.sourceRecordTrace.trim() || !url
        )) throw new Error("Unverified decisive classification");
        counts[fact.status]++;
        rows.push(Object.freeze({
          id: record.id, name: record.name,
          address: typeof record.address === "string" ? record.address : null,
          facilityType: typeof record.facility_type === "string" ? record.facility_type : null,
          status: fact.status, reason: fact.reason,
          sourceUrl: url,
          sourceTrace: typeof fact.sourceRecordTrace === "string" ? fact.sourceRecordTrace : null,
          hazardScopeRaw: fact.hazardScopeRaw,
          officialStatusRaw: typeof fact.officialStatusRaw === "string" ? fact.officialStatusRaw : null,
          hasCoordinates: record.hasCoordinates === true
        }));
      }
    } catch {
      return { state: "INVALID", message: "施設ID・洪水分類・出典の整合を確認できません。比較を停止しました。" };
    }
    rows.sort((a, b) => a.id.localeCompare(b.id));
    let query = "", filter = "all", selected = [], chosen = null;

    function filtered() {
      const words = query.normalize("NFKC").toLocaleLowerCase("ja-JP").trim().split(/\s+/u).filter(Boolean);
      return rows.filter(row => {
        if (filter !== "all" && row.status !== filter) return false;
        const haystack = [row.name, row.address, row.facilityType].filter(Boolean)
          .join(" ").normalize("NFKC").toLocaleLowerCase("ja-JP");
        return words.every(word => haystack.includes(word));
      });
    }
    function selectionReset() { selected = []; chosen = null; }
    return Object.freeze({
      state: "READY", regionCode: summary.region.code, regionName: summary.region.name,
      total: rows.length, counts: Object.freeze({ ...counts }),
      // A source's original publication/update time is NOT established by this adapter.
      officialSourceTimeVerified: false,
      setCriteria(nextQuery, nextFilter) {
        if (typeof nextQuery !== "string" || !["all", ...VALID].includes(nextFilter)) {
          return { ok: false, reason: "INVALID_FILTER" };
        }
        if (nextQuery !== query || nextFilter !== filter) {
          query = nextQuery; filter = nextFilter; selectionReset();
        }
        return { ok: true };
      },
      page(page = 0) {
        const matched = filtered();
        const pages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
        const current = Number.isInteger(page) ? Math.max(0, Math.min(page, pages - 1)) : 0;
        return Object.freeze({
          state: rows.length === 0 ? "NO_DATA" : matched.length === 0 ? "NO_MATCH" : "HAS_ROWS",
          page: current, pages, matched: matched.length,
          records: matched.slice(current * PAGE_SIZE, (current + 1) * PAGE_SIZE)
        });
      },
      selected() { return selected.map(id => rows.find(row => row.id === id)); },
      toggle(id) {
        if (!filtered().some(row => row.id === id)) return { ok: false, reason: "NOT_IN_RESULT" };
        if (selected.includes(id)) selected = selected.filter(value => value !== id);
        else if (selected.length < 2) selected = [...selected, id];
        else return { ok: false, reason: "TWO_ONLY" };
        chosen = null;
        return { ok: true, count: selected.length };
      },
      choose(id) {
        if (selected.length !== 2 || !selected.includes(id)) return { ok: false, reason: "COMPARE_TWO_FIRST" };
        chosen = id;
        return { ok: true, id };
      },
      choice() { return chosen ? rows.find(row => row.id === chosen) : null; },
      clear() { selectionReset(); }
    });
  }
  window.HINANEX_FACILITY_EXPLORE = Object.freeze({
    apiVersion: "flood-facility-explore-20261023-v1", createSession
  });
})();
