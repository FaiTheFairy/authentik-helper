// shared constants and app state

export const PAGE_SIZE_PRESETS = [25, 50, 100];
export const PS_KEY_GUEST  = 'pager:guest:size';
export const PS_KEY_MEMBER = 'pager:member:size';

export const SIMPLE_NAV_MAX = 2;  // only prev and next when pages ≤ 2
export const MAX_FULL_PAGES = 7;  // full numbers when pages ≤ 7, else truncate

export let GUEST_DATA = [];
export let MEMBER_DATA = [];

export const guestSelected = new Set();   // pk number
export const memberSelected = new Set();

export let guestPage = 1;
export let membersPage = 1;

export let guestPageSize;
export let membersPageSize;

// local storage helpers
export function loadSize(key, fallback = 50) {
  try {
    const raw = localStorage.getItem(key);
    const n = Number(raw);
    return Number.isFinite(n) && n > 0 ? n : fallback;
  } catch { return fallback; }
}

export function saveSize(key, n) {
  try { localStorage.setItem(key, String(n)); } catch {}
}

// init sizes once
guestPageSize   = loadSize(PS_KEY_GUEST, 50);
membersPageSize = loadSize(PS_KEY_MEMBER, 50);

// allow controlled updates from other modules
export function setGuestData(list)        { GUEST_DATA = list; }
export function setMemberData(list)       { MEMBER_DATA = list; }
export function setGuestPage(n)           { guestPage = n; }
export function setMembersPage(n)         { membersPage = n; }
export function setGuestPageSize(n)       { guestPageSize = n; }
export function setMembersPageSize(n)     { membersPageSize = n; }
