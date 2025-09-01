// --- API base + fetch wrapper (robust) ---
;(function () {
  function getApiBase() {
    try {
      if (window.__PF_RUNTIME__?.API_BASE) return window.__PF_RUNTIME__.API_BASE.replace(/\/+$/, '');
      const meta = document.querySelector('meta[name="pf:apiBase"]');
      if (meta?.content) return meta.content.replace(/\/+$/, '');
    } catch (e) { /* ignore */ }
    return '';
  }

  const API_BASE = getApiBase();
  if (API_BASE) console.info('[PF] API base:', API_BASE);

  async function apiFetch(path, options = {}) {
    const url = (API_BASE || '') + (String(path).startsWith('/') ? path : '/' + path);
    const init = { credentials: "include", ...options };
    init.headers = {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    };
    const res = await fetch(url, init);
    return res;
  }

  try { window.API_BASE = API_BASE; } catch (e) {}
  try { window.apiFetch = apiFetch; } catch (e) {}
  try { window.PF_apiFetch = apiFetch; } catch (e) {}
  try { window.getApiBase = getApiBase; } catch (e) {}
  try {
    // Legacy global alias (best-effort)
    if (typeof apiFetch === 'undefined') {
      // eslint-disable-next-line no-global-assign
      apiFetch = window.apiFetch;
    }
  } catch (e) {}
})();
