"use strict";
// Ephemeral F07 S3 exact-source QA. Do not merge this helper into main.
const assert=require("node:assert/strict");
const http=require("node:http");
const fs=require("node:fs");
const path=require("node:path");
const {chromium}=require("playwright");
const dir=path.resolve(__dirname,"../gis/prototypes/f07-reference-route");
const allow=new Set(["/index.html","/app.js","/route-model.js","/style.css"]);
const mime={".html":"text/html; charset=utf-8",".js":"text/javascript; charset=utf-8",".css":"text/css; charset=utf-8"};
async function main(){
 const hits=[];
 const server=http.createServer((req,res)=>{
  const uri=req.url.split("?")[0];hits.push(uri);
  if(!allow.has(uri)){res.writeHead(404);res.end();return;}
  res.writeHead(200,{"Content-Type":mime[path.extname(uri)]});
  res.end(fs.readFileSync(path.join(dir,path.basename(uri))));
 });
 await new Promise(resolve=>server.listen(0,"127.0.0.1",resolve));
 let browser;
 const origin="http://127.0.0.1:"+server.address().port;
 const errors=[],requested=[],responses=[],audits=[];
 try{
  browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN,headless:true,
   args:["--no-sandbox","--disable-background-networking","--disable-extensions","--disable-sync"]});
  const context=await browser.newContext({serviceWorkers:"block"});
  const page=await context.newPage();
  page.on("pageerror",error=>errors.push("pageerror:"+error.message));
  page.on("console",message=>{if(message.type()==="error")errors.push("console:"+message.text())});
  page.on("request",request=>requested.push(request.url()));
  page.on("response",response=>responses.push([new URL(response.url()).pathname,response.status()]));
  for(const width of [320,390,1440]){
   await page.setViewportSize({width,height:844});
   const r=await page.goto(origin+"/index.html",{waitUntil:"load",timeout:15000});
   assert.equal(r.status(),200);
   assert.equal(await page.locator("#status").getAttribute("data-state"),"UNSELECTED");
   assert.match(await page.locator("#nextAction").textContent(),/架空の出発点/);
   assert.equal(await page.locator('[role="status"]').count(),1);
   await page.locator("#origin").selectOption("start-a");
   await page.locator("#destination").selectOption("goal-x");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   assert.notEqual(await page.locator("#routeLine").getAttribute("points"),"");
   assert.equal(await page.locator("#routeLine").evaluate(e=>getComputedStyle(e).display),"inline");
   await page.locator("#destination").selectOption("goal-y");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"READY");
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   await page.locator("#condition").selectOption("pattern-2");
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   assert.match(await page.locator("#selectionSummary").textContent(),/模式線パターン 2/);
   await page.locator("#condition").evaluate(el => { el.value = "unsupported-pattern"; el.dispatchEvent(new Event("change",{bubbles:true})); });
   assert.equal(await page.locator("#status").getAttribute("data-state"),"NO_GO");
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   assert.equal(await page.locator("#generate").isDisabled(),true);
   assert.equal(await page.locator("#status").getAttribute("data-reason-code"),"UNSUPPORTED_CONDITION");
   assert.match(await page.locator("#nextAction").textContent(),/選び直してください/);
   await page.locator("#condition").selectOption("pattern-2");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"READY");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   await page.locator("#simulateFailure").focus();
   await page.keyboard.press("Space");
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"NO_GO");
   assert.match(await page.locator("#status").textContent(),/NO-GO/);
   assert.equal(await page.locator("#status").getAttribute("data-reason-code"),"SYNTHETIC_FAILURE");
   assert.match(await page.locator("#nextAction").textContent(),/チェックを外して/);
   await page.locator("#simulateFailure").focus();
   await page.keyboard.press("Space");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   await page.locator("#clear").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   assert.equal(await page.locator("#origin").inputValue(),"start-a");
   assert.equal(await page.locator("#destination").inputValue(),"goal-y");
   await page.locator("#generate").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"SHOWN");
   await page.locator("#reset").focus();
   await page.keyboard.press("Enter");
   assert.equal(await page.locator("#status").getAttribute("data-state"),"UNSELECTED");
   assert.equal(await page.locator("#origin").inputValue(),"");
   assert.equal(await page.locator("#destination").inputValue(),"");
   assert.equal(await page.locator("#condition").inputValue(),"pattern-1");
   assert.equal(await page.locator("#simulateFailure").isChecked(),false);
   assert.equal(await page.locator("#routeLine").getAttribute("points"),"");
   assert.equal(await page.locator("#generate").isDisabled(),true);
   assert.equal(await page.locator("#origin").evaluate(el=>document.activeElement===el),true);
   assert.match(await page.locator("#nextAction").textContent(),/出発点と目的地/);
   const widthInfo=await page.evaluate(()=>({doc:document.documentElement.scrollWidth,viewport:innerWidth}));
   assert.ok(widthInfo.doc<=widthInfo.viewport+1,JSON.stringify(widthInfo));
   assert.match(await page.locator(".warning").textContent(),/架空地点・合成デモ/);
   assert.equal(await page.evaluate(()=>localStorage.length+sessionStorage.length),0);
   audits.push({width,keyboard:"Enter/Space",state:"PASS",widthInfo});
  }
  const paths=new Set(responses.filter(([pathname,status])=>status===200).map(([pathname])=>pathname));
  for(const expected of allow)assert.ok(paths.has(expected),"missing HTTP 200 "+expected);
  assert.ok(responses.every(([pathname,status])=>status===200 && allow.has(pathname)),
   "unexpected HTTP response "+JSON.stringify(responses));
  assert.ok(requested.every(u=>u.startsWith(origin+"/")),"external request: "+requested);
  assert.deepEqual(errors,[],"console/page errors");
  console.log("F07_REAL_HTTP_PLAYWRIGHT_PASS "+JSON.stringify({browser:browser.version(),csp:"original unmodified",responses:responses.length,networkTargets:[...new Set(requested)],audits,consoleErrors:errors.length}));
 }finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
 }
}
main().catch(e=>{console.error(e);process.exitCode=1});
