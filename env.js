(function(){
  'use strict';

  // ---- Config ----
  var CF_RE = /^https:\/\/[^/]*cloudfunctions\.net\/pfsystem-api(\/|$)/i;
  var LEGACY_REWRITES = {
    '/login': '/v1/login',
    '/register': '/v1/register',
    '/generate-script': '/v1/generate-script',
    '/projects': '/v1/projects',
    '/plans': '/v1/plans'
  };

  function normalizeBase(input) {
    var base = (typeof input === 'string' && input.trim()) ? input.trim() : "";
    if (CF_RE.test(base)) base = "";
    if (base.endsWith('/')) base = base.slice(0, -1);
    return base;
  }

  // Get API base from runtime-config.js if available
  var BASE = "";
  try {
    if (window.__PF_RUNTIME__?.API_BASE) {
      BASE = window.__PF_RUNTIME__.API_BASE.replace(/\/+$/, "");
    } else if (window.PF_API_BASE) {
      BASE = normalizeBase(window.PF_API_BASE);
    }
  } catch (e) {
    console.warn("[PF][env] Could not resolve API base:", e.message);
  }

  // public
  window.PF_API_BASE = BASE;

  // ---- core url rewriter ----
  function rewriteUrl(u) {
    try {
      if (!u) return u;

      // If Request object
      if (typeof Request !== 'undefined' && u instanceof Request) {
        var nurl = rewriteUrl(u.url);
        return (nurl !== u.url) ? new Request(nurl, u) : u;
      }

      // String URL
      if (typeof u === 'string') {
        // 1) Force Cloud Functions -> Cloud Run
        if (CF_RE.test(u)) u = u.replace(CF_RE, BASE + '/');

        // 2) Absolute or relative handling
        var abs = null;
        try { abs = new URL(u, BASE); } catch(_) {}

        var path = abs ? abs.pathname : (u.startsWith('/') ? u : '');

        // 3) Legacy -> v1 mapping
        if (path && LEGACY_REWRITES[path]) {
          var mapped = LEGACY_REWRITES[path];
          if (abs) {
            u = BASE + mapped + (abs.search || '') + (abs.hash || '');
          } else {
            u = BASE + mapped;
          }
        }

        // 4) Leading-slash relative -> attach to base
        if (u.startsWith('/')) u = BASE + u;

        return u;
      }
    } catch(_){}
    return u;
  }

  // ---- fetch hook ----
  try {
    if (typeof window.fetch === 'function') {
      var _fetch = window.fetch.bind(window);
      window.fetch = function(input, init){
        return _fetch(rewriteUrl(input), init);
      };
    }
  } catch(_){}

  // ---- axios hook (if axios is present later) ----
  try {
    var hookAxios = function(ax){
      if (!ax || !ax.interceptors || !ax.interceptors.request) return;
      ax.interceptors.request.use(function(cfg){
        try {
          if (cfg && typeof cfg.url === 'string') {
            cfg.url = rewriteUrl(cfg.url);
          }
        } catch(_){}
        return cfg;
      });
    };
    if (window.axios) hookAxios(window.axios);
    // also hook future axios assignment
    Object.defineProperty(window, 'axios', {
      configurable: true,
      enumerable: true,
      set: function(v){ hookAxios(v); this._axios = v; },
      get: function(){ return this._axios; }
    });
  } catch(_){}

  // ---- XHR hook (for libraries using raw XHR) ----
  try {
    if (window.XMLHttpRequest) {
      var _open = XMLHttpRequest.prototype.open;
      XMLHttpRequest.prototype.open = function(method, url){
        try { url = rewriteUrl(url); } catch(_){}
        return _open.apply(this, [method, url].concat([].slice.call(arguments, 2)));
      };
    }
  } catch(_){}

})();