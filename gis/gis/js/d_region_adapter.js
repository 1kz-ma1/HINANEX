(function () {
  "use strict";

  const SHELTER_REQUIREMENT_CODE = "shelter_location";
  const SUPPORTED_SCHEMA_VERSION = "0.9";

  function isFiniteCoordinate(value) {
    return typeof value === "number" && Number.isFinite(value);
  }

  function assertNullableString(value, path) {
    if (value !== null && value !== undefined && typeof value !== "string") {
      throw new Error(`${path} must be string or null`);
    }
  }

  function assertRegionExport(payload) {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      throw new Error("RegionExport must be an object");
    }
    if (!payload.region || typeof payload.region.code !== "string" || !payload.region.code) {
      throw new Error("RegionExport.region.code is required");
    }
    if (typeof payload.region.name !== "string" || !payload.region.name) {
      throw new Error("RegionExport.region.name is required");
    }
    if (!Array.isArray(payload.datasets)) {
      throw new Error("RegionExport.datasets must be an array");
    }
    if (!payload.meta || typeof payload.meta.schema_version !== "string") {
      throw new Error("RegionExport.meta.schema_version is required");
    }
    if (payload.meta.schema_version !== SUPPORTED_SCHEMA_VERSION) {
      throw new Error(
        `Unsupported RegionExport schema_version: ${payload.meta.schema_version} (expected ${SUPPORTED_SCHEMA_VERSION})`
      );
    }
  }

  function findShelterDataset(payload) {
    assertRegionExport(payload);
    return payload.datasets.find(
      dataset => dataset && dataset.requirement_code === SHELTER_REQUIREMENT_CODE
    ) || null;
  }

  function normalizeShelterRecord(record, index) {
    const prefix = `shelter_location.records[${index}]`;
    if (!record || typeof record !== "object" || Array.isArray(record)) {
      throw new Error(`${prefix} must be an object`);
    }
    if (typeof record.id !== "string" || !record.id) {
      throw new Error(`${prefix}.id is required`);
    }
    if (typeof record.name !== "string" || !record.name) {
      throw new Error(`${prefix}.name is required`);
    }

    const latitude = record.latitude;
    const longitude = record.longitude;
    const bothNull = latitude == null && longitude == null;
    const bothNumbers = isFiniteCoordinate(latitude) && isFiniteCoordinate(longitude);

    if (!bothNull && !bothNumbers) {
      throw new Error(`${prefix} coordinates must both be numbers or both be null`);
    }
    if (bothNumbers && (latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180)) {
      throw new Error(`${prefix} coordinates are out of range`);
    }

    assertNullableString(record.address, `${prefix}.address`);
    assertNullableString(record.administrative_area, `${prefix}.administrative_area`);
    assertNullableString(record.facility_type, `${prefix}.facility_type`);
    assertNullableString(record.detail_url, `${prefix}.detail_url`);
    assertNullableString(record.notes, `${prefix}.notes`);

    if (record.supported_disasters != null && !Array.isArray(record.supported_disasters)) {
      throw new Error(`${prefix}.supported_disasters must be array or null`);
    }
    if (Array.isArray(record.supported_disasters) && record.supported_disasters.some(value => typeof value !== "string")) {
      throw new Error(`${prefix}.supported_disasters must contain strings only`);
    }
    if (record.accessibility != null && typeof record.accessibility !== "boolean") {
      throw new Error(`${prefix}.accessibility must be boolean or null`);
    }
    if (record.capacity != null && (!Number.isInteger(record.capacity) || record.capacity < 0)) {
      throw new Error(`${prefix}.capacity must be a non-negative integer or null`);
    }

    return {
      id: record.id,
      name: record.name,
      latitude,
      longitude,
      address: record.address ?? null,
      administrative_area: record.administrative_area ?? null,
      facility_type: record.facility_type ?? null,
      supported_disasters: record.supported_disasters ?? null,
      accessibility: record.accessibility ?? null,
      capacity: record.capacity ?? null,
      detail_url: record.detail_url ?? null,
      notes: record.notes ?? null,
      hasCoordinates: bothNumbers
    };
  }

  function extractShelterLocation(payload, expectedRegionCode) {
    assertRegionExport(payload);

    if (expectedRegionCode && payload.region.code !== expectedRegionCode) {
      throw new Error(`Region mismatch: expected ${expectedRegionCode}, got ${payload.region.code}`);
    }

    const dataset = findShelterDataset(payload);
    if (!dataset) {
      return {
        region: payload.region,
        schemaVersion: payload.meta.schema_version,
        dataset: null,
        records: [],
        mappableRecords: [],
        missingCoordinateRecords: [],
        evidence: []
      };
    }

    if (dataset.region_code !== payload.region.code) {
      throw new Error(
        `shelter_location region_code mismatch: export ${payload.region.code}, dataset ${dataset.region_code}`
      );
    }
    if (typeof dataset.region_name !== "string" || !dataset.region_name) {
      throw new Error("shelter_location.region_name is required");
    }
    if (!Array.isArray(dataset.records)) {
      throw new Error("shelter_location.records must be an array");
    }

    const records = dataset.records.map(normalizeShelterRecord);
    return {
      region: payload.region,
      schemaVersion: payload.meta.schema_version,
      dataset,
      records,
      mappableRecords: records.filter(record => record.hasCoordinates),
      missingCoordinateRecords: records.filter(record => !record.hasCoordinates),
      evidence: Array.isArray(dataset.evidence) ? dataset.evidence : []
    };
  }

  window.HINANEX_D_ADAPTER = {
    SHELTER_REQUIREMENT_CODE,
    SUPPORTED_SCHEMA_VERSION,
    extractShelterLocation
  };
})();
