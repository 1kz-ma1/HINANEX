// F05 P0 is a manual navigation guard, not a hazard or shelter decision engine.
export const F05_REGION = "13123";
export const F05_F01 = "/gis/gis/";
export const F05_F02_LOCAL = "/frontend/f02.html";

export function isLocalPreviewOrigin(origin) {
  if (typeof origin !== "string") return false;
  try {
    const url = new URL(origin);
    return url.protocol === "http:" && !url.username && !url.password &&
      ["127.0.0.1", "localhost", "[::1]"].includes(url.hostname);
  } catch {
    return false;
  }
}

export function buildF05Journey({ regionCode = null, origin = null } = {}) {
  const chosen = regionCode === F05_REGION;
  const local = isLocalPreviewOrigin(origin);
  return Object.freeze({
    status: !chosen ? "REGION_UNSELECTED" :
      local ? "LOCAL_F02_LINK" : "F02_UNPUBLISHED",
    regionCode: chosen ? F05_REGION : null,
    f01Href: F05_F01,
    f02Href: chosen && local ? F05_F02_LOCAL : null,
    routeHref: null,
    facilityId: null,
    floodSuitability: null,
    currentOpenStatus: null
  });
}
