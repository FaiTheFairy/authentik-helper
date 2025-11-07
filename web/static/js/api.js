// http helpers

export async function apiFetch(path, options = {}) {
  const res = await fetch(path, { credentials: 'same-origin', ...options });
  const ct = res.headers.get('content-type') || '';
  const looksJson = ct.includes('application/json');

  if (!looksJson) {
    const isLogin = res.redirected || (res.url && res.url.includes('/login'));
    if (isLogin || res.status === 401 || res.status === 303) {
      try { window.location.href = '/login'; } catch {}
      throw new Error('redirected to login');
    }
    throw new Error(`unexpected response ${res.status}`);
  }

  let body;
  try { body = await res.json(); } catch { throw new Error('invalid json response'); }

  if (!res.ok) {
    const detail = body && (body.detail || body.error || body.message);
    const err = new Error(detail ? String(detail) : `http ${res.status}`);
    err.status = res.status;
    err.body = body;
    throw err;
  }
  return body;
}
