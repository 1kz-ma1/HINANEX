import {createB2Session,isB2Loopback} from "../b2-compare/model.js";
import {fixedSnapshot,conditions} from "./fixtures.js";
export {isB2Loopback,conditions};
export function createJourney() {
  let step="IDLE", condition=null, session=null, revision=0;
  const active=()=>["J02","J03","J04","J05"].includes(step);
  function discard(next) {
    if(session) session.clear();
    session=null; condition=null; step=next;
  }
  function load(key) {
    const next=createB2Session(fixedSnapshot(key));
    if(next.state!=="READY"){discard("LOAD_ERROR");return false;}
    session?.clear(); session=next; condition=key; return true;
  }
  const view=()=>Object.freeze({
    step,condition,revision,rows:session?.rows()??[],selected:session?.selected()??[],
    choice:session?.choice()??null,complete:step==="J05"&&session?.choice()!=null
  });
  function dispatch(action, expectedRevision) {
    if(expectedRevision!==revision || !action || typeof action.type!=="string") return false;
    switch(action.type) {
      case "START":
        if(!["IDLE","LOAD_ERROR"].includes(step))return false;
        discard("J02");break;
      case "CONDITION":
        if(step!=="J02"||typeof action.key!=="string"||!Object.hasOwn(conditions,action.key))return false;
        condition=action.key;break;
      case "SHOW":
        if(step!=="J02"||!condition)return false;
        if(load(condition))step="J03";break;
      case "CONTINUE":
        if(step!=="J03"||!session)return false;
        step="J04";break;
      case "TOGGLE":
        if(step!=="J04"||!session?.toggle(action.id).ok)return false;
        break;
      case "COMPARE":
        if(step!=="J04"||session?.selected().length!==2)return false;
        step="J05";break;
      case "CHOOSE":
        if(step!=="J05"||!session?.choose(action.id).ok)return false;
        break;
      case "BACK":
        if(step!=="J05"||!session)return false;
        if(load(condition))step="J04";break;
      case "CHANGE":
        if(!["J03","J04","J05"].includes(step))return false;
        discard("J02");break;
      case "FAIL":
        if(!active())return false;
        discard("LOAD_ERROR");break;
      case "END":
        if(step==="IDLE")return false;
        discard("IDLE");break;
      default:return false;
    }
    revision++;return true;
  }
  return Object.freeze({view,dispatch});
}
