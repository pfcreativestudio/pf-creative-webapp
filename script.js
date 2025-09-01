// PF Creative WebApp - Script Generator Logic (clean rebuild)
// This file replaces a corrupted version that contained literal "..." and invalid syntax.
// It is designed to be defensive: it will not throw if elements are missing.

(function(){
  'use strict';

  // ---------- Backend base resolution ----------
  // Get API base from runtime-config.js if available
  var BACKEND_URL = "";
  try {
    if (window.__PF_RUNTIME__?.API_BASE) {
      BACKEND_URL = window.__PF_RUNTIME__.API_BASE.replace(/\/+$/, "");
    } else if (window.PF_API_BASE) {
      BACKEND_URL = window.PF_API_BASE.trim();
    }
  } catch (e) {
    console.warn("[PF][script] Could not resolve API base:", e.message);
  }

  if (BACKEND_URL.endsWith('/')) BACKEND_URL = BACKEND_URL.slice(0, -1);
  try { window.PF_BACKEND_URL = BACKEND_URL; } catch(e) {}

  function buildUrl(path){
    path = String(path || '');
    if (path.startsWith('/')) return BACKEND_URL + path;
    return BACKEND_URL + '/' + path;
  }

  function getToken(){
    try { return localStorage.getItem('jwtToken') || ''; } catch(e){ return ''; }
  }

  function authHeaders(){
    var t = getToken();
    return t ? { 'Authorization': 'Bearer ' + t } : {};
  }

  async function apiFetch(path, options){
    options = options || {};
    var headers = Object.assign({ 'Content-Type': 'application/json' }, options.headers || {}, authHeaders());
    var final = Object.assign({}, options, { headers: headers });
    var res = await fetch(buildUrl(path), final);
    return res;
  }

  // ---------- DOM bindings (optional / safe) ----------
  document.addEventListener('DOMContentLoaded', function(){
    var generateBtn = document.getElementById('generateBtn');
    var copyBtn = document.getElementById('copyBtn');
    var resultDiv = document.getElementById('result');
    var resultContainer = document.getElementById('result-container') || document.getElementById('resultContainer');
    var loadingDiv = document.getElementById('loading');

    function setLoading(on){
      if (!loadingDiv) return;
      if (on) loadingDiv.classList.remove('hidden');
      else loadingDiv.classList.add('hidden');
    }

    function showResult(text){
      if (!resultDiv) return;
      if (resultContainer && resultContainer.classList) resultContainer.classList.remove('hidden');
      resultDiv.textContent = String(text || '');
    }

    if (generateBtn){
      generateBtn.addEventListener('click', async function(){
        var token = getToken();
        if (!token){
          alert('Please log in first.');
          return;
        }

        var brandName = (document.getElementById('brandName') || {}).value || '';
        var productName = (document.getElementById('productName') || {}).value || '';
        var targetAudience = (document.getElementById('targetAudience') || {}).value || '';
        var duration = (document.getElementById('duration') || {}).value || '';

        // Basic guard but allow empty to still test connectivity
        // (real validation should be done server-side as well)
        setLoading(true);
        if (generateBtn){ generateBtn.disabled = true; generateBtn.textContent = 'Generating...'; }

        try{
          var payload = {
            brand_name: brandName,
            product_name: productName,
            target_audience: targetAudience,
            duration: duration
          };

          // Try the newer endpoint first
          var res = await apiFetch('/v1/director/veo-3-prompt', {
            method: 'POST',
            body: JSON.stringify(payload)
          });

          // If not found, try legacy spelling
          if (res.status === 404){
            res = await apiFetch('/v1/director/veo3-prompt', {
              method: 'POST',
              body: JSON.stringify(payload)
            });
          }

          // As a last resort, prove connectivity by listing projects
          if (res.status === 404){
            res = await apiFetch('/v1/projects', { method: 'GET' });
          }

          var text = '';
          if (res.ok){
            var data = null;
            try { data = await res.json(); } catch(_){ /* ignore */ }
            if (data && typeof data.veo3_prompt === 'string') text = data.veo3_prompt;
            else if (data && typeof data.prompt === 'string') text = data.prompt;
            else text = JSON.stringify(data, null, 2);
          }else{
            var errText = await res.text().catch(function(){ return ''; });
            text = 'HTTP ' + res.status + '\n' + errText;
          }
          showResult(text);

        }catch(err){
          showResult('Error: ' + (err && err.message ? err.message : String(err)));
        }finally{
          setLoading(false);
          if (generateBtn){ generateBtn.disabled = false; generateBtn.textContent = '🚀 Generate My Veo 3 Script'; }
        }
      });
    }

    if (copyBtn){
      copyBtn.addEventListener('click', function(){
        if (!resultDiv) return;
        var text = resultDiv.textContent || '';
        if (navigator.clipboard && navigator.clipboard.writeText){
          navigator.clipboard.writeText(text).then(function(){
            copyBtn.textContent = 'Copied!';
            setTimeout(function(){ copyBtn.textContent = '📋 Copy Script'; }, 2000);
          }).catch(function(){
            alert('Copy failed.');
          });
        }else{
          // Fallback
          var ta = document.createElement('textarea');
          ta.value = text;
          document.body.appendChild(ta);
          ta.select();
          try { document.execCommand('copy'); } catch(e) {}
          document.body.removeChild(ta);
          copyBtn.textContent = 'Copied!';
          setTimeout(function(){ copyBtn.textContent = '📋 Copy Script'; }, 2000);
        }
      });
    }

    try { console.log('[PF][script] Using backend =', BACKEND_URL); } catch(e){}
  });
})();
