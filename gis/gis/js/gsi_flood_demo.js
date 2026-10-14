(() => {
  "use strict";
  // GSI-only presenter. Never invents or joins an actual D building identity.
  const get=id=>document.getElementById(id);
  const panel=get("gsiFloodDemoPanel"),opener=get("mapGsiFloodDemoOpen");
  const api=window.HINANEX_GSI_FLOOD_PRESENTER;
  const timings=[7,12,12,12,7]; // 50 presenter seconds exactly
  let sequence=0,state="idle",clock=null,scene=0,remaining=7,elapsed=0,
      data=null,item=null,dStatus=null,restore=true;
  const titles=[
    "洪水の指定は、どの資料で確認する？",
    "洪水用に指定された掲載地点だけを表示",
    "１つ選んで、公式データを確認",
    "確認できたことと、未判定を分ける",
    "ここから、避難先選定を支える仕組みへ"
  ];
  const explanations=[
    "D施設の一覧と、国土地理院の災害種別ごとの指定緊急避難場所は別の情報源です。",
    "GSIが洪水向けに公開したskhb01だけを地図に表示。これは全避難所からの安全ランキングではありません。",
    "掲載地点の名称・住所・原文の行を確認。disaster1=1は洪水について指定があることを示します。",
    "GSIで指定を確認できても、Dの未判定を勝手に確定できません。両データは未照合です。",
    "今は公式指定と出典を確認する基盤。開設・浸水・経路等を統合した避難先選定支援は今後の構想です。"
  ];
  function stopClock(){if(clock!==null)window.clearInterval(clock);clock=null;}
  function writeStatus(s){get("gsiFloodDemoStatus").textContent=s;}
  function unavailable(reason) {
    // A missing/invalid official catalog is never interpreted as "no
    // designated sites". Offer the already working D-only presentation,
    // clearly labeled as a different source and a different capability.
    const messages={
      NO_REGION_SOURCE_POINT:"選択地域の元座標を確認できません。公式掲載地点を推測せず停止しました。",
      ORIGIN_OUTSIDE_SOURCE_TILE:"この地点を含むGSIタイルは検証・配信されていません。別地点の結果を流用しません。",
      UNVERIFIED_SOURCE:"この地点のGSI検証済みデータを読み込めません。配信・検証状態の確認が必要です。"
    };
    writeStatus(messages[reason] || "GSI公式データの検証結果を確認できないため、再生を停止しました。");
    get("gsiFloodDemoFallback").hidden=false;
    get("gsiFloodDemoFallbackReason").textContent=
      "洪水指定の掲載有無・現在の安全性は判断できません。"+
      "D施設の属性絞り込みは別データで実行できます。";
  }
  function value(v){return v==null||v===""?"未確認":String(v);}
  function render(){
    if(!data)return;
    get("gsiFloodDemoPhase").textContent=String(scene+1).padStart(2,"0")+" / 05";
    get("gsiFloodDemoClock").textContent=state==="complete"?"終了":remaining+"秒";
    get("gsiFloodDemoTitle").textContent=titles[scene];
    get("gsiFloodDemoMessage").textContent=explanations[scene];
    get("gsiFloodDemoCount").textContent=String(data.total);
    get("gsiFloodDemoShown").textContent=String(data.shown);
    get("gsiFloodDemoEvidence").hidden=scene<2||!item;
    get("gsiFloodDemoContrast").hidden=scene!==3;
    get("gsiFloodDemoFuture").hidden=scene!==4;
    if(item){
      get("gsiFloodDemoName").textContent=item.name;
      get("gsiFloodDemoAddress").textContent=value(item.address);
      get("gsiFloodDemoTrace").textContent=value(item.sourceTrace);
      get("gsiFloodDemoCoverage").textContent=item.tileCount+"/"+item.requestedTiles+
        " タイル（未検証範囲は含まない）";
      const a=get("gsiFloodDemoOfficial");
      a.hidden=!item.sourceUrl;
      if(item.sourceUrl)a.href=item.sourceUrl;
      else a.removeAttribute("href");
    }
    if(scene===3){
      get("gsiFloodDemoDStatus").textContent=dStatus?.state==="separate-source"
        ?"D施設の元座標あり "+dStatus.mapped+"件のうち洪水対応未判定 "+
          dStatus.unclassified+"件。GSI掲載地点との同一施設照合は未実施。"
        :"D施設の判定情報は未取得。0件や危険とは断定できません。";
    }
    get("gsiFloodDemoProgress").style.width=Math.round(elapsed/50*100)+"%";
    get("gsiFloodDemoPlay").disabled=state==="playing"||state==="complete";
    get("gsiFloodDemoPause").disabled=state!=="playing";
    get("gsiFloodDemoNext").disabled=state==="complete";
    get("gsiFloodDemoRestart").disabled=false;
    writeStatus((state==="complete"?"再生完了":state==="paused"?"一時停止中":"再生中")+
      "｜公式に検証済み "+data.verifiedTiles+"/"+data.requestedTiles+
      " タイル。掲載地点 "+data.total+"件（選択した自治体全体の件数ではありません）。");
  }
  function changeScene(next) {
    if(!data||next<0||next>=timings.length)return;
    // Ground every visible transition in the existing accepted-source map.
    let proof=null;
    if(next===1){
      proof=api.show();
      if(proof?.state!=="shown"||proof.count!==data.total) return false;
    }else if(next===2){
      proof=api.inspect();
      if(proof?.state!=="inspected"||!proof.name||proof.disaster1Raw!==1||
          !proof.sourceTrace||!proof.sourceUrl) return false;
      item=proof;
    }else if(next===3){
      dStatus=api.compareD(); // does not assert D/GSI identity
    }else if(next===0){
      return false;
    }
    scene=next;
    remaining=timings[next];
    elapsed=timings.slice(0,next).reduce((a,b)=>a+b,0);
    render();return true;
  }
  function advance(){
    if(scene===4){stopClock();state="complete";elapsed=50;remaining=0;render();return;}
    if(!changeScene(scene+1)){
      stopClock();state="paused";
      writeStatus("公式データの表示や根拠の確認に失敗したため再生を停止しました。");
    }
  }
  function tick(){
    if(state!=="playing"||panel.hidden)return;
    remaining=Math.max(0,remaining-1);
    elapsed=Math.min(50,elapsed+1);
    if(!remaining)advance();
    else{
      get("gsiFloodDemoClock").textContent=remaining+"秒";
      get("gsiFloodDemoProgress").style.width=Math.round(elapsed/50*100)+"%";
    }
  }
  function play(){
    if(!data||state==="playing"||state==="complete")return;
    state="playing";stopClock();clock=window.setInterval(tick,1000);render();
  }
  function pause(){
    if(state!=="playing")return;
    stopClock();state="paused";render();
  }
  function close(){
    if(panel.hidden)return;
    ++sequence;stopClock();state="idle";
    api?.end(restore);
    panel.hidden=true;data=null;item=null;dStatus=null;
    opener.setAttribute("aria-expanded","false");
    get("mapTourOpen").click();
    opener.focus();
  }
  async function open(){
    if(!panel.hidden)return;
    if(!api||!["begin","show","inspect","compareD","halt","end"].every(x=>typeof api[x]==="function"))
      return;
    // Close other players first, before saving our own camera/source state.
    if(!get("filterDemoPanel").hidden)get("filterDemoClose").click();
    if(!get("storyPanel").hidden)get("storyClose").click();
    if(!get("mapEvidenceReplayPanel").hidden)get("mapEvidenceReplayClose").click();
    get("mapTourClose").click();
    const token=++sequence;
    panel.hidden=false;opener.setAttribute("aria-expanded","true");
    get("gsiFloodDemoClose").focus();
    get("gsiFloodDemoContent").hidden=true;
    get("gsiFloodDemoFallback").hidden=true;
    stopClock();state="loading";scene=0;remaining=timings[0];elapsed=0;
    data=null;item=null;dStatus=null;restore=true;
    writeStatus("独立に検証されたGSI洪水指定データを確認しています。");
    try{
      const result=await api.begin();
      if(token!==sequence||panel.hidden)return;
      if(result?.state!=="ready"||result.source!=="GSI_SKHB01_FLOOD"||
         result.rawDisaster1!==1||!(result.total>0)||
         !(result.shown>0)||result.shown>result.total){
        unavailable(result?.reason);
        return;
      }
      data=result;
      get("gsiFloodDemoContent").hidden=false;
      play();
    }catch(error){
      if(token!==sequence||panel.hidden)return;
      unavailable("UNVERIFIED_SOURCE");
      console.warn("[HINANEX] GSI flood presenter unavailable",error);
    }
  }
  opener.addEventListener("click",open);
  get("gsiFloodDemoClose").addEventListener("click",close);
  get("gsiFloodDemoFallbackD").addEventListener("click",()=>{
    // Hand-off is explicit user action; never pretend this is a GSI result.
    close();
    get("mapFilterDemoOpen").click();
  });
  get("gsiFloodDemoPlay").addEventListener("click",play);
  get("gsiFloodDemoPause").addEventListener("click",()=>{pause();api?.halt();});
  get("gsiFloodDemoNext").addEventListener("click",()=>{pause();advance();});
  get("gsiFloodDemoRestart").addEventListener("click",()=>{close();void open();});
  document.addEventListener("visibilitychange",()=>{if(document.hidden){pause();api?.halt();}});
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
  function manualGesture(){
    if(panel.hidden)return;
    restore=false;pause();api?.halt();
    writeStatus("地図を手動操作したため再生を停止。閉じても今の地図視点を維持します。");
  }
  for(const name of ["pointerdown","wheel","touchstart"]){
    get("map").addEventListener(name,manualGesture,{passive:true});
  }
})();
