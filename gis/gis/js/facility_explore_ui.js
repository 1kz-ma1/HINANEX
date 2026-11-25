(function () {
"use strict";
// User choice is a temporary inspection target, not an evacuation recommendation.
const get = id => document.getElementById(id);
const engine = window.HINANEX_FACILITY_EXPLORE;
const panel = get("facilityExplorePanel"), opener = get("mapFacilityExploreOpen");
const query = get("facilityExploreQuery"), filter = get("facilityExploreFilter");
const list = get("facilityExploreList"), comparison = get("facilityExploreComparison");
const choice = get("facilityExploreChoice"), count = get("facilityExploreCount");
const status = get("facilityExploreStatus"), pageLabel = get("facilityExplorePage");
const prev = get("facilityExplorePrev"), next = get("facilityExploreNext");
let session = null, page = 0;
function node(tag, value, className) {
  const element = document.createElement(tag);
  if (value !== null && value !== undefined) element.textContent = String(value);
  if (className) element.className = className;
  return element;
}
function field(dl, name, value) {
  dl.append(node("dt",name),node("dd",value == null || value === "" ? "元データで未確認" : value));
}
function createCard(record, letter) {
  const item = node("article",null,"edogawa-compare-card facility-explore-card");
  item.append(node("h3",letter+"："+record.name));
  const dl = node("dl");
  field(dl,"住所",record.address);
  field(dl,"施設区分",record.facilityType);
  field(dl,"洪水対応分類",{
    CANDIDATE:"D分類：参考候補（安全性未確認）",
    EXCLUDED:"D分類：対象外（危険を証明しません）",
    UNKNOWN:"未判定（安全・危険のどちらでもありません）"
  }[record.status]);
  item.append(dl);
  const details=node("details",null,"edogawa-compare-card-extra");
  details.append(node("summary","判定理由・原本の詳細"));
  const extra=node("dl");
  field(extra,"判定理由",record.reason || "未確認");
  field(extra,"公式災害列（原文）",record.hazardScopeRaw);
  field(extra,"公式記号（原文）",record.officialStatusRaw);
  field(extra,"原本の行",record.sourceTrace);
  field(extra,"位置情報",record.hasCoordinates ?
    "元データに座標あり（位置承認ではありません）" : "座標未確認。地図表示しません");
  field(extra,"公式資料の更新時点","この画面では検証できません");
  details.append(extra);
  if (record.sourceUrl) {
    const link=node("a","原本出典を開く ↗");
    link.href=record.sourceUrl;link.target="_blank";link.rel="noopener noreferrer";
    details.append(link);
  }
  item.append(details);
  return item;
}
function renderComparison() {
  comparison.replaceChildren();choice.replaceChildren();
  if (session?.state !== "READY") return;
  const picked = session.selected();
  if (picked.length !== 2) {
    comparison.append(node("p","異なる2施設を選ぶと、住所・分類・根拠・不明点を比較できます。"));
    return;
  }
  const columns=node("div",null,"edogawa-compare-result facility-explore-columns");
  columns.append(createCard(picked[0],"A"),createCard(picked[1],"B"));
  comparison.append(columns);
  choice.append(node("p","次に詳しく確認する施設を本人が選べます。安全な避難先の認定ではありません。"));
  const actions=node("div",null,"facility-explore-actions");
  for(const record of picked) {
    const button=node("button",record.name+"を確認対象にする");
    button.type="button";
    button.setAttribute("aria-pressed",String(session.choice()?.id===record.id));
    button.addEventListener("click",()=>{
      if(session.choose(record.id).ok)renderComparison();
    });
    actions.append(button);
  }
  choice.append(actions);
  const selected=session.choice();
  if(selected) choice.append(node("p","本人の確認対象："+selected.name+
    "。一時的な選択であり、安全性・開設は未確認です。","facility-explore-chosen"));
}
function render() {
  list.replaceChildren();count.textContent="";
  if(session?.state !== "READY") {
    status.textContent=session?.message || "地域の施設情報を読み込んでいます。";
    query.disabled=true;filter.disabled=true;prev.disabled=true;next.disabled=true;
    pageLabel.textContent="—";renderComparison();return;
  }
  query.disabled=false;filter.disabled=false;
  const result=session.page(page);page=result.page;
  const n=session.counts;
  count.textContent="取得 "+session.total+"件｜参考候補 "+n.CANDIDATE+
    "件｜対象外 "+n.EXCLUDED+"件｜未判定 "+n.UNKNOWN+"件";
  status.textContent=session.regionName+"／洪水｜検索一致 "+result.matched+
    "件。Dの既存分類を表示しています。施設の安全性・開設状況は未認定です。";
  prev.disabled=page<=0;next.disabled=page>=result.pages-1;
  pageLabel.textContent=(page+1)+" / "+result.pages;
  if(result.state==="NO_DATA")list.append(node("p","元データは0件です。未評価・未取得とは区別します。"));
  else if(result.state==="NO_MATCH")list.append(node("p","検索一致なし。施設が存在しないという意味ではありません。"));
  const chosenIds=new Set(session.selected().map(row=>row.id));
  for(const record of result.records) {
    const line=node("div",null,"facility-explore-item");
    const desc=node("div",null,"facility-explore-item-description");
    desc.append(node("strong",record.name));
    desc.append(node("small",(record.address||"住所未確認")+"｜"+(
      record.status==="UNKNOWN"?"未判定":record.status==="CANDIDATE"?
      "D分類：参考候補":"D分類：対象外")));
    line.append(desc);
    const button=node("button",chosenIds.has(record.id)?"選択を外す":"比較に追加");
    button.type="button";button.disabled=chosenIds.size>=2&&!chosenIds.has(record.id);
    button.setAttribute("aria-pressed",String(chosenIds.has(record.id)));
    button.addEventListener("click",()=>{if(session.toggle(record.id).ok)render();});
    line.append(button);list.append(line);
  }
  renderComparison();
}
function setSummary(summary) {
  session=engine?.createSession(summary)||null;
  query.value="";filter.value="all";page=0;render();
}
function close() {panel.hidden=true;opener.setAttribute("aria-expanded","false");}
function open() {
  if(!panel.hidden)return;
  if(!get("referenceComparePanel")?.hidden)get("referenceCompareClose")?.click();
  if(!get("edogawaComparePanel")?.hidden)get("edogawaCompareClose")?.click();
  // A left-open toolbar dropdown is another overlay over the research panel.
  document.querySelectorAll(".map-toolbar .map-tool[open]").forEach(menu => { menu.open = false; });
  panel.hidden=false;opener.setAttribute("aria-expanded","true");
  render();get("facilityExploreClose").focus();
}
opener.addEventListener("click",open);
get("facilityExploreClose").addEventListener("click",close);
query.addEventListener("input",()=>{if(session?.state==="READY"){session.setCriteria(query.value,filter.value);page=0;render();}});
filter.addEventListener("change",()=>{if(session?.state==="READY"){session.setCriteria(query.value,filter.value);page=0;render();}});
prev.addEventListener("click",()=>{page--;render();});
next.addEventListener("click",()=>{page++;render();});
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&!panel.hidden)close();});
window.HINANEX_FACILITY_EXPLORE_UI=Object.freeze({setSummary,close});
setSummary(window.HINANEX_FACILITY_EXPLORE_GET_SUMMARY?.()||null);
})();