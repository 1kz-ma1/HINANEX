'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const { spawn } = require('node:child_process');
const path = require('node:path');
const here = __dirname;
const allowed = new Set(['/index.html', '/app.js', '/route-model.js', '/style.css']);
const harness = `<!doctype html><meta charset="utf-8"><title>F07 Chromium smoke</title>
<iframe id="app" src="/index.html" style="width:320px;height:840px"></iframe><pre id="result">PENDING</pre>
<script>
const check=(ok,msg)=>{if(!ok)throw Error(msg)};
app.addEventListener('load',()=>{try{
 const d=app.contentDocument; const by=id=>d.getElementById(id);
 const fire=(node,value)=>{node.value=value;node.dispatchEvent(new Event('change',{bubbles:true}))};
 const visible=()=>by('routeLine').getAttribute('points');
 const drawn=()=>visible() && !by('routeLine').hasAttribute('hidden') && d.defaultView.getComputedStyle(by('routeLine')).display!=='none';
 const result=()=>by('status').dataset.state;
 check(result()==='UNSELECTED','initial state');
 check(by('selectionSummary').textContent.includes('未選択'),'initial selection summary');
 check(!visible(),'initial geometry');
 check(by('generate').disabled,'initial disabled action');
 check(by('origin').getAttribute('id')==='origin'&&d.querySelector('label[for="origin"]'),'label');
 fire(by('origin'),'start-a');fire(by('destination'),'goal-x');
 check(result()==='READY','ready');
 by('generate').focus();check(d.activeElement===by('generate'),'keyboard focus');
 by('generate').click();check(result()==='SHOWN'&&drawn(),'shown');
 fire(by('destination'),'goal-y');check(result()==='READY'&&!visible(),'destination invalidation');
 by('generate').click();check(drawn(),'route regenerate');
 fire(by('condition'),'pattern-2');check(!visible(),'condition invalidation');
 fire(by('condition'),'invalid-pattern');check(result()==='NO_GO'&&!visible(),'unsupported pattern is NO-GO');
 check(by('generate').disabled,'unsupported pattern blocks generate');
 fire(by('condition'),'pattern-2');check(result()==='READY','valid pattern recovery');
 by('generate').click();check(drawn(),'second pattern');
 check(by('selectionSummary').textContent.includes('模式線パターン 2'),'selection summary updated');
 by('simulateFailure').click();check(!visible(),'failure toggle invalidation');
 by('generate').click();check(result()==='NO_GO'&&!visible(),'failure NO-GO');
 check(by('status').textContent.includes('NO-GO'),'NO-GO copy');
 by('simulateFailure').click();by('generate').click();check(drawn(),'recovery');
 by('clear').click();check(!visible()&&result()==='READY','clear');
 fire(by('origin'),'');check(result()==='UNSELECTED'&&!visible(),'reset selection');
 for(const w of [320,390,1440]){
   app.style.width=w+'px';
   check(d.documentElement.scrollWidth<=d.documentElement.clientWidth+1,'horizontal overflow '+w);
 }
 check(d.querySelector('.warning').textContent.includes('架空地点・合成デモ'),'permanent warning');
 document.getElementById('result').textContent='F07_BROWSER_PASS: selection / stale purge / no-go / focus / 320-390-1440';
}catch(e){document.getElementById('result').textContent='F07_BROWSER_FAIL: '+e.stack}}
);
</script>`;
async function run() {
  const requests=[];
  const server=http.createServer((req,res)=>{
    requests.push(req.url);
    const url=req.url.split('?')[0];
    if(url==='/__harness') {res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(harness);return;}
    if(!allowed.has(url)){res.writeHead(404);res.end();return;}
    const ext=path.extname(url);
    res.writeHead(200,{'Content-Type':ext==='.css'?'text/css':ext==='.html'?'text/html':'text/javascript'});
    res.end(fs.readFileSync(path.join(here,path.basename(url))));
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  try {
    const browser=process.env.CHROMIUM_BIN || 'chromium';
    const args=['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
      '--disable-background-networking','--no-first-run','--no-default-browser-check',
      '--disable-extensions','--disable-sync','--window-size=1550,1100',
      '--virtual-time-budget=4000','--dump-dom',`http://127.0.0.1:${server.address().port}/__harness`];
    const output=await new Promise((resolve,reject)=>{
      const proc=spawn(browser,args,{stdio:['ignore','pipe','pipe']});
      let stdout='',stderr='';
      const timeout=setTimeout(()=>{proc.kill('SIGKILL');reject(new Error('Chromium timeout'))},18000);
      proc.stdout.on('data',b=>stdout+=b);proc.stderr.on('data',b=>stderr+=b);
      proc.on('error',e=>{clearTimeout(timeout);reject(e)});
      proc.on('close',code=>{clearTimeout(timeout);if(code!==0)reject(new Error(stderr.slice(-2500)));else resolve(stdout)});
    });
    const result=output.match(/<pre id="result">([^<]*)<\/pre>/)?.[1];
    assert.ok(result && result.startsWith('F07_BROWSER_PASS:'),result||'No browser test result');
    assert.deepEqual([...new Set(requests)].filter(p=>p!=='/favicon.ico').sort(),
      ['/__harness','/app.js','/index.html','/route-model.js','/style.css'].sort());
    console.log(result);
    console.log('LOCAL_NETWORK_ONLY_PASS:',requests.filter(x=>x!=='/favicon.ico').join(', '));
  } finally {await new Promise(resolve=>server.close(resolve));}
}
run().catch(e=>{console.error(e);process.exitCode=1});
