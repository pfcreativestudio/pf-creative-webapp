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

  // Project ID management functions
  async function ensureProjectId() {
    let projectId = localStorage.getItem('pf_project_id');
    if (projectId) return projectId;
    
    try {
      // Try to get recent project
      const projects = await apiJson('/v1/projects?recent=1');
      if (projects && projects.length > 0) {
        projectId = projects[0].id;
        localStorage.setItem('pf_project_id', projectId);
        return projectId;
      }
      
      // Create new project if none found
      const newProject = await apiJson('/v1/projects', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({title: 'Untitled', source: 'chatroom'})
      });
      
      if (newProject && newProject.id) {
        projectId = newProject.id;
        localStorage.setItem('pf_project_id', projectId);
        return projectId;
      }
    } catch (e) {
      console.warn('[PF] Failed to ensure project ID:', e);
    }
    
    // Fallback to generated ID
    projectId = 'proj_' + Date.now();
    localStorage.setItem('pf_project_id', projectId);
    return projectId;
  }
  
  function clearProjectId() {
    localStorage.removeItem('pf_project_id');
  }

  // Safe JSON helper for CORS failures
  async function apiJson(url, init) {
    const res = await apiFetch(url, init);
    const ct = (res.headers.get('content-type')||'').toLowerCase();
    if (!res.ok) throw new Error('HTTP '+res.status);
    if (!ct.includes('application/json')) return null;
    return await res.json();
  }

  try { window.API_BASE = API_BASE; } catch (e) {}
  try { window.apiFetch = apiFetch; } catch (e) {}
  try { window.PF_apiFetch = apiFetch; } catch (e) {}
  try { window.getApiBase = getApiBase; } catch (e) {}
  try { window.ensureProjectId = ensureProjectId; } catch (e) {}
  try { window.clearProjectId = clearProjectId; } catch (e) {}
  try { window.apiJson = apiJson; } catch (e) {}
  try {
    // Legacy global alias (best-effort)
    if (typeof apiFetch === 'undefined') {
      // eslint-disable-next-line no-global-assign
      apiFetch = window.apiFetch;
    }
  } catch (e) {}
})();
