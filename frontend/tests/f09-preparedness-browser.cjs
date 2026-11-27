// F09 true loopback HTTP Chromium acceptance. No injected fallback.
'use strict';
const assert = require('node:assert/strict');
const {spawn} = require('node:child_process');
const {createServer} = require('node:http');
const fs = require('node:fs');
const {tmpdir} = require('node:os');
const path = require('node:path');
const {once} = require('node:events');
const {setTimeout: sleep} = require('node:timers/promises');
const {browserBinary, stopChrome} = require('./helpers/http-chrome.cjs');

const root = path.resolve(__dirname, '../prototypes/f09-preparedness');
const allow = new Map([['/', 'index.html'], ['/index.html', 'index.html'], ['/styles.css', 'styles.css'], ['/app.js', 'app.js'], ['/model.js', 'model.js']]);
const mime = {html:'text/html', css:'text/css', js:'text/javascript'};
function deadline(promise, ms, label) {
  let timer;
  return Promise.race([promise, new Promise((_,reject) => {
    timer=setTimeout(() => reject(Error(label+' timed out')),ms);
  })]).finally(() => clearTimeout(timer));
}
function connectCdp(ws) {
  let nextId=0;
  const pending=new Map(), exceptions=[], outbound=[];
  const rejectPending=error => {
    for(const task of pending.values()) task.reject(error);
    pending.clear();
  };
  ws.addEventListener('close',()=>rejectPending(Error('CDP WebSocket closed')));
  ws.addEventListener('error',()=>rejectPending(Error('CDP WebSocket error')));
  ws.addEventListener('message',event=>{
    let message;
    try{message=JSON.parse(event.data);}catch(error){rejectPending(error);return;}
    if(message.method==='Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    if(message.method==='Network.requestWillBeSent') outbound.push(message.params.request.url);
    const task=pending.get(message.id);
    if(!task)return;
    pending.delete(message.id);
    message.error?task.reject(Error(message.error.message)):task.resolve(message.result);
  });
  const send=(method,params={})=>new Promise((resolve,reject)=>{
    if(ws.readyState!==WebSocket.OPEN){reject(Error('CDP not open: '+method));return;}
    const id=++nextId;
    const timer=setTimeout(()=>{pending.delete(id);reject(Error('CDP command timed out: '+method));},8000);
    const task={resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}};
    pending.set(id,task);
    try{ws.send(JSON.stringify({id,method,params}));}
    catch(error){pending.delete(id);task.reject(error);}
  });
  return {send,rejectPending,exceptions,outbound};
}
// Always attempt every cleanup, even if an earlier cleanup fails.
async function cleanupResources(cleaners) {
  const errors=[];
  for(const clean of cleaners){
    try{await clean();}catch(error){errors.push(error);}
  }
  if(errors.length)throw new AggregateError(errors,'F09 cleanup failed');
}
async function main() {
  let server, profile, chrome, ws, cdp, spawnError, failure;
  const requests=[];
  try {
    // Explicit overrides are authoritative: a bad value is a test failure, not a fallback.
    const binary=process.env.F09_BROWSER_BIN || process.env.F02_BROWSER_BIN || process.env.CHROMIUM_BIN || browserBinary();
    if(!binary)throw Error('Chromium / Chrome is required for F09 browser acceptance');
    if((path.isAbsolute(binary)||binary.includes('/')||binary.includes('\\'))&&!fs.existsSync(binary))
      throw Error('F09 browser binary not found: '+binary);
    server=createServer((request,response)=>{
      try{
        const route=new URL(request.url,'http://127.0.0.1').pathname;
        requests.push(route);
        if(route==='/away'){
          response.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});
          response.end('<!doctype html><title>F09 history test</title><p>history test</p>');return;
        }
        const filename=allow.get(route);
        if(!filename){response.writeHead(404);response.end('Not found');return;}
        response.writeHead(200,{'Content-Type':mime[filename.split('.').at(-1)]+'; charset=utf-8','Cache-Control':'no-store'});
        response.end(fs.readFileSync(path.join(root,filename)));
      }catch(error){response.writeHead(500);response.end('Read failed');}
    });
    const listening=once(server,'listening');
    server.listen(0,'127.0.0.1');
    await deadline(listening,5000,'HTTP listen');
    const url='http://127.0.0.1:'+server.address().port+'/';
    profile=fs.mkdtempSync(path.join(tmpdir(),'hinanex-f09-chrome-'));
    chrome=spawn(binary,[
      '--headless=new','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
      '--disable-background-networking','--no-first-run','--no-default-browser-check','--no-proxy-server',
      '--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'
    ],{stdio:'ignore',detached:process.platform!=='win32'});
    chrome.on('error',error=>{spawnError=error;});
    let port=0;
    const startupDeadline=Date.now()+12000;
    while(Date.now()<startupDeadline){
      if(spawnError)throw Error('Chrome spawn failed: '+spawnError.message);
      if(chrome.exitCode!==null||chrome.signalCode!==null)throw Error('Chrome exited during startup');
      try{
        const candidate=Number(fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').split('\n')[0]);
        if(Number.isInteger(candidate)&&candidate>0){port=candidate;break;}
      }catch(error){if(!['ENOENT','EBUSY','EPERM','EACCES'].includes(error.code))throw error;}
      await sleep(80);
    }
    if(!port)throw Error('Chrome CDP startup timed out');
    const response=await fetch('http://127.0.0.1:'+port+'/json/list',{signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw Error('CDP HTTP '+response.status);
    const tabs=await response.json();
    const target=tabs.find(tab=>tab.type==='page'&&tab.webSocketDebuggerUrl);
    assert.ok(target,'headless Chrome page target');
    ws=new WebSocket(target.webSocketDebuggerUrl);
    await deadline(new Promise((resolve,reject)=>{
      ws.addEventListener('open',resolve,{once:true});
      ws.addEventListener('error',()=>reject(Error('CDP open error')),{once:true});
      ws.addEventListener('close',()=>reject(Error('CDP closed before open')),{once:true});
    }),8000,'CDP open');
    cdp=connectCdp(ws);
    const {send}=cdp;
    async function evaluate(expression){
      const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));
      return result.result.value;
    }
    async function eventually(expression,predicate=Boolean){
      const until=Date.now()+10000;
      while(Date.now()<until){
        // Execution context can disappear during real navigation; do not hide other failures.
        let result;
        try{result=await evaluate(expression);}
        catch(error){
          if(!/context.*(destroyed|not found)|Cannot find context|Inspected target navigated/i.test(String(error)))throw error;
          await sleep(50);continue;
        }
        if(predicate(result))return result;
        await sleep(50);
      }
      throw Error('Condition not reached: '+expression);
    }
    async function key(key,code,vk){
      await send('Input.dispatchKeyEvent',{type:key==='Enter'?'keyDown':'rawKeyDown',key,code,windowsVirtualKeyCode:vk,...(key==='Enter'?{text:'\r'}:{})});
      await send('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:vk});
    }
    await send('Page.enable');await send('Runtime.enable');await send('Network.enable');
    await send('Page.addScriptToEvaluateOnNewDocument',{source:"window.__f09PageShows=[]; addEventListener('pageshow',e=>window.__f09PageShows.push(e.persisted));"});
    await send('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
    const navigation=await send('Page.navigate',{url});
    if(navigation.errorText)throw Error('Real HTTP navigation failed (no fallback): '+navigation.errorText);
    const ready= 'location.href==='+JSON.stringify(url)+" && document.readyState==='complete' && document.querySelectorAll('#checklist input').length===10 && window.__f09PageShows?.length>0";
    await eventually(ready);
    const count=()=>evaluate('document.querySelector("#checked-count").textContent');
    const assertZero=async()=>{
      assert.equal(await count(),'0');
      assert.equal(await evaluate('document.querySelector("#progress-percent").textContent'),'0%');
      assert.equal(await evaluate('document.querySelectorAll("#checklist input:checked").length'),0);
      assert.equal(await evaluate('Object.keys(localStorage).length + Object.keys(sessionStorage).length'),0);
    };
    await assertZero();
    for(const asset of ['/','/styles.css','/app.js','/model.js'])assert.ok(requests.includes(asset),'real asset '+asset);
    console.log('PASS real HTTP assets and initial 0/10');
    await evaluate('document.querySelector("[data-item-id=water]").focus()');
    await key('Tab','Tab',9);
    assert.equal(await evaluate('document.activeElement.dataset.itemId'),'food');
    await evaluate('document.querySelector("[data-item-id=water]").focus()');
    await key(' ','Space',32);
    await eventually('document.querySelector("#checked-count").textContent',x=>x==='1');
    assert.equal(await evaluate('document.activeElement.dataset.itemId'),'water');
    assert.equal(await evaluate('document.querySelector("#progress-percent").textContent'),'10%');
    await key(' ','Space',32);
    await assertZero();
    console.log('PASS Space toggle/untoggle and focus retention');
    const filterState=()=>evaluate('({name:document.querySelector("#filter-button").textContent,pressed:document.querySelector("#filter-button").getAttribute("aria-pressed"),state:document.querySelector("#filter-state").textContent})');
    const off=await filterState();
    assert.equal(off.pressed,'false');
    await evaluate('document.querySelector("[data-item-id=water]").click()');
    await evaluate('document.querySelector("#filter-button").click()');
    const on=await filterState();
    assert.equal(on.name,off.name);assert.equal(on.pressed,'true');assert.notEqual(on.state,off.state);
    assert.equal(await evaluate('document.querySelector("[data-item-id=water]").closest(".item").hidden'),true);
    await evaluate('document.querySelector("#filter-button").click()');
    assert.deepEqual(await filterState(),off);
    await evaluate('document.querySelectorAll("#checklist input:not(:checked)").forEach(input=>input.click())');
    assert.equal(await count(),'10');
    await evaluate('document.querySelector("#filter-button").click()');
    assert.equal(await evaluate('document.querySelector("#empty-message").hidden'),false);
    assert.equal(await evaluate('document.querySelectorAll(".category:not([hidden])").length'),0);
    await evaluate('document.querySelector("#reset-button").focus()');
    await key('Enter','Enter',13);
    await assertZero();
    assert.equal(await evaluate('document.activeElement.id'),'filter-button');
    assert.equal(await evaluate('document.querySelector("#reset-button").disabled'),true);
    assert.equal(await evaluate('document.querySelector("#empty-message").hidden'),true);
    assert.equal(await evaluate('document.querySelectorAll(".category:not([hidden])").length'),3);
    await evaluate('document.querySelector("#filter-button").click()');
    console.log('PASS stable filter name/state, all-checked empty state, keyboard reset/focus');
    for(const width of [320,390,1440]){
      await send('Emulation.setDeviceMetricsOverride',{width,height:900,deviceScaleFactor:1,mobile:false});
      await sleep(80);
      const overflow=await evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth');
      assert.ok(overflow<=1,'Horizontal overflow at '+width+': '+overflow);
      assert.equal(await evaluate('document.querySelector("[data-item-id=water]").getBoundingClientRect().width >= 24'),true);
      console.log('PASS responsive '+width+'px');
    }
    await evaluate('document.querySelector("[data-item-id=food]").click(); window.__f09OldDocument="reload-old"');
    assert.equal(await count(),'1');
    const loaderBefore=(await send('Page.getFrameTree')).frameTree.frame.loaderId;
    await send('Page.reload',{ignoreCache:true});
    await eventually(ready+' && window.__f09OldDocument!=="reload-old"');
    const loaderAfter=(await send('Page.getFrameTree')).frameTree.frame.loaderId;
    assert.ok(loaderBefore&&loaderAfter&&loaderBefore!==loaderAfter,'reload must have new loader');
    await assertZero();
    console.log('PASS real HTTP reload, new document sentinel/loader, 0/10 and empty storage');
    await evaluate('document.querySelector("[data-item-id=water]").click(); document.querySelector("#filter-button").click(); window.__f09OldDocument="history-old"');
    assert.equal(await count(),'1');
    const history=await send('Page.getNavigationHistory');
    const entry=history.entries[history.currentIndex];
    const away=await send('Page.navigate',{url:url+'away'});
    assert.ok(!away.errorText);
    await eventually('location.href==='+JSON.stringify(url+'away')+" && document.readyState==='complete'");
    await send('Page.navigateToHistoryEntry',{entryId:entry.id});
    await eventually(ready);
    const persisted=await evaluate('window.__f09PageShows.at(-1)===true');
    const sameDocument=await evaluate('window.__f09OldDocument==="history-old"');
    assert.equal(persisted,sameDocument,'BFCache requires persisted pageshow and old document');
    await assertZero();
    assert.equal((await filterState()).pressed,'false');
    console.log(persisted?'PASS actual BFCache restoration resets state':'NOT_RUN actual BFCache (history created new document); PASS history reload reset');
    assert.deepEqual(cdp.exceptions,[]);
    assert.ok(cdp.outbound.every(u=>u.startsWith(url)||u==='about:blank'),'unexpected outbound: '+cdp.outbound.join(', '));
    const screenshot=process.env.F09_SCREENSHOT;
    if(screenshot){
      const shot=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      fs.writeFileSync(screenshot,Buffer.from(shot.data,'base64'));
    }
  }catch(error){failure=error;}
  finally{
    try{
      await cleanupResources([
        async()=>{if(cdp)cdp.rejectPending(Error('F09 cleanup'));if(ws&&ws.readyState!==WebSocket.CLOSED){
          const closed=new Promise(resolve=>ws.addEventListener('close',resolve,{once:true}));
          ws.close();
          await deadline(closed,2000,'CDP close');
        }},
        async()=>{if(chrome&&Number.isInteger(chrome.pid)){await stopChrome(chrome,profile);}
          else if(profile){fs.rmSync(profile,{recursive:true,force:true,maxRetries:3,retryDelay:100});}
          if(profile&&fs.existsSync(profile))throw Error('F09 profile remains: '+profile);},
        async()=>{if(server){const closed=new Promise((resolve,reject)=>server.close(error=>error&&error.code!=='ERR_SERVER_NOT_RUNNING'?reject(error):resolve()));
          server.closeAllConnections();await deadline(closed,3000,'HTTP close');}}
      ]);
    }catch(error){failure=failure?new AggregateError([failure,error],'F09 test and cleanup failed'):error;}
  }
  if(failure)throw failure;
}
module.exports={cleanupResources,connectCdp};
if(require.main===module)main().catch(error=>{console.error(error);process.exit(1);});
