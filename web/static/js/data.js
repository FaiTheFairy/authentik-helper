// data loading

import { apiFetch } from './api.js';
import {
  setGuestData, setMemberData, guestSelected, memberSelected, setGuestPage, setMembersPage
} from './state.js';
import { refreshTable } from './ui.js';

export async function loadGuestUsers() {
  const statusEl = document.getElementById('guest-status');
  const titleEl  = document.getElementById('guest-title');
  statusEl.textContent = 'loading…';

  const data = await apiFetch('/guest-users');

  titleEl.textContent = data.group_name || 'Guests';
  const list = (Array.isArray(data.users) ? data.users : []).map(u => ({...u, __action: 'promote'}));
  setGuestData(list);

  const existing = new Set(list.map(u => Number(u.pk)));
  for (const pk of Array.from(guestSelected)) {
    if (!existing.has(pk)) guestSelected.delete(pk);
  }

  setGuestPage(1);
  refreshTable('guest');

  statusEl.textContent = list.length ? `loaded ${list.length} users.` : 'no users found.';
}

export async function loadMemberUsers() {
  const statusEl = document.getElementById('members-status');
  const titleEl  = document.getElementById('members-title');
  statusEl.textContent = 'loading…';

  const data = await apiFetch('/members-users');

  titleEl.textContent = data.group_name || 'Members';
  const list = (Array.isArray(data.users) ? data.users : []).map(u => ({...u, __action: 'demote'}));
  setMemberData(list);

  const existing = new Set(list.map(u => Number(u.pk)));
  for (const pk of Array.from(memberSelected)) {
    if (!existing.has(pk)) memberSelected.delete(pk);
  }

  setMembersPage(1);
  refreshTable('members');

  statusEl.textContent = list.length ? `loaded ${list.length} users.` : 'no users found.';
}
