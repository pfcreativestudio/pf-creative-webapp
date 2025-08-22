// admin-activity.js
// 活动日志模块：仅使用内存中的 window.__adminPassword，不持久化；日期转换、空筛选不传参、分页

(function(){
  const apiUrl = window.adminApiUrl;
  const tbody = document.getElementById('activityTbody');
  const loadBtn = document.getElementById('loadActivityBtn');
  const prevBtn = document.getElementById('prevPageBtn');
  const nextBtn = document.getElementById('nextPageBtn');

  const actorInput = document.getElementById('actorInput');
  const actionInput = document.getElementById('actionInput');
  const sinceInput = document.getElementById('sinceInput');
  const untilInput = document.getElementById('untilInput');
  const sortSelect = document.getElementById('sortSelect');

  let offset = 0;
  const limit = 50;
  let lastFetched = 0;

  function toISO(raw){
    if(!raw) return null;
    // 支持: "dd/mm/yyyy" 或 "dd/mm/yyyy HH:mm"
    const m = raw.match(/^(\d{2})\/(\d{2})\/(\d{4})(?:\s+(\d{2}):(\d{2}))?$/);
    if(!m) return null;
    const [_, dd, mm, yyyy, HH='00', MM='00'] = m;
    const d = new Date(`${yyyy}-${mm}-${dd}T${HH}:${MM}:00Z`);
    return isNaN(d.getTime()) ? null : d.toISOString();
  }

  function renderRows(items){
    tbody.innerHTML = '';
    if(!items || !items.length){
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 6;
      td.className = 'muted';
      td.textContent = 'No activities.';
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    items.forEach(it=>{
      const tr = document.createElement('tr');
      const tdTs = document.createElement('td');
      const tdActor = document.createElement('td');
      const tdAction = document.createElement('td');
      const tdDetails = document.createElement('td');
      const tdIp = document.createElement('td');
      const tdUa = document.createElement('td');

      tdTs.textContent = it.ts ? it.ts.replace('T',' ').substring(0,19) : '';
      tdActor.textContent = it.actor || '';
      tdAction.textContent = it.action || '';
      tdDetails.textContent = typeof it.details === 'object' ? JSON.stringify(it.details) : (it.details || '');
      tdIp.textContent = it.ip || '';
      tdUa.textContent = it.user_agent || '';

      tr.append(tdTs, tdActor, tdAction, tdDetails, tdIp, tdUa);
      tbody.appendChild(tr);
    });
  }

  async function fetchActivity(reset=false){
    try{
      if(reset){ offset = 0; }

      const adminPw = window.__adminPassword || '';
      if(!adminPw) throw new Error('Missing admin password');

      const params = new URLSearchParams();
      const actor = (actorInput.value || '').trim();
      const action = (actionInput.value || '').trim();
      const sinceISO = toISO((sinceInput.value||'').trim());
      const untilISO = toISO((untilInput.value||'').trim());
      const sort = sortSelect.value || 'desc';

      if(actor) params.set('actor', actor);
      if(action) params.set('action', action);
      if(sinceISO) params.set('since', sinceISO);
      if(untilISO) params.set('until', untilISO);
      params.set('sort', sort);
      params.set('limit', String(limit));
      params.set('offset', String(offset));

      const res = await fetch(`${apiUrl}/admin/activity?${params.toString()}`, {
        method: 'GET',
        headers: { 'X-Admin-Password': adminPw }
      });

      if(!res.ok){
        const txt = await res.text().catch(()=> '');
        throw new Error(`Activity load failed: ${res.status} ${txt}`);
      }

      const data = await res.json();
      lastFetched = (data.items || []).length;
      renderRows(data.items || []);
    }catch(err){
      console.error(err);
      renderRows([]); // 显示空态
    }
  }

  // expose for other scripts
  window.PFActivity = { fetchActivity };

  // events
  loadBtn.addEventListener('click', ()=> fetchActivity(true));
  prevBtn.addEventListener('click', ()=>{
    offset = Math.max(0, offset - limit);
    fetchActivity(false);
  });
  nextBtn.addEventListener('click', ()=>{
    if(lastFetched < limit) return;
    offset += limit;
    fetchActivity(false);
  });
})();
