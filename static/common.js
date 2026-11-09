// One browser tab can hold several signed-in frames, so each pane keeps its own session.
const TOKEN_KEY = 'counsel-token-' + (new URLSearchParams(location.search).get('pane') || 'main');
function token() { try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } }
function setToken(t) { try { sessionStorage.setItem(TOKEN_KEY, t); } catch {} }
function clearToken() { try { sessionStorage.removeItem(TOKEN_KEY); } catch {} }

async function api(path, opts = {}) {
  const headers = { ...(opts.body ? { 'content-type': 'application/json' } : {}), ...(token() ? { 'x-session': token() } : {}) };
  const res = await fetch(path, { ...opts, headers, credentials: 'include' });
  if (res.status === 401) { clearToken(); throw Object.assign(new Error('signin'), { signin: true, detail: (await res.json().catch(() => ({}))).detail }); }
  if (!res.ok) { const detail = (await res.json().catch(() => ({}))).detail; throw Object.assign(new Error(detail || String(res.status)), { status: res.status, detail }); }
  return res.headers.get('content-type')?.includes('json') ? res.json() : res.text();
}
const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) });

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tagged = s => esc(s).replace(/\[[A-Z]+_\d+\]/g, m => `<span class="tag">${m}</span>`);

const BRAND = '<span class="brand"><svg viewBox="0 0 64 64" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" d="M14 60H50A4 4 0 0 0 54 56V26A22 22 0 0 0 10 26V56A4 4 0 0 0 14 60ZM22 60V36A10 10 0 0 1 42 36V60Z"/></svg>Chamber</span>';

async function signOut() {
  try { await post('/api/logout'); } catch {}
  clearToken();
  location.href = '/';
}

function accountForm(root, html, submit, done) {
  root.innerHTML = `<form class="signin">${BRAND}${html}<div class="fail" id="err" role="alert"></div></form>`;
  root.querySelector('form').onsubmit = async ev => {
    ev.preventDefault();
    try { const r = await submit(Object.fromEntries(new FormData(ev.target))); setToken(r.token); done(); }
    catch (e) { root.querySelector('#err').textContent = e.detail || 'Something went wrong. Try again.'; }
  };
}

async function signIn(root, pane, done) {
  if (pane) {
    try { const r = await post('/api/demo-login', { pane }); setToken(r.token); return done(); } catch {}
  }
  try { await api('/api/me'); return done(); } catch (e) { if (!e.signin) throw e; }
  const state = await api('/api/state');
  if (state.setup) {
    return accountForm(root, `<h1>Set up your firm</h1>
      <input name="firm" placeholder="Firm name" required autofocus>
      <input name="name" placeholder="Your full name" required autocomplete="name">
      <input name="email" type="email" placeholder="Work email" required autocomplete="email">
      <input name="password" type="password" placeholder="Password, 8 characters or more" required minlength="8" autocomplete="new-password">
      <button>Create firm</button>`, body => post('/api/setup', body), done);
  }
  if (state.demo) {
    const people = await api('/api/people');
    return accountForm(root, `<select name="user">${people.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}</select>
      <input name="pin" type="password" inputmode="numeric" placeholder="PIN" autofocus>
      <button>Sign in</button>`, body => post('/api/login', body), done);
  }
  accountForm(root, `<h1>Sign in</h1>
    <input name="email" type="email" placeholder="Work email" required autofocus autocomplete="email">
    <input name="password" type="password" placeholder="Password" required autocomplete="current-password">
    <button>Sign in</button>`, body => post('/api/login', body), done);
}
