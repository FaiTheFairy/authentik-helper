// event wiring

import { apiFetch } from './api.js';
import {
  guestSelected, memberSelected,
  setGuestPage, setMembersPage,
  setGuestPageSize, setMembersPageSize,
  PS_KEY_GUEST, PS_KEY_MEMBER, saveSize
} from './state.js';
import { debounce, getVisible, refreshTable, renderInviteResult } from './ui.js';
import { loadGuestUsers, loadMemberUsers } from './data.js';

const $ = (id) => document.getElementById(id);
const str = (v) => String(v ?? '');
const setText = (id, text) => { const el = $(id); if (el) el.textContent = text; };

async function promoteOne(pk, sendMail) {
  return apiFetch('/promote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pk, send_mail: !!sendMail }),
  });
}

async function demoteOne(pk) {
  return apiFetch('/demote', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pk }),
  });
}

export function wireHandlers() {
  // initial loads (run in parallel)
  window.addEventListener('load', () => {
    Promise.allSettled([loadGuestUsers(), loadMemberUsers()]);
  });

  // filters
  $('guest-filter')?.addEventListener('input', debounce(() => {
    setGuestPage(1);
    refreshTable('guest');
  }, 150));

  $('members-filter')?.addEventListener('input', debounce(() => {
    setMembersPage(1);
    refreshTable('members');
  }, 150));

  // header select all (visible rows)
  $('guest-select-all')?.addEventListener('change', () => {
    const visible = getVisible('guest');
    const cb = $('guest-select-all');
    if (cb?.checked) visible.forEach(u => guestSelected.add(str(u.pk)));
    else visible.forEach(u => guestSelected.delete(str(u.pk)));
    refreshTable('guest');
  });

  $('members-select-all')?.addEventListener('change', () => {
    const visible = getVisible('members');
    const cb = $('members-select-all');
    if (cb?.checked) visible.forEach(u => memberSelected.add(str(u.pk)));
    else visible.forEach(u => memberSelected.delete(str(u.pk)));
    refreshTable('members');
  });

  // invite button
  $('invite-btn')?.addEventListener('click', async (e) => {
    e.preventDefault();

    const name      = $('inv-name').value.trim();
    const username  = ($('inv-username').value.trim() || name);
    const email     = $('inv-email').value.trim();
    const single    = $('inv-single').checked;
    const daysStr   = $('inv-days').value.trim();
    const flow      = $('inv-flow').value.trim() || undefined;
    const expires_days = daysStr ? Number(daysStr) : undefined;

    const statusEl = $('invite-status');
    const resultEl = $('invite-result');
    if (statusEl) statusEl.textContent = 'creating…';
    if (resultEl) resultEl.textContent = '';

    try {
      const j = await apiFetch('/invites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, username, email, single_use: single, expires_days, flow }),
      });
      if (statusEl) statusEl.textContent = 'invitation created ✓';
      renderInviteResult(j);
    } catch (err) {
      if (statusEl) statusEl.textContent = 'failed';
      if (resultEl) resultEl.textContent = String((err && err.message) || err);
    }
  });

  // bulk actions
  $('guest-promote-selected')?.addEventListener('click', async (e) => {
    e.preventDefault();
    const pks = Array.from(guestSelected);
    if (pks.length === 0) return;

    const sendMail = !!$('promo-mail')?.checked;
    const btn = $('guest-promote-selected');
    btn.disabled = true;
    setText('guest-status', `promoting ${pks.length}…`);

    try {
      await Promise.all(pks.map(pk => promoteOne(pk, sendMail)));
      guestSelected.clear();
      await Promise.all([loadGuestUsers(), loadMemberUsers()]);
      setText('guest-status', `promoted ${pks.length} user${pks.length === 1 ? '' : 's'}`);
    } catch (err) {
      setText('guest-status', `error: ${String((err && err.message) || err)}`);
    } finally {
      btn.disabled = false;
      refreshTable('guest');
      refreshTable('members');
    }
  });

  $('members-demote-selected')?.addEventListener('click', async (e) => {
    e.preventDefault();
    const pks = Array.from(memberSelected);
    if (pks.length === 0) return;

    const btn = $('members-demote-selected');
    btn.disabled = true;
    setText('members-status', `demoting ${pks.length}…`);

    try {
      await Promise.all(pks.map(pk => demoteOne(pk)));
      memberSelected.clear();
      await Promise.all([loadGuestUsers(), loadMemberUsers()]);
      setText('members-status', `demoted ${pks.length} user${pks.length === 1 ? '' : 's'}`);
    } catch (err) {
      setText('members-status', `error: ${String((err && err.message) || err)}`);
    } finally {
      btn.disabled = false;
      refreshTable('guest');
      refreshTable('members');
    }
  });

  // delegated clicks (pager, row select, single promote/demote)
  document.addEventListener('click', async (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;

    // pager buttons
    const pagerBtn = target.closest('button[data-kind][data-page]');
    if (pagerBtn) {
      const kind = pagerBtn.getAttribute('data-kind');
      const page = Number(pagerBtn.getAttribute('data-page'));
      if (kind === 'guest') setGuestPage(page); else setMembersPage(page);
      refreshTable(kind);
      return;
    }

    // row select
    const cb = target.closest('input.row-select[data-pk]');
    if (cb) {
      const pk = str(cb.getAttribute('data-pk'));
      const row = cb.closest('table');
      const isGuestTable = row && row.id === 'guest-users';
      const set = isGuestTable ? guestSelected : memberSelected;
      if (cb.checked) set.add(pk); else set.delete(pk);
      refreshTable(isGuestTable ? 'guest' : 'members');
      return;
    }

    // single promote/demote
    const btn = target.closest('button[data-action][data-pk]');
    if (btn) {
      const action = btn.getAttribute('data-action'); // promote or demote
      const pk = str(btn.getAttribute('data-pk'));
      const sendMail = action === 'promote' ? !!$('promo-mail')?.checked : false;

      btn.disabled = true;
      btn.textContent = (action === 'promote' ? 'promoting' : 'demoting') + '…';

      try {
        if (action === 'promote') await promoteOne(pk, sendMail);
        else await demoteOne(pk);

        btn.textContent = (action === 'promote' ? 'Promoted' : 'Demoted') + ' ✓';

        await Promise.all([loadGuestUsers(), loadMemberUsers()]);

        const targetStatus = action === 'promote' ? 'guest-status' : 'members-status';
        setText(targetStatus, action === 'promote' ? 'promoted 1 user' : 'demoted 1 user');
      } catch (err) {
        const targetStatus = action === 'promote' ? 'guest-status' : 'members-status';
        setText(targetStatus, `error: ${String((err && err.message) || err)}`);
        btn.textContent = 'Error';
      }
    }
  });

  // page size changes
  document.addEventListener('change', (e) => {
    const target = e.target;
    if (!(target instanceof Element)) return;
    const sel = target.closest('select.pager-size[data-kind]');
    if (!sel) return;

    const kind = sel.getAttribute('data-kind');
    const val = Number(sel.value);
    if (kind === 'guest') {
      setGuestPageSize(val);
      saveSize(PS_KEY_GUEST, val);
      setGuestPage(1);
      refreshTable('guest');
    } else {
      setMembersPageSize(val);
      saveSize(PS_KEY_MEMBER, val);
      setMembersPage(1);
      refreshTable('members');
    }
  });
}
