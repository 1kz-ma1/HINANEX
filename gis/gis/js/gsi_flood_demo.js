(() => {
  "use strict";
  // GSI-only presenter. Never invents or joins an actual D building identity.
  const get=id=>document.getElementById(id);
  const panel=get("gsiFloodDemoPanel"),opener=get("mapGsiFloodDemoOpen"),
        narration=get("gsiDemoNarration");
  const mobileToggle=get("gsiDemoMobileToggle");
  const mobileClose=get("gsiDemoMobileClose");
  const isMobile=()=>Boolean(window.matchMedia?.("(max-width: 780px)")?.matches);
  function updateMobileControls(){
    mobileToggle.hidden=state==="unavailable";
    // Pin-navigation is explicit. While awaiting a verified pin, reuse
    // the existing top play button rather than adding a fifth control.
    mobileToggle.disabled=state==="loading";
    const label=state==="playing"?"一時停止":
      state==="complete"?"最初から":state==="awaiting-pin"?"紫ピンへ":
      state==="loading"?"確認中":"再生";
    mobileToggle.textContent=label;
    mobileToggle.setAttribute("aria-label",state==="awaiting-pin"
      ? "必要な場合、周辺の検証済みGSI掲載地点へ移動します。千葉県側を含むことがあります"
      : label+"：GSI洪水指定デモ");
    mobileToggle.setAttribute("title",state==="awaiting-pin"
      ? "地図が移動するのはこの操作を選んだときだけです。千葉県側のGSI掲載地点を含む場合があります"
      : label+"：GSI洪水指定デモ");
    const next=get("gsiDemoNext");
    next.disabled=state==="loading"||state==="unavailable"||state==="awaiting-pin"||state==="complete";
    next.hidden=state==="loading"||state==="unavailable";
    const details=get("gsiDemoDetailsToggle");
    details.hidden=state==="loading"||state==="unavailable";
  }
  const api=window.HINANEX_GSI_FLOOD_PRESENTER;
  const timings=[7,12,12,12]; // 43 seconds plus unbounded human pin selection
  let sequence=0,state="idle",clock=null,scene=0,remaining=7,elapsed=0,
      data=null,item=null,dStatus=null,restore=true;
  // These are map-watching cues, not a duplicate source explanation.
  // GSI's published designation must never be presented as live safety data.
  // Official policy is presented as reference guidance, NOT as a D/GSI
  // facility classification or live instruction. The policies apply to the
  // specified large-scale flood scenario, not every storm or every person.
  const officialSources=[
    {name:"江戸川区：大規模水害時の広域避難（公式）",
      url:"https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/koikihinan.html"},
    {name:"江戸川区：待避施設の位置付け（公式）",
      url:"https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/ikinaihinan.html"},
    {name:"国土地理院：指定緊急避難場所の資料",
      url:"https://www.gsi.go.jp/bousaichiri/hinanbasho.html"},
    {name:"江戸川区：水害時の避難判断フロー（公式）",
      url:"https://www.city.edogawa.tokyo.jp/e007/bosaianzen/bosai/kanrenmap/hazardmap/suigaihinan.html"}
  ];
  const titles=[
    "近くに学校があっても、最初の避難先とは限りません。",
    "区の「待避施設」と、紫のGSI洪水指定ピンは別情報です。",
    "紫のピンを選んで、掲載場所と出典を確かめよう。",
    "ピンだけで避難先を決めない。「未判定」を残します。"
  ];
  const explanations=[
    "江戸川区は大規模水害時に早期の広域避難を案内。区の待避施設は、避難する時間がないなどやむを得ない場合の緊急避難先です。",
    "紫は周辺の検証済みGSI掲載地点から最大5件。千葉県側を含む場合があり、江戸川区内の施設数や推奨先を示しません。",
    "紫のピンを選び、住所・出典の元データを確認してください。掲載だけでは現在の開設・混雑・移動の安全を確認できません。",
    "江戸川区の避難方針、緊急時の待避施設、GSI洪水指定、Dの洪水未判定は別々の情報。開設・混雑・経路の現況はこのデモでは未確認です。"
  ];
  function showOfficialSource(index){
    const a=get("gsiDemoSceneSource"),detail=get("gsiDemoFullSource"),
          source=officialSources[index];
    // The top link is intentionally short to keep the map unobstructed.
    // Preserve the complete source title for accessible link text/tooltip
    // and in the opt-in details; never change the exact official URL.
    a.href=source.url;
    a.textContent="公式資料 ↗";
    a.setAttribute("aria-label",source.name+"の出典を開く（新しいタブ）");
    a.setAttribute("title",source.name);
    detail.href=source.url;
    detail.textContent=source.name+" ↗";
  }
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
  // The big evidence card is optional on desktop. The official source link,
  // scene narration, playback and close controls remain in the top strip.
  function setDesktopDetailsOpen(open){
    const expanded=Boolean(open)&&!isMobile()&&!panel.hidden;
    panel.setAttribute("data-details-open",String(expanded));
    const button=get("gsiDemoDetailsToggle");
    button.setAttribute("aria-expanded",String(expanded));
    button.textContent=expanded?"根拠を閉じる":"根拠を見る";
    if(!expanded)get("gsiFloodDemoContent").scrollTop=0;
  }
  function writeStatus(s){get("gsiFloodDemoStatus").textContent=s;}
  function unavailable(reason) {
    stopClock();state="unavailable";setDesktopDetailsOpen(false); // Fail closed on all screen sizes.
    // A missing/invalid official catalog is never interpreted as "no
    // designated sites". Offer the already working D-only presentation,
    // clearly labeled as a different source and a different capability.
    const messages={
      NO_REGION_SOURCE_POINT:"選択地域の元座標を確認できません。公式掲載地点を推測せず停止しました。",
      ORIGIN_OUTSIDE_SOURCE_TILE:"この地点を含むGSIタイルは検証・配信されていません。別地点の結果を流用しません。",
      UNVERIFIED_SOURCE:"この地点のGSI検証済みデータを読み込めません。配信・検証状態の確認が必要です。"
    };
    writeStatus(messages[reason] || "GSI公式データの検証結果を確認できません。再生を停止しました。");
    narration.hidden=false; // Mobile shows a truthful fail-closed message in the ONLY visible demo surface.
    narration.setAttribute("data-source-state","unavailable");
    get("gsiFloodDemoPhase").textContent="確認不可";
    get("gsiFloodDemoTitle").textContent="公式データを確認できません";
    get("gsiFloodDemoMessage").textContent=(messages[reason]||
      "GSI公式データの検証結果を確認できません。")+
      " 未確認は指定地点がないことや安全であることを意味しません。区の避難方針は公式資料を参照してください。";
    showOfficialSource(0);
    updateMobileControls();
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
    narration.setAttribute("data-source-state","verified");
    const awaitingPin=scene===2&&!item;
    get("gsiFloodDemoPhase").textContent=String(scene+1).padStart(2,"0")+" / 04";
    get("gsiFloodDemoClock").textContent=state==="complete"?"終了":
      scene===2&&!item?"操作待ち":remaining+"秒";
    get("gsiFloodDemoTitle").textContent=scene===2&&item
      ? "選んだGSI掲載地点の公式情報を地図で確認しました。" : titles[scene];
    get("gsiFloodDemoMessage").textContent=scene===2&&item
      ? "地図のピンから原文を確認できます。区の待避施設との同一性、現在の開設・混雑・安全は未確認です。"
      : explanations[scene];
    showOfficialSource(scene);
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
    updateMobileControls();
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
    setDesktopDetailsOpen(false); // Always return map pixels to the scene.
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
    setDesktopDetailsOpen(false);
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
    if(!api||!["begin","show","focusPins","inspect","compareD","halt","end"].every(x=>typeof api[x]==="function"))
      return;
    // Close other players first, before saving our own camera/source state.
    if(!get("filterDemoPanel").hidden)get("filterDemoClose").click();
    if(!get("storyPanel").hidden)get("storyClose").click();
    if(!get("mapEvidenceReplayPanel").hidden)get("mapEvidenceReplayClose").click();
    get("mapTourClose").click();
    const token=++sequence;
    panel.hidden=false;narration.hidden=false;
    setDesktopDetailsOpen(false);
    narration.setAttribute("data-source-state","loading");
    get("gsiFloodDemoPhase").textContent="確認中";
    get("gsiFloodDemoTitle").textContent="検証済みの公式資料を確認しています";
    get("gsiFloodDemoMessage").textContent="出典を確認できるまで、洪水指定のピンは表示しません。大規模水害時の避難は江戸川区の公式方針も確認してください。";
    showOfficialSource(0);
    opener.setAttribute("aria-expanded","true");
    setMobileExpanded(false);
    (isMobile()?mobileClose:get("gsiFloodDemoClose")).focus();
    get("gsiFloodDemoContent").hidden=true;
    get("gsiFloodDemoActions").hidden=true;
    get("gsiFloodDemoFallback").hidden=true;
    stopClock();state="loading";scene=0;remaining=timings[0];elapsed=0;
    updateMobileControls();
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
  mobileClose.addEventListener("click",close);
  get("gsiDemoNext").addEventListener("click",()=>{
    if(panel.hidden||!data||["loading","unavailable","awaiting-pin","complete"].includes(state))return;
    pause();advance();
  });
  get("gsiDemoDetailsToggle").addEventListener("click",()=>{
    if(panel.hidden||!data||isMobile())return;
    setDesktopDetailsOpen(panel.getAttribute("data-details-open")!=="true");
  });
  mobileToggle.addEventListener("click",()=>{
    if(panel.hidden||!data)return;
    if(state==="complete"){close();void open();}
    else if(state==="playing"){pause();api?.halt();}
    else if(state==="paused"){play();}
    else if(state==="awaiting-pin"){
      // Only a real user click pans to the current verified candidates.
      // This is NOT a facility recommendation or an automatic scene transition.
      api?.focusPins?.();
    }
    // Even after explicit focusing, the actual verified pin must be selected.
  });
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
      // The desktop panel is CSS-hidden on mobile; do not trap focus there.
      if(isMobile())return;
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
