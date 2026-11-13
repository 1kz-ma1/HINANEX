// F02: read-only RegionExport v0.9 presentation adapter.
// Facility records are reference data, NOT verified shelter suitability,
// operating status, entrance locations or safe routes.
const SCHEMA_VERSION = "0.9";
const REQUIREMENT = "shelter_location";

function nonempty(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function optionalString(value, path) {
  if (value != null && typeof value !== "string") {
    throw new TypeError(path + " must be a string or null");
  }
  return value ?? null;
}

function coordinatesPresent(record, label) {
  const { latitude, longitude } = record;
  if (latitude == null && longitude == null) return false;
  if (typeof latitude !== "number" || !Number.isFinite(latitude) ||
      typeof longitude !== "number" || !Number.isFinite(longitude) ||
      Math.abs(latitude) > 90 || Math.abs(longitude) > 180) {
    throw new TypeError(label + " coordinates must be a valid pair or both null");
  }
  return true;
}

function httpsSourceUrl(value) {
  if (!nonempty(value)) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function buildF02ShelterReference(payload, expectedRegion = "13123") {
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    throw new TypeError("Invalid RegionExport object");
  }
  if (payload?.meta?.schema_version !== SCHEMA_VERSION) {
    throw new TypeError("Unsupported RegionExport schema version");
  }
  if (!nonempty(payload?.region?.code) || !nonempty(payload?.region?.name) ||
      payload.region.code !== expectedRegion) {
    throw new TypeError("RegionExport region mismatch");
  }
  if (!Array.isArray(payload.datasets)) {
    throw new TypeError("RegionExport datasets must be an array");
  }
  const matches = payload.datasets.filter(item => item?.requirement_code === REQUIREMENT);
  if (matches.length > 1) throw new TypeError("Duplicate shelter_location datasets");
  const region = { code: payload.region.code, name: payload.region.name };
  if (matches.length === 0) {
    return { state: "NO_DATASET", region, records: [], evidence: [], withoutCoordinates: 0 };
  }
  const dataset = matches[0];
  if (dataset.region_code !== region.code || !nonempty(dataset.region_name) ||
      !Array.isArray(dataset.records)) {
    throw new TypeError("shelter_location dataset contract mismatch");
  }
  const ids = new Set();
  const records = dataset.records.map((row, index) => {
    const label = "shelter_location.records[" + index + "]";
    if (!row || typeof row !== "object" || Array.isArray(row) ||
        !nonempty(row.id) || !nonempty(row.name) || ids.has(row.id)) {
      throw new TypeError(label + " has an invalid or duplicate ID/name");
    }
    ids.add(row.id);
    const hasCoordinates = coordinatesPresent(row, label);
    const supported = row.supported_disasters;
    if (supported != null &&
        (!Array.isArray(supported) || supported.some(v => typeof v !== "string"))) {
      throw new TypeError(label + ".supported_disasters must be string[] or null");
    }
    return {
      id: row.id,
      name: row.name,
      addressRaw: optionalString(row.address, label + ".address"),
      facilityTypeRaw: optionalString(row.facility_type, label + ".facility_type"),
      disasterValues: supported == null ? null : [...supported],
      hasCoordinates
    };
  });
  if (dataset.evidence != null && !Array.isArray(dataset.evidence)) {
    throw new TypeError("shelter_location.evidence must be an array");
  }
  const evidence = (dataset.evidence ?? []).map((source, index) => {
    if (!source || typeof source !== "object" || Array.isArray(source) ||
        !nonempty(source.source_name)) {
      throw new TypeError("Invalid dataset evidence at index " + index);
    }
    return {
      name: source.source_name,
      publisher: optionalString(source.publisher, "evidence.publisher"),
      licenseRaw: optionalString(source.license, "evidence.license"),
      publishedAt: optionalString(source.published_at, "evidence.published_at"),
      fetchedAt: optionalString(source.fetched_at, "evidence.fetched_at"),
      url: httpsSourceUrl(source.source_url)
    };
  });
  return {
    state: "READY",
    region,
    records,
    evidence,
    withoutCoordinates: records.filter(row => !row.hasCoordinates).length,
  };
}

function normalizeFacilitySearch(value) {
  return String(value ?? "").normalize("NFKC").trim().toLocaleLowerCase("ja")
    .replace(/[\u30a1-\u30f6]/g, c => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

function searchF02Facilities(records, query) {
  const needle = normalizeFacilitySearch(query);
  return records.filter(row => !needle || normalizeFacilitySearch(row.name).includes(needle));
}

export { buildF02ShelterReference, searchF02Facilities, httpsSourceUrl };
