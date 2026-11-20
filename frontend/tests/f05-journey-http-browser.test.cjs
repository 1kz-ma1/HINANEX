"use strict";
// Independent B1 browser regression. F01/F02 destinations are QA stubs, not acceptance.
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const http=require("node:http");
const {browserBinary,launchChrome,stopChrome,waitUntil}=require("./helpers/http-chrome.cjs");
const root=path.resolve(__dirname,"../..");
const hub="/frontend/prototypes/f05-flood-journey/index.html";
const model="/frontend/src/f05-journey-model.js";
const f01="/gis/gis/";
const f02="/frontend/f02.html";
const files=new Map([[hub,"frontend/prototypes/f05-flood-journey/index.html"],[model,"frontend/src/f05-journey-model.js"]]);
async function serve(){
  const requests=[];
  const server=http.createServer((req,res)=>{
    const route=new URL(req.url,"http://127.0.0.1").pathname;
    requests.push(route);
    if(req.method!=="GET"){res.writeHead(405);res.end();return;}
    if(route==="/favicon.ico"){res.writeHead(204);res.end();return;}
    if(route===f01||route===f02){
      res.writeHead(200,{"Content-Type":"text/html; charset=utf-8","Cache-Control":"no-store"});
      res.end("<!doctype html><title>QA_STUB:"+route+"</title><main>QA_STUB:"+route+"</main>");
      return;
    }
    if(!files.has(route)){res.writeHead(404);res.end();return;}
    res.writeHead(200,{"Content-Type":route.endsWith(".js")?"text/javascript; charset=utf-8":"text/html; charset=utf-8","Cache-Control":"no-store"});
    fs.createReadStream(path.join(root,files.get(route))).pipe(res);
  });
  await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"0.0.0.0",resolve);});
  return {server,requests,base:"http://127.0.0.1:"+server.address().port,alias:"http://127.0.0.2:"+server.address().port};
}
async function press(command,key,code,virtual,char){
  await command("Input.dispatchKeyEvent",{type:"rawKeyDown",key,code,windowsVirtualKeyCode:virtual});
  if(char)await command("Input.dispatchKeyEvent",{type:"char",key,code,windowsVirtualKeyCode:virtual,text:char,unmodifiedText:char});
  await command("Input.dispatchKeyEvent",{type:"keyUp",key,code,windowsVirtualKeyCode:virtual});
}
test("F05 B1 real HTTP Chrome: manual region, F01/F02 links, reset, keyboard, widths and privacy",
  {timeout:120000},async t=>{
    const bin=browserBinary();
    if(!bin){
      if(process.env.CI||process.env.B1_REQUIRE_CHROME==="1")throw Error("Chrome is required for B1 in CI");
      t.skip("Chrome binary unavailable");return;
    }
    const srv=await serve();let browser;
    try{
      browser=await launchChrome(bin);
      const {command,evaluate}=browser;
      await command("Page.enable");await command("Runtime.enable");await command("Network.enable");
      await command("Page.addScriptToEvaluateOnNewDocument",{source:
        "window.__b1Writes=0;const orig=Storage.prototype.setItem;Storage.prototype.setItem=function(...a){window.__b1Writes++;return orig.apply(this,a)};"});
      for(const width of [320,390,1440]){
        await command("Emulation.setDeviceMetricsOverride",{width,height:800,deviceScaleFactor:1,mobile:width<500});
        let nav=await command("Page.navigate",{url:srv.base+hub});
        assert.ok(!nav.errorText,"B1 page navigation: "+nav.errorText);
        await waitUntil(evaluate,"document.readyState==='complete' && !!document.querySelector('#regionSelect')","B1 page load");
        assert.ok(srv.requests.includes(hub)&&srv.requests.includes(model),"B1 HTML + model ESM must be served over HTTP");
        assert.equal(await evaluate("document.querySelector('#regionSelect').value"),"");
        assert.equal(await evaluate("document.querySelector('#f02Link').hidden && !document.querySelector('#f02Link').hasAttribute('href')"),true);
        assert.equal(await evaluate("document.querySelector('#f01Link').getAttribute('href')"),f01);
        assert.equal(await evaluate("document.body.textContent.includes('参考経路は未提供です。')"),true);
        assert.equal(await evaluate("document.body.textContent.includes('災害時の避難判断には使用できません。')"),true);
        assert.equal(await evaluate("document.documentElement.scrollWidth<=window.innerWidth"),true,"horizontal overflow "+width);
        await evaluate("{const e=document.querySelector('#regionSelect');e.value='13123';e.dispatchEvent(new Event('change',{bubbles:true}));}");
        assert.equal(await evaluate("document.querySelector('#f02Link').getAttribute('href')"),f02);
        assert.equal(await evaluate("!document.querySelector('#f02Link').hidden"),true);
        await evaluate("{const e=document.querySelector('#regionSelect');e.value='';e.dispatchEvent(new Event('change',{bubbles:true}));}");
        assert.equal(await evaluate("document.querySelector('#f02Link').hidden && !document.querySelector('#f02Link').hasAttribute('href')"),true);
        await evaluate("document.querySelector('#regionSelect').focus()");
        await press(command,"ArrowDown","ArrowDown",40);
        await press(command,"Tab","Tab",9);
        await press(command,"Tab","Tab",9); // F01 precedes F02 in native tab order.
        await waitUntil(evaluate,"document.querySelector('#regionSelect').value==='13123' && !document.querySelector('#f02Link').hidden","keyboard selection");
        assert.equal(await evaluate("document.activeElement.id"),"f02Link");
        await press(command,"Enter","Enter",13,"\r");
        await waitUntil(evaluate,"location.pathname==='/frontend/f02.html'","F02 keyboard navigation");
        assert.equal(await evaluate("document.title"),"QA_STUB:"+f02);
        assert.equal(await evaluate("location.search"),"");
        nav=await command("Page.navigate",{url:srv.base+hub});assert.ok(!nav.errorText);
        await waitUntil(evaluate,"document.readyState==='complete' && !!document.querySelector('#f01Link')","B1 reload");
        await evaluate("document.querySelector('#f01Link').click()");
        await waitUntil(evaluate,"location.pathname==='/gis/gis/'","F01 manual navigation");
        assert.equal(await evaluate("document.title"),"QA_STUB:"+f01);
        assert.equal(await evaluate("location.search"),"");
        nav=await command("Page.navigate",{url:srv.base+hub});assert.ok(!nav.errorText);
        await waitUntil(evaluate,"document.readyState==='complete' && !!document.querySelector('#regionSelect')","B1 final reload");
        assert.equal(await evaluate("localStorage.length===0 && sessionStorage.length===0 && window.__b1Writes===0"),true);
        assert.deepEqual(browser.exceptions,[],"no page exceptions");
        console.log("F05_B1_CHROME_HTTP: "+width+"px region/select/reset/keyboard/F01+F02 stub paths/no storage PASS");
      }
      const alias=await command("Page.navigate",{url:srv.alias+hub});
      if(!alias.errorText){
        await waitUntil(evaluate,"document.readyState==='complete' && !!document.querySelector('#regionSelect')","disallowed alias");
        await evaluate("{const e=document.querySelector('#regionSelect');e.value='13123';e.dispatchEvent(new Event('change',{bubbles:true}));}");
        assert.equal(await evaluate("document.querySelector('#f02Link').hidden && !document.querySelector('#f02Link').hasAttribute('href')"),true);
        console.log("F05_B1_NONALLOWLISTED_HTTP: 127.0.0.2 disallowed PASS");
      }else console.log("F05_B1_NONALLOWLISTED_HTTP: NOT_RUN "+alias.errorText);
      assert.ok(browser.outbound.every(u=>u.startsWith(srv.base)||u.startsWith(srv.alias)||u.startsWith("about:")),"unwanted external network request");
      assert.ok(srv.requests.every(u=>[hub,model,f01,f02,"/favicon.ico"].includes(u)),"unexpected HTTP route");
      console.log("F05_B1_CHROME_HTTP: external auto requests=0; F01/F02 target content NOT TESTED (QA_STUB)");
    }finally{
      if(browser)await stopChrome(browser.child,browser.profile,browser.ws);
      await new Promise((resolve,reject)=>srv.server.close(err=>err?reject(err):resolve()));
    }
  });