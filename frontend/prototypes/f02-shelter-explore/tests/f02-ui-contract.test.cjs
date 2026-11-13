const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const app = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const css = fs.readFileSync(path.join(__dirname, '..', 'styles.css'), 'utf8');

test('T11: closing detail targets the previously chosen record, not the first card', () => {
  assert.match(app, /button\.dataset\.facilityId=item\.id/);
  assert.match(app, /\.find\(button=>button\.dataset\.facilityId===item\.id\)/);
  assert.doesNotMatch(app, /const first=elements\.list\.querySelector\('button'\)/);
});

test('T12: focused mobile detail is offset below the persistent warning', () => {
  assert.match(css, /#detailHeading\s*\{scroll-margin-top:100px\}/);
  assert.match(app, /safetyBottom=document\.querySelector\('\.safety-strip'\)/);
  assert.match(app, /window\.scrollBy\(\{top:introTop-safetyBottom-12/);
});
