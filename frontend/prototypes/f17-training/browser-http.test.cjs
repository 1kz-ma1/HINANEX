'use strict';
// F17 actual loopback HTTP + actual headless Chrome CDP. No browser test fixtures from official sources.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const {spawn, spawnSync} = require('node:child_process');

const prefix = '/frontend/prototypes/f17-training/';
const files = new Map([
  [prefix, 'index.html'], [prefix+'index.html', 'index.html'],
  [prefix+'app.js','app.js'], [prefix+'model.js','model.js'], [prefix+'style.css','style.css']
]);
const delay = ms => new Promise(resolve=>setTimeout(resolve,ms));
function browserBinary() {
  for(const bin of [process.env.F17_CHROME_BIN,process.env.CHROME_BIN,'/usr/bin/google-chrome','/usr/bin/chromium','google-chrome','chromium'].filter(Boolean)) {
    if (fs.existsSync(bin)) return bin;
    if (!bin.includes('/') && spawnSync(process.platform==='win32'?'where':'which',[bin]).status===0) return bin;
  }
  return null;
}
async function localServer() {
  const requests = [];
  const server = http.createServer((req,res)=>{
    const pathname = new URL(req.url,'http://127.0.0.1').pathname;
    requests.push(pathname);
    if (req.method!=='GET' || !files.has(pathname)) {res.writeHead(404);res.end();return;}
    const file = files.get(pathname);
    const type = file.endsWith('.js')?'text/javascript':file.endsWith('.css')?'text/css':'text/html';
    res.writeHead(200, {'Content-Type':type+'; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});
    fs.createReadStream(path.join(__dirname,file)).pipe(res);
  });
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  return {server,requests,origin:'http://127.0.0.1:'+server.address().port};
}
async function chrome(bin) {
  const profile=fs.mkdtempSync(path.join(os.tmpdir(),'hinanex-f17-'));
  const child=spawn(bin,['--headless=new','--no-sandbox','--disable-dev-shm-usage','--disable-background-networking','--no-first-run','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'],{stdio:['ignore','ignore','pipe']});
  let stderr='';child.stderr.on('data',d=>{stderr=(stderr+d.toString()).slice(-1000);});
  let ws,closed=false;
  async function close() {
    if(closed)return;closed=true;
    try{ws?.close();}catch{}
    if(child.exitCode===null) {
      child.kill('SIGTERM');
      await Promise.race([new Promise(r=>child.once('exit',r)),delay(2500)]);
      if(child.exitCode===null) child.kill('SIGKILL');
      await Promise.race([new Promise(r=>child.once('exit',r)),delay(2500)]);
    }
    await fs.promises.rm(profile,{recursive:true,force:true,maxRetries:6,retryDelay:200});
  }
  try {
    let port;
    for(let i=0;i<160;i++) {
      const active=path.join(profile,'DevToolsActivePort');
      if(fs.existsSync(active)){port=Number(fs.readFileSync(active,'utf8').split('\n')[0]);break;}
      if(child.exitCode!==null) throw Error('Chrome exited: '+stderr);
      await delay(100);
    }
    if(!port)throw Error('Chrome CDP startup timeout: '+stderr);
    const targets=await(await fetch('http://127.0.0.1:'+port+'/json/list',{signal:AbortSignal.timeout(10000)})).json();
    const page=targets.find(t=>t.type==='page'&&t.webSocketDebuggerUrl);
    if(!page)throw Error('Chrome page target missing');
    ws=new WebSocket(page.webSocketDebuggerUrl);
    await new Promise((resolve,reject)=>{
      const timer=setTimeout(()=>reject(Error('Chrome CDP socket timeout')),9000);
      ws.addEventListener('open',()=>{clearTimeout(timer);resolve();},{once:true});
      ws.addEventListener('error',()=>{clearTimeout(timer);reject(Error('CDP WebSocket error'));},{once:true});
    });
    let id=0;
    const pending=new Map(),errors=[],network=[];
    ws.addEventListener('message',e=>{
      const m=JSON.parse(e.data);
      if(m.method==='Runtime.exceptionThrown')errors.push(m.params.exceptionDetails.text);
      if(m.method==='Network.requestWillBeSent')network.push(m.params.request.url);
      const task=pending.get(m.id);if(!task)return;
      pending.delete(m.id);clearTimeout(task.timer);
      m.error?task.reject(Error(m.error.message)):task.resolve(m.result);
    });
    const command=(method,params={})=>new Promise((resolve,reject)=>{
      const idx=++id;
      const timer=setTimeout(()=>{pending.delete(idx);reject(Error('CDP timeout '+method));},15000);
      pending.set(idx,{resolve,reject,timer});
      ws.send(JSON.stringify({id:idx,method,params}));
    });
    const evaluate=async expression=>{
      const r=await command('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
      if(r.exceptionDetails)throw Error('Chrome script: '+(r.exceptionDetails.text||''));
      return r.result.value;
    };
    return {close,command,evaluate,errors,network};
  }catch(e){await close();throw e;}
}
async function waitFor(evalFn,expression,label) {
  for(let i=0;i<90;i++) {
    try{if(await evalFn(expression))return;}catch{}
    await delay(100);
  }
  throw Error('Timed out waiting for '+label);
}
async function keyboard(cmd,key,code) {
  const vk=key==='Enter'?13:key==='Tab'?9:32;
  const params={key,code,windowsVirtualKeyCode:vk,nativeVirtualKeyCode:vk};
  if(key==='Enter') {
    await cmd('Input.dispatchKeyEvent',{...params,type:'rawKeyDown'});
    await cmd('Input.dispatchKeyEvent',{type:'char',text:'\\r',unmodifiedText:'\\r',windowsVirtualKeyCode:vk,nativeVirtualKeyCode:vk});
  } else {
    await cmd('Input.dispatchKeyEvent',{...params,type:'keyDown'});
  }
  await cmd('Input.dispatchKeyEvent',{...params,type:'keyUp'});
}

test('F17 actual HTTP Chrome: 3 steps, keyboard, invalidation, reset, mobile and network scope', {timeout:120000},async t=>{
  const bin=browserBinary();
  if(!bin){if(process.env.CI || process.env.F17_REQUIRE_CHROME==='1')throw Error('F17 Chrome is required in CI');t.skip('Chrome not installed');return;}
  const {server,requests,origin}=await localServer();
  let b;
  try {
    b=await chrome(bin);
    const {command,evaluate}=b;
    await command('Page.enable');await command('Runtime.enable');await command('Network.enable');
    const url=origin+prefix;
    const nav=await command('Page.navigate',{url});
    assert.ok(!nav.errorText,'Browser must navigate over real HTTP: '+nav.errorText);
    await waitFor(evaluate,"document.readyState==='complete' && !document.querySelector('#app').hidden && !document.querySelector('#step1').hidden",'initial F17 scene');
    for(const part of [prefix,prefix+'app.js',prefix+'model.js',prefix+'style.css'])assert.ok(requests.includes(part),'HTTP asset not fetched: '+part);
    assert.ok(await evaluate("document.querySelector('#fictionNotice').textContent.includes('完全架空')"));
    assert.ok(await evaluate("document.querySelector('#scenarioSource').textContent.includes('公式情報ではありません')"));
    assert.ok(await evaluate("document.querySelector('#scenarioUnknowns').textContent.includes('警戒情報')"));

    // Native keyboard Enter advances; focus is moved to new step heading.
    await evaluate("document.querySelector('#next1').focus()");
    await keyboard(command,'Enter','Enter');
    await waitFor(evaluate,"!document.querySelector('#step2').hidden",'comparison');
    assert.equal(await evaluate('document.activeElement?.id'),'heading2');
    await keyboard(command,'Tab','Tab');
    assert.equal(await evaluate('document.activeElement?.id'),'back2','Native Tab should reach previous-step control');
    assert.equal(await evaluate("document.querySelectorAll('#facilityCards article').length"),2);
    assert.ok(await evaluate("document.querySelector('#facilityCards').textContent.includes('記載なし・未確認')"));
    await evaluate("document.querySelector('#back2').click()");
    assert.equal(await evaluate("document.querySelector('#step1').hidden"),false);
    await evaluate("document.querySelector('#conditionPet').click()");
    await evaluate("document.querySelector('#next1').click()");
    assert.ok(await evaluate("document.querySelector('#conditionSummary').textContent.includes('ペット同行')"));
    await evaluate("document.querySelector('#next2').click()");
    assert.equal(await evaluate('document.activeElement?.id'),'heading3');
    assert.equal(await evaluate("document.querySelector('#review').disabled"),true);
    await evaluate("document.querySelectorAll('#choiceButtons button')[1].focus()");
    await keyboard(command,' ','Space');
    assert.equal(await evaluate("document.querySelectorAll('#choiceButtons button[aria-pressed=true]').length"),1);
    assert.equal(await evaluate("document.activeElement?.dataset.choiceId"),'invented-b');
    assert.equal(await evaluate("document.querySelector('#review').disabled"),false);
    await evaluate("document.querySelector('#review').click()");
    assert.ok(await evaluate("document.querySelector('#reviewChoice').textContent.includes('みずき交流室')"));
    assert.ok(await evaluate("document.querySelector('#reviewUnknowns').textContent.includes('開設状況')"));
    assert.ok(await evaluate("document.querySelector('#reviewArea').textContent.includes('安全かどうかは判断しません')"));

    // A new choice revokes the prior review immediately.
    await evaluate("document.querySelectorAll('#choiceButtons button')[0].click()");
    assert.equal(await evaluate("document.querySelector('#reviewArea').hidden"),true);
    await evaluate("document.querySelector('#back3').click()");
    await evaluate("document.querySelector('#next2').click()");
    assert.equal(await evaluate("document.querySelectorAll('#choiceButtons button[aria-pressed=true]').length"),0);
    assert.equal(await evaluate("document.querySelector('#review').disabled"),true);
    await evaluate("document.querySelector('#stop').click()");
    assert.equal(await evaluate("document.querySelector('#interrupted').hidden"),false);
    assert.equal(await evaluate("document.querySelector('#reviewChoice').textContent"),'');
    await evaluate("document.querySelector('#restart').click()");
    assert.equal(await evaluate("document.querySelector('#step1').hidden"),false);
    assert.equal(await evaluate("document.querySelector('#conditionPet').checked"),false);
    assert.equal(await evaluate("document.querySelector('#reviewArea').hidden"),true);

    // Viewports: assert actual scrollWidth does not exceed viewport width.
    for(const width of [320,390,1440]) {
      await command('Emulation.setDeviceMetricsOverride',{width,height:820,deviceScaleFactor:1,mobile:width<700});
      for(const step of [1,2,3]) {
        if(step===2)await evaluate("document.querySelector('#next1').click()");
        if(step===3)await evaluate("document.querySelector('#next2').click()");
        const size=await evaluate('({viewport:document.documentElement.clientWidth, scroll:document.documentElement.scrollWidth, notice:!document.querySelector("#fictionNotice").hidden})');
        assert.ok(size.scroll<=size.viewport+1,`${width}px step ${step}: horizontal overflow ${JSON.stringify(size)}`);
        assert.ok(size.notice,`${width}px step ${step}: training notice missing`);
      }
      await evaluate("document.querySelector('#reset').click()");
    }
    // Fresh HTTP reload starts at step 1, no persisted choice or conditions.
    await evaluate("document.querySelector('#conditionStep').click()");
    await command('Page.navigate',{url});
    await waitFor(evaluate,"document.readyState==='complete' && !document.querySelector('#step1').hidden",'reload');
    assert.equal(await evaluate("document.querySelector('#conditionStep').checked"),false);
    assert.equal(await evaluate("document.querySelector('#reviewChoice').textContent"),'');
    assert.equal(b.errors.length,0,'Chrome runtime errors: '+b.errors.join('; '));
    assert.ok(b.network.every(u=>u.startsWith(origin+'/')||u.startsWith('data:')),'Unexpected external browser request: '+b.network.join(', '));
  } finally {
    await b?.close();
    await new Promise(resolve=>server.close(resolve));
  }
});
