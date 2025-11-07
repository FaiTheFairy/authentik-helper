// ~/web/static/js/theme-toggle.js
const storageKey = 'theme-preference';

function getColorPreference() {
  try {
    const saved = localStorage.getItem(storageKey);
    if (saved === 'light' || saved === 'dark') return saved;
  } catch {}
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function ensureThemeMeta() {
  let meta = document.querySelector('meta#theme-color');
  if (!meta) {
    meta = document.createElement('meta');
    meta.id = 'theme-color';
    meta.name = 'theme-color';
    document.head.appendChild(meta);
  }
  return meta;
}

function updateThemeColorMeta() {
  const meta = ensureThemeMeta();
  // match head defaults (#111827 light, #000000 dark)
  meta.setAttribute('content', theme.value === 'dark' ? '#000000' : '#111827');
}

function reflectPreference() {
  document.documentElement.setAttribute('data-theme', theme.value);
  const btn = document.querySelector('#theme-toggle');
  if (btn) {
    const label = theme.value === 'dark' ? 'switch to light theme' : 'switch to dark theme';
    btn.setAttribute('aria-label', label);
    btn.setAttribute('title', label);
  }
  updateThemeColorMeta();
}

function setPreference() {
  try { localStorage.setItem(storageKey, theme.value); } catch {}
  reflectPreference();
}

function onClick() {
  theme.value = theme.value === 'light' ? 'dark' : 'light';
  setPreference();
}

const theme = { value: getColorPreference() };

// set early (index.html ran an even earlier inline that sets [data-theme])
reflectPreference();

// attach on load
window.addEventListener('load', () => {
  reflectPreference();
  const btn = document.querySelector('#theme-toggle');
  if (btn) btn.addEventListener('click', onClick);
});

// keep in sync with os
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
  // only auto-follow if user hasn’t explicitly chosen? (optional)
  // if (localStorage.getItem(storageKey)) return;
  theme.value = e.matches ? 'dark' : 'light';
  setPreference();
});
