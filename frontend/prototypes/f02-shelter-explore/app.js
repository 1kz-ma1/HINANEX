(function () {
  'use strict';
  const model = window.F02Model;
  const fixture = window.F02Fixtures;
  const $ = (id) => document.getElementById(id);
  const elements = {
    region: $('region'), query: $('query'), scenario: $('scenario'),
    list: $('facilityList'), resultCount: $('resultCount'), resultTitle: $('resultTitle'),
    stats: $('stats'), message: $('statusMessage'), detail: $('detailBody'), heading: $('detailHeading'),
  };
  const ui = {selectedId:null};
  function create(tag, className, text) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined) el.textContent = String(text);
    return el;
  }
  function clean(el) { el.replaceChildren(); }
  function node(parent, tag, className, text) { const child=create(tag,className,text);parent.append(child);return child; }
  function chip(parent, text, kind='') { return node(parent,'span',`chip ${kind}`,text); }
  function keyValue(parent, key, value, wide=false) {
    const wrap=node(parent,'div',`info-line${wide?' wide':''}`);
    node(wrap,'span','info-key',key);
    node(wrap,'div',`info-value${model.isKnown(value)?'':' unverified'}`,model.displayRaw(value));
    return wrap;
  }
  function showMessage(kind, title, detail, sub) {
    clean(elements.message);
    elements.message.hidden=false;
    elements.message.className=`status-message${kind==='error'?' error':''}`;
    elements.message.setAttribute('role',kind==='error'?'alert':'status');
    node(elements.message,'strong','',title);
    node(elements.message,'p','',detail);
    if(sub)node(elements.message,'span','substatus',sub);
  }
  function hideMessage() {elements.message.hidden=true;elements.message.removeAttribute('role');clean(elements.message);}
  function resetDetail() {
    clean(elements.detail);
    const wrap=node(elements.detail,'div','detail-placeholder');
    node(wrap,'span','placeholder-circle','⌕').setAttribute('aria-hidden','true');
    node(wrap,'strong','','施設を選択してください');
    node(wrap,'p','','一覧から施設を選ぶと、掲載内容と未確認事項が表示されます。');
  }
  function renderStats(stats, kind) {
    clean(elements.stats);
    if (kind==='LOAD_ERROR') return;
    for (const [label, count] of [ ['地域の全記録',stats.total],['検索結果',stats.matched],['座標なし（結果内）',stats.noCoordinates],['資料未取得（結果内）',stats.sourceUnretrieved]]) {
      const wrap=node(elements.stats,'span','stat');
      wrap.append(document.createTextNode(label+' '));
      node(wrap,'strong','',count+'件');
    }
  }
  function renderList() {
    const error=elements.scenario.value==='error';
    const regionId=elements.region.value;
    const query=elements.query.value;
    const stats=model.getRegionStats(fixture.records,regionId,query);
    const kind=model.viewState({error,regionalCount:stats.total,matchedCount:stats.matched});
    const matches=error?[]:model.searchRecords(fixture.records,regionId,query);
    clean(elements.list);
    renderStats(stats,kind);
    elements.resultCount.textContent=error?'読込不可':`${stats.matched} 件`;
    if(kind!=='RESULTS'){
      ui.selectedId=null;resetDetail();
      if(kind==='LOAD_ERROR') showMessage('error','データ読込エラー','このデモでは読込失敗を再現しています。施設数0件とは異なります。','「表示ケース」を「通常データ」に戻すと再表示できます。');
      if(kind==='NO_REGION_RECORDS') showMessage('empty','この地域のfixture記録は0件です','対象の合成データに登録がありません。実在地域に施設が存在しないという意味ではありません。','通信障害ではありません。');
      if(kind==='NO_SEARCH_RESULTS') showMessage('empty','検索結果が0件です','この地域には記録がありますが、入力した施設名に一致する記録はありません。','検索語を消すか、地域を変更してください。');
      return;
    }
    hideMessage();
    if(ui.selectedId && !matches.some(item=>item.id===ui.selectedId)){ui.selectedId=null;resetDetail();}
    matches.forEach(item=>{
      const button=node(elements.list,'button','facility-card');
      button.type='button';button.dataset.facilityId=item.id;
      button.setAttribute('aria-controls','detailBody');
      button.setAttribute('aria-pressed',String(ui.selectedId===item.id));
      button.setAttribute('aria-label',`${item.name} の詳細を表示。${model.locationLabel(item)}`);
      const head=node(button,'div','facility-card-head');
      node(head,'span','facility-icon','▦').setAttribute('aria-hidden','true');
      const middle=node(head,'span','');
      node(middle,'span','facility-title',item.name);
      node(middle,'small','',model.displayRaw(item.addressRaw));
      node(head,'span','facility-arrow','→').setAttribute('aria-hidden','true');
      const badges=node(button,'div','facility-badges');
      if(!item.position?.coordinates)chip(badges,'位置未確認','unknown');
      else chip(badges,'参考座標あり（合成）');
      if(item.source?.retrieved===false)chip(badges,'元資料未取得','missing');
      if(!model.isKnown(item.roleRaw))chip(badges,'区分 UNKNOWN','unknown');
      button.addEventListener('click',()=>{
        ui.selectedId=item.id;
        renderList();
        renderDetail(item);
        elements.heading.focus({preventScroll:true});
        if(window.matchMedia('(max-width: 850px)').matches){
          elements.heading.scrollIntoView({block:'start',behavior:'auto'});
          const safetyBottom=document.querySelector('.safety-strip')?.getBoundingClientRect().bottom||0;
          const headingTop=elements.heading.getBoundingClientRect().top;
          if(headingTop<safetyBottom+12){window.scrollBy({top:headingTop-safetyBottom-12,behavior:'auto'});}
        }
      });
    });
  }
  function renderDetail(item) {
    clean(elements.detail);
    const top=node(elements.detail,'div','detail-top');
    const over=node(top,'div','detail-overline');
    node(over,'span','',`FIXTURE RECORD / ${item.id}`);
    const close=node(over,'button','close-detail','×  詳細を閉じる');close.type='button';
    close.addEventListener('click',()=>{
      ui.selectedId=null;renderList();
      const selected=Array.from(elements.list.querySelectorAll('button')).find(button=>button.dataset.facilityId===item.id);
      if(selected)selected.focus();
    });
    node(top,'h3','',item.name);
    const tags=node(top,'div','detail-tags');chip(tags,'架空施設・実在しません');
    chip(tags,model.locationLabel(item),item.position?.coordinates?'':'unknown');
    if(!item.source.retrieved)chip(tags,'元資料未取得','missing');
    node(top,'p','','この施設は表示試験用の合成記録です。公式指定・避難可否・開設状況を示しません。');
    const general=node(elements.detail,'div','detail-section');
    const titleA=node(general,'h4');node(titleA,'span','section-number','A');titleA.append(' 資料に記載されたという想定の値');
    const generalGrid=node(general,'div','info-grid');
    keyValue(generalGrid,'施設名（fixture）',item.name);
    keyValue(generalGrid,'施設役割／区分（架空の元文）',item.roleRaw);
    keyValue(generalGrid,'住所（架空の元文）',item.addressRaw,true);
    keyValue(generalGrid,'対象災害の原記号（解釈しない）',item.disasterRaw,true);
    const source=node(elements.detail,'div','detail-section');
    const titleB=node(source,'h4');node(titleB,'span','section-number','B');titleB.append(' 架空資料の出典・版');
    const sourceBox=node(source,'div','source-box');
    keyValue(sourceBox,'資料ラベル（合成）',item.source.label,true);
    keyValue(sourceBox,'資料版（fixture）',item.source.version,true);
    keyValue(sourceBox,'元資料の取得状態',item.source.retrieved?'fixtureのみ存在（実資料ではない）':'元資料未取得（合成ケース）',true);
    keyValue(sourceBox,'公開日／更新日',item.source.publishedAt,true);
    keyValue(sourceBox,'デモ用URL（リンク無効）',item.source.url,true);
    node(source,'p','source-warning','※ example.invalid は無効なテスト用URLです。外部ページへのリンクは作成していません。');
    const position=node(elements.detail,'div','detail-section');
    const titleC=node(position,'h4');node(titleC,'span','section-number','C');titleC.append(' 位置情報・指定範囲');
    const posGrid=node(position,'div','info-grid');
    keyValue(posGrid,'位置情報',model.locationLabel(item));
    keyValue(posGrid,'参照点の種別',item.position.referenceType);
    node(position,'p','position-explainer',item.position.positionNote+'。参照点・敷地の境界・正式指定範囲・災害時の使用入口は別情報です。実際の案内には使用できません。');
    const attrs=node(elements.detail,'div','detail-section');
    const titleD=node(attrs,'h4');node(titleD,'span','section-number','D');titleD.append(' 属性ごとの確認状況');
    const labels=[['designation','公的な指定区分'],['boundaryEntrance','敷地・建物・入口'],['hazardConditions','災害ごとの利用条件'],['operations','現在の開設・混雑'],['designatedArea','参照点・正式な指定範囲']];
    labels.forEach(([key,label])=>{
      const entry=item.attributes[key];
      const wrap=node(attrs,'div','status-row');const header=node(wrap,'div','status-row-head');
      node(header,'strong','',label);chip(header,model.stateLabels[entry.state]||'未確認',entry.state==='FIXTURE_ONLY'?'':'unknown');
      node(wrap,'p','',entry.reason);
    });
  }
  function update(){renderList();if(ui.selectedId){const entry=fixture.records.find(r=>r.id===ui.selectedId);if(entry)renderDetail(entry);}}
  elements.region.addEventListener('change',()=>{ui.selectedId=null;resetDetail();update();});
  elements.query.addEventListener('input',update);
  elements.scenario.addEventListener('change',()=>{ui.selectedId=null;resetDetail();update();});
  update();
})();
