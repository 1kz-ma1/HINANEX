import test from 'node:test';
import assert from 'node:assert/strict';
import {F17_FIXTURE, isF17Loopback, createTraining, transition, recap} from './model.js';

const go = (...actions) => actions.reduce(transition, createTraining());
const complete = () => go({type:'NEXT'}, {type:'NEXT'}, {type:'CHOOSE',id:'invented-a'}, {type:'REVIEW'});

test('original scenario has precisely two invented sources and clear unknowns', () => {
  assert.equal(F17_FIXTURE.facilities.length, 2);
  assert.equal(F17_FIXTURE.marker, 'HINANEX_F17_FICTION_ONLY');
  for(const f of F17_FIXTURE.facilities) {
    assert.match(f.name, /架空/);
    assert.match(f.source, /架空/);
    assert.ok(f.unknowns.length >= 3);
    assert.ok(!('score' in f) && !('coordinates' in f));
  }
});

test('three steps require explicit personal selection and review', () => {
  const s1 = createTraining();
  assert.equal(s1.step, 1);
  assert.equal(recap(s1), null);
  const s2 = transition(s1, {type:'NEXT'});
  assert.equal(s2.step, 2);
  const s3 = transition(s2, {type:'NEXT'});
  assert.equal(s3.step, 3);
  assert.equal(recap(s3), null);
  const selected = transition(s3, {type:'CHOOSE', id:'invented-b'});
  assert.equal(recap(selected), null);
  const reviewed = transition(selected, {type:'REVIEW'});
  assert.equal(recap(reviewed).name, '架空施設B・みずき交流室');
  assert.equal(recap(reviewed).unknowns.includes('現在の開設状況'), true);
});

test('condition changes always clear prior selection and recap', () => {
  let s = complete();
  assert.ok(recap(s));
  s = transition(s, {type:'SET_CONDITION',name:'pet',value:true});
  assert.deepEqual([s.step,s.choice,s.reviewed,s.conditions.pet],[1,null,false,true]);
  assert.equal(recap(s),null);
  s = transition(s,{type:'NEXT'});
  assert.equal(s.step,2);
  assert.equal(recap(s),null);
});

test('back from review clears selection, and a new choice requires a new review', () => {
  let s = transition(complete(),{type:'BACK'});
  assert.deepEqual([s.step,s.choice,s.reviewed],[2,null,false]);
  s = transition(s,{type:'NEXT'});
  s = transition(s,{type:'CHOOSE',id:'invented-a'});
  s = transition(s,{type:'CHOOSE',id:'invented-b'});
  assert.equal(recap(s),null);
  assert.equal(recap(transition(s,{type:'REVIEW'})).name,'架空施設B・みずき交流室');
});

test('stopping and resetting always discard old results', () => {
  let s = transition(complete(),{type:'STOP'});
  assert.equal(s.phase,'STOPPED');
  assert.equal(s.choice,null);
  assert.equal(recap(s),null);
  assert.equal(transition(s,{type:'NEXT'}).phase,'INVALID');
  s = transition(s,{type:'RESET'});
  assert.equal(s.phase,'ACTIVE');
  assert.deepEqual(s.conditions,{pet:false,stepFree:false});
  assert.equal(s.step,1);
});

test('unexpected inputs and steps fail closed without any recap', () => {
  const invalidActions = [
    {type:'CHOOSE',id:'not-an-id'}, {type:'NEXT',id:'wrong'},
    {type:'SET_CONDITION',name:'pet',value:'true'},
    {type:'SET_CONDITION',name:'realSafety',value:true},
    {type:'INJECT',id:'invented-a'}, null, {},
  ];
  for(const action of invalidActions) {
    const from = complete();
    const result = transition(from,action);
    assert.equal(result.phase,'INVALID',String(action?.type));
    assert.equal(result.choice,null);
    assert.equal(recap(result),null);
  }
  const forged = {...F17_FIXTURE};
  assert.equal(createTraining(forged).phase,'INVALID');
  assert.equal(createTraining(null).phase,'INVALID');
  const fromReview = go({type:'NEXT'}, {type:'NEXT'}, {type:'REVIEW'});
  assert.equal(fromReview.phase,'INVALID');
  const badId = transition(go({type:'NEXT'},{type:'NEXT'}),{type:'CHOOSE',id:'unknown'});
  assert.equal(badId.phase,'INVALID');
});

test('loopback origin only; public/file/credential origins blocked', () => {
  for (const url of ['http://localhost:8000','http://127.0.0.1:1234','http://[::1]:5000']) {
    assert.equal(isF17Loopback(url),true,url);
  }
  for (const url of ['https://localhost:8000','http://hinanex.com','file://',
    'http://localhost.evil.com', 'http://x@localhost:8000','http://127.0.0.1:8000/path', null, '']) {
    assert.equal(isF17Loopback(url),false,String(url));
  }
});
