// F09: local-only, non-persistent checklist. No network, storage, or personal data.
export const CATEGORIES = Object.freeze([
  Object.freeze({
    id: 'home', title: '自宅で備える', subtitle: '暮らしを維持するための確認',
    items: Object.freeze([
      Object.freeze({ id: 'water', label: '飲料水を備えている', detail: '人数や状況に応じた量を確認する' }),
      Object.freeze({ id: 'food', label: '保存できる食料を備えている', detail: '期限と日常での入れ替えも確認する' }),
      Object.freeze({ id: 'toilet', label: '携帯・簡易トイレを備えている', detail: '断水時の衛生面を確認する' }),
      Object.freeze({ id: 'supplies', label: '生活用品を備えている', detail: '紙類などの消耗品を見直す' }),
    ]),
  }),
  Object.freeze({
    id: 'carry', title: '持ち出しに備える', subtitle: '急な移動に向けた確認',
    items: Object.freeze([
      Object.freeze({ id: 'bag', label: '非常用持ち出し袋を準備している', detail: '取り出しやすい場所に置く' }),
      Object.freeze({ id: 'light', label: '懐中電灯を用意している', detail: '点灯と電源を確認する' }),
      Object.freeze({ id: 'radio', label: '携帯ラジオなど情報収集手段を確認している', detail: '停電時に使えるか確認する' }),
    ]),
  }),
  Object.freeze({
    id: 'actions', title: '日ごろから確認する', subtitle: '行動や連絡方法の確認',
    items: Object.freeze([
      Object.freeze({ id: 'furniture', label: '家具の転倒防止を確認している', detail: '出入り口をふさがない配置も見直す' }),
      Object.freeze({ id: 'route', label: '地域の避難情報・経路を確認している', detail: '最新の自治体情報を別途確認する' }),
      Object.freeze({ id: 'contact', label: '災害時の連絡方法を確認している', detail: '災害用伝言サービスなどを調べる' }),
    ]),
  }),
]);

const VALID_IDS = new Set(CATEGORIES.flatMap(category => category.items.map(item => item.id)));
export const TOTAL_ITEMS = VALID_IDS.size;
if (TOTAL_ITEMS !== CATEGORIES.reduce((sum, category) => sum + category.items.length, 0)) {
  throw new Error('F09 checklist item IDs must be unique');
}

export function createChecklist() {
  const checkedIds = new Set();
  return Object.freeze({
    setChecked(id, checked) {
      if (typeof id !== 'string' || !VALID_IDS.has(id) || typeof checked !== 'boolean') return false;
      if (checked) checkedIds.add(id);
      else checkedIds.delete(id);
      return true;
    },
    isChecked(id) { return VALID_IDS.has(id) && checkedIds.has(id); },
    reset() { checkedIds.clear(); },
    snapshot() {
      const checkedCount = checkedIds.size;
      return Object.freeze({
        checkedCount,
        totalCount: TOTAL_ITEMS,
        uncheckedCount: TOTAL_ITEMS - checkedCount,
        percent: TOTAL_ITEMS === 0 ? 0 : Math.round((checkedCount / TOTAL_ITEMS) * 100),
        checkedIds: Object.freeze([...checkedIds]),
      });
    },
  });
}
