import { readFileSync } from "node:fs";
import { test } from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";

const source=readFileSync(new URL("../docs/20261022-seven-minute-rehearsal.html",import.meta.url),"utf8");
const json=source.match(/<script id="agenda" type="application\/json">([\s\S]*?)<\/script>/);
const code=source.match(/<script>\s*([\s\S]*?)<\/script>\s*<\/body>/);
assert.ok(json, "must embed an offline-readable agenda");
assert.ok(code, "must embed inline controller for file:// use");
const agenda=JSON.parse(json[1]);

test("exact 7-minute timeline includes original C and E demo time budgets",()=>{
    assert.equal(agenda.length,7);
    assert.equal(agenda.reduce((s,row)=>s+row.seconds,0),420);
    assert.deepEqual(agenda.map(s=>s.seconds),[40,45,60,90,65,65,55]);
    assert.equal(agenda.filter(s=>s.id==="evidence").length,1);
    assert.equal(agenda.find(s=>s.id==="evidence").seconds,60);
    assert.equal(agenda.find(s=>s.id==="map").seconds,90);
    assert.equal(new Set(agenda.map(s=>s.id)).size,7);
    assert.ok(agenda.every(s=>s.title && s.spoken && s.actions.length>0 && s.fallback && Array.isArray(s.links)));
});

test("read-only evidence/safety distinctions are explicit",()=>{
    const joined=agenda.map(a=>a.spoken+" "+a.actions.join(" ")).join(" ");
    for(const mustInclude of ["65","66","205","11","UNKNOWN","未評価","未検証","名古屋","公式"]){
        assert.ok(joined.includes(mustInclude),"required evidence/safety term: "+mustInclude);
    }
    assert.ok(source.includes("未受入の発表支援ツール"));
    assert.ok(source.includes("当日避難した建物"));
    assert.ok(source.includes("C_20261022_offline_evidence.html"));
    assert.ok(source.includes("35.70, 140.10"));
    assert.ok(source.includes("予測精度"));
    assert.ok(!source.includes("MATCH率100%"));
    assert.ok(!source.includes("安全な避難先を推薦できます"));
});

test("external links are pinned HTTPS and cannot inherit opener",()=>{
    const links=agenda.flatMap(s=>s.links);
    assert.ok(links.length>2);
    for(const link of links){
        assert.ok(link.label);
        const url=new URL(link.url);
        assert.equal(url.protocol,"https:");
        assert.ok(["github.com","hinanex-staging.onrender.com"].includes(url.hostname));
    }
    assert.ok(source.includes('a.rel="noopener noreferrer"'));
    assert.ok(source.includes("ステージング（未検証）"));
});

class FakeElement{
    constructor(){this.children=[];this.dataset={};this.listeners={};this.attributes={};this.textContent="";this.style={};this.disabled=false;}
    addEventListener(type,cb){this.listeners[type]=cb;}
    setAttribute(key,value){this.attributes[key]=value;}
    appendChild(value){this.children.push(value);return value;}
    append(...values){this.children.push(...values);}
    replaceChildren(...values){this.children=values;}
}
class FakeButton extends FakeElement{}
class FakeAnchor extends FakeElement{}

