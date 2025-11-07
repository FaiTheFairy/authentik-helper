// ui logic: filtering, paging, renderers

import {
  PAGE_SIZE_PRESETS, SIMPLE_NAV_MAX, MAX_FULL_PAGES,
  GUEST_DATA, MEMBER_DATA,
  guestSelected, memberSelected,
  guestPage, membersPage,
  guestPageSize, membersPageSize,
  setGuestPage, setMembersPage
} from './state.js';

// debounce
export function debounce(fn, ms = 200) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

// filtering and paging
export function filterUsers(list, q) {
  const needle = (q || '').trim().toLowerCase();
  if (!needle) return list;
  return list.filter(u =>
    [u.pk, u.username, u.email].some(v =>
      String(v ?? '').toLowerCase().includes(needle)
    )
  );
}

export function paginate(list, page, pageSize) {
  const total = list.length;
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const safePage = Math.min(Math.max(1, page), pages);
  const start = (safePage - 1) * pageSize;
  const end = start + pageSize;
  const slice = list.slice(start, end);
  return { slice, total, pages, page: safePage, start, end: Math.min(end, total) };
}

export function getVisible(kind) {
  const isGuest = kind === 'guest';
  const data = isGuest ? GUEST_DATA : MEMBER_DATA;
  const q = document.getElementById(isGuest ? 'guest-filter' : 'members-filter')?.value || '';
  const filtered = filterUsers(data, q);
  const size = isGuest ? guestPageSize : membersPageSize;
  const curPage = isGuest ? guestPage : membersPage;
  const { slice } = paginate(filtered, curPage, size);
  return slice;
}

