"use strict";
/** Mobile QA of actual GIS pages served from a temporary Render-equivalent build.
 * Chromium emulation is NOT iOS Safari / Android Chrome device acceptance.
 * No geolocation, flood safety judgement, or live staging mutation.
 */
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const SIZES = [[320,568],[375,812],[390,844],[430,932]];

async function runMobileUIAcceptanceBrowser({context,base,out,waitUntilLoaded}) {
  const auditDir = path.join(out, "mobile-ui-qa");
  fs.mkdirSync(auditDir, {recursive:true});
  // Preserve exactly the PR-tested public GIS source in the CI evidence artifact.
  // This also makes offline re-review possible without embedding private data.
  const repoRoot=path.resolve(__dirname,'../..');
  for(const relative of [
    'gis/gis/css/map_first.css',
    'gis/tests/mobile_ui_acceptance_browser.js',
    'gis/tests/mobile_ui_acceptance.test.js',
    'gis/tests/map_controller.test.js',
    'gis/tests/demo_20261022_browser_smoke.js',
  ]) {
    const target=path.join(auditDir,'source',relative);
    fs.mkdirSync(path.dirname(target),{recursive:true});
    fs.copyFileSync(path.join(repoRoot,relative),target);
  }
  const report = {source:"temporary Render-equivalent HTTP build with actual D exports",
    browser:"headless Chromium / Playwright CSS-viewport emulation (not a phone device)",
    staging_tested:false, physical_devices_tested:false,
    viewports:[], checks:[], failures:[], console_errors:[]};
  const record = (label,passed,detail,viewport) => {
    const x = {id:label,viewport,status:passed?"PASS":"FAIL",detail};
    report.checks.push(x);
    if (!passed) report.failures.push(x);
  };
  const save = () => fs.writeFileSync(path.join(auditDir,"mobile_ui_metrics.json"),
    JSON.stringify(report,null,2)+"\n","utf8");
  try {
    for(const [width,height] of SIZES) {
      const page = await context.newPage();
      const label = `${width}x${height}`;
      page.on("pageerror",error=>report.console_errors.push({viewport:label,message:error.message}));
      page.on("console",message=>{
        if(message.type()==="error" && !/ERR_BLOCKED_BY_CLIENT|ERR_BLOCKED_BY_ADMINISTRATOR/i.test(message.text()))
          report.console_errors.push({viewport:label,message:message.text()});
      });
      try {
        await page.setViewportSize({width,height});
        const response=await page.goto(base+"/gis/gis/?region=13123",{waitUntil:"domcontentloaded"});
        assert.equal(response.status(),200);
        await waitUntilLoaded(page,"13123");
        const metrics = await page.evaluate(() => {
          const selectors = {
            brand:'.header .brand',share:'#mapShareOpen',evidence:'.header-actions a.header-evidence-link',
            scene:'#mapToolScene > summary',scenario:'#mapToolScenario > summary',
            marks:'#mapToolMarks > summary',hazards:'#mapToolHazards > summary',
            map:'#map',panel:'#gisLayout',zoomIn:'.leaflet-control-zoom-in',
            zoomOut:'.leaflet-control-zoom-out',nav:'.hinanex-bottom-nav',
            planned1:'.bottom-nav-entry.is-planned:nth-child(2)',
            planned2:'.bottom-nav-entry.is-planned:nth-child(3)',
            settings:'#mapSettingsToggle',locate:'#mapLocateMe'};
          const rects={};
          for(const [name,selector] of Object.entries(selectors)) {
            const el=document.querySelector(selector);
            if(!el){rects[name]={missing:true};continue;}
            const r=el.getBoundingClientRect(),st=getComputedStyle(el);
            rects[name]={x:r.x,y:r.y,left:r.left,top:r.top,right:r.right,bottom:r.bottom,
              width:r.width,height:r.height,visible:st.visibility!=="hidden"&&st.display!=="none",
              text:el.textContent.trim().replace(/\s+/g," ").slice(0,100),
              fontSize:st.fontSize,color:st.color,backgroundColor:st.backgroundColor,
              textClipped:el.scrollWidth>el.clientWidth+2};
          }
          const cssRGB=(str)=>{const m=str.match(/rgba?\((\d+)[ ,]+(\d+)[ ,]+(\d+)/);return m?m.slice(1,4).map(Number):null};
          const luminance=c=>{const v=c.map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4);return .2126*v[0]+.7152*v[1]+.0722*v[2]};
          const contrast=(fg,bg)=>{const f=cssRGB(fg),b=cssRGB(bg);if(!f||!b)return null;const a=luminance(f),c=luminance(b);return Number(((Math.max(a,c)+.05)/(Math.min(a,c)+.05)).toFixed(2))};
          const navBG=getComputedStyle(document.querySelector('.hinanex-bottom-nav')).backgroundColor;
          for(const n of ['planned1','planned2']) {
            const el=document.querySelector(selectors[n]);
            rects[n].contrast=contrast(getComputedStyle(el).color,navBG);
            rects[n].tag=el.tagName.toLowerCase();rects[n].tabindex=el.getAttribute('tabindex');
            rects[n].role=el.getAttribute('role');
            rects[n].plannedLabel=el.querySelector('small')?.textContent.trim();
          }
          return {viewport:{innerWidth:innerWidth,innerHeight:innerHeight,
            docScrollWidth:document.documentElement.scrollWidth,bodyScrollWidth:document.body.scrollWidth},rects};
        });
        report.viewports.push({size:label,...metrics});
        const r=metrics.rects,intersects=(a,b)=>a.left<b.right-1&&a.right>b.left+1&&a.top<b.bottom-1&&a.bottom>b.top+1;
        const menu=['scene','scenario','marks','hazards'];
        record('top-four-targets-44',menu.every(n=>r[n].width>=44&&r[n].height>=44),
          menu.map(n=>({id:n,w:r[n].width,h:r[n].height})),label);
        record('share-44',r.share.width>=44&&r.share.height>=44,r.share,label);
        record('evidence-44',r.evidence.width>=44&&r.evidence.height>=44,r.evidence,label);
        record('header-no-overlap',!intersects(r.brand,r.share)&&!intersects(r.brand,r.evidence)&&!intersects(r.share,r.evidence),
          {brand:r.brand,share:r.share,evidence:r.evidence},label);
        record('menu-no-overlap',menu.every((n,i)=>menu.slice(i+1).every(other=>!intersects(r[n],r[other]))),
          menu.map(n=>r[n]),label);
        record('no-horizontal-document-overflow',metrics.viewport.docScrollWidth<=width+1,
          {scrollWidth:metrics.viewport.docScrollWidth,width},label);
        record('header-primary-controls-on-screen',['share','evidence',...menu].every(n=>r[n].left>=-1&&r[n].right<=width+1),
          ['share','evidence',...menu].map(n=>({id:n,left:r[n].left,right:r[n].right})),label);
        record('leaflet-zoom-44',['zoomIn','zoomOut'].every(n=>r[n].width>=44&&r[n].height>=44),
          ['zoomIn','zoomOut'].map(n=>({id:n,w:r[n].width,h:r[n].height})),label);
        record('planned-label-contrast',r.planned1.contrast>=4.5&&r.planned2.contrast>=4.5,
          {first:r.planned1.contrast,second:r.planned2.contrast},label);
        record('planned-noninteractive',['planned1','planned2'].every(n=>
          r[n].tag==='span'&&r[n].tabindex===null&&r[n].role===null&&r[n].plannedLabel==='予定'),
          [r.planned1,r.planned2],label);
        record('nav-map-separation',r.map.bottom<=r.nav.top+2&&r.locate.bottom<=r.nav.top+2,
          {mapBottom:r.map.bottom,locateBottom:r.locate.bottom,navTop:r.nav.top},label);
        record('header-label-not-clipped',!r.share.textClipped&&!r.evidence.textClipped,
          {share:r.share.textClipped,evidence:r.evidence.textClipped},label);
        for (const id of ['mapToolScene','mapToolScenario','mapToolMarks','mapToolHazards']) {
          const summary=page.locator(`#${id} > summary`);
          await summary.click();
          record(`menu-${id}-opens`,await page.locator(`#${id}`).evaluate(el=>el.open),{},label);
          await page.keyboard.press('Escape');
          record(`menu-${id}-escape-closes`,!(await page.locator(`#${id}`).evaluate(el=>el.open)),{},label);
        }
        await page.locator('#mapToolHazards > summary').click();
        await page.locator('#hazardGuideOpen').click();
        record('f01-panel-warning',await page.locator('#hazardGuidePanel').isVisible() &&
          /元図面の作成年・改訂日を特定できません/.test(await page.locator('#hazardGuidePanel').innerText()),
          {visible:await page.locator('#hazardGuidePanel').isVisible()},label);
        await page.keyboard.press('Escape');
        await page.locator('#mapToolHazards > summary').click();
        await page.locator('#officialAlertsOpen').click();
        record('f06-panel-warning',await page.locator('#officialAlertsPanel').isVisible() &&
          /外部サイトで最新の情報を確認/.test(await page.locator('#officialAlertsPanel').innerText()),
          {visible:await page.locator('#officialAlertsPanel').isVisible()},label);
        await page.keyboard.press('Escape');
        await page.locator('#mapShareOpen').click();
        record('share-opens',await page.locator('#mapSharePanel').isVisible(),{},label);
        await page.keyboard.press('Escape');
        record('share-escape-focus',!(await page.locator('#mapSharePanel').isVisible()) &&
          await page.evaluate(()=>document.activeElement?.id==='mapShareOpen'),{},label);
        const shotDir=path.join(auditDir,`${width}px`);
        fs.mkdirSync(shotDir,{recursive:true});
        await page.screenshot({path:path.join(shotDir,'initial.png'),animations:'disabled',fullPage:false});
      } catch(error) {
        record('browser-execution',false,String(error.stack||error),label);
      } finally {await page.close();save();}
    }
    record('no-pageerrors',!report.console_errors.some(x=>!/Failed to load resource/.test(x.message)),
      report.console_errors,'all');
    save();
    if(report.failures.length)throw new Error('Mobile Chromium QA failures: '+report.failures.map(x=>`${x.viewport}/${x.id}`).join(', ')+
      '; audit JSON: '+path.join(auditDir,'mobile_ui_metrics.json'));
    return report.checks.map(x=>x.id+'@'+x.viewport);
  } finally {save();}
}
module.exports={runMobileUIAcceptanceBrowser};