/* Fictional fixture records only. Never use for actual disaster decisions. */
(function (root) {
  'use strict';
  const regions = [
    { id: 'sample-blue', name: '青地区（架空）' },
    { id: 'sample-amber', name: '橙地区（架空）' },
    { id: 'sample-empty', name: '空白地区（記録0件のテスト用）' },
  ];
  const records = [
    {
      id: 'FA-001', regionId: 'sample-blue', name: '青空学園 東館',
      addressRaw: '架空県 青地区 一番街1-1（合成）', roleRaw: '指定避難所（架空の原文例）',
      disasterRaw: '洪水：○ ／ 地震：△（架空記号。意味の解釈禁止）',
      source: { label: '架空資料A／避難施設一覧（合成）', version: 'fixture-2026-A', retrieved: true, publishedAt: null, url: 'https://example.invalid/f02/source-a' },
      position: { coordinates: {lat: 0, lng: 0}, referenceType: '参考地点（合成）', positionNote: '座標は合成のダミー値であり、現実の位置を示しません' },
      attributes: {
        designation: { state: 'FIXTURE_ONLY', reason: '架空資料内の記載。公式指定の確認ではありません' },
        boundaryEntrance: { state: 'UNKNOWN', reason: '敷地境界、建物位置、使用入口を検証していません' },
        hazardConditions: { state: 'UNKNOWN', reason: '架空の○/△に実際の災害適合性の意味を与えません' },
        operations: { state: 'UNKNOWN', reason: '災害時の開設・収容・混雑についてデータがありません' },
        designatedArea: { state: 'UNKNOWN', reason: '参考地点と指定範囲は異なります。正式な範囲は未検証です' },
      },
    },
    {
      id: 'FA-002', regionId: 'sample-blue', name: 'すずらん交流室',
      addressRaw: '架空県 青地区 二丁目4（合成）', roleRaw: 'UNKNOWN',
      disasterRaw: 'UNKNOWN',
      source: { label: '架空資料A／避難施設一覧（合成）', version: 'fixture-2026-A', retrieved: true, publishedAt: null, url: 'https://example.invalid/f02/source-a' },
      position: { coordinates: null, referenceType: 'UNKNOWN', positionNote: '座標なし。位置や入口を推測して補完しません' },
      attributes: {
        designation: { state: 'UNKNOWN', reason: '施設区分の原文が合成資料に入っていません' },
        boundaryEntrance: { state: 'UNKNOWN', reason: '敷地・入口の根拠がありません' },
        hazardConditions: { state: 'UNKNOWN', reason: '災害区分を確認できる合成セルがありません' },
        operations: { state: 'UNKNOWN', reason: '開設状況の情報がありません' },
        designatedArea: { state: 'UNKNOWN', reason: '正式指定範囲の資料・座標がありません' },
      },
    },
    {
      id: 'FA-003', regionId: 'sample-blue', name: '木かげ文化会館',
      addressRaw: null, roleRaw: '指定緊急避難場所（架空の原文例）',
      disasterRaw: '地震：○（架空記号。意味の解釈禁止）',
      source: { label: '架空資料B／施設注記（未取得を再現）', version: null, retrieved: false, publishedAt: null, url: 'https://example.invalid/f02/source-b' },
      position: { coordinates: null, referenceType: 'UNKNOWN', positionNote: '元資料未取得のため座標と参照点種別を確認できません' },
      attributes: {
        designation: { state: 'UNVERIFIED_SOURCE', reason: 'fixture上の記述で、元資料の取得を再現していません' },
        boundaryEntrance: { state: 'UNKNOWN', reason: '元資料未取得、敷地・入口の確認不可' },
        hazardConditions: { state: 'UNVERIFIED_SOURCE', reason: '元資料未取得のため原記号の照合ができません' },
        operations: { state: 'UNKNOWN', reason: '開設・混雑の情報はありません' },
        designatedArea: { state: 'UNKNOWN', reason: '正式な指定範囲の根拠がありません' },
      },
    },
    {
      id: 'FA-004', regionId: 'sample-blue', name: '青い丘スポーツ館',
      addressRaw: '架空県 青地区 丘通り8（合成）', roleRaw: '広域避難場所（架空の原文例）',
      disasterRaw: null,
      source: { label: '架空資料C／地域別一覧（合成）', version: 'fixture-2026-C', retrieved: true, publishedAt: 'UNKNOWN', url: 'https://example.invalid/f02/source-c' },
      position: { coordinates: {lat: 0, lng: 0}, referenceType: '参考地点（合成）', positionNote: '座標は合成のダミー値。正式な指定範囲や入口ではありません' },
      attributes: {
        designation: { state: 'FIXTURE_ONLY', reason: '架空資料の名称だけを表示し、他の役割へ統合しません' },
        boundaryEntrance: { state: 'UNKNOWN', reason: '建物・入口情報は未確認です' },
        hazardConditions: { state: 'UNKNOWN', reason: '対象災害の原記号がありません' },
        operations: { state: 'UNKNOWN', reason: '現在の開設状況は未確認です' },
        designatedArea: { state: 'UNKNOWN', reason: '参考地点のみ。正式な指定範囲は不明です' },
      },
    },
    {
      id: 'FB-001', regionId: 'sample-amber', name: '夕凪こどもセンター',
      addressRaw: '架空県 橙地区 夕町3-2（合成）', roleRaw: '指定避難所（架空の原文例）',
      disasterRaw: '地震：○（架空記号。意味の解釈禁止）',
      source: { label: '架空資料D／橙地区一覧（合成）', version: 'fixture-2026-D', retrieved: true, publishedAt: null, url: 'https://example.invalid/f02/source-d' },
      position: { coordinates: null, referenceType: 'UNKNOWN', positionNote: '座標がないため一覧のみで閲覧できます' },
      attributes: {
        designation: { state: 'FIXTURE_ONLY', reason: '合成資料の例であり公的な確認ではありません' },
        boundaryEntrance: { state: 'UNKNOWN', reason: '敷地・入口の確認資料なし' },
        hazardConditions: { state: 'UNKNOWN', reason: '現実の災害種別と適合性は未確認' },
        operations: { state: 'UNKNOWN', reason: '開設状況の確認資料なし' },
        designatedArea: { state: 'UNKNOWN', reason: '範囲を示す根拠がありません' },
      },
    },
  ];
  const fixture = { regions, records, fixtureVersion: 'F02-ISSUE348-20261104' };
  root.F02Fixtures = fixture;
  if (typeof module !== 'undefined' && module.exports) module.exports = fixture;
})(typeof globalThis === 'object' ? globalThis : this);
