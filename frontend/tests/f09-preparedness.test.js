import test from 'node:test';
import assert from 'node:assert/strict';
import { CATEGORIES, TOTAL_ITEMS, createChecklist } from '../prototypes/f09-preparedness/model.js';

const IDS = CATEGORIES.flatMap(category => category.items.map(item => item.id));

test('F09 initial state: no checked item, every item is unprepared', () => {
  const store = createChecklist();
  assert.equal(TOTAL_ITEMS, 10);
  assert.deepEqual(store.snapshot(), {
    checkedCount: 0, totalCount: 10, uncheckedCount: 10, percent: 0, checkedIds: [],
  });
  for (const id of IDS) assert.equal(store.isChecked(id), false);
});

test('F09 toggle on and off changes checked count and ratio', () => {
  const store = createChecklist();
  assert.equal(store.setChecked('water', true), true);
  assert.equal(store.setChecked('water', true), true); // idempotent
  assert.equal(store.snapshot().percent, 10);
  assert.equal(store.snapshot().checkedCount, 1);
  assert.equal(store.setChecked('water', false), true);
  assert.equal(store.snapshot().percent, 0);
});

test('F09 all reset returns every item to unchecked and zero progress', () => {
  const store = createChecklist();
  for (const id of IDS) assert.equal(store.setChecked(id, true), true);
  assert.equal(store.snapshot().percent, 100);
  store.reset();
  assert.equal(store.snapshot().checkedCount, 0);
  assert.equal(store.snapshot().uncheckedCount, TOTAL_ITEMS);
  assert.deepEqual(store.snapshot().checkedIds, []);
});

test('F09 rejects unknown IDs / malformed values without changing state', () => {
  const store = createChecklist();
  store.setChecked('water', true);
  const before = store.snapshot();
  for (const invalid of ['unknown', '__proto__', '', undefined, null, 42, {}]) {
    assert.equal(store.setChecked(invalid, true), false);
    assert.equal(store.isChecked(invalid), false);
  }
  assert.equal(store.setChecked('water', 'true'), false);
  assert.deepEqual(store.snapshot(), before);
});

test('F09 new session is empty: no cross-instance persistence', () => {
  const first = createChecklist();
  first.setChecked('water', true);
  assert.equal(first.snapshot().checkedCount, 1);
  assert.equal(createChecklist().snapshot().checkedCount, 0);
});

test('F09 exactly scoped to unique, non-personal example IDs', () => {
  assert.equal(new Set(IDS).size, TOTAL_ITEMS);
  assert.deepEqual(CATEGORIES.map(category => category.title), [
    '自宅で備える', '持ち出しに備える', '日ごろから確認する',
  ]);
  assert.ok(CATEGORIES.every(category => category.items.length > 0));
});
