import { assertRegionMatches, getRegionSource } from "./region-export-source.js";

class RegionExportLoadError extends Error {
  constructor(message, options = {}) {
    super(message, options);
    this.name = "RegionExportLoadError";
  }
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

  async function selectRegion(regionCode) {
    const source = getRegionSource(regionCode);
    const requestId = activeRequestId + 1;
    activeRequestId = requestId;

    activeController?.abort();
    const controller = new AbortController();
    activeController = controller;
    onLoading(source);

    try {
      const response = await fetchImpl(source.url, {
        cache: "no-store",
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new RegionExportLoadError(
          `RegionExportの取得に失敗しました（HTTP ${response.status}）。`,
        );
      }

      const payload = await response.json();
      assertRegionMatches(payload, source.code);

      if (requestId !== activeRequestId) return { status: "stale", source };

      onSuccess(payload, source);
      return { status: "success", source, payload };
    } catch (error) {
      if (requestId !== activeRequestId) return { status: "stale", source };
      if (error?.name === "AbortError") return { status: "aborted", source };

      const normalized =
        error instanceof Error ? error : new RegionExportLoadError("不明な取得エラーです。");
      onError(normalized, source);
      return { status: "error", source, error: normalized };
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

export { RegionExportLoadError, createRegionExportController };
