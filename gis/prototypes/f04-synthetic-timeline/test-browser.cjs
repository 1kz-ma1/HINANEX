'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const { spawn } = require('node:child_process');
const path = require('node:path');
const here = __dirname;
const allowed = new Set(['/index.html','/style.css','/synthetic-data.js','/timeline-model.js','/app.js',
  '/comparison-model.js','/comparison-app.js']);
const harness = `<!doctype html><html><meta charset="utf-8"><title>F04 real HTTP Chromium QA</title>
<iframe id="app" src="/index.html" style="width:320px;height:850px;border:0"></iframe>
<pre id="result">PENDING</pre><script>
const check = (ok, msg) => { if(!ok) throw Error(msg); };
function change(node,value,event='change'){node.value=value;node.dispatchEvent(new Event(event,{bubbles:true}));}
app.addEventListener('load', async ()=>{
 try {
  const d=app.contentDocument, by=id=>d.getElementById(id);
  const state=()=>by('status').dataset.state;
  const count=()=>Number(by('floodGrid').dataset.paintedCount);
  const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
  check(state()==='UNSELECTED'&&count()===0&&by('step').disabled,'initial NO-GO');
  check(by('emptyOverlay').hidden===false,'unselected overlay');
  check(d.querySelectorAll('.cell').length===40,'40 synthetic cells');
  check(d.querySelectorAll('[role=status]').length===1,'one live status');
  check(d.querySelector('meta[http-equiv=Content-Security-Policy]').content.includes("connect-src 'none'"),'strict CSP');
  check(by('play').disabled&&by('pause').disabled,'initial disabled controls');
  check(by('scenario').options.length===3,'explicit scenario choices');
  change(by('scenario'),'fiction-a');
  check(state()==='PAUSED'&&count()===0&&by('step').max==='3','A first frame');
  change(by('step'),'2','input');
  check(by('step').value==='2'&&count()===5&&by('timeLabel').textContent.includes('模擬ステップ 2'),'slider moves frame');
  by('play').click();
  check(state()==='PLAYING'&&!by('pause').disabled,'play starts');
  change(by('scenario'),'fiction-b');
  check(state()==='PAUSED'&&count()===1&&by('step').value==='0','switch deletes A');
  await sleep(1000);
  check(count()===1&&by('step').value==='0','stale timer cannot advance B');
  by('play').click();
  await sleep(1000);
  check(count()===3&&by('step').value==='1','real clock advances on HTTP Chromium');
  by('pause').click();
  check(state()==='PAUSED'&&by('pause').disabled,'pause stops');
  await sleep(1000);
  check(by('step').value==='1','paused remains on same frame');
  by('restart').click();
  check(by('step').value==='0'&&count()===1,'restart clears and starts from first');
  by('clear').click();
  check(state()==='UNSELECTED'&&count()===0&&by('scenario').value===''&&by('step').disabled,'clear erases all');
  check(d.activeElement===by('scenario'),'clear focuses scenario');
  check(by('emptyOverlay').hidden===false,'clear restores warning overlay');
  // Model NO-GO input is tested independently from the UI's closed select.
  const bad=d.defaultView.HINANEX_F04.createSession().select('not-a-fixture');
  check(bad.status==='NO_GO'&&bad.cells.length===0,'invalid model fails closed');
  for(const w of [320,390,1440]){
   app.style.width=w+'px';
   await sleep(50);
   check(d.documentElement.scrollWidth<=d.documentElement.clientWidth+1,'no horizontal overflow '+w);
  }
  check(d.querySelector('.warning').textContent.includes('完全架空・訓練用'),'persistent synthetic warning');
  result.textContent='F04_BROWSER_PASS: localhost HTTP / switch / slider / play / pause / restart / stale purge / 320-390-1440';
 } catch(e) {result.textContent='F04_BROWSER_FAIL: '+e.stack;}
});</script></html>`;

async function run() {
  const requests = [];
  const server = http.createServer((req,res)=>{
    requests.push(req.url);
    const url = req.url.split('?')[0];
    if (url === '/__qa') {res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(harness);return;}
    if (!allowed.has(url)) {res.writeHead(404);res.end();return;}
    const type = url.endsWith('.html') ? 'text/html' : url.endsWith('.css') ? 'text/css' : 'text/javascript';
    res.writeHead(200,{'Content-Type':type+'; charset=utf-8'});
    res.end(fs.readFileSync(path.join(here, url.slice(1))));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    const browser=process.env.CHROMIUM_BIN || 'chromium';
    const args=['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
      '--disable-background-networking','--no-first-run','--no-default-browser-check',
      '--disable-extensions','--disable-sync','--window-size=1550,1000',
      '--virtual-time-budget=6000','--dump-dom',`http://127.0.0.1:${server.address().port}/__qa`];
    const output=await new Promise((resolve,reject)=>{
      const proc=spawn(browser,args,{stdio:['ignore','pipe','pipe']});
      let stdout='',stderr='';
      const timeout=setTimeout(()=>{proc.kill('SIGKILL');reject(new Error('Chromium timeout'))},18000);
      proc.stdout.on('data',b=>stdout+=b);proc.stderr.on('data',b=>stderr+=b);
      proc.on('error',e=>{clearTimeout(timeout);reject(e)});
      proc.on('close',code=>{clearTimeout(timeout);if(code!==0) reject(new Error(stderr.slice(-1500)));else resolve(stdout)});
    });
    const result=output.match(/<pre id="result">([^<]*)<\/pre>/)?.[1];
    assert.ok(result && result.startsWith('F04_BROWSER_PASS:'), result||'No QA result');
    assert.deepEqual([...new Set(requests)].filter(x=>x!=='/favicon.ico').sort(),
      ['/__qa',...allowed].sort());
    console.log(result);
    console.log('LOOPBACK_REQUESTS_ONLY_PASS:',requests.filter(x=>x!=='/favicon.ico').join(', '));
  } finally {await new Promise(resolve=>server.close(resolve));}
}
run().catch(error=>{console.error(error);process.exitCode=1});
