/* Optional pre-event preparation. Not connected to GIS UI or D until reviewed.
 * No startup storage, no GPS, no disaster data, no background sync.
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else if (root) root.HINANEX_PRE_EVENT_PREPARATION = api;
})(typeof window === "object" ? window : null, function () {
  "use strict";
  const STORAGE_KEY = "hinanex.gis.pre_event.optin.v1";
  const SCHEMA_VERSION = 1;
  const MAX_AGE_MS = 180 * 24 * 60 * 60 * 1000;
  const FIELD_NAMES = ["regionCode", "occupiedFloor", "upperFloorAccess"];

  function plainObject(value) {
    return value !== null && typeof value === "object" &&
      !Array.isArray(value) &&
      (Object.getPrototypeOf(value) === Object.prototype ||
       Object.getPrototypeOf(value) === null);
  }
  function exactKeys(value, allowed) {
    return plainObject(value) &&
      Object.keys(value).every(name => allowed.includes(name));
  }
  function validProfile(input) {
    if (!exactKeys(input, FIELD_NAMES)) return null;
    const regionCode = input.regionCode === undefined ? null : input.regionCode;
    const occupiedFloor = input.occupiedFloor === undefined ? null : input.occupiedFloor;
    const upperFloorAccess = input.upperFloorAccess === undefined ?
      null : input.upperFloorAccess;
    if (regionCode !== null &&
        (typeof regionCode !== "string" || !/^[0-9]{5}$/.test(regionCode))) return null;
    if (occupiedFloor !== null &&
        (!Number.isInteger(occupiedFloor) || occupiedFloor < 1 ||
         occupiedFloor > 200)) return null;
    if (upperFloorAccess !== null && typeof upperFloorAccess !== "boolean") return null;
    return { regionCode, occupiedFloor, upperFloorAccess };
  }
  function createStore(storage, clock = () => Date.now()) {
    // The caller owns the browser permission and user-facing consent UI.
    // Factory is intentionally inert: no reads/writes at construction.
    if (!storage || !["getItem", "setItem", "removeItem"].every(
      method => typeof storage[method] === "function"
    )) throw new TypeError("explicit storage adapter required");
    if (typeof clock !== "function") throw new TypeError("clock must be a function");

    function save(profile, { consentGiven } = {}) {
      // The caller MUST set this only after a specific user save/consent action.
      // The flag itself is NOT proof of legal consent or UI implementation.
      if (consentGiven !== true) return { status: "CONSENT_REQUIRED", profile: null };
      const clean = validProfile(profile);
      if (!clean) return { status: "INVALID_INPUT", profile: null };
      const now = clock();
      if (!Number.isFinite(now) || now < 0)
        return { status: "CLOCK_UNAVAILABLE", profile: null };
      const envelope = {
        schemaVersion: SCHEMA_VERSION, consentSaved: true,
        savedAt: new Date(now).toISOString(), profile: clean,
      };
      try {
        storage.setItem(STORAGE_KEY, JSON.stringify(envelope));
      } catch (_) {
        return { status: "STORAGE_UNAVAILABLE", profile: null };
      }
      return { status: "SAVED_LOCALLY", profile: { ...clean } };
    }

    function read() {
      let text;
      try {
        text = storage.getItem(STORAGE_KEY);
      } catch (_) {
        return { status: "STORAGE_UNAVAILABLE", profile: null };
      }
      if (text === null) return { status: "NOT_SAVED", profile: null };
      let record;
      try { record = JSON.parse(text); } catch (_) {
        return { status: "INVALID_SAVED_DATA", profile: null };
      }
      if (!exactKeys(record, ["schemaVersion", "consentSaved", "savedAt", "profile"]) ||
          record.schemaVersion !== SCHEMA_VERSION || record.consentSaved !== true) {
        return { status: "INVALID_SAVED_DATA", profile: null };
      }
      const clean = validProfile(record.profile);
      if (!clean || typeof record.savedAt !== "string" ||
          !/^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$/.test(record.savedAt)) {
        return { status: "INVALID_SAVED_DATA", profile: null };
      }
      const timestamp = Date.parse(record.savedAt), now = clock();
      if (!Number.isFinite(timestamp) || !Number.isFinite(now))
        return { status: "CLOCK_UNAVAILABLE", profile: null };
      if (timestamp > now + 300000 || now - timestamp > MAX_AGE_MS)
        return { status: "STALE_SAVED_DATA", profile: null };
      return { status: "SAVED_LOCALLY", profile: { ...clean } };
    }

    function deleteSaved() {
      // No automatic re-save. Explicit user deletion also handles invalid data.
      try {
        storage.removeItem(STORAGE_KEY);
        if (storage.getItem(STORAGE_KEY) !== null)
          return { status: "DELETE_UNCONFIRMED" };
      } catch (_) {
        return { status: "DELETE_UNCONFIRMED" };
      }
      return { status: "DELETED_LOCALLY" };
    }
    return { read, save, deleteSaved };
  }

  return Object.freeze({ createStore, STORAGE_KEY, SCHEMA_VERSION });
});
