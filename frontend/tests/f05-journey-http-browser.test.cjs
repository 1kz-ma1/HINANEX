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

// Test the already-approved manual B1 -> F02 link with real F02 assets,
// not a replacement page. Only generated synthetic JSON is served.
// F01 GIS, B2/S1 connections, official data, physical devices and LIVE
// are outside this test. Keep this test in the existing private path.
test("F05 B1 to actual F02 HTTP Chrome: explicit navigation, failed fetch, retry and read-only record",
  {timeout:120000},async t=>{
    const bin=browserBinary();
    if(!bin){
      if(process.env.CI||process.env.B1_REQUIRE_CHROME==="1")throw Error("Chrome is required for B1 integration in CI");
      t.skip("Chrome binary unavailable");return;
    }
    const exportPath="/pipeline/data/output/edogawa.json";
    const allowed=new Set([hub,model,f02,"/frontend/f02.css",
      "/frontend/src/f02-page.js","/frontend/src/f02-shelter-reference.js",
      "/frontend/src/region-export-loader.js","/frontend/src/region-export-source.js"]);
    const fixture={meta:{schema_version:"0.9"},
      region:{code:"13123",name:"東京都江戸川区（合成fixture）"},
      datasets:[{region_code:"13123",region_name:"東京都江戸川区（合成fixture）",
        requirement_code:"shelter_location",records:[
          {id:"synthetic-handoff-1",name:"架空引継ぎ施設A",address:null,facility_type:null,
            supported_disasters:null,latitude:null,longitude:null},
          {id:"synthetic-handoff-2",name:"架空引継ぎ施設B",address:null,facility_type:null,
            supported_disasters:null,latitude:null,longitude:null}],
        evidence:[{source_name:"合成引継ぎ資料",source_url:"https://example.invalid/b1-f02-fixture"}]}]};
    const requests=[];
    let attempts=0,browser;
    const server=http.createServer((req,res)=>{
      requests.push(req.url);
      if(req.method!=="GET"){res.writeHead(405);res.end();return;}
      if(req.url==="/favicon.ico"){res.writeHead(204);res.end();return;}
      if(req.url===exportPath){
        if(req.headers.referer!=="http://127.0.0.1:"+server.address().port+f02){
          res.writeHead(400);res.end("F02 document required");return;
        }
        attempts++;
        res.writeHead(attempts===1?503:200,{"Content-Type":"application/json; charset=utf-8","Cache-Control":"no-store"});
        res.end(attempts===1?"{}":JSON.stringify(fixture));return;
      }
      if(!allowed.has(req.url)){res.writeHead(404);res.end();return;}
      res.writeHead(200,{"Content-Type":(req.url.endsWith(".js")?"text/javascript":req.url.endsWith(".css")?"text/css":"text/html")+"; charset=utf-8","Cache-Control":"no-store","Referrer-Policy":"same-origin"});
      fs.createReadStream(path.join(root,req.url.slice(1))).pipe(res);
    });
    await new Promise((resolve,reject)=>{server.once("error",reject);server.listen(0,"127.0.0.1",resolve);});
    const base="http://127.0.0.1:"+server.address().port;
    try{
      browser=await launchChrome(bin);
      const {command,evaluate}=browser;
      await command("Page.enable");await command("Runtime.enable");await command("Network.enable");
      await command("Emulation.setDeviceMetricsOverride",{width:390,height:844,deviceScaleFactor:1,mobile:false});
      const navigation=await command("Page.navigate",{url:base+hub});
      assert.ok(!navigation.errorText,navigation.errorText);
      await waitUntil(evaluate,"location.pathname==="+JSON.stringify(hub)+" && document.readyState==='complete' && !!document.querySelector('#regionSelect')","real B1");
      assert.equal(await evaluate("document.querySelector('#regionSelect').value"),"");
      assert.ok(await evaluate("document.querySelector('#f02Link').hidden && !document.querySelector('#f02Link').hasAttribute('href')"));
      assert.equal(attempts,0);
      await evaluate("document.querySelector('#regionSelect').focus()");
      await press(command,"ArrowDown","ArrowDown",40);
      await press(command,"Tab","Tab",9);await press(command,"Tab","Tab",9);
      assert.equal(await evaluate("document.activeElement.id"),"f02Link");
      assert.equal(await evaluate("document.querySelector('#f02Link').getAttribute('href')"),f02);
      assert.equal(attempts,0,"no fetch before explicit navigation");
      await press(command,"Enter","Enter",13,"\r");
      await waitUntil(evaluate,"location.pathname==="+JSON.stringify(f02)+" && document.readyState==='complete' && document.querySelector('#load-state')?.classList.contains('error') && document.querySelector('#retry-load')?.hidden===false","real F02 first transport failure");
      assert.equal(await evaluate("location.search"),"");
      assert.equal(await evaluate("document.querySelector('#search').disabled"),true);
      assert.equal(await evaluate("document.querySelectorAll('#results .record').length"),0);
      assert.ok(await evaluate("document.querySelector('#load-state').textContent.includes('施設0件と同一視せず')"));
      assert.equal(attempts,1);
      await evaluate("document.querySelector('#retry-load').focus()");
      await press(command,"Enter","Enter",13,"\r");
      await waitUntil(evaluate,"document.querySelector('#search')?.disabled===false && document.querySelectorAll('#results .record').length===2 && document.querySelector('#sources')?.textContent.includes('合成引継ぎ資料')","actual F02 retry renders synthetic records and evidence");
      assert.equal(attempts,2);
      assert.equal(await evaluate("document.activeElement.id"),"search");
      assert.ok(await evaluate("document.querySelector('#record-count').textContent.includes('座標なし 2件') && document.querySelector('#clear-record').hidden"));
      await command("Input.insertText",{text:"施設A"});
      await waitUntil(evaluate,"document.querySelectorAll('#results .record').length===1","search in actual F02");
      await press(command,"Tab","Tab",9);
      assert.equal(await evaluate("document.activeElement.dataset.recordId"),"synthetic-handoff-1");
      await press(command,"Enter","Enter",13,"\r");
      assert.ok(await evaluate("document.querySelector('#detail h3')?.textContent==='架空引継ぎ施設A' && document.querySelector('#detail').textContent.includes('座標なし・位置未確認') && document.querySelector('#detail').textContent.includes('安全性は未確認')"));
      await evaluate("document.querySelector('#clear-record').focus()");
      await press(command,"Enter","Enter",13,"\r");
      assert.deepEqual(await evaluate("({query:document.querySelector('#search').value,id:document.activeElement.dataset.recordId,pressed:document.activeElement.getAttribute('aria-pressed'),hidden:document.querySelector('#clear-record').hidden})"),{query:"施設A",id:"synthetic-handoff-1",pressed:"false",hidden:true});
      assert.equal(await evaluate("localStorage.length+sessionStorage.length"),0);
      assert.deepEqual(browser.exceptions,[]);
      assert.ok(browser.outbound.every(u=>u.startsWith(base+"/")&&[...allowed,exportPath,"/favicon.ico"].includes(u.slice(base.length))),JSON.stringify(browser.outbound));
      assert.ok(requests.every(u=>allowed.has(u)||u===exportPath||u==="/favicon.ico"),JSON.stringify(requests));
      for(const asset of allowed)assert.ok(requests.includes(asset),"missing real asset "+asset);
      console.log("F05_B1_F02_REAL_HANDOFF_HTTP: explicit Enter, actual F02 assets, synthetic 503 then retry, search/detail/clear, unknown retained, no auto external requests PASS");
    }finally{
      try{if(browser)await stopChrome(browser.child,browser.profile,browser.ws);}
      finally{await new Promise(resolve=>{server.close(resolve);server.closeAllConnections?.();});}
    }
  });
