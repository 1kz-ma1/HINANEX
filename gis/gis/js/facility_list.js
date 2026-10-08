(function () {
  "use strict";

  // Pure UI selection; no geocoding, hazard classification or source rewriting.
  const PAGE_SIZE = 20;

  function searchable(value) {
    return typeof value === "string" ? value.normalize("NFKC").toLocaleLowerCase("ja-JP") : "";
  }

  function filterFacilityRecords(summary, query = "", page = 0) {
    const records = Array.isArray(summary?.records) ? summary.records : [];
    const sourceFacts = summary?.floodScenario?.byId;
    const words = searchable(query).trim().split(/\s+/u).filter(Boolean);
    const matched = records.filter(record => {
      const fact = typeof sourceFacts?.get === "function" ? sourceFacts.get(record.id) : null;
      const haystack = searchable([
        record.id, record.name, record.address, record.administrative_area,
        fact?.officialStatusRaw, fact?.usableFloorRaw, fact?.sourceRecordTrace
      ].filter(value => typeof value === "string").join(" "));
      return words.every(word => haystack.includes(word));
    });
    const pages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
    const safePage = Number.isInteger(page) ? Math.min(Math.max(page, 0), pages - 1) : 0;
    return {
      total: records.length,
      matched: matched.length,
      page: safePage,
      pages,
      first: matched.length ? safePage * PAGE_SIZE + 1 : 0,
      last: Math.min((safePage + 1) * PAGE_SIZE, matched.length),
      records: matched.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE)
    };
  }

  window.HINANEX_FACILITY_LIST = { PAGE_SIZE, filterFacilityRecords };
})();
