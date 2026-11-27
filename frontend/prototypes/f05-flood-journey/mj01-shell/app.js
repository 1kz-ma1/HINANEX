import {createJourney,isB2Loopback,conditions} from "./model.js";
const $=id=>document.getElementById(id);
if(isB2Loopback(location.origin)) {
  const journey=createJourney();
  let restoreStartFocus=false;
  const el=(tag,text,attrs={})=>{
    const node=document.createElement(tag);
    if(text!==null)node.textContent=text;
    for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value);
    return node;
  };
  const statusLabel={CANDIDATE:"合成条件一致（CANDIDATE）",UNKNOWN:"未確認（UNKNOWN）",EXCLUDED:"合成条件不一致（EXCLUDED）"};
  const labels={IDLE:"訓練開始",J02:"J02 条件を選ぶ",J03:"J03 根拠と未確認事項",J04:"J04 2施設を比較",J05:"J05 本人の確認対象",LOAD_ERROR:"取得失敗（模擬）"};
  function render(focusId="heading"){
    const v=journey.view(), content=$("content"), actions=$("actions");
    content.replaceChildren();actions.replaceChildren();$("steps").replaceChildren();
    $("heading").textContent=labels[v.step];
    $("status").textContent=v.step==="J04" ? "比較対象 "+v.selected.length+"/2件" :
      v.step==="J05" ? (v.complete?"本人確認対象："+v.choice.name+"。模擬ジャーニー完了。":"比較した2件から本人が選択してください。") :
      v.step==="LOAD_ERROR"?"模擬データ取得失敗。以前の結果は破棄しました。":"";
    for(const key of ["J02","J03","J04","J05"]){
      const item=el("li",labels[key],key===v.step?{"aria-current":"step"}:{});
      $("steps").append(item);
    }
    const button=(parent,id,label,action,{disabled=false,pressed,keep=false,primary=false}={})=>{
      const b=el("button",label,{id,type:"button"});
      b.disabled=disabled;
      if(pressed!==undefined)b.setAttribute("aria-pressed",String(pressed));
      if(primary)b.className="primary";
      b.addEventListener("click",()=>{
        if(journey.dispatch(action,v.revision))render(keep?id:"heading");
      });
      parent.append(b);return b;
    };
    const card=(record)=>{
      const a=el("article",null,{"data-record":record.id});a.append(el("h3",record.name));
      const dl=el("dl",null);
      for(const [k,val] of [["合成区分",statusLabel[record.status]],["根拠",record.reason],["元値（合成）",record.rawValue??"合成データに値なし"],["出典（固定合成）",record.sourceId+" / "+record.sourceTrace],["現在の開設","未確認"],["安全性","未認定"]]){
        dl.append(el("dt",k),el("dd",val));
      }
      dl.append(el("dt","未確認事項"));
      const dd=el("dd",null),ul=el("ul",null);for(const u of record.unknowns)ul.append(el("li",u));dd.append(ul);dl.append(dd);a.append(dl);return a;
    };
    if(v.step==="IDLE"||v.step==="LOAD_ERROR"){
      content.append(el("p","架空の条件と施設の根拠を確認し、本人が確認対象を選ぶ練習です。"));
      button(actions,"start","合成訓練を開始",{type:"START"},{primary:true});
      if(v.step==="LOAD_ERROR")button(actions,"end","終了",{type:"END"});
    }else if(v.step==="J02"){
      content.append(el("p","固定表示例を1つ明示選択してください。個人情報の入力はありません。"));
      const group=el("div",null,{role:"group","aria-label":"架空の条件",class:"controls"});
      for(const [key,label] of Object.entries(conditions))button(group,"condition-"+key,label,{type:"CONDITION",key},{pressed:v.condition===key,keep:true});
      content.append(group);
      button(actions,"show","根拠を確認",{type:"SHOW"},{disabled:!v.condition,primary:true});
    }else{
      content.append(el("p","選択した架空条件："+conditions[v.condition]));
      const grid=el("div",null,{class:"cards"});
      for(const record of v.step==="J05"?v.selected:v.rows){
        const a=card(record);
        if(v.step==="J04"){
          const selected=v.selected.some(x=>x.id===record.id);
          a.append(el("p",selected?"比較対象に選択済み":"比較対象に未選択"));
          button(a,"toggle-"+record.id,record.name+"を比較対象にする",{type:"TOGGLE",id:record.id},{pressed:selected,disabled:!selected&&v.selected.length===2,keep:true});
        }
        if(v.step==="J05")button(a,"choose-"+record.id,record.name+"を確認対象にする",{type:"CHOOSE",id:record.id},{pressed:v.choice?.id===record.id,keep:true});
        grid.append(a);
      }
      content.append(grid);
      if(v.step==="J03")button(actions,"continue","比較対象を選ぶ",{type:"CONTINUE"},{primary:true});
      if(v.step==="J04")button(actions,"compare","2施設の比較へ",{type:"COMPARE"},{disabled:v.selected.length!==2,primary:true});
      if(v.step==="J05")button(actions,"back","比較対象を選び直す",{type:"BACK"});
      button(actions,"change","条件を変更",{type:"CHANGE"});
    }
    if(["J02","J03","J04","J05"].includes(v.step)){
      button(actions,"fail","取得失敗を模擬",{type:"FAIL"});
      button(actions,"end","訓練を終了",{type:"END"});
    }
    if(focusId)($(focusId)??$("heading")).focus({preventScroll:focusId!=="heading"});
  }
  function reset(){
    const active=document.activeElement;
    if(!journey.dispatch({type:"END"},journey.view().revision))return;
    restoreStartFocus=$("content").contains(active)||$("actions").contains(active);
    render(null);
  }
  function restoreFocus(){
    if(document.hidden||!restoreStartFocus)return;
    restoreStartFocus=false;
    const active=document.activeElement;
    if(!active||active===document.body||!active.isConnected)$("start").focus({preventScroll:true});
  }
  window.addEventListener("pagehide",reset);
  window.addEventListener("pageshow",e=>{
    if(!e.persisted)return;
    reset();
    restoreFocus();
  });
  document.addEventListener("visibilitychange",()=>{
    if(document.hidden)reset();
    else restoreFocus();
  });
  render(null);$("onlyLocal").hidden=true;$("prototype").hidden=false;
}