// renderers
export function renderTable(tbody, list, opts) {
  const isGuest = opts.kind === 'guest';
  const selectedSet = isGuest ? guestSelected : memberSelected;

  tbody.innerHTML = '';
  for (const u of list) {
    const key = String(u.pk ?? '');
    const checked = selectedSet.has(key) ? 'checked' : '';
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td><input type="checkbox" class="row-select" data-pk="${key}" ${checked}></td>
      <td>${u.pk ?? ''}</td>
      <td>${u.username ?? ''}</td>
      <td>${u.email ?? ''}</td>
      <td style="text-align:center">
        ${u.__action === 'promote'
          ? `<button data-action="promote" data-pk="${u.pk}">Promote</button>`
          : `<button data-action="demote" data-pk="${u.pk}">Demote</button>`}
      </td>`;
    tbody.appendChild(tr);
  }
}

function pageNumbersFor(totalPages, current) {
  if (totalPages <= MAX_FULL_PAGES) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }
  const items = [];
  const left = Math.max(2, current - 1);
  const right = Math.min(totalPages - 1, current + 1);
  items.push(1);
  if (left > 2) items.push('…');
  for (let p = left; p <= right; p++) items.push(p);
  if (right < totalPages - 1) items.push('…');
  items.push(totalPages);
  return items;
}

export function renderPager(kind, filteredTotal, page, pages, start, end) {
  const el = document.getElementById(kind === 'guest' ? 'guest-pager' : 'members-pager');
  if (!el) return;

  const pageSize = kind === 'guest' ? guestPageSize : membersPageSize;

  if (filteredTotal <= pageSize) {
    el.innerHTML = '';
    return;
  }

  const presets = PAGE_SIZE_PRESETS.slice();
  if (!presets.includes(pageSize)) presets.unshift(pageSize);

  const sizeOptions = presets
    .map(v => `<option value="${v}" ${v === pageSize ? 'selected' : ''}>${v}</option>`)
    .join('');

  const disabledPrev = page <= 1 ? 'disabled' : '';
  const disabledNext = page >= pages ? 'disabled' : '';

  const leftCluster = `
    <label class="pager-label">result per page</label>
    <select class="pager-size" data-kind="${kind}">
      ${sizeOptions}
    </select>
    <span class="pager-count">${start + 1}–${end} of ${filteredTotal}</span>
  `;

  let rightCluster = '';

  if (pages <= SIMPLE_NAV_MAX) {
    rightCluster = `
      <button class="pager-btn" data-page="1" data-kind="${kind}" ${disabledPrev} title="first">«</button>
      <button class="pager-btn" data-page="${page - 1}" data-kind="${kind}" ${disabledPrev} title="previous">‹</button>
      <button class="pager-btn" data-page="${page + 1}" data-kind="${kind}" ${disabledNext} title="next">›</button>
      <button class="pager-btn" data-page="${pages}" data-kind="${kind}" ${disabledNext} title="last">»</button>
    `;
  } else if (pages <= MAX_FULL_PAGES) {
    const nums = Array.from({length: pages}, (_, i) => i + 1)
      .map(n => `<button class="pager-num ${n === page ? 'is-active' : ''}" data-page="${n}" data-kind="${kind}">${n}</button>`)
      .join('');
    rightCluster = `
      <button class="pager-btn" data-page="1" data-kind="${kind}" ${disabledPrev} title="first">«</button>
      <button class="pager-btn" data-page="${page - 1}" data-kind="${kind}" ${disabledPrev} title="previous">‹</button>
      <div class="pager-numbers">${nums}</div>
      <button class="pager-btn" data-page="${page + 1}" data-kind="${kind}" ${disabledNext} title="next">›</button>
      <button class="pager-btn" data-page="${pages}" data-kind="${kind}" ${disabledNext} title="last">»</button>
    `;
  } else {
    const items = pageNumbersFor(pages, page).map(item => {
      if (item === '…') return `<span class="pager-ellipsis">…</span>`;
      return `<button class="pager-num ${item === page ? 'is-active' : ''}" data-page="${item}" data-kind="${kind}">${item}</button>`;
    }).join('');
    rightCluster = `
      <button class="pager-btn" data-page="1" data-kind="${kind}" ${disabledPrev} title="first">«</button>
      <button class="pager-btn" data-page="${page - 1}" data-kind="${kind}" ${disabledPrev} title="previous">‹</button>
      <div class="pager-numbers">${items}</div>
      <button class="pager-btn" data-page="${page + 1}" data-kind="${kind}" ${disabledNext} title="next">›</button>
      <button class="pager-btn" data-page="${pages}" data-kind="${kind}" ${disabledNext} title="last">»</button>
    `;
  }

  el.innerHTML = `
    <div class="pager">
      <div class="pager-left">${leftCluster}</div>
      <div class="pager-right">${rightCluster}</div>
    </div>
  `;
}

export function updateHeaderSelectAll(kind) {
  const set = kind === 'guest' ? guestSelected : memberSelected;
  const headerCb = document.getElementById(
    kind === 'guest' ? 'guest-select-all' : 'members-select-all'
  );
  if (!headerCb) return;

  const visible = getVisible(kind);
  const allVisibleSelected =
    visible.length > 0 && visible.every(u => set.has(String(u.pk ?? '')));

  headerCb.checked = allVisibleSelected;
  headerCb.indeterminate =
    visible.length > 0 && !allVisibleSelected && visible.some(u => set.has(String(u.pk)));
}

export function updateBulkButtons() {
  const gpBtn   = document.getElementById('guest-promote-selected');
  const gmCount = document.getElementById('guest-selected-count');
  const mdBtn   = document.getElementById('members-demote-selected');
  const mmCount = document.getElementById('members-selected-count');

  const showBulk = (btn, countEl, count) => {
    if (!btn || !countEl) return;
    btn.disabled = count === 0;
    countEl.textContent = `${count} selected`;
    btn.classList.toggle('is-hidden', count === 0);
    countEl.classList.toggle('is-hidden', count === 0);
  };

  showBulk(gpBtn, gmCount, guestSelected.size);
  showBulk(mdBtn, mmCount, memberSelected.size);
}

export function renderInviteResult(payload) {
  const resultEl = document.getElementById('invite-result');
  if (!resultEl) return;

  const url = payload?.invite_url || '';
  const pk  = payload?.pk || '';
  const exp = payload?.expires_friendly || '';

  if (url) {
    resultEl.innerHTML =
      `invite url: <a href="${url}" target="_blank" rel="noopener">${url}</a>` +
      (exp ? ` <span class="small">(expires ${exp})</span>` : '');
    try { navigator.clipboard.writeText(url); } catch {}
  } else if (pk) {
    resultEl.textContent = `invite uuid: ${pk}`;
  } else {
    resultEl.textContent = 'no invite url returned';
  }
}

// main refresh hook that ties it together
export function refreshTable(kind) {
  const isGuest = kind === 'guest';
  const data = isGuest ? GUEST_DATA : MEMBER_DATA;
  const filterInput = document.getElementById(isGuest ? 'guest-filter' : 'members-filter');
  const tbody = document.querySelector(isGuest ? '#guest-users tbody' : '#members-users tbody');
  const size = isGuest ? guestPageSize : membersPageSize;
  const curPage = isGuest ? guestPage : membersPage;

  const filtered = filterUsers(data, filterInput?.value || '');
  const { slice, total, pages, page, start, end } = paginate(filtered, curPage, size);

  if (isGuest) setGuestPage(page); else setMembersPage(page);

  renderTable(tbody, slice, { kind });
  renderPager(kind, total, page, pages, start, end);
  updateHeaderSelectAll(kind);
  updateBulkButtons();
}
