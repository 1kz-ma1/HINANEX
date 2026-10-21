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
    ["01 / 03", "江戸川区の施設を、実データから確認します。",
      "位置が分かることと、洪水時に安全かどうかは別です。"],
    ["02 / 03", "江戸川区の施設を2件選んでください。",
      "施設名や住所を比較します。元データにない情報は補いません。"],
    ["03 / 03", "2件の取得済み施設データを比較。",
      "洪水時の適合性・現在の開設・移動経路は未判定です。"]
  ];
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
    const info = steps[Math.min(2,step)];
    get("edogawaComparePhase").textContent = info[0];
    get("edogawaCompareTitle").textContent = info[1];
    get("edogawaCompareMessage").textContent = info[2];
    get("edogawaCompareSelectArea").hidden = !session;
    get("edogawaCompareViewArea").hidden = step!==2;
    get("edogawaCompareAdvance").hidden = !session || step!==0;
    get("edogawaCompareAdvance").textContent = "施設を選ぶ →";
  }
  function buildField(list, label, value) {
    const dt = document.createElement("dt"), dd = document.createElement("dd");
    dt.textContent = label; dd.textContent = value == null || value === "" ? "元データで未確認" : String(value);
    list.append(dt,dd);
  }
  function buildSite(record, letter) {
    const card = document.createElement("article");
    card.className = "edogawa-compare-card";
    const h = document.createElement("h3");h.textContent=letter+"： "+record.name;card.append(h);
    const dl = document.createElement("dl");
    for (const [k,v] of [
      ["住所（D原値）",record.address],
      ["施設区分（D原値）",record.facilityType],
      ["行政区域（D原値）",record.administrativeArea],
      ["収容人数（D原値）",record.capacity],
      ["座標の状態", "RegionExportの元レコードに座標あり（境界内の正確性は別途検証）"],
      ["洪水時の分類",record.floodStatus],
      ["判定理由（D記録）",record.reason],
      ["元データID",record.id]
    ]) buildField(dl,k,v);
    card.append(dl);
    if(record.sourceUrl && /^https:\/\//.test(record.sourceUrl)){
      const a = document.createElement("a");
      a.href=record.sourceUrl;
      a.target="_blank";a.rel="noopener noreferrer";
      a.textContent="記録された出典を確認 ↗";card.append(a);
    }
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
    }
  }
  function finish(){
    ++sequence;
    if(session)api?.end?.();
    session=null;step=0;panel.hidden=true;banner.hidden=true;
    openButton?.setAttribute("aria-expanded","false");
    get("edogawaCompareResult").replaceChildren();
  }
  async function open(){
    if(!panel.hidden)return;
    if(!api||typeof api.begin!=="function"||typeof api.compare!=="function")return;
    const token=++sequence;
    panel.hidden=false;banner.hidden=false;session=null;step=0;
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
  get("edogawaCompareRun").addEventListener("click",()=>{
    if(!session||!first.value||!second.value||first.value===second.value)return;
    const compared=api.compare(first.value,second.value);
    if(compared?.state!=="compared")return;
    const result=get("edogawaCompareResult");result.replaceChildren();
    result.append(buildSite(compared.first,"A"),buildSite(compared.second,"B"));
    step=2;updateStep();
  });
  get("edogawaCompareMapFocus").addEventListener("click",()=>{
    if(!session||!first.value||!second.value||first.value===second.value)return;
    api.focus(first.value,second.value);
  });
  get("edogawaCompareClose").addEventListener("click",finish);
  openButton?.addEventListener("click",open);
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"&&!panel.hidden){event.preventDefault();finish();}
  });
  window.HINANEX_EDOGAWA_COMPARE_UI=Object.freeze({open,close:finish});
})();