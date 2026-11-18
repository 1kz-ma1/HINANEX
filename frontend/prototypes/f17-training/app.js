import {F17_FIXTURE, createTraining, isF17Loopback, transition, recap} from './model.js';
const el = id => document.getElementById(id);
const make = (tag, value, cls) => {
  const item = document.createElement(tag);
  if (value !== undefined && value !== null) item.textContent = String(value);
  if (cls) item.className = cls;
  return item;
};
function listContents(container, items) {
  container.replaceChildren(...items.map(item => make('li', item)));
}
if (isF17Loopback(location.origin)) {
  el('localBlock').hidden = true;
  el('app').hidden = false;
  let current = createTraining();
  const fixture = F17_FIXTURE;
  el('scenarioTitle').textContent = fixture.title;
  el('scenarioDescription').textContent = fixture.description;
  el('scenarioSource').textContent = fixture.source;
  listContents(el('scenarioUnknowns'), fixture.unknowns);

  function detail(parent, title, value) {
    parent.append(make('dt', title), make('dd', value));
  }
  function facilityCard(item) {
    const card = make('article', null, 'facility');
    card.append(make('h3',item.name),make('p','これは訓練専用の架空施設です。','tag'));
    const facts = make('dl');
    detail(facts,'出典',item.source);
    detail(facts,'ペット条件',item.pet);
    detail(facts,'段差の情報',item.stepFree);
    const unknowns = make('dd', null, 'unknown');
    const ul = make('ul');
    listContents(ul, item.unknowns);
    unknowns.append(ul);
    facts.append(make('dt','未確認事項'),unknowns);
    card.append(facts);
    return card;
  }
  function render({focusHeading=false, focusChoice=null}={}) {
    const active = current.phase === 'ACTIVE';
    if (!recap(current)) {
      el('reviewChoice').textContent = '';
      el('reviewSource').textContent = '';
      el('reviewConditions').textContent = '';
      el('reviewUnknowns').replaceChildren();
    }
    for (let i=1; i<=3; i++) {
      el('step'+i).hidden = !active || current.step !== i;
      const progress = document.querySelector(`[data-progress="${i}"]`);
      if (active && current.step === i) progress.setAttribute('aria-current','step');
      else progress.removeAttribute('aria-current');
    }
    el('progress').hidden = !active;
    el('interrupted').hidden = active;
    el('stop').disabled = !active;
    el('status').textContent = !active ? '古い選択と振り返りは消去済みです。' :
      `完全架空の訓練：ステップ ${current.step} / 3`;
    if (!active) {
      el('stopTitle').textContent = current.phase === 'STOPPED' ? '訓練を中断しました' : '入力を検証できず停止しました';
      el('stopMessage').textContent = current.phase === 'STOPPED' ? '再開する場合は最初から始めてください。' : '無効な操作またはデータを検出しました。';
      el('facilityCards').replaceChildren();
      el('choiceButtons').replaceChildren();
      el('reviewArea').hidden = true;
      if (focusHeading) el('stopTitle').focus({preventScroll:true});
      return;
    }
    el('conditionPet').checked = current.conditions.pet;
    el('conditionStep').checked = current.conditions.stepFree;
    el('conditionSummary').textContent = '本人が確認したい条件：' +
      (current.conditions.pet ? 'ペット同行　' : '') +
      (current.conditions.stepFree ? '段差の少なさ' : '') +
      (!current.conditions.pet && !current.conditions.stepFree ? '指定なし（両施設の出典は確認）' : '') +
      '。条件から施設の安全性を判定しません。';
    if (current.step === 2) {
      el('facilityCards').replaceChildren(...fixture.facilities.map(facilityCard));
    } else el('facilityCards').replaceChildren();
    if (current.step === 3) {
      el('choiceButtons').replaceChildren(...fixture.facilities.map(item => {
        const b = make('button', item.name + 'を確認対象にする');
        b.type = 'button';
        b.dataset.choiceId = item.id;
        b.setAttribute('aria-pressed', String(current.choice === item.id));
        b.setAttribute('aria-label', item.name + 'を確認対象にする（架空訓練）');
        b.addEventListener('click', () => act({type:'CHOOSE',id:item.id},{focusChoice:item.id}));
        return b;
      }));
      el('review').disabled = !current.choice;
      const info = recap(current);
      el('reviewArea').hidden = !info;
      if (info) {
        el('reviewChoice').textContent = '本人が選んだ確認対象：' + info.name + '（安全な避難先の決定ではありません）';
        el('reviewSource').textContent = '参照した架空出典：' + info.source;
        el('reviewConditions').textContent = '気にした条件：' +
          (info.conditions.pet ? 'ペット同行　' : '') +
          (info.conditions.stepFree ? '段差の少なさ' : '') +
          (!info.conditions.pet && !info.conditions.stepFree ? '指定なし' : '');
        listContents(el('reviewUnknowns'),info.unknowns);
      } else {
        el('reviewChoice').textContent = '';
        el('reviewSource').textContent = '';
        el('reviewConditions').textContent = '';
        el('reviewUnknowns').replaceChildren();
      }
    } else {
      el('choiceButtons').replaceChildren();
      el('reviewArea').hidden = true;
      el('reviewUnknowns').replaceChildren();
    }
    if (focusChoice) {
      [...el('choiceButtons').querySelectorAll('button')].find(b=>b.dataset.choiceId===focusChoice)?.focus({preventScroll:true});
    } else if (focusHeading) {
      el('heading'+current.step).focus({preventScroll:true});
    }
  }
  function act(action,options={}) {current = transition(current,action);render(options);}
  el('next1').addEventListener('click',()=>act({type:'NEXT'},{focusHeading:true}));
  el('next2').addEventListener('click',()=>act({type:'NEXT'},{focusHeading:true}));
  el('back2').addEventListener('click',()=>act({type:'BACK'},{focusHeading:true}));
  el('back3').addEventListener('click',()=>act({type:'BACK'},{focusHeading:true}));
  el('review').addEventListener('click',()=>{
    act({type:'REVIEW'});
    if (!el('reviewArea').hidden) el('reviewHeading').focus({preventScroll:true});
  });
  el('conditionPet').addEventListener('change',e=>act({type:'SET_CONDITION',name:'pet',value:e.target.checked}));
  el('conditionStep').addEventListener('change',e=>act({type:'SET_CONDITION',name:'stepFree',value:e.target.checked}));
  el('stop').addEventListener('click',()=>act({type:'STOP'},{focusHeading:true}));
  el('reset').addEventListener('click',()=>act({type:'RESET'},{focusHeading:true}));
  el('restart').addEventListener('click',()=>act({type:'RESET'},{focusHeading:true}));
  render();
}
