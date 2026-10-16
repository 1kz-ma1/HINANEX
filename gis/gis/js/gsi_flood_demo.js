(() => {
  "use strict";
  // GSI-only presenter. Never invents or joins an actual D building identity.
  const get=id=>document.getElementById(id);
  const panel=get("gsiFloodDemoPanel"),opener=get("mapGsiFloodDemoOpen"),
        narration=get("gsiDemoNarration");
  const api=window.HINANEX_GSI_FLOOD_PRESENTER;
  const timings=[7,12,12,12]; // 43 seconds plus unbounded human pin selection
  let sequence=0,state="idle",clock=null,scene=0,remaining=7,elapsed=0,
      data=null,item=null,dStatus=null,restore=true;
  // These are map-watching cues, not a duplicate source explanation.
  // GSI's published designation must never be presented as live safety data.
  const titles=[
    "洪水の公式指定と、地域の施設一覧は別の資料です。",
    "地図の紫のピンが、検証できた公式掲載地点です。",
    "紫のピンを1つ選んで、出典を確認してください。",
    "公式指定が確認できても、施設の「未判定」は残ります。"
  ];
  const explanations=[
    "まず国土地理院が公開する洪水用の指定緊急避難場所を確認します。",
    "検証済みGSIデータの範囲だけを表示中。すべての施設や現在の安全性を示すものではありません。",
    "選んだ地点の名称・住所・原データは、右側（スマホでは下部）のカードに表示します。",
    "HINANEXは、確認済みの根拠と未判定の情報を区別します。両資料の施設同一性は未照合です。"
  ];
  function stopClock(){if(clock!==null)window.clearInterval(clock);clock=null;}
  let mobileExpanded=false;
  function setMobileExpanded(expanded){
    mobileExpanded=Boolean(expanded);
    panel.setAttribute("data-mobile-expanded",String(mobileExpanded));
    const toggle=get("gsiFloodDemoExpand");
    toggle.setAttribute("aria-expanded",String(mobileExpanded));
    toggle.textContent=mobileExpanded?"地図に戻る":"詳細を見る";
    // A collapsed panel always starts with the current evidence scene, not
    // the scrollbar position from an earlier visit to the details.
    if(!mobileExpanded){
      const body=get("gsiFloodDemoContent");
      if(body)body.scrollTop=0;
    }
  }
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
    writeStatus(messages[reason] || "GSI公式データの検証結果を確認できません。再生を停止しました。");
    narration.hidden=true;
    get("gsiFloodDemoFallback").hidden=false;
    get("gsiFloodDemoFallbackReason").textContent=
      "GSI洪水指定の掲載情報は未確認です。現在の安全性は判断できません。"+
      "デモを閉じて地図を確認してください。";
  }
  function value(v){return v==null||v===""?"未確認":String(v);}
  function render(){
    if(!data)return;
    panel.setAttribute("data-scene",String(scene+1));
    narration.hidden=false;
    narration.setAttribute("data-scene",String(scene+1));
    const awaitingPin=scene===2&&!item;
    get("gsiFloodDemoPhase").textContent=String(scene+1).padStart(2,"0")+" / 04";
    get("gsiFloodDemoClock").textContent=state==="complete"?"終了":
      scene===2&&!item?"操作待ち":remaining+"秒";
    get("gsiFloodDemoTitle").textContent=scene===2&&item
      ? "選んだピンの公式情報をカードで確かめましょう。" : titles[scene];
    get("gsiFloodDemoMessage").textContent=scene===2&&item
      ? "掲載地点の名前・住所・元データを確認できます。現在の安全性や開設を示すものではありません。"
      : explanations[scene];
    get("gsiFloodDemoCount").textContent=String(data.total);
    get("gsiFloodDemoShown").textContent=String(data.shown);
    get("gsiFloodDemoEvidence").hidden=scene<2||!item;
    get("gsiFloodDemoContrast").hidden=scene!==3;
    get("gsiFloodDemoFuture").hidden=true; // archived, outside public four-scene demo
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
        ?"地域の避難施設の元座標あり "+dStatus.mapped+"件のうち洪水対応未判定 "+
          dStatus.unclassified+"件。GSI掲載地点との同一施設照合は未実施。"
        :"地域の避難施設の判定情報は未取得。0件や危険とは断定できません。";
    }
    get("gsiFloodDemoProgress").style.width=Math.round(elapsed/43*100)+"%";
    get("gsiFloodDemoPlay").disabled=state==="playing"||state==="complete"||awaitingPin;
    get("gsiFloodDemoPause").disabled=state!=="playing";
    get("gsiFloodDemoNext").disabled=state==="complete"||awaitingPin;
    get("gsiFloodDemoRestart").disabled=false;
    writeStatus((awaitingPin?"操作待ち：地図の紫色のピンを選んでください":
      state==="complete"?"再生完了":state==="paused"?"一時停止中":"再生中")+
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
      // Visitors, not the presenter, choose an actual verified GSI pin.
      // Never auto-inspect the first record or fabricate a convenient site.
      item=null;
    }else if(next===3){
      dStatus=api.compareD(); // does not assert D/GSI identity
    }else if(next===0){
      return false;
    }
    scene=next;
    remaining=timings[next];
    elapsed=timings.slice(0,next).reduce((a,b)=>a+b,0);
    if(next===2){stopClock();state="awaiting-pin";setMobileExpanded(false);}
    render();return true;
  }
  function advance(){
    if(scene===3){stopClock();state="complete";elapsed=43;remaining=0;render();return;}
    if(!changeScene(scene+1)){
      stopClock();state="paused";
      writeStatus("公式データの表示や根拠の確認に失敗したため再生を停止しました。");
    }
  }
  function tick(){
    if(state!=="playing"||panel.hidden)return;
    remaining=Math.max(0,remaining-1);
    elapsed=Math.min(43,elapsed+1);
    if(!remaining)advance();
    else{
      get("gsiFloodDemoClock").textContent=remaining+"秒";
      get("gsiFloodDemoProgress").style.width=Math.round(elapsed/43*100)+"%";
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
    panel.hidden=true;narration.hidden=true;
    get("gsiFloodDemoActions").hidden=true;
    data=null;item=null;dStatus=null;
    setMobileExpanded(false);
    opener.setAttribute("aria-expanded","false");
    // A shared-link visitor should return to the map, never be sent to
    // another presenter/menu after completing the one supported demo.
    get("map").focus?.();
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
    panel.hidden=false;narration.hidden=true;
    opener.setAttribute("aria-expanded","true");
    setMobileExpanded(false);
    get("gsiFloodDemoClose").focus();
    get("gsiFloodDemoContent").hidden=true;
    get("gsiFloodDemoActions").hidden=true;
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
      get("gsiFloodDemoActions").hidden=false;
      play();
    }catch(error){
      if(token!==sequence||panel.hidden)return;
      unavailable("UNVERIFIED_SOURCE");
      console.warn("[HINANEX] GSI flood presenter unavailable",error);
    }
  }
  opener.addEventListener("click",open);
  get("gsiFloodDemoExpand").addEventListener("click",()=>{
    if(panel.hidden)return;
    setMobileExpanded(!mobileExpanded);
  });
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
  window.addEventListener?.("hinanex:gsi-verified-pin",event=>{
    if(panel.hidden||!data||scene!==2)return;
    const proof=event.detail;
    if(proof?.state!=="inspected"||proof.disaster1Raw!==1||
       !proof.name||!proof.sourceTrace||!proof.sourceUrl)return;
    item=proof;
    remaining=timings[scene];
    state="paused";
    render();
    play(); // Resume the elapsed-time presentation only after real selection.
  });
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
    // Map inspection never pauses the presentation clock or halts the scene.
    // Only the automatic return-to-original-camera is suppressed on close.
    restore=false;
  }
  for(const name of ["pointerdown","wheel","touchstart"]){
    get("map").addEventListener(name,manualGesture,{passive:true});
  }
})();
