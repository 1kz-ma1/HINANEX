'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const {spawn} = require('node:child_process');
const path = require('node:path');
const here=__dirname;
const allowed=new Set([
  '/index.html','/style.css','/synthetic-data.js','/timeline-model.js','/app.js',
  '/comparison-model.js','/comparison-app.js'
]);
const harness=`<!doctype html><html><meta charset="utf-8"><title>F04 S2 localhost Chrome</title>
<iframe id="app" src="/index.html" style="width:320px;height:900px;border:0"></iframe>
<pre id="result">PENDING</pre>
<script>
const check=(ok,msg)=>{if(!ok)throw Error(msg)};
function change(node,value){node.value=value;node.dispatchEvent(new Event('change',{bubbles:true}))}
app.addEventListener('load',async ()=>{
 try {
  const d=app.contentDocument, by=id=>d.getElementById(id);
  const status=()=>by('compareStatus').dataset.state;
  const grid=id=>by(id);
  const actual=()=>grid('compareGridDelta').dataset.active;
  const filled=id=>Number(grid(id).dataset.filledCount);
  const cleared=()=>['compareGridBefore','compareGridAfter','compareGridDelta']
    .every(id=>grid(id).dataset.active==='false'&&filled(id)===0);
  check(status()==='UNSELECTED'&&cleared(),'initial no-go empty comparison');
  check(d.querySelectorAll('[role=status]').length===1,'S1 live status remains unique');
  check(by('compareBefore').disabled&&by('compareAfter').disabled&&by('compareRun').disabled,'initial no controls');
  check(d.querySelectorAll('.compare-cell').length===120,'all three 40-cell grids built');
  check(d.querySelector('.warning').textContent.includes('完全架空・訓練用'),'permanent synthetic warning');
  change(by('scenario'),'fiction-a');
  check(status()==='SELECTING'&&by('compareBefore').options.length===5,'case activates 4 steps');
  check(by('compareRun').disabled&&cleared(),'explicit pair required');
  change(by('compareBefore'),'0');change(by('compareAfter'),'3');
  check(status()==='READY'&&cleared(),'pair selected but compare not yet displayed');
  by('compareRun').click();
  check(status()==='SHOWN'&&actual()==='true','compare explicit');
  check(by('addedCount').textContent==='8'&&by('removedCount').textContent==='0','forward additions');
  check(by('emptyCount').textContent==='32','unchanged empty counted');
  check(filled('compareGridBefore')===0&&filled('compareGridAfter')===8,'two complete frames');
  check(d.querySelector('#compareGridDelta [data-cell="3-1"]').classList.contains('compare-newly'),'delta marked with class');
  check(by('comparisonSummary').textContent.includes('現実の浸水面積'),'textual caveat');
  change(by('compareBefore'),'3');
  check(cleared()&&status()==='READY','changing selection synchronously purges old grids');
  change(by('compareAfter'),'0');by('compareRun').click();
  check(by('removedCount').textContent==='8'&&by('addedCount').textContent==='0','reverse changes');
  check(d.querySelector('#compareGridDelta [data-cell="3-1"]').classList.contains('compare-removed'),'removed class distinct');
  change(by('compareAfter'),'3');by('compareRun').click();
  check(by('continuedCount').textContent==='8'&&by('addedCount').textContent==='0'&&by('removedCount').textContent==='0','same step unchanged filled');
  by('compareClear').click();
  check(cleared()&&by('compareBefore').value===''&&d.activeElement===by('compareBefore'),'comparison reset and keyboard focus');
  change(by('compareBefore'),'0');change(by('compareAfter'),'3');by('compareRun').click();
  change(by('scenario'),'fiction-b');
  check(cleared()&&by('compareAfter').value===''&&status()==='SELECTING','switch purges stale result');
  change(by('compareBefore'),'0');change(by('compareAfter'),'3');by('compareRun').click();
  check(by('addedCount').textContent==='5'&&by('continuedCount').textContent==='1','B fixture difference');
  by('play').click();
  check(by('status').dataset.state==='PLAYING'&&status()==='SHOWN','S1 playback independent');
  by('pause').click();
  check(by('status').dataset.state==='PAUSED'&&status()==='SHOWN','S1 pause independent');
  by('clear').click();
  check(cleared()&&status()==='UNSELECTED'&&by('scenario').value==='','S1 clear also clears S2');
  const unsupported=d.createElement('option');
  unsupported.value='real-area';unsupported.textContent='invalid';by('scenario').appendChild(unsupported);
  change(by('scenario'),'real-area');
  check(status()==='NO_GO'&&cleared()&&by('status').dataset.state==='NO_GO','invalid scenario NO-GO');
  for(const width of [320,390,1440]){
    app.style.width=width+'px';
    await new Promise(resolve=>setTimeout(resolve,70));
    check(d.documentElement.scrollWidth<=d.documentElement.clientWidth+1,'no horizontal overflow '+width);
  }
  document.getElementById('result').textContent='F04_S2_BROWSER_PASS: HTTP / forward / reverse / equal / reset / scenario invalidation / S1 / 320-390-1440';
 } catch(e){document.getElementById('result').textContent='F04_S2_BROWSER_FAIL: '+e.stack;}
});
</script></html>`;

async function main(){
 const requests=[];
 const server=http.createServer((req,res)=>{
   const url=req.url.split('?')[0];
   requests.push(url);
   if(url==='/__qa'){res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});res.end(harness);return;}
   if(!allowed.has(url)){res.writeHead(404);res.end();return;}
   const contentType=url.endsWith('.html')?'text/html':url.endsWith('.css')?'text/css':'text/javascript';
   res.writeHead(200,{'Content-Type':contentType+'; charset=utf-8'});
   res.end(fs.readFileSync(path.join(here,url.slice(1))));
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
   const binary=process.env.CHROMIUM_BIN||'chromium';
   const args=['--headless','--no-sandbox','--disable-gpu','--disable-dev-shm-usage',
     '--disable-background-networking','--no-first-run','--no-default-browser-check',
     '--disable-extensions','--disable-sync','--window-size=1550,1100',
     '--virtual-time-budget=3500','--dump-dom',`http://127.0.0.1:${server.address().port}/__qa`];
   const output=await new Promise((resolve,reject)=>{
     const child=spawn(binary,args,{stdio:['ignore','pipe','pipe']});
     let stdout='',stderr='';
     const timer=setTimeout(()=>{child.kill('SIGKILL');reject(new Error('Chromium timeout'))},22000);
     child.stdout.on('data',chunk=>stdout+=chunk);
     child.stderr.on('data',chunk=>stderr+=chunk);
     child.on('error',err=>{clearTimeout(timer);reject(err)});
     child.on('close',code=>{clearTimeout(timer);code===0?resolve(stdout):reject(new Error(stderr.slice(-2500)))});
   });
   const result=output.match(/<pre id="result">([^<]*)<\/pre>/)?.[1];
   assert.ok(result&&result.startsWith('F04_S2_BROWSER_PASS:'),result||'Missing browser result');
   assert.deepEqual([...new Set(requests)].filter(x=>x!=='/favicon.ico').sort(),
     ['/__qa',...allowed].sort());
   console.log(result);
   console.log('F04_S2_LOOPBACK_ONLY_PASS: '+requests.join(', '));
 } finally{await new Promise(resolve=>server.close(resolve));}
}
main().catch(err=>{console.error(err);process.exitCode=1});
