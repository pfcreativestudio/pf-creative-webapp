// public/runtime-config.js
(() => {
  function readMetaBase() {
    try {
      const el = document.querySelector('meta[name="pf:apiBase"]');
      const v = (el && el.content ? el.content : '').trim();
      return v && /^https?:\/\//i.test(v) ? v.replace(/\/+$/, '') : '';
    } catch { return ''; }
  }

  function readEnvBase() {
    try {
      const v = (window.NEXT_PUBLIC_API_BASE || window.VITE_API_BASE || '').trim();
      return v && /^https?:\/\//i.test(v) ? v.replace(/\/+$/, '') : '';
    } catch { return ''; }
  }

  const metaBase = readMetaBase();
  const envBase = readEnvBase();
  let API_BASE = metaBase || envBase;

  if (!API_BASE) {
    const host = (location.hostname || '').toLowerCase();
    const isProdHost = /vercel\.app$/.test(host) || /\./.test(host);
    if (isProdHost) {
      console.error('[PF][env] No pf:apiBase meta found; refusing to use same-origin /api on production.');
      try { window.__PF_API_RESOLUTION_ERROR = true; } catch {}
    } else {
      try { window.__PF_API_RESOLUTION_ERROR = true; } catch {}
    }
  }

  if (API_BASE) {
    try { console.info('[PF] API base:', API_BASE); } catch {}
  }

  try {
    window.__PF_RUNTIME__ = Object.freeze({ API_BASE });
  } catch {}
})();
