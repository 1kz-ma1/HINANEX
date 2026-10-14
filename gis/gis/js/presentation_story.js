(() => {
  "use strict";
  // E-owned presenter animation: never modifies C's verdict or D's map records.
  const el = id => document.getElementById(id);
  const panel = el("storyPanel");
  const opener = el("mapStoryOpen");
  const camera = window.HINANEX_PRESENTATION_TOUR;
  const timings = [5, 13, 16, 14, 7]; // 55 seconds exactly (wall-clock when tab visible).
  const scenes = [
    { id:"intro", kicker:"2019年 台風19号 / 江戸川区", title:"この避難記録、どこまで確かめられる？",
      line:"地図は現行施設の参考位置。2019年当日の避難先は確定していません。",
      a:["公式資料","事後報告"], b:["HINANEX","読み取り・保持"], c:["C独立監査","根拠を確認"], verdict:"3つの検証を見てみよう" },
    { id:"trace", kicker:"CASE 1 / T0・原本との機械照合", title:"資料を、正しく読み取れたか。",
      line:"65は運用グループ数、66は明細数。建物数ではありません。",
      a:["公式記録","66 明細"], b:["抽出データ","65 グループ / 66 明細"], c:["C機械照合","整合を確認"], verdict:"整合 PASS（人手承認前）" },
    { id:"abstain", kicker:"CASE 2 / T1・判断不能", title:"証拠がなければ、場所は決めない。",
      line:"通常205人・夜間11人の報告はある。しかし当日使われた建物は不明。",
      a:["事後報告","205 人 + 11 人"], b:["使用建物","？ 未確定"], c:["独立監査","紐付け承認 0 件"], verdict:"NOT_EVALUABLE / 比較不可" },
    { id:"negative", kicker:"CASE 3 / 合成負系テスト", title:"誤った処理は、そこで止める。",
      line:"テストで夜間11人を削除、または校舎住所を避難建物と決め付ける。",
      a:["合成の不正入力","11 人の明細を削除"], b:["不正な紐付け","根拠なく建物を断定"], c:["Cの負系テスト","拒否"], verdict:"合成テスト PASS / 実災害の予測不一致ではない" },
    { id:"summary", kicker:"55秒で分かる HINANEX", title:"根拠のない判断を、通さない。",
      line:"正しく読み、分からなければ止め、誤処理を拒否する。予測精度の実証ではありません。",
      a:["読み取る","T0 整合"], b:["決め付けない","T1 比較不可"], c:["誤りを拒否","合成テスト"], verdict:"3つの検証で示したこと" }
  ];
  let deck=null, current=0, remaining=timings[0], elapsed=0, state="idle";
  let interval=null, request=0, mapStarted=false, restoreMap=true, mapRun=0;
  const pauseReason = () => state==="paused" ? "一時停止中" : state==="finished" ? "55秒の説明が終了" : "自動再生中";
  function stopClock(){ if(interval!==null) window.clearInterval(interval); interval=null; }
  function status(v){el("storyLiveStatus").textContent=v;}
  function setMapText(v){el("storyMapStatus").textContent=v;}
  function endCamera(){
    mapRun++;
    if(mapStarted){ camera.halt(); camera.end(restoreMap); mapStarted=false; }
  }
  function startCamera(){
    if(!camera || !["begin","focus","halt","end"].every(k=>typeof camera[k]==="function")){
      setMapText("地図データの参照機能を確認できません。位置は未確認です。"); return;
    }
    const token=++mapRun;
    mapStarted=true;
    camera.begin();
    setMapText("現行D施設の元座標を照合中（2019年の実際の避難先ではありません）。");
    const reduced=!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
    Promise.resolve().then(()=>camera.focus("13123",!reduced,false)).then(result=>{
      if(token!==mapRun||panel.hidden||!mapStarted)return;
      if(result?.state==="mapped" && Number.isSafeInteger(result.total) &&
        Number.isSafeInteger(result.mapped) && result.mapped>0 &&
        result.total>=result.mapped){
        setMapText("現行D：取得 "+result.total+"件 ／ 元座標あり "+result.mapped+
          "件 ／ 位置未確認 "+(result.total-result.mapped)+"件。2019年の使用建物ではありません。");
      }else{
        setMapText("現行Dの位置未取得・未確認。地図のピンなし＝避難施設なし、ではありません。");
      }
    }).catch(()=>{
      if(token===mapRun&&!panel.hidden)setMapText("現行D位置の取得に失敗。場所は推測しません。");
    });
  }
  function render(){
    const scene=scenes[current], visible=state!=="loading"&&state!=="error";
    panel.dataset.scene=scene.id;
    el("storySceneKicker").textContent=scene.kicker;
    el("storySceneTitle").textContent=scene.title;
    el("storySceneLine").textContent=scene.line;
    for(let i=0;i<3;i++){
      el("storyNodeTitle"+i).textContent=[scene.a,scene.b,scene.c][i][0];
      el("storyNodeValue"+i).textContent=[scene.a,scene.b,scene.c][i][1];
    }
    el("storyVerdict").textContent=scene.verdict;
    el("storySceneCount").textContent=(current+1)+" / 5";
    el("storyClock").textContent=remaining+" 秒";
    el("storyBar").style.width=Math.round(elapsed/55*100)+"%";
    el("storyPlay").disabled=!visible||state==="playing"||state==="finished";
    el("storyPause").disabled=state!=="playing";
    el("storyNext").disabled=!visible||state==="finished";
    el("storyRestart").disabled=!visible;
    for (const sceneId of ["trace","abstain","negative"]){
      el("storyJump"+sceneId).setAttribute("aria-pressed",String(scene.id===sceneId));
    }
    status(pauseReason()+(state==="finished"?"。詳細版から原本と監査記録も確認できます。":"。"));
  }
  function advance(){
    if(current===4){
      stopClock();state="finished";remaining=0;elapsed=55;
      render();return;
    }
    current++;
    remaining=timings[current];
    elapsed=timings.slice(0,current).reduce((a,b)=>a+b,0);
    render();
  }
  function tick(){
    if(state!=="playing"||panel.hidden)return;
    if(remaining>0) { remaining--; elapsed=Math.min(55,elapsed+1); }
    if(remaining===0)advance();else{
      el("storyClock").textContent=remaining+" 秒";
      el("storyBar").style.width=Math.round(elapsed/55*100)+"%";
    }
  }
  function play(){
    if(!deck||state==="playing"||state==="finished")return;
    state="playing"; stopClock();
    interval=window.setInterval(tick,1000);render();
  }
  function pause(){
    if(state!=="playing")return;
    stopClock();state="paused";render();
  }
  function jump(index){
    if(!deck||index<0||index>4)return;
    stopClock();state="paused";current=index;
    remaining=timings[index];
    elapsed=timings.slice(0,index).reduce((a,b)=>a+b,0);render();
  }
  function restart(){
    if(!deck)return;
    jump(0);play();
  }
  function linkEvidence(data){
    const school=data.sources.find(x=>x.id==="school");
    if(school){
      el("storyOfficialSource").href=school.official_url;
      el("storyMachineAudit").href=school.machine_audit_url;
    }
  }
  function validate(data){
    const safe=window.HINANEX_VALIDATE_EVIDENCE;
    if(typeof safe!=="function") throw new Error("C verification gate missing");
    const verified=safe(data);
    const a=verified.cases;
    const contains=(s,parts)=>typeof s==="string"&&parts.every(v=>s.includes(v));
    if(!contains(a[0].input_text,["65","66","26,761"]) ||
       !contains(a[0].output_text,["65","66","26,761"]) ||
       !contains(a[1].input_text,["205","11"]) ||
       !contains(a[1].output_text,["null"]) ||
       !contains(a[2].input_text,["11","合成"]) ||
       !contains(a[2].audit_text,["合成","MISMATCH"])){
      throw new Error("C numeric labels do not match 55-second presentation");
    }
    return verified;
  }
  async function open(){
    if(!panel.hidden)return;
    if(!el("mapEvidenceReplayPanel").hidden) el("mapEvidenceReplayClose").click();
    el("mapTourClose").click(); // stop legacy flyover first
    request++;const token=request;
    panel.hidden=false;opener.setAttribute("aria-expanded","true");
    el("map").dataset.storyActive="true";
    el("storyClose").focus();
    stopClock();state="loading"; deck=null; restoreMap=true; current=0;elapsed=0;
    remaining=timings[0];
    status("Cの記録を検証中。読み込めない場合は再生しません。");
    el("storyContent").hidden=true;
    el("storyLoadStatus").hidden=false;
    el("storyLoadStatus").textContent="正本データを確認しています。";
    setMapText("Cの正本を確認しています。現行D座標は参考表示です。");
    try{
      const url=new URL("../../evidence/2019_edogawa_evidence_cases.json",document.baseURI);
      const response=await window.fetch(url,{cache:"no-store"});
      if(!response.ok)throw new Error("C evidence HTTP "+response.status);
      const verified=validate(await response.json());
      if(token!==request||panel.hidden)return;
      deck=verified;linkEvidence(verified);
      el("storyContent").hidden=false;
      el("storyLoadStatus").hidden=true;
      current=0;state="paused";
      startCamera();play();
    }catch(e){
      if(token!==request||panel.hidden)return;
      state="error";deck=null;el("storyContent").hidden=true;
      el("storyLoadStatus").hidden=false;
      el("storyLoadStatus").textContent="説明用の正本データを確認できず、再生を停止しました。";
      status("根拠データを確認できません。55秒デモは停止しました。");
      setMapText("未確認のデータを地図に追加していません。");
      console.warn("[HINANEX] 55-second evidence storyboard unavailable",e);
    }
  }
  function close(){
    if(panel.hidden)return;
    request++;stopClock();endCamera();
    delete el("map").dataset.storyActive;
    panel.hidden=true;opener.setAttribute("aria-expanded","false");
    state="idle";el("mapTourOpen").click();opener.focus();
  }
  function openDetailed(){
    close();
    el("mapHistoricalEvidenceDemo").click();
  }
  opener.addEventListener("click",open);
  el("storyClose").addEventListener("click",close);
  el("storyPlay").addEventListener("click",play);
  el("storyPause").addEventListener("click",pause);
  el("storyNext").addEventListener("click",()=>{pause();advance();});
  el("storyRestart").addEventListener("click",restart);
  el("storyJumptrace").addEventListener("click",()=>jump(1));
  el("storyJumpabstain").addEventListener("click",()=>jump(2));
  el("storyJumpnegative").addEventListener("click",()=>jump(3));
  el("storyDetailed").addEventListener("click",openDetailed);
  document.addEventListener("visibilitychange",()=>{if(document.hidden)pause();});
  document.addEventListener("keydown",event=>{
    if(panel.hidden)return;
    if(event.key==="Escape"){
      event.preventDefault();event.stopImmediatePropagation?.();close();return;
    }
    if(event.key==="Tab"){
      const f=Array.from(panel.querySelectorAll('button:not([disabled]),a[href]'));
      if(!f.length)return;
      if(event.shiftKey&&document.activeElement===f[0]){event.preventDefault();f[f.length-1].focus();}
      else if(!event.shiftKey&&document.activeElement===f[f.length-1]){event.preventDefault();f[0].focus();}
    }
  },true);
  function onGesture(){
    if(panel.hidden)return;
    restoreMap=false;pause();mapRun++;if(mapStarted)camera.halt();
    setMapText("手動で地図を操作しました。選択した位置は閉じても保持されます。");
  }
  for(const e of ["pointerdown","wheel","touchstart"]){
    el("map").addEventListener(e,onGesture,{passive:true});
  }
})();