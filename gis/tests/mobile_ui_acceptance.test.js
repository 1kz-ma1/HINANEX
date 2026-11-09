"use strict";
/** Deterministic GIS mobile UI gates invoked by map_controller.test.js in required CI.
 * These checks do not claim browser geometry or device acceptance.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const html=fs.readFileSync(path.join(__dirname,'../gis/index.html'),'utf8');
const css=fs.readFileSync(path.join(__dirname,'../gis/css/map_first.css'),'utf8');
const browserCode=fs.readFileSync(path.join(__dirname,'mobile_ui_acceptance_browser.js'),'utf8');
new vm.Script(browserCode,{filename:'mobile_ui_acceptance_browser.js'});
const menus=['mapToolScene','mapToolScenario','mapToolMarks','mapToolHazards'];
for(const id of menus){
 assert.equal((html.match(new RegExp('id="'+id+'"','g'))||[]).length,1,`unique ${id}`);
 assert.match(html,new RegExp('id="'+id+'"[^>]*><summary>'),`${id} native keyboard summary`);
}
assert.match(html,/id="mapShareOpen"[^>]*aria-controls="mapSharePanel"[^>]*aria-expanded="false"/);
assert.match(html,/class="header-evidence-link"[^>]*href="\.\.\/\.\.\/frontend\/"/);
assert.match(html,/id="hazardGuideOpen"[^>]*aria-controls="hazardGuidePanel"/);
assert.match(html,/id="officialAlertsOpen"[^>]*aria-controls="officialAlertsPanel"/);
const planned=[...html.matchAll(/<(\w+)\s+class="bottom-nav-entry is-planned"[^>]*>([\s\S]*?)<\/\1>/g)];
assert.equal(planned.length,2,'planned entries must not be enabled');
for(const [,tag,contents] of planned){
 assert.equal(tag,'span','non-interactive placeholder');
 assert.match(contents,/<small>予定<\/small>/);
 assert.doesNotMatch(contents,/href=|tabindex=|onclick=/i);
}
assert.match(css,/\.bottom-nav-entry\.is-planned\{opacity:1;color:#b9cbd4\}/);
assert.match(css,/\.map-tool>summary\{min-height:48px;font-size:12px/);
assert.match(css,/\.header-share-button\{min-height:44px;font-size:13px/);
assert.match(css,/env\(safe-area-inset-bottom/);
for(const size of ['320,568','375,812','390,844','430,932']) {
 assert.ok(browserCode.includes('['+size+']'),size+' declared as real viewport probe');
}
for(const flag of ['getBoundingClientRect','docScrollWidth','leaflet-zoom-44',
 'planned-label-contrast','f01-panel-warning','f06-panel-warning',
 'share-escape-focus','console_errors','mobile_ui_metrics.json']){
 assert.ok(browserCode.includes(flag),'Browser audit retains '+flag);
}
assert.match(browserCode,/physical_devices_tested:false/);
assert.doesNotMatch(browserCode,/https:\/\/hinanex-staging\.onrender\.com/);
console.log('GIS_MOBILE_STATIC_GATES_PASS: semantics, guards, browser audit registration; not device acceptance');