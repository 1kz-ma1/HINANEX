(() => {
  "use strict";
  // Evidence-only audience demo. Unlike GSI source markers, these records
  // come only from the exact Edogawa D RegionExport shelter_location dataset.
  // No safety ranking, GSI/D auto-join, geocoding, or live shelter status.
  const get = id => document.getElementById(id);
  const panel = get("edogawaComparePanel");
  const banner = get("edogawaCompareBanner");
  const openButton = get("mapEdogawaCompareOpen");
  const first = get("edogawaCompareFirst"), second = get("edogawaCompareSecond");
  const api = window.HINANEX_EDOGAWA_FACILITY_COMPARE;
  let sequence = 0, session = null, step = 0;

  const steps = [
    ["01 / 03", "地図にある施設だけで、避難先は決められる？",
      "江戸川区の取得レコードから、2施設の情報を見比べます。"],
    ["02 / 03", "比べたい2施設を選びましょう。",
      "地図の背景ピンは控えめに表示し、選んだA・Bだけを強調します。"],
    ["03 / 03", "比較できたことと、判断できないこと。",
      "住所や施設区分は比較できても、洪水時の利用可否までは判定できません。"]
  ];
  // A repeatable educational example from existing 13123 source records:
  // prefer two different recorded facility types, never flood suitability,
  // opening, distance, capacity or a presumed recommendation. No randomness.
  function chooseDemoPair(records) {
    if (!Array.isArray(records) || records.length < 2) return null;
    const eligible = records.filter(r => r && r.key !== "" && r.key != null);
    if (eligible.length < 2) return null;
    const firstRecord = eligible.find(r => typeof r.facilityType === "string" &&
      r.facilityType.trim() !== "") || eligible[0];
    const alternate = eligible.find(r => r.key !== firstRecord.key &&
      typeof r.facilityType === "string" && r.facilityType.trim() !== "" &&
      r.facilityType !== firstRecord.facilityType);
    const secondRecord = alternate || eligible.find(r => r.key !== firstRecord.key);
    return secondRecord ? [firstRecord.key, secondRecord.key] : null;
  }
  function resetOptions(select, records, label) {
    select.replaceChildren();
    const placeholder = document.createElement("option");
    placeholder.value = ""; placeholder.textContent = label;
    select.append(placeholder);
    for (const record of records) {
      const option = document.createElement("option");
      option.value = record.key;
      option.textContent = record.name + (record.address ? "｜" + record.address : "");
      select.append(option);
    }
  }
  function updateStep() {
    const info = steps[Math.min(2,step)], result = step === 2;
    get("edogawaComparePhase").textContent = info[0];
    get("edogawaCompareTitle").textContent = info[1];
    get("edogawaCompareMessage").textContent = info[2];
    get("edogawaCompareSelectArea").hidden = !session || result;
    get("edogawaComparePickControls").hidden = !session || step !== 1;
    get("edogawaCompareViewArea").hidden = !result;
    get("edogawaCompareAdvance").hidden = !session || step !== 0;
    get("edogawaComparePrompt").hidden = !session || step !== 0;
    panel.dataset.stage = result ? "result" : step === 1 ? "pick" : "intro";
  }
  function buildField(list, label, value) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = label; dd.textContent = value == null || value === "" ? "元データで未確認" : String(value);
    list.append(dt,dd);
  }
  function buildSite(record, letter) {
    const card = document.createElement("article");
    card.className = "edogawa-compare-card";
    card.dataset.marker = letter;
    const h = document.createElement("h3");
    h.textContent = letter + "：" + record.name;
    card.append(h);
    const dl = document.createElement("dl");
    for (const [k,v] of [
      ["住所（取得データ）",record.address],
      ["施設区分（取得データ）",record.facilityType]
    ]) buildField(dl,k,v);
    card.append(dl);
    const status = document.createElement("p");
    status.className="edogawa-compare-flood";
    const title = document.createElement("strong");
    title.textContent = "洪水時の分類：";
    status.append(title,document.createTextNode(record.floodStatus));
    card.append(status);
    const detail=document.createElement("details");
    detail.className="edogawa-compare-card-extra";
    const summary=document.createElement("summary");
    summary.textContent="その他の元データ・判定理由";
    detail.append(summary);
    const extra=document.createElement("dl");
    for(const [k,v] of [
      ["行政区域（D原値）",record.administrativeArea],
      ["収容人数（D原値）",record.capacity],
      ["位置情報","元レコードの座標あり（境界内の正確性は別途確認が必要）"],
      ["判定理由（D記録）",record.reason],
      ["元データID",record.id]
    ])buildField(extra,k,v);
    detail.append(extra);
    if(record.sourceUrl && /^https:\/\//.test(record.sourceUrl)){
      const a=document.createElement("a");
      a.href=record.sourceUrl;a.target="_blank";a.rel="noopener noreferrer";
      a.textContent="記録された出典 ↗";detail.append(a);
    }
    card.append(detail);
    return card;
  }
  function selection() {
    if(!session)return;
    const a=first.value,b=second.value;
    const ok=Boolean(a&&b&&a!==b);
    get("edogawaCompareRun").disabled=!ok;
    get("edogawaCompareMapFocus").disabled=!ok;
    get("edogawaCompareChoiceStatus").textContent = !a||!b
      ? "江戸川区として収録された施設を2件選択してください。"
      : !ok ? "異なる2件を選んでください。" : "2件選択済み。情報を比較できます。";
    if(step===2){
      step=1;get("edogawaCompareResult").replaceChildren();updateStep();
      api?.clear?.();
    }
  }
  function finish(){
    ++sequence;
    if(session)api?.end?.();
    session=null;step=0;panel.hidden=true;banner.hidden=true;
    openButton?.setAttribute("aria-expanded","false");
    get("edogawaCompareResult").replaceChildren();
    get("edogawaComparePairBasis").hidden=true;
    panel.dataset.stage="intro";
  }
  async function open(){
    if(!panel.hidden)return;
    if(!api||typeof api.begin!=="function"||typeof api.compare!=="function")return;
    const token=++sequence;
    panel.hidden=false;banner.hidden=false;session=null;step=0;
    get("edogawaCompareAutoPick").disabled=true;
    get("edogawaCompareAutoPickFromPicker").disabled=true;
    get("edogawaComparePairBasis").hidden=true;
    openButton?.setAttribute("aria-expanded","true");
    get("edogawaCompareLoading").hidden=false;
    get("edogawaCompareLoading").textContent="江戸川区の取得済み施設データを確認しています…";
    updateStep();
    try{
      const result=await api.begin();
      if(token!==sequence||panel.hidden)return;
      if(result?.state!=="ready"||!Array.isArray(result.records)||result.records.length<2){
        get("edogawaCompareLoading").textContent=
          "江戸川区の比較可能な位置付きレコードを確認できません。未取得は施設がないことを意味しません。";
        return;
      }
      session=result;get("edogawaCompareLoading").hidden=true;
      const canAuto=Boolean(chooseDemoPair(result.records));
      get("edogawaCompareAutoPick").disabled=!canAuto;
      get("edogawaCompareAutoPickFromPicker").disabled=!canAuto;
      resetOptions(first,result.records,"施設Aを選ぶ");
      resetOptions(second,result.records,"施設Bを選ぶ");
      get("edogawaCompareCount").textContent =
        "取得レコード "+result.total+"件／元座標あり "+result.records.length+
        "件／洪水分類未判定 "+result.unknown+"件（元座標ありの範囲）";
      updateStep();selection();
    }catch(err){
      if(token===sequence)get("edogawaCompareLoading").textContent=
        "施設データを読み込めませんでした。安全な施設がないことを意味しません。";
    }
  }
  get("edogawaCompareAdvance").addEventListener("click",()=>{if(session){step=1;updateStep();first.focus();}});
  first.addEventListener("change",selection);second.addEventListener("change",selection);
  function runComparison(autoSelected=false){
    if(!session||!first.value||!second.value||first.value===second.value)return;
    const compared=api.compare(first.value,second.value);
    if(compared?.state!=="compared")return;
    const result=get("edogawaCompareResult");result.replaceChildren();
    result.append(buildSite(compared.first,"A"),buildSite(compared.second,"B"));
    const bothUnknown=[compared.first,compared.second].every(r=>r.floodStatus.startsWith("UNKNOWN"));
    get("edogawaCompareTakeawayTitle").textContent=bothUnknown
      ? "結論：2施設とも洪水時の利用可否は未判定"
      : "結論：記録の比較と、安全性の判定は別";
    get("edogawaCompareTakeawayText").textContent=bothUnknown
      ? "住所・施設区分は確認できます。しかし「未判定」は安全・危険のどちらでもありません。現時点ではこの比較から避難先を推奨できません。"
      : "記録された分類が異なっても、安全・開設・移動可能性を保証しません。出典の確認と追加の検証が必要です。";
    get("edogawaComparePairBasis").hidden=!autoSelected;
    step=2;updateStep();panel.scrollTop=0;
  }
  function autoPick() {
    if(!session)return;
    const keys=chooseDemoPair(session.records);
    if(!keys)return;
    first.value=String(keys[0]);second.value=String(keys[1]);
    selection();
    runComparison(true);
  }
  get("edogawaCompareAutoPick").addEventListener("click",autoPick);
  get("edogawaCompareAutoPickFromPicker").addEventListener("click",autoPick);
  get("edogawaCompareRun").addEventListener("click",()=>runComparison(false));
  get("edogawaCompareMapFocus").addEventListener("click",()=>{
    if(!session||!first.value||!second.value||first.value===second.value)return;
    api.focus(first.value,second.value);
  });
  get("edogawaCompareResultFocus").addEventListener("click",()=>{
    if(session&&first.value&&second.value&&first.value!==second.value)
      api.focus(first.value,second.value);
  });
  get("edogawaCompareAgain").addEventListener("click",()=>{
    if(!session)return;
    api?.clear?.();
    step=1;updateStep();panel.scrollTop=0;first.focus();
  });
  get("edogawaCompareClose").addEventListener("click",finish);
  openButton?.addEventListener("click",open);
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&!panel.hidden){event.preventDefault();finish();}
  });
  window.HINANEX_EDOGAWA_COMPARE_UI=Object.freeze({open,close:finish});
})();