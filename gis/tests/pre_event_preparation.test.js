const assert = require("node:assert/strict");
const { createStore, STORAGE_KEY } = require("../gis/js/pre_event_preparation.js");

function fakeStorage() {
  const data = new Map();
  const calls = [];
  return {
    calls,
    data,
    getItem(key) { calls.push("get"); return data.has(key) ? data.get(key) : null; },
    setItem(key, value) { calls.push("set"); data.set(key, value); },
    removeItem(key) { calls.push("remove"); data.delete(key); }
  };
}

const time = Date.parse("2026-10-26T00:00:00.000Z");
const profile = { regionCode: "13123", occupiedFloor: 2, upperFloorAccess: null };

{
  const storage = fakeStorage();
  const store = createStore(storage, () => time);
  assert.deepEqual(storage.calls, [], "module/factory must not auto-read storage");
  assert.equal(store.read().status, "NOT_SAVED");
  assert.equal(store.save(profile).status, "CONSENT_REQUIRED");
  assert.equal(store.save(profile, { consentGiven: false }).status, "CONSENT_REQUIRED");
  assert.equal(storage.data.size, 0, "nothing saved without explicit opt-in");
  assert.equal(store.save(profile, { consentGiven: true }).status, "SAVED_LOCALLY");
  assert.deepEqual(store.read().profile, profile);
  assert.equal(storage.data.size, 1);
  assert.deepEqual(Object.keys(JSON.parse(storage.data.get(STORAGE_KEY))).sort(),
    ["consentSaved", "profile", "savedAt", "schemaVersion"]);
  assert.equal(store.deleteSaved().status, "DELETED_LOCALLY");
  assert.equal(store.read().status, "NOT_SAVED");
  assert.equal(storage.data.size, 0);
}
{
  const storage = fakeStorage();
  const store = createStore(storage, () => time);
  for (const p of [
    { ...profile, latitude: 35 }, { ...profile, longitude: 139 },
    { ...profile, streetAddress: "private" }, { ...profile, medicalNote: "private" },
    { ...profile, name: "private" }, { ...profile, isSafeAtHome: true },
    { ...profile, regionCode: "invalid" }, { ...profile, regionCode: 13123 },
    { ...profile, occupiedFloor: 0 }, { ...profile, occupiedFloor: 1.5 },
    { ...profile, occupiedFloor: "2" }, { ...profile, upperFloorAccess: "false" },
    { ...profile, upperFloorAccess: 0 }, [],
  ]) assert.equal(store.save(p, { consentGiven: true }).status, "INVALID_INPUT");
  assert.equal(storage.data.size, 0, "invalid input never persisted");
}
{
  const storage = fakeStorage();
  const store = createStore(storage, () => time);
  assert.equal(store.save(profile, { consentGiven: true }).status, "SAVED_LOCALLY");
  const raw = JSON.parse(storage.data.get(STORAGE_KEY));
  for (const changed of [
    { ...raw, schemaVersion: 999 }, { ...raw, consentSaved: false },
    { ...raw, latitude: 35.7 }, { ...raw, profile: { ...raw.profile, gps: 1 } },
  ]) {
    storage.data.set(STORAGE_KEY, JSON.stringify(changed));
    assert.equal(store.read().status, "INVALID_SAVED_DATA");
  }
  storage.data.set(STORAGE_KEY, "{bad");
  assert.equal(store.read().status, "INVALID_SAVED_DATA");
  assert.equal(store.deleteSaved().status, "DELETED_LOCALLY");
}
{
  const storage = fakeStorage();
  const store = createStore(storage, () => time);
  store.save(profile, { consentGiven: true });
  assert.equal(createStore(storage, () => time + 181 * 86400000).read().status,
    "STALE_SAVED_DATA");
  assert.equal(createStore(storage, () => time - 300001).read().status,
    "STALE_SAVED_DATA");
  assert.equal(createStore(storage, () => time + 181 * 86400000).deleteSaved().status,
    "DELETED_LOCALLY");
}
{
  const unavailable = {
    getItem() { throw Error("browser denied access"); },
    setItem() { throw Error("quota exceeded"); },
    removeItem() { throw Error("browser denied access"); },
  };
  const store = createStore(unavailable, () => time);
  assert.equal(store.save(profile, { consentGiven: true }).status,
    "STORAGE_UNAVAILABLE");
  assert.equal(store.read().status, "STORAGE_UNAVAILABLE");
  assert.equal(store.deleteSaved().status, "DELETE_UNCONFIRMED");
}
{
  const storage = fakeStorage();
  const store = createStore(storage, () => time);
  store.save(profile, { consentGiven: true });
  assert.deepEqual(JSON.parse(storage.data.get(STORAGE_KEY)).profile, profile);
  const revised = { regionCode: "23100", occupiedFloor: null, upperFloorAccess: false };
  assert.equal(store.save(revised, { consentGiven: true }).status, "SAVED_LOCALLY");
  assert.deepEqual(store.read().profile, revised);
  assert.equal(storage.data.size, 1);
}
console.log("pre_event_preparation.test.js: OK");
