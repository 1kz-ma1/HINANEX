import { CATEGORIES, createChecklist } from './model.js';

export function mountChecklist(doc = document) {
  const root = doc.querySelector('#checklist');
  const count = doc.querySelector('#checked-count');
  const total = doc.querySelector('#total-count');
  const percent = doc.querySelector('#progress-percent');
  const bar = doc.querySelector('#progress-bar');
  const remaining = doc.querySelector('#remaining-count');
  const reset = doc.querySelector('#reset-button');
  const filter = doc.querySelector('#filter-button');
  const empty = doc.querySelector('#empty-message');
  if (![root, count, total, percent, bar, remaining, reset, filter, empty].every(Boolean)) {
    throw new Error('F09 checklist markup is incomplete');
  }
  const checklist = createChecklist();
  let onlyUnchecked = false;
  const itemNodes = new Map();

  for (const category of CATEGORIES) {
    const section = doc.createElement('section');
    section.className = 'category';
    section.setAttribute('aria-labelledby', `heading-${category.id}`);
    const header = doc.createElement('div');
    header.className = 'category-heading';
    const heading = doc.createElement('h2');
    heading.id = `heading-${category.id}`;
    heading.textContent = category.title;
    const description = doc.createElement('p');
    description.textContent = category.subtitle;
    header.append(heading, description);
    section.append(header);
    const list = doc.createElement('ul');
    list.className = 'items';
    for (const item of category.items) {
      const li = doc.createElement('li');
      li.className = 'item';
      const label = doc.createElement('label');
      label.className = 'item-label';
      const input = doc.createElement('input');
      input.type = 'checkbox';
      input.name = 'prepared';
      input.value = item.id;
      input.dataset.itemId = item.id;
      const copy = doc.createElement('span');
      copy.className = 'item-copy';
      const name = doc.createElement('strong');
      name.textContent = item.label;
      const detail = doc.createElement('span');
      detail.className = 'item-detail';
      detail.textContent = item.detail;
      copy.append(name, detail);
      const status = doc.createElement('span');
      status.className = 'item-status';
      status.textContent = '未準備';
      label.append(input, copy, status);
      li.append(label);
      list.append(li);
      itemNodes.set(item.id, { li, input, status });
    }
    section.append(list);
    root.append(section);
  }

  function render() {
    const state = checklist.snapshot();
    count.textContent = String(state.checkedCount);
    total.textContent = String(state.totalCount);
    remaining.textContent = String(state.uncheckedCount);
    percent.textContent = `${state.percent}%`;
    bar.value = state.checkedCount;
    bar.max = state.totalCount;
    bar.setAttribute('aria-label', `チェックした項目 ${state.checkedCount} / ${state.totalCount}`);
    reset.disabled = state.checkedCount === 0;
    filter.setAttribute('aria-pressed', String(onlyUnchecked));
    filter.textContent = onlyUnchecked ? 'すべて表示' : '未準備だけ表示';
    let visible = 0;
    for (const [id, node] of itemNodes) {
      const checked = checklist.isChecked(id);
      node.input.checked = checked;
      node.li.classList.toggle('is-checked', checked);
      node.status.textContent = checked ? '準備済み' : '未準備';
      node.li.hidden = onlyUnchecked && checked;
      if (!node.li.hidden) visible++;
    }
    for (const section of root.querySelectorAll('.category')) {
      section.hidden = !section.querySelector('.item:not([hidden])');
    }
    empty.hidden = visible !== 0;
  }
  root.addEventListener('change', event => {
    const target = event.target;
    if (!(target instanceof doc.defaultView.HTMLInputElement)) return;
    if (!checklist.setChecked(target.dataset.itemId, target.checked)) {
      render(); // Unrecognized IDs are ignored, not persisted.
      return;
    }
    const hideFocused = onlyUnchecked && target.checked;
    render(); // No wholesale DOM replacement during interaction.
    if (hideFocused) {
      (root.querySelector('.item:not([hidden]) input') || filter).focus();
    }
  });
  reset.addEventListener('click', () => { checklist.reset(); render(); });
  filter.addEventListener('click', () => { onlyUnchecked = !onlyUnchecked; render(); });
  render();
  return Object.freeze({ snapshot: () => checklist.snapshot() });
}

if (typeof document !== 'undefined' && document.querySelector('#checklist')) {
  mountChecklist();
}
