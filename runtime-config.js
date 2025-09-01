// public/runtime-config.js
(() => {
  // Priority: 1) window.PF_API_BASE (injected by hosting), 2) <meta name="pf:apiBase">, 
  // 3) env-exposed var (NEXT_PUBLIC_API_BASE or VITE_API_BASE if injected at build), 
  // 4) localStorage override, 5) same-origin '/api' (for future proxy usage)
  const metaBase = document.querySelector('meta[name="pf:apiBase"]')?.content?.trim();
  const envBase = (window.NEXT_PUBLIC_API_BASE || window.VITE_API_BASE || "").trim();
  const lsBase  = (window.localStorage.getItem("PF_API_BASE") || "").trim();

  const pick = (...xs) => xs.find(v => v && /^https?:\/\//i.test(v));
  const API_BASE = pick(window.PF_API_BASE, metaBase, envBase, lsBase) 
                   || (location.origin + "/api"); // proxy-friendly default

  window.__PF_RUNTIME__ = Object.freeze({
    API_BASE
  });
})();
