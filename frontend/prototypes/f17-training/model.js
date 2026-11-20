// F17 training is a self-contained, entirely fictional UI drill. No production data.
export const F17_FIXTURE = Object.freeze({
  marker: 'HINANEX_F17_FICTION_ONLY',
  id: 'f17-invented-flood-01',
  title: '架空の青葉地区・大雨を想定した操作練習',
  source: 'F17自作・架空シナリオシート／場面01（公式情報ではありません）',
  description: '架空の地域で雨が続いているという設定です。災害情報の出典と未確認事項を確認する操作だけを練習します。',
  unknowns: Object.freeze(['実際の浸水の有無', '警戒情報・避難情報', '道路や移動の安全性']),
  facilities: Object.freeze([
    Object.freeze({
      id: 'invented-a', name: '架空施設A・あおば会館',
      source: 'F17自作・架空施設資料／A行（公式資料ではありません）',
      pet: '記載なし・未確認', stepFree: '段差が少ないとの架空の記載',
      unknowns: Object.freeze(['現在の開設状況', '洪水時の利用可否', 'ペット同行の可否', '移動経路の安全性'])
    }),
    Object.freeze({
      id: 'invented-b', name: '架空施設B・みずき交流室',
      source: 'F17自作・架空施設資料／B行（公式資料ではありません）',
      pet: 'ペット同行可能との架空の記載', stepFree: '記載なし・未確認',
      unknowns: Object.freeze(['現在の開設状況', '洪水時の利用可否', '実際の段差・アクセス', '移動経路の安全性'])
    })
  ])
});

const CONDITIONS = Object.freeze(['pet', 'stepFree']);
const choiceIds = new Set(F17_FIXTURE.facilities.map(item => item.id));

export function isF17Loopback(origin) {
  if (typeof origin !== 'string') return false;
  try {
    const url = new URL(origin);
    return url.protocol === 'http:' && !url.username && !url.password &&
      ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname) &&
      url.origin === origin;
  } catch { return false; }
}

function state(phase, step = 1, conditions = {pet: false, stepFree: false}, choice = null, reviewed = false) {
  return Object.freeze({phase, step, conditions: Object.freeze({...conditions}), choice, reviewed});
}
const fresh = () => state('ACTIVE');
const stopped = () => state('STOPPED');
const invalid = () => state('INVALID');

/** Do not accept dynamically supplied scenario content, even if its shape looks valid. */
export function createTraining(snapshot = F17_FIXTURE) {
  return snapshot === F17_FIXTURE ? fresh() : invalid();
}

/** Every invalid action fails closed; prior choice/review cannot survive it. */
export function transition(current, action) {
  if (!current || typeof current !== 'object' ||
      !['ACTIVE', 'STOPPED', 'INVALID'].includes(current.phase) ||
      typeof action?.type !== 'string') return invalid();
  const keys = Object.keys(action).sort().join(',');
  const expected = ({RESET:'type', STOP:'type', NEXT:'type', BACK:'type', REVIEW:'type', CHOOSE:'id,type', SET_CONDITION:'name,type,value'})[action.type];
  if (keys !== expected) return invalid();
  if (action.type === 'RESET') return fresh();
  if (action.type === 'STOP') return stopped();
  if (current.phase !== 'ACTIVE' || ![1, 2, 3].includes(current.step)) return invalid();
  if (action.type === 'SET_CONDITION') {
    if (!CONDITIONS.includes(action.name) || typeof action.value !== 'boolean') return invalid();
    return state('ACTIVE', 1, {...current.conditions, [action.name]: action.value});
  }
  if (action.type === 'NEXT') {
    if (current.step === 1) return state('ACTIVE', 2, current.conditions);
    if (current.step === 2) return state('ACTIVE', 3, current.conditions);
    return invalid();
  }
  if (action.type === 'BACK') {
    if (current.step === 2) return state('ACTIVE', 1, current.conditions);
    if (current.step === 3) return state('ACTIVE', 2, current.conditions);
    return invalid();
  }
  if (action.type === 'CHOOSE') {
    if (current.step !== 3 || !choiceIds.has(action.id)) return invalid();
    return state('ACTIVE', 3, current.conditions, action.id, false);
  }
  if (action.type === 'REVIEW') {
    if (current.step !== 3 || !choiceIds.has(current.choice)) return invalid();
    return state('ACTIVE', 3, current.conditions, current.choice, true);
  }
  return invalid();
}

/** Only a personally chosen *review target* appears in the recap; no safety ranking. */
export function recap(current) {
  if (current?.phase !== 'ACTIVE' || current.step !== 3 ||
      !current.reviewed || !choiceIds.has(current.choice)) return null;
  const facility = F17_FIXTURE.facilities.find(item => item.id === current.choice);
  return Object.freeze({
    name: facility.name,
    source: facility.source,
    conditions: Object.freeze({...current.conditions}),
    unknowns: Object.freeze([...new Set([...F17_FIXTURE.unknowns, ...facility.unknowns])])
  });
}
