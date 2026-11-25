// All records are invented for a UI exercise. No public source, location or
// hazard condition is represented. No fetch and no runtime data fallback.
const base = {
  kind:"SYNTHETIC_FIXTURE", syntheticOnly:true,
  fixtureId:"synthetic-b2-ready", sourceId:"SYN-B2-DESIGN",
  regionCode:"TEST_ONLY", hazardScope:"SYNTHETIC_FLOOD",
  records:[
    {id:"fake-a", name:"架空施設A", address:null, status:"CANDIDATE",
      reason:"合成条件A：テスト上の分類値をそのまま表示", sourceId:"SYN-B2-DESIGN",
      hazardScope:"SYNTHETIC_FLOOD", sourceTrace:"fixture_row=1",
      rawValue:"SYNTHETIC_A", unknowns:["実際の災害適合性", "現在の開設状況", "正確な所在地"],
      openStatus:null, safetyVerified:false},
    {id:"fake-b", name:"架空施設B", address:null, status:"UNKNOWN",
      reason:"合成Fixtureで判定不能に設定", sourceId:"SYN-B2-DESIGN",
      hazardScope:"SYNTHETIC_FLOOD", sourceTrace:"fixture_row=2",
      rawValue:null, unknowns:["元の指定条件", "利用可能性", "現在の開設状況"],
      openStatus:null, safetyVerified:false},
    {id:"fake-c", name:"架空施設C", address:null, status:"EXCLUDED",
      reason:"合成条件B：テスト上の分類値をそのまま表示（危険認定ではない）",
      sourceId:"SYN-B2-DESIGN", hazardScope:"SYNTHETIC_FLOOD",
      sourceTrace:"fixture_row=3", rawValue:"SYNTHETIC_B",
      unknowns:["実際の施設安全性", "現在の開設状況"],
      openStatus:null, safetyVerified:false}
  ]
};

export function getB2Fixture(mode) {
  if (mode === "ready") return structuredClone(base);
  if (mode === "empty") return {...structuredClone(base), fixtureId:"synthetic-b2-empty", records:[]};
  if (mode === "load-error") return {
    kind:"SIMULATED_LOAD_ERROR", syntheticOnly:true, fixtureId:"synthetic-b2-load-error"
  };
  if (mode === "invalid") {
    const broken=structuredClone(base);
    broken.fixtureId="synthetic-b2-invalid";
    broken.records[1].sourceId="SYN-B2-UNMATCHED";
    return broken;
  }
  return null;
}
