"use strict";
/* F02 standalone fixture: actual Chrome opens HTTP-loaded HTML/CSS/JS.
 * No third-party APIs, geolocation, real facilities, or URL-less DOM mocks.
 * CI fails when browser/HTTP navigation is blocked.
 */
const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs");
const os=require("node:os"),path=require("node:path"),http=require("node:http");
const {spawn,spawnSync}=require("node:child_process");
const dir=path.resolve(__dirname,"..");
const files=["index.html","styles.css","fixtures.js","model.js","app.js"];
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function chromeBinary(){
  for(const candidate of [process.env.F02_BROWSER_BIN,process.env.CHROME_BIN,
    "/usr/bin/google-chrome","/usr/bin/chromium","google-chrome","chromium"].filter(Boolean)){
    if(candidate.includes("/")&&fs.existsSync(candidate))return candidate;
    if(!candidate.includes("/")&&spawnSync("which",[candidate]).status===0)return candidate;
  }
  return null;
}
async function serve(){
  const requests=new Map();
  const server=http.createServer((req,res)=>{
    const name=decodeURIComponent(new URL(req.url,"http://localhost").pathname).replace(/^\/+/,"")||"index.html";
    requests.set(name,(requests.get(name)||0)+1);
    if(req.method!=="GET"||!files.includes(name)){res.writeHead(404);res.end();return;}
    const mime=name.endsWith(".css")?"text/css":name.endsWith(".js")?"text/javascript":"text/html";
    res.writeHead(200,{"Content-Type":mime+"; charset=utf-8","Cache-Control":"no-store"});
    fs.createReadStream(path.join(dir,name)).pipe(res);
  });
  await new Promise((ok,fail)=>{server.once("error",fail);server.listen(0,"127.0.0.1",ok);});
  return {requests,server,url:"http://127.0.0.1:"+server.address().port+"/"};
}
async function launch(bin){
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),"f02-chrome-"));
  const child=spawn(bin,["--headless=new","--no-sandbox","--disable-dev-shm-usage",
    "--disable-background-networking","--no-first-run","--remote-debugging-port=0",
    "--user-data-dir="+profile,"about:blank"],{stdio:["ignore","ignore","pipe"]});
  let stderr="";child.stderr.on("data",x=>{stderr=(stderr+x.toString()).slice(-1500);});
  try{
    let port=0;
    for(let i=0;i<150;i++){
      const active=path.join(profile,"DevToolsActivePort");
      if(fs.existsSync(active)){port=Number(fs.readFileSync(active,"utf8").split("\n")[0]);break;}
      if(child.exitCode!==null)throw Error("Browser exited: "+stderr);
      await wait(100);
    }
    if(!port)throw Error("Browser CDP startup timed out: "+stderr);
    const targets=await(await fetch("http://127.0.0.1:"+port+"/json/list")).json();
    const page=targets.find(x=>x.type==="page"&&x.webSocketDebuggerUrl);
    if(!page)throw Error("CDP page target missing");
    const ws=new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((ok,fail)=>{ws.addEventListener("open",ok,{once:true});ws.addEventListener("error",fail,{once:true});});
    let nextId=0;const pending=new Map(),exceptions=[],requests=[];
    ws.addEventListener("message",event=>{
      const data=JSON.parse(event.data);
      if(data.method==="Runtime.exceptionThrown")exceptions.push(data.params.exceptionDetails.exception?.description||data.params.exceptionDetails.text);
      if(data.method==="Network.requestWillBeSent")requests.push(data.params.request.url);
      if(!pending.has(data.id))return;
      const p=pending.get(data.id);pending.delete(data.id);
      data.error?p.reject(Error(data.error.message)):p.resolve(data.result);
    });
    const command=(method,params={})=>new Promise((resolve,reject)=>{
      const id=++nextId;pending.set(id,{resolve,reject});
      ws.send(JSON.stringify({id,method,params}));
    });
    const evalJs=async expression=>{
      const result=await command("Runtime.evaluate",{expression,returnByValue:true,awaitPromise:true});
      if(result.exceptionDetails)throw Error("Browser JavaScript: "+(result.exceptionDetails.exception?.description||result.exceptionDetails.text));
      return result.result.value;
    };
    return {profile,child,ws,command,evalJs,exceptions,requests};
  }catch(e){child.kill("SIGKILL");fs.rmSync(profile,{recursive:true,force:true});throw e;}
}
test("F02 HTTP-served Chrome functional and error-state acceptance",{timeout:90000},async t=>{
  const bin=chromeBinary();
  if(!bin){if(process.env.CI)throw Error("Real Chrome required in CI; cannot pass with mocks");t.skip("Chrome unavailable locally");return;}
  const {server,requests,url}=await serve();
  let browser;
  try{
    browser=await launch(bin);
    const {command,evalJs}=browser;
    await command("Page.enable");await command("Runtime.enable");await command("Network.enable");
    const nav=await command("Page.navigate",{url});
    assert.ok(!nav.errorText,"HTTP navigation blocked/failed: "+nav.errorText);
    let ready=false;
    for(let i=0;i<80;i++){
      ready=await evalJs("document.readyState==='complete'&&!!window.F02Model&&!!window.F02Fixtures&&document.querySelectorAll('.facility-card').length===4");
      if(ready)break;
      await wait(100);
    }
    assert.ok(ready,"F02 scripts failed to render when fetched by browser HTTP");
    for(const name of files)assert.ok(requests.has(name),"HTTP asset not fetched: "+name);
    assert.equal(await evalJs("getComputedStyle(document.querySelector('.safety-strip')).position"),"sticky");
    assert.equal(await evalJs("document.querySelectorAll('a[href^=\"https://\"]').length"),0);
    assert.equal(await evalJs("document.querySelectorAll('.facility-card').length"),4);
    assert.ok(await evalJs("document.body.innerText.includes('合成データ')&&document.body.innerText.includes('安全な避難先・開設中の保証ではありません')"));
    console.log("F02_REAL_HTTP: HTML/CSS/JS all fetched and synthetic warning visible");

    assert.ok(await evalJs("(()=>{const c=[...document.querySelectorAll('.facility-card')].find(x=>x.dataset.facilityId==='FA-002');c.click();return document.activeElement?.id==='detailHeading'&&document.querySelector('#detailBody').innerText.includes('未確認')})()"));
    assert.ok(await evalJs("(()=>{document.querySelector('.close-detail').click();return document.activeElement?.dataset.facilityId==='FA-002'})()"));
    assert.equal(await evalJs("(()=>{const q=document.querySelector('#query');q.value='ｽｽﾞﾗﾝ';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelectorAll('.facility-card').length})()"),1);
    assert.ok(await evalJs("(()=>{const q=document.querySelector('#query');q.value='該当しない名前';q.dispatchEvent(new Event('input',{bubbles:true}));return document.querySelector('#statusMessage').innerText.includes('検索結果が0件')})()"));
    assert.ok(await evalJs("(()=>{const q=document.querySelector('#query');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}));const r=document.querySelector('#region');r.value='sample-empty';r.dispatchEvent(new Event('change',{bubbles:true}));return document.querySelector('#statusMessage').innerText.includes('fixture記録は0件')})()"));
    assert.ok(await evalJs("(()=>{const c=document.querySelector('#scenario');c.value='error';c.dispatchEvent(new Event('change',{bubbles:true}));return document.querySelector('#statusMessage').innerText.includes('データ読込エラー')&&document.querySelector('#resultCount').textContent==='読込不可'})()"));
    assert.ok(await evalJs("(()=>{const c=document.querySelector('#scenario');c.value='normal';c.dispatchEvent(new Event('change',{bubbles:true}));const r=document.querySelector('#region');r.value='sample-amber';r.dispatchEvent(new Event('change',{bubbles:true}));return document.querySelectorAll('.facility-card').length===1})()"));
    console.log("F02_REAL_HTTP: detail, focus, normalized search, 0-record, 0-hit, load-error PASS");

    for(const pair of [[320,700],[390,844],[1440,900]]){
      const width=pair[0],height=pair[1];
      await command("Emulation.setDeviceMetricsOverride",{width,height,deviceScaleFactor:1,mobile:false});
      const metric=await evalJs("({width:innerWidth,overflow:document.documentElement.scrollWidth-innerWidth})");
      assert.equal(metric.width,width);
      assert.ok(metric.overflow<=2,"Horizontal overflow at "+width+"px: "+metric.overflow+"px");
    }
    assert.equal(browser.exceptions.length,0,"Page exceptions: "+browser.exceptions.join(" | "));
    assert.ok(browser.requests.every(x=>x.startsWith(url)||x==="about:blank"||x.startsWith("data:")),
      "Unexpected external request: "+browser.requests.join("; "));
    console.log("F02_REAL_HTTP: 320/390/1440 responsive, no JS errors or outbound HTTP PASS");
  }finally{
    if(browser){browser.ws.close();browser.child.kill("SIGKILL");fs.rmSync(browser.profile,{recursive:true,force:true});}
    await new Promise(resolve=>server.close(resolve));
  }
});