
// Admin Activity & User sorting extensions
(function(){
  function fmtTs(ts){
    try { return new Date(ts).toLocaleString(); } catch(e){ return ts; }
  }
  async function fetchActivity(params={}){
    const usp = new URLSearchParams(params);
    const res = await fetch(`${window.adminApiUrl}/admin/activity?${usp.toString()}`, {headers:{'X-Admin-Password': window.__adminPassword || ''}});
    if(!res.ok) throw new Error("Failed to load activity");
    return await res.json();
  }

  // Render activity UI
  window.renderActivityPanel = async function(containerId){
    const root = document.getElementById(containerId);
    root.innerHTML = `
      <div class="glass-effect rounded-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-xl font-semibold text-white">Activity Log</h3>
          <div class="flex gap-2">
            <input id="actActor" placeholder="Actor" class="px-3 py-2 rounded bg-gray-800 text-sm">
            <input id="actAction" placeholder="Action" class="px-3 py-2 rounded bg-gray-800 text-sm">
            <input id="actSince" type="datetime-local" class="px-3 py-2 rounded bg-gray-800 text-sm">
            <input id="actUntil" type="datetime-local" class="px-3 py-2 rounded bg-gray-800 text-sm">
            <select id="actSort" class="px-3 py-2 rounded bg-gray-800 text-sm">
              <option value="desc">Newest first</option>
              <option value="asc">Oldest first</option>
            </select>
            <button id="actReload" class="btn-primary px-3 py-2 rounded text-white">Load</button>
          </div>
        </div>
        <div class="overflow-auto max-h-[60vh] border border-gray-700 rounded-lg">
          <table class="w-full text-sm">
            <thead class="bg-gray-800 sticky top-0">
              <tr>
                <th class="px-3 py-2 text-left">Time</th>
                <th class="px-3 py-2 text-left">Actor</th>
                <th class="px-3 py-2 text-left">Action</th>
                <th class="px-3 py-2 text-left">Details</th>
                <th class="px-3 py-2 text-left">IP</th>
              </tr>
            </thead>
            <tbody id="actRows" class="divide-y divide-gray-800"></tbody>
          </table>
        </div>
        <div class="flex items-center justify-between mt-3">
          <div id="actInfo" class="text-gray-400 text-xs"></div>
          <div class="flex gap-2">
            <button id="actPrev" class="px-3 py-1 rounded bg-gray-800">Prev</button>
            <button id="actNext" class="px-3 py-1 rounded bg-gray-800">Next</button>
          </div>
        </div>
      </div>
    `;
    let offset=0, limit=50, total=0;
    async function load(){
      const params = {
        limit, offset,
        actor: document.getElementById('actActor').value || '',
        action: document.getElementById('actAction').value || '',
        sort: document.getElementById('actSort').value || 'desc',
      };
      const sinceV = document.getElementById('actSince').value;
      const untilV = document.getElementById('actUntil').value;
      if(sinceV) params.since = new Date(sinceV).toISOString();
      if(untilV) params.until = new Date(untilV).toISOString();

      const data = await fetchActivity(params);
      total = data.total || 0;
      const rows = data.items || [];
      const tbody = document.getElementById('actRows');
      tbody.innerHTML = rows.map(r=>`
        <tr>
          <td class="px-3 py-2 whitespace-nowrap">${fmtTs(r.ts)}</td>
          <td class="px-3 py-2">${r.actor||''}</td>
          <td class="px-3 py-2">${r.action||''}</td>
          <td class="px-3 py-2 text-xs"><pre class="whitespace-pre-wrap">${JSON.stringify(r.details||{}, null, 2)}</pre></td>
          <td class="px-3 py-2">${r.ip||''}</td>
        </tr>
      `).join('');
      document.getElementById('actInfo').textContent = `Showing ${rows.length} / ${total} (offset ${offset})`;
    }
    document.getElementById('actReload').onclick = ()=>{ offset=0; load(); };
    document.getElementById('actPrev').onclick = ()=>{ offset=Math.max(0, offset-50); load(); };
    document.getElementById('actNext').onclick = ()=>{ offset=offset+50; if(offset>=total) offset=total-50; if(offset<0) offset=0; load(); };
    await load();
  }

  // User sorting helpers (if AdminPanel exposes loadUsers, we can intercept rendering via DOM)
  window.applyUserListSorting = function(){
    const sortSelect = document.getElementById('userSort');
    if(!sortSelect) return;
    sortSelect.addEventListener('change', ()=>{
      const val = sortSelect.value;
      const container = document.getElementById('usersContainer') || document;
      const cards = Array.from(container.querySelectorAll('[data-user-created]'));
      cards.sort((a,b)=>{
        const ta = Date.parse(a.getAttribute('data-user-created')||'')||0;
        const tb = Date.parse(b.getAttribute('data-user-created')||'' )||0;
        return val==='oldest' ? (ta-tb) : (tb-ta);
      });
      const list = container.querySelector('.user-list');
      if(list){
        list.innerHTML = '';
        cards.forEach(c=>list.appendChild(c));
      }
    });
  }
})();
// Public logging helper for admin UI actions
window.logActivity = async function(action, details){
  try {
    await fetch(`${window.adminApiUrl}/activity/log`, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({actor:'admin', action, details})
    });
  } catch(e){ /* ignore */ }
}
