'use strict';
// Optional real-keyboard QA; install playwright in a temporary QA runner, never in the public bundle.
const assert = require('node:assert/strict');
const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');
const here=__dirname;
const allowed=new Set([
  '/index.html','/style.css','/synthetic-data.js','/timeline-model.js','/app.js',
  '/comparison-model.js','/comparison-app.js'
]);
async function run() {
  const server=http.createServer((req,res)=>{
    const url=req.url.split('?')[0];
    if(!allowed.has(url)){res.writeHead(404);res.end();return;}
    const type=url.endsWith('.html')?'text/html':url.endsWith('.css')?'text/css':'text/javascript';
    res.writeHead(200,{'Content-Type':type+'; charset=utf-8'});
    res.end(fs.readFileSync(path.join(here,url.slice(1))));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  let browser;
  try {
    browser=await chromium.launch({
      executablePath:process.env.CHROMIUM_BIN||undefined,
      headless:true,
      args:['--no-sandbox','--disable-dev-shm-usage','--disable-background-networking',
        '--no-first-run','--no-default-browser-check','--disable-extensions','--disable-sync']
    });
    const page=await browser.newPage({viewport:{width:390,height:900}});
    const external=[],failed=[],errors=[];
    page.on('request',request=>{
      if(!request.url().startsWith(`http://127.0.0.1:${server.address().port}/`)) external.push(request.url());
    });
    page.on('requestfailed',request=>failed.push(request.url()));
    page.on('pageerror',error=>errors.push(error.message));
    page.on('console',msg=>{if(msg.type()==='error')errors.push(msg.text())});
    await page.goto(`http://127.0.0.1:${server.address().port}/index.html`,{waitUntil:'load'});
    assert.equal(await page.locator('#compareRun').isDisabled(),true,'start NO-GO');
    await page.locator('#scenario').focus();
    await page.keyboard.press('ArrowDown'); // first fictional scenario, native select change
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#scenario').inputValue(),'fiction-a');
    assert.equal(await page.locator('#compareBefore').isDisabled(),false);
    await page.locator('#compareBefore').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#compareAfter').evaluate(e=>e===document.activeElement),true,'native Tab moves to next select');
    await page.locator('#compareBefore').focus();
    await page.keyboard.press('ArrowDown'); // placeholder -> step 0
    await page.keyboard.press('Enter');
    await page.locator('#compareAfter').focus();
    await page.keyboard.press('End'); // placeholder -> last step 3
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#compareBefore').inputValue(),'0');
    assert.equal(await page.locator('#compareAfter').inputValue(),'3');
    assert.equal(await page.locator('#compareRun').isDisabled(),false);
    await page.locator('#compareRun').focus();
    await page.keyboard.press('Enter'); // actual native button activation
    assert.equal(await page.locator('#compareStatus').getAttribute('data-state'),'SHOWN');
    assert.equal(await page.locator('#addedCount').textContent(),'8');
    assert.equal(await page.locator('#comparisonCounts').isVisible(),true);
    assert.equal(await page.locator('#compareRun').evaluate(e=>e===document.activeElement),true,'compare preserves focus');
    await page.locator('#compareBefore').focus();
    await page.keyboard.press('End'); // step 3 invalidates previous comparison
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#compareGridDelta').getAttribute('data-active'),'false','native selection purges old graphics');
    await page.locator('#compareRun').focus();
    await page.keyboard.press('Space'); // native Space on button
    assert.equal(await page.locator('#continuedCount').textContent(),'8','same step via keyboard');
    await page.locator('#compareClear').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#compareGridDelta').getAttribute('data-active'),'false');
    assert.equal(await page.locator('#compareBefore').evaluate(e=>e===document.activeElement),true,'reset focus moves to first input');
    await page.locator('#scenario').focus();
    await page.keyboard.press('ArrowDown'); // A -> B
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#scenario').inputValue(),'fiction-b');
    assert.equal(await page.locator('#compareGridDelta').getAttribute('data-active'),'false');
    await page.locator('#clear').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#compareBefore').isDisabled(),true,'S1 reset clears S2');
    assert.equal(await page.locator('#status').getAttribute('data-state'),'UNSELECTED','S1 remains intact');
    for(const width of [320,390,1440]){
      await page.setViewportSize({width,height:900});
      assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=document.documentElement.clientWidth+1),true,
        `horizontal overflow at ${width}px`);
    }
    assert.deepEqual(external,[],'no external network');
    assert.deepEqual(failed,[],'no failed requests');
    assert.deepEqual(errors,[],'no page or console errors');
    await page.close();
    console.log('F04_S2_NATIVE_KEYBOARD_PASS: Tab / ArrowDown / End / Enter / Space / focus / purge / 320-390-1440');
  } finally {
    if(browser)await browser.close();
    await new Promise(resolve=>server.close(resolve));
  }
}
run().catch(err=>{console.error(err);process.exitCode=1});
