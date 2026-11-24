// Hand-authored display snapshots. NOT S1 output, no evaluator, no official records.
const common = {
  kind:"SYNTHETIC_FIXTURE", syntheticOnly:true, regionCode:"TEST_ONLY",
  hazardScope:"SYNTHETIC_FLOOD", sourceId:"SYN-B2-MJ01"
};
const row = (id, name, status, reason, rawValue, unknowns, sourceTrace) => ({
  id, name, status, reason, rawValue, unknowns, sourceTrace,
  address:null, sourceId:common.sourceId, hazardScope:common.hazardScope,
  openStatus:null, safetyVerified:false
});
const unknownReal = ["実際の安全性", "現在の開設状況", "実際の所在地"];
const snapshots = {
  pet: {
    ...common, fixtureId:"synthetic-b2-mj01-pet", records:[
      row("mj01-a","架空施設A","CANDIDATE","固定表示例：架空のペット条件に一致","架空属性：あり",unknownReal,"MJ01-PET-1"),
      row("mj01-b","架空施設B","UNKNOWN","固定表示例：架空のペット条件が未確認",null,["架空のペット条件",...unknownReal],"MJ01-PET-2"),
      row("mj01-c","架空施設C","EXCLUDED","固定表示例：架空のペット条件に不一致","架空属性：なし",unknownReal,"MJ01-PET-3")
    ]
  },
  step: {
    ...common, fixtureId:"synthetic-b2-mj01-step", records:[
      row("mj01-a","架空施設A","UNKNOWN","固定表示例：架空の段差条件が未確認",null,["架空の段差条件",...unknownReal],"MJ01-STEP-1"),
      row("mj01-b","架空施設B","CANDIDATE","固定表示例：架空の段差条件に一致","架空属性：あり",unknownReal,"MJ01-STEP-2"),
      row("mj01-c","架空施設C","EXCLUDED","固定表示例：架空の段差条件に不一致","架空属性：なし",unknownReal,"MJ01-STEP-3")
    ]
  }
};
export const conditions = Object.freeze({pet:"ペットへの配慮（架空）",step:"段差への配慮（架空）"});
export function fixedSnapshot(key) {
  return Object.hasOwn(snapshots,key) ? structuredClone(snapshots[key]) : null;
}
