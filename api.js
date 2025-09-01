// frontend/js/api.js
export function getApiBase() {
  if (!window.__PF_RUNTIME__?.API_BASE) {
    throw new Error("PF runtime not initialized: API_BASE missing");
  }
  return window.__PF_RUNTIME__.API_BASE.replace(/\/+$/, "");
}

export async function apiFetch(path, init = {}) {
  const url = `${getApiBase()}${path.startsWith("/") ? "" : "/"}${path}`;
  const headers = new Headers(init.headers || {});
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  // Add other common headers if needed (Authorization, X-Admin-Password, etc.)
  const resp = await fetch(url, { ...init, headers, credentials: "include", mode: "cors" });
  return resp;
}

// Legacy compatibility - expose globally for existing code
if (typeof window !== 'undefined') {
  window.apiFetch = apiFetch;
  window.getApiBase = getApiBase;
}
