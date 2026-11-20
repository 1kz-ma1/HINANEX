/* All labels, cells and relative steps are fictional illustration data. No geography. */
(function (root, factory) {
  'use strict';
  const value = factory();
  if (typeof module === 'object' && module.exports) module.exports = value;
  if (root) root.HINANEX_F04_DATA = value;
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';
  const makeFrames = (sets) => sets.map((cells, index) => ({
    label: `模擬ステップ ${index}`, cells
  }));
  const SCENARIOS = [
    { id: 'fiction-a', label: '架空ケース A（模式的な広がり）', frames: makeFrames([
      [], ['3-1', '3-2'], ['3-1', '3-2', '2-2', '2-3', '3-3'],
      ['3-1', '3-2', '2-2', '2-3', '3-3', '1-3', '2-4', '3-4']
    ]) },
    { id: 'fiction-b', label: '架空ケース B（異なる模式変化）', frames: makeFrames([
      ['1-6'], ['1-6', '2-6', '2-5'], ['1-6', '2-6', '2-5', '3-5', '3-4'],
      ['1-6', '2-6', '2-5', '3-5', '3-4', '4-4']
    ]) }
  ];
  return Object.freeze({ ROWS: 5, COLS: 8, SCENARIOS });
});
