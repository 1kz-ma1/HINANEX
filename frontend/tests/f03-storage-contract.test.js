import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
const demo = join(dirname(fileURLToPath(import.meta.url)), '..', 'prototypes', 'f03-storage-contract-qa');
const js = readFileSync(join(demo, 'app.js'), 'utf8');
const html = readFileSync(join(demo, 'index.html'), 'utf8');

test('F03 B prototype remains isolated from existing GIS/RegionExport', () => {
  assert.match(html, /DEMO \/ 試作/);
  assert.match(html, /id="load-btn"/);
  assert.match(html, /id="save-btn"/);
  assert.match(html, /id="clear-btn"/);
  assert.match(js, /hinanex\.preparedness\.demo\.v1/);
  assert.match(js, /const SCHEMA_VERSION = 1/);
  assert.match(js, /\$\('load-btn'\)\.addEventListener\('click', readSavedRegion\)/);
  assert.doesNotMatch(js, /\bfetch\s*\(|\bXMLHttpRequest\b|\bsendBeacon\s*\(|\bgeolocation\b/);
  assert.doesNotMatch(js, /\.location\s*=|\.location\.href\s*=|\.location\.search\s*=/);
  assert.match(html, /同一オリジンのJavaScript/);
  assert.match(html, /共用端末/);
  assert.match(html, /バックアップ/);
  assert.match(html, /自動期限もありません/);
});