function mount(){
    const registry=new Map();
    for(const id of ["remaining","elapsed","progress-bar","scene-label","scene-title",
       "speaker","actions","fallback","resources","timeline","play","prev","next","reset","state"]){
        registry.set(id,id==="play"||id==="prev"||id==="next"||id==="reset"?
            new FakeButton():new FakeElement());
    }
    registry.set("agenda",{textContent:JSON.stringify(agenda)});
    const listeners={};
    const frames=new Map();let nextFrame=0;let milliseconds=0;
    const doc={
        getElementById(id){const e=registry.get(id);assert.ok(e,"element "+id);return e;},
        createElement(tag){if(tag==="a")return new FakeAnchor();if(tag==="button")return new FakeButton();return new FakeElement();},
        createTextNode(txt){return {textContent:txt};},
        addEventListener(type,fn){listeners[type]=fn;}
    };
    const globals={
        document:doc,performance:{now:()=>milliseconds},
        requestAnimationFrame(fn){const id=++nextFrame;frames.set(id,fn);return id;},
        cancelAnimationFrame(id){frames.delete(id);},
        HTMLButtonElement:FakeButton,HTMLAnchorElement:FakeAnchor,
    };
    const runnable=new vm.Script(code[1],{filename:"20261022-seven-minute-rehearsal-inline.js"});
    runnable.runInNewContext(globals,{timeout:2000});
    return {
        get:(id)=>registry.get(id),
        click:(id)=>registry.get(id).listeners.click(),
        time(ms){milliseconds=ms;const old=Array.from(frames);frames.clear();for(const [,fn] of old)fn();},
        key(k,buttonFocused=false){let blocked=false;const key=k==="KeyR"?"r":k==="Space"?" ":k;listeners.keydown({code:k,key,target:buttonFocused?new FakeButton():new FakeElement(),preventDefault(){blocked=true}});return blocked;},
    };
}

test("offline HTML controller initializes and changes scenes via timeline controls",()=>{
    const a=mount();
    assert.equal(a.get("remaining").textContent,"00:40");
    assert.equal(a.get("elapsed").textContent,"00:00 / 07:00");
    assert.ok(a.get("scene-title").textContent.includes("完成像"));
    assert.equal(a.get("timeline").children.length,7);
    a.click("next");
    assert.equal(a.get("elapsed").textContent,"00:40 / 07:00");
    assert.ok(a.get("scene-title").textContent.includes("疑問"));
    a.click("prev");
    assert.equal(a.get("elapsed").textContent,"00:00 / 07:00");
    a.get("timeline").children[3].listeners.click();
    assert.equal(a.get("elapsed").textContent,"02:25 / 07:00");
    assert.ok(a.get("scene-title").textContent.includes("GIS"));
    assert.equal(a.get("actions").children.length,5);
    a.click("reset");
    assert.equal(a.get("elapsed").textContent,"00:00 / 07:00");
});

test("clock advances by wall-time, pauses, resumes, and ends at exactly 7:00",()=>{
    const a=mount();
    a.click("play");
    a.time(85000);
    assert.equal(a.get("elapsed").textContent,"01:25 / 07:00");
    assert.ok(a.get("scene-title").textContent.includes("方向転換"));
    a.click("play");
    assert.equal(a.get("state").textContent,"一時停止中");
    a.time(130000);
    assert.equal(a.get("elapsed").textContent,"01:25 / 07:00");
    a.click("play");
    a.time(465000);
    assert.equal(a.get("elapsed").textContent,"07:00 / 07:00");
    assert.equal(a.get("state").textContent,"7分終了");
    assert.equal(a.get("next").disabled,true);
    a.click("play");
    assert.equal(a.get("elapsed").textContent,"00:00 / 07:00");
});

test("keyboard next/back/play/reset work without claiming browser demo acceptance",()=>{
    const a=mount();
    assert.equal(a.key("ArrowRight"),true);
    assert.ok(a.get("scene-title").textContent.includes("疑問"));
    assert.equal(a.key("ArrowLeft"),true);
    assert.ok(a.get("scene-title").textContent.includes("完成像"));
    assert.equal(a.key("Space"),true);
    assert.equal(a.get("state").textContent,"リハーサル進行中");
    assert.equal(a.key("KeyR",true),true); // real key=r, code=KeyR, button still focused
    assert.equal(a.get("state").textContent,"未開始");
    assert.equal(a.key("ArrowRight",true),true);
    assert.ok(a.get("scene-title").textContent.includes("疑問"));
    assert.equal(a.key("Space",true),false); // native focused button Space click must not double-toggle
});
