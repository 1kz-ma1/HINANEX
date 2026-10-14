(() => {
  "use strict";
  // Presentation-only orchestrator: all filtering and proof are computed from
  // actual source records by the E map adapter. Never decide flood safety here.
  const el=id=>document.getElementById(id);
  const panel=el("filterDemoPanel"),opener=el("mapFilterDemoOpen");
  const api=window.HINANEX_FACILITY_PRESENTER;
  const durations=[8,12,14,11,7]; // 52 seconds
  let request=0,clock=null,scene=0,remaining=durations[0],elapsed=0,
    state="idle",summary=null,detail=null,restore=true;
  const set=id=>text=>{el(id).textContent=text;};
  const status=set("filterDemoStatus");
  function clearTimer(){if(clock!==null)window.clearInterval(clock);clock=null;}
  function label(value){return value===null||value===undefined||value===""?"未確認（null）":String(value);}
  function render(){
    if(!summary)return;
    const titles=[
      "いま、どの施設情報が確認できる？",
      "条件に一致する施設だけを表示",
      "抽出した施設へ地図が移動",
      "指定した条件と、元データを照合",
      "絞り込みを、避難先選定の基盤へ"
    ],descriptions=[
      "最初に取得レコード数と、地図に置ける元座標の数を確認します。",
      "データから確認できた属性を使い、実際に地図上の施設マーカーを絞り込みます。",
      "条件に一致した地域の避難施設の元座標へ移動し、その施設の情報を確認します。",
      "なぜ表示されたかを条件と元データの値で照合。未判定の情報もそのまま示します。",
      "将来は災害状況や施設の利用条件を組み合わせる構想。現時点では安全な避難先の推奨ではありません。"
    ];
    el("filterDemoStep").textContent="STEP "+(scene+1)+" / 5";
    el("filterDemoTitle").textContent=titles[scene];
    el("filterDemoCaption").textContent=descriptions[scene];
    el("filterDemoClock").textContent=(state==="finished"?"終了":remaining+"秒");
    el("filterDemoTotal").textContent=String(summary.mapped);
    el("filterDemoMatched").textContent=String(scene===0?summary.mapped:summary.matches);
    el("filterDemoCriterion").textContent=scene===0?"まず、施設情報の全体像を確認":summary.criterion;
    el("filterDemoCriterionNote").textContent=summary.classified===0 ?
      "洪水対応分類が確定した記録は0件。今回は元データの施設属性で絞り込みます。" :
      "洪水対応分類が付いた施設でも、安全性・開設状況は未判定です。";
    el("filterDemoEvidence").hidden=scene<2||!detail;
    el("filterDemoFuture").hidden=scene!==4;
    if(detail){
      el("filterDemoFacility").textContent=detail.name;
      el("filterDemoEvidenceCriterion").textContent=detail.criterion;
      el("filterDemoEvidenceValue").textContent=label(detail.criterionValue);
      el("filterDemoDecision").textContent=detail.decision==="UNKNOWN"?"未判定（UNKNOWN）":
        detail.decision==="CANDIDATE"?"候補として分類（安全性未判定）":"対象外として分類（安全性未判定）";
      el("filterDemoReason").textContent=label(detail.reason||detail.sourceTrace);
      const link=el("filterDemoSourceLink");
      link.hidden=!detail.sourceUrl;
      if(detail.sourceUrl)link.href=detail.sourceUrl;else link.removeAttribute("href");
    }
    el("filterDemoProgress").style.width=Math.round(elapsed/52*100)+"%";
    el("filterDemoPlay").disabled=state==="playing"||state==="finished";
    el("filterDemoPause").disabled=state!=="playing";
    el("filterDemoNext").disabled=state==="finished";
    el("filterDemoRestart").disabled=false;
    status((state==="finished"?"発表デモの再生完了":state==="paused"?"一時停止中":"自動再生中")+
      "｜"+summary.region+"：取得 "+summary.sourceTotal+"件／元座標あり "+summary.mapped+
      "件／座標未確認 "+summary.missing+"件。");
  }
  function switchScene(next){
    if(!summary||next<0||next>=durations.length)return;
    scene=next;remaining=durations[scene];
    elapsed=durations.slice(0,scene).reduce((a,b)=>a+b,0);
    if(scene===1){
      const r=api.apply();
      if(r.state!=="filtered"||r.matches!==summary.matches){
        clearTimer();state="paused";
        status("抽出条件の反映を確認できません。再生を停止しました。");return;
      }
    }
    if(scene===2){
      const r=api.inspect();
      if(r.state!=="inspected"||!r.name||!r.criterion){
        clearTimer();state="paused";
        status("施設の元データを確認できません。再生を停止しました。");return;
      }
      detail=r;
    }
    render();
  }
  function advance(){
    if(scene===durations.length-1){
      clearTimer();state="finished";remaining=0;elapsed=52;render();return;
    }
    switchScene(scene+1);
  }
  function tick(){
    if(state!=="playing"||panel.hidden)return;
    remaining=Math.max(0,remaining-1);elapsed=Math.min(52,elapsed+1);
    if(remaining===0)advance();else{
      el("filterDemoClock").textContent=remaining+"秒";
      el("filterDemoProgress").style.width=Math.round(elapsed/52*100)+"%";
    }
  }
  function play(){
    if(!summary||state==="playing"||state==="finished")return;
    state="playing";clearTimer();
    clock=window.setInterval(tick,1000);render();
  }
  function pause(){
    if(state!=="playing")return;
    clearTimer();state="paused";render();
  }
  function close(){
    if(panel.hidden)return;
    request++;clearTimer();state="idle";
    api?.end(restore);
    panel.hidden=true;summary=null;detail=null;
    opener.setAttribute("aria-expanded","false");
    getLegacyTour();opener.focus();
  }
  function getLegacyTour(){el("mapTourOpen").click();}
  async function open(){
    if(!panel.hidden)return;
    if(!api||!["begin","apply","inspect","halt","end"].every(k=>typeof api[k]==="function")){
      return;
    }
    el("mapTourClose").click();
    if(!el("storyPanel").hidden)el("storyClose").click();
    if(!el("mapEvidenceReplayPanel").hidden)el("mapEvidenceReplayClose").click();
    const token=++request;
    panel.hidden=false;opener.setAttribute("aria-expanded","true");
    el("filterDemoClose").focus();
    el("filterDemoContent").hidden=true;
    summary=null;detail=null;scene=0;elapsed=0;remaining=durations[0];
    restore=true;state="loading";clearTimer();
    status("現在の地域の施設データを確認しています。根拠不明の施設は絞り込みません。");
    try {
      const r=await api.begin();
      if(token!==request||panel.hidden)return;
      if(r.state!=="ready" || !r.criterion || !(r.matches>0) ||
        !(r.matches<r.mapped) || !(r.mapped<=r.sourceTotal)){
        status("この地域の取得済みデータでは、施設を分ける条件を確認できません。架空の候補や絞込件数は表示しません。");
        return;
      }
      summary=r;
      el("filterDemoContent").hidden=false;
      play();
    } catch(e){
      if(token!==request||panel.hidden)return;
      status("施設情報の確認に失敗しました。推測による抽出は行いません。");
      console.warn("[HINANEX] D source presenter unavailable",e);
    }
  }
  opener.addEventListener("click",open);
  el("filterDemoClose").addEventListener("click",close);
  el("filterDemoPlay").addEventListener("click",play);
  el("filterDemoPause").addEventListener("click",()=>{pause();api.halt();});
  el("filterDemoNext").addEventListener("click",()=>{pause();advance();});
  el("filterDemoRestart").addEventListener("click",()=>{close();open();});
  document.addEventListener("keydown",event=>{
    if(panel.hidden)return;
    if(event.key==="Escape"){
      event.preventDefault();event.stopImmediatePropagation?.();close();
    }else if(event.key==="Tab"){
      const nodes=Array.from(panel.querySelectorAll('button:not([disabled]),a[href]'));
      if(!nodes.length)return;
      if(event.shiftKey&&document.activeElement===nodes[0]){
        event.preventDefault();nodes[nodes.length-1].focus();
      }else if(!event.shiftKey&&document.activeElement===nodes[nodes.length-1]){
        event.preventDefault();nodes[0].focus();
      }
    }
  },true);
  document.addEventListener("visibilitychange",()=>{if(document.hidden){pause();api?.halt();}});
  function onManualGesture(){
    if(panel.hidden)return;
    restore=false;pause();api.halt();
    status("手動で地図を操作したため再生を停止しました。閉じてもこの地図位置を保持します。");
  }
  for(const e of ["pointerdown","wheel","touchstart"]){
    el("map").addEventListener(e,onManualGesture,{passive:true});
  }
})();