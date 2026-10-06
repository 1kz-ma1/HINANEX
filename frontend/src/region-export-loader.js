const regionExports = Object.freeze({
  edogawa: Object.freeze({
    key: "edogawa",
    label: "東京都江戸川区",
    url: "../pipeline/data/output/edogawa.json",
  }),
  niigata: Object.freeze({
    key: "niigata",
    label: "新潟県新潟市",
    url: "../pipeline/data/output/niigata.json",
  }),
  nagoya: Object.freeze({
    key: "nagoya",
    label: "愛知県名古屋市",
    url: "../pipeline/data/output/nagoya.json",
  }),
});

class RegionExportLoadError extends Error {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "RegionExportLoadError";
  }
}

function getRegionExportConfig(regionKey) {
  const config = regionExports[regionKey];
  if (!config) {
    throw new RangeError(`未定義の地域キーです: ${regionKey ?? "値なし"}`);
  }
  return config;
}

function createRegionExportController({
  fetchImpl = globalThis.fetch,
  onLoading = () => {},
  onSuccess = () => {},
  onError = () => {},
} = {}) {
  if (typeof fetchImpl !== "function") {
    throw new TypeError("RegionExportの取得関数がありません。");
  }

  let activeController = null;
  let activeRequestId = 0;

  async function selectRegion(regionKey) {
    const config = getRegionExportConfig(regionKey);
    const requestId = activeRequestId + 1;
    activeRequestId = requestId;

    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    onLoading(config);

    try {
      const response = await fetchImpl(config.url, {
        cache: "no-store",
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new RegionExportLoadError(
          `RegionExportの取得に失敗しました（HTTP ${response.status}）。`,
        );
      }

      const exportData = await response.json();
      if (requestId !== activeRequestId) return { status: "stale", config };

      onSuccess(exportData, config);
      return { status: "success", config, exportData };
    } catch (error) {
      if (requestId !== activeRequestId) return { status: "stale", config };
      if (error?.name === "AbortError") return { status: "aborted", config };

      const normalizedError =
        error instanceof Error ? error : new RegionExportLoadError("不明な取得エラーです。");
      onError(normalizedError, config);
      return { status: "error", config, error: normalizedError };
    } finally {
      if (requestId === activeRequestId) activeController = null;
    }
  }

  function cancel() {
    activeRequestId += 1;
    activeController?.abort();
    activeController = null;
  }

  return Object.freeze({ cancel, selectRegion });
}

export {
  RegionExportLoadError,
  createRegionExportController,
  getRegionExportConfig,
  regionExports,
};
