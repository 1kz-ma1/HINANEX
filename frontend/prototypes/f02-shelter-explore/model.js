/* F02 prototype-only display model. No RegionExport contract or safety evaluation. */
(function (root) {
  'use strict';
  const stateLabels = Object.freeze({
    UNKNOWN: '未確認（UNKNOWN）',
    UNVERIFIED_SOURCE: '元資料未取得',
    FIXTURE_ONLY: '架空資料の記載例',
  });
  function isKnown(value) {
    return value !== undefined && value !== null && value !== '' && value !== 'UNKNOWN';
  }
  function displayRaw(value) { return isKnown(value) ? String(value) : '未確認'; }
  function normalizeSearch(value) {
    return String(value || '').normalize('NFKC').trim().toLocaleLowerCase('ja')
      .replace(/[\u30a1-\u30f6]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
  }
  function searchRecords(records, regionId, query) {
    const needle = normalizeSearch(query);
    return records.filter(item => item.regionId === regionId &&
      (!needle || normalizeSearch(item.name).includes(needle)));
  }
  function getRegionStats(records, regionId, query) {
    const regional = records.filter(item => item.regionId === regionId);
    const filtered = searchRecords(records, regionId, query);
    return {
      total: regional.length,
      matched: filtered.length,
      noCoordinates: filtered.filter(item => !item.position?.coordinates).length,
      sourceUnretrieved: filtered.filter(item => item.source && item.source.retrieved === false).length,
      withCoordinates: filtered.filter(item => !!item.position?.coordinates).length,
    };
  }
  function viewState({ loading = false, error = false, regionalCount = 0, matchedCount = 0 }) {
    if (loading) return 'LOADING';
    if (error) return 'LOAD_ERROR';
    if (regionalCount === 0) return 'NO_REGION_RECORDS';
    if (matchedCount === 0) return 'NO_SEARCH_RESULTS';
    return 'RESULTS';
  }
  function locationLabel(item) { return item.position?.coordinates ? '参考座標あり（合成）' : '位置未確認（座標なし）'; }
  const model = Object.freeze({displayRaw, isKnown, searchRecords, getRegionStats, viewState, locationLabel, stateLabels});
  root.F02Model = model;
  if (typeof module !== 'undefined' && module.exports) module.exports = model;
})(typeof globalThis === 'object' ? globalThis : this);
