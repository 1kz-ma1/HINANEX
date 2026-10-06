const REGION_SOURCES = Object.freeze({
  "13123": {
    code: "13123",
    label: "東京都 江戸川区",
    url: "../pipeline/data/output/edogawa.json",
  },
  "15100": {
    code: "15100",
    label: "新潟県 新潟市",
    url: "../pipeline/data/output/niigata.json",
  },
  "23100": {
    code: "23100",
    label: "愛知県 名古屋市",
    url: "../pipeline/data/output/nagoya.json",
  },
});

function getRegionSource(regionCode) {
  const source = REGION_SOURCES[regionCode];
  if (!source) {
    throw new Error(`未対応の地域コードです: ${regionCode ?? "値なし"}`);
  }
  return source;
}

function getPayloadRegionCode(payload) {
  const regionCode = payload?.region?.code;
  if (typeof regionCode !== "string" || !regionCode) {
    throw new Error("RegionExport.region.code がありません。");
  }
  getRegionSource(regionCode);
  return regionCode;
}

function assertRegionMatches(payload, expectedRegionCode) {
  const actualRegionCode = getPayloadRegionCode(payload);
  if (expectedRegionCode && actualRegionCode !== expectedRegionCode) {
    throw new Error(
      `選択地域とRegionExportが一致しません: expected ${expectedRegionCode}, got ${actualRegionCode}`,
    );
  }
  return actualRegionCode;
}

export { REGION_SOURCES, assertRegionMatches, getPayloadRegionCode, getRegionSource };
