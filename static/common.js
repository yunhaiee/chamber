// One browser tab can hold several signed-in frames, so each pane keeps its own session.
const TOKEN_KEY = 'counsel-token-' + (new URLSearchParams(location.search).get('pane') || 'main');
function token() { try { return sessionStorage.getItem(TOKEN_KEY) || ''; } catch { return ''; } }
function setToken(t) { try { sessionStorage.setItem(TOKEN_KEY, t); } catch {} }
function clearToken() { try { sessionStorage.removeItem(TOKEN_KEY); } catch {} }

async function api(path, opts = {}) {
  const headers = { ...(opts.body ? { 'content-type': 'application/json' } : {}), ...(token() ? { 'x-session': token() } : {}) };
  const res = await fetch(path, { ...opts, headers, credentials: 'include' });
  if (res.status === 401) { clearToken(); throw Object.assign(new Error('signin'), { signin: true }); }
  if (!res.ok) throw Object.assign(new Error(String(res.status)), { status: res.status });
  return res.headers.get('content-type')?.includes('json') ? res.json() : res.text();
}
const post = (path, body) => api(path, { method: 'POST', body: JSON.stringify(body || {}) });

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const tagged = s => esc(s).replace(/\[[A-Z]+_\d+\]/g, m => `<span class="tag">${m}</span>`);
const clock = ts => new Date(ts * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

async function signIn(root, pane, done) {
  if (token()) { try { await api('/api/me'); return done(); } catch (e) { if (!e.signin) throw e; } }
  if (pane) {
    try { const r = await post('/api/demo-login', { pane }); setToken(r.token); return done(); } catch {}
  }
  const people = await api('/api/people');
  root.innerHTML = `<form class="signin"><div class="eyebrow">Chamber</div>
    <select name="user">${people.map(p => `<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('')}</select>
    <input name="pin" type="password" inputmode="numeric" placeholder="PIN" autofocus>
    <button>Sign in</button><div class="fail" id="err"></div></form>`;
  root.querySelector('form').onsubmit = async ev => {
    ev.preventDefault();
    const f = new FormData(ev.target);
    try { const r = await post('/api/login', { user: f.get('user'), pin: f.get('pin') }); setToken(r.token); done(); }
    catch { root.querySelector('#err').textContent = 'Wrong name or PIN'; }
  };
}
