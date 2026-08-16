const CATS = {
  kultura:  {label:'Kultura',            color:'var(--teal)'},
  sport:    {label:'Sport',              color:'var(--amber)'},
  dzieci:   {label:'Dzieci i rodzina',   color:'var(--plum)'},
  historia: {label:'Historia i tradycja',color:'var(--wood)'},
  samorzad: {label:'Samorząd',           color:'var(--slate)'}
};

// Update these two if you fork / rename the repo.
const GITHUB_OWNER = 'extraterestra';
const GITHUB_REPO  = 'rabka-wydarzenia-kalendarz';
const MANUAL_FILE_EDIT_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/edit/main/data/events-manual.json`;

let events = [];
let activeCats = new Set(Object.keys(CATS));
let viewYear, viewMonth, selectedDateStr = null;

const $ = sel => document.querySelector(sel);
const pad = n => String(n).padStart(2,'0');
const dstr = (y,m,d) => `${y}-${pad(m+1)}-${pad(d)}`;
const todayStr = (()=>{const t=new Date();return dstr(t.getFullYear(),t.getMonth(),t.getDate());})();

async function loadEvents(){
  const [autoRes, cksipRes, vmRes, manualRes] = await Promise.all([
    fetch('data/events-auto.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-cksip.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-visitmalopolska.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-manual.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]}))
  ]);
  const auto = (autoRes.events||[]).map(e => ({...e, source:'Urząd Miejski'}));
  const cksip = (cksipRes.events||[]).map(e => ({...e, source:'CKSiP'}));
  const vm = (vmRes.events||[]).map(e => ({...e, source:'VisitMałopolska'}));
  const manual = (manualRes.events||[]).filter(e => !e.id?.startsWith('manual-1') || e.title.indexOf('Przykładowe') === -1)
    .map(e => ({...e, source:'Fundacja'}));

  // de-dupe across sources: same title + same start date -> keep first occurrence
  const seen = new Set();
  events = [...auto, ...cksip, ...vm, ...manual].filter(e => {
    const key = (e.title||'').trim().toLowerCase() + '|' + e.start;
    if(seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function eventsOnDay(dateStr){
  return events.filter(e => dateStr >= e.start && dateStr <= (e.end || e.start));
}
function upcomingEvents(){
  return events.filter(e => (e.end || e.start) >= todayStr)
    .sort((a,b)=> a.start.localeCompare(b.start)).slice(0,6);
}

function renderFilters(){
  const box = $('#filters'); box.innerHTML = '';
  Object.entries(CATS).forEach(([key,c])=>{
    const chip = document.createElement('div');
    chip.className = 'chip' + (activeCats.has(key)?' active':'');
    chip.innerHTML = `<span class="dot" style="background:${c.color}"></span>${c.label}`;
    chip.onclick = () => {
      if(activeCats.has(key)) activeCats.delete(key); else activeCats.add(key);
      renderFilters(); renderCalendar(); renderAgenda(); renderUpcoming();
    };
    box.appendChild(chip);
  });
}

function renderCalendar(){
  const first = new Date(viewYear, viewMonth, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(viewYear, viewMonth+1, 0).getDate();
  const monthNames = ['Styczeń','Luty','Marzec','Kwiecień','Maj','Czerwiec','Lipiec','Sierpień','Wrzesień','Październik','Listopad','Grudzień'];
  $('#monthLabel').textContent = `${monthNames[viewMonth]} ${viewYear}`;

  const grid = $('#days'); grid.innerHTML = '';
  for(let i=0;i<startOffset;i++){
    const filler = document.createElement('div'); filler.className='day muted';
    grid.appendChild(filler);
  }
  for(let d=1; d<=daysInMonth; d++){
    const ds = dstr(viewYear, viewMonth, d);
    const cell = document.createElement('div');
    cell.className = 'day' + (ds===todayStr?' today':'') + (ds===selectedDateStr?' selected':'');
    const dayEvents = eventsOnDay(ds).filter(e=>activeCats.has(e.category));
    cell.innerHTML = `<span>${d}</span><div class="dots">${dayEvents.slice(0,4).map(e=>`<span style="background:${CATS[e.category].color}"></span>`).join('')}</div>`;
    cell.onclick = () => { selectedDateStr = ds; renderCalendar(); renderAgenda(); };
    grid.appendChild(cell);
  }
}

function eventItemHTML(e){
  const c = CATS[e.category] || CATS.kultura;
  const dateLabel = e.start === e.end || !e.end ? formatDate(e.start) : `${formatDate(e.start)} – ${formatDate(e.end)}`;
  return `<div class="event-item" style="border-color:${c.color}">
    <div class="cat" style="color:${c.color}">${c.label}</div>
    <div class="title">${escapeHtml(e.title)}</div>
    <div class="meta">${dateLabel}${e.time?` · ${escapeHtml(e.time)}`:''}${e.location?` · ${escapeHtml(e.location)}`:''}</div>
    ${e.desc?`<div class="desc">${escapeHtml(e.desc)}</div>`:''}
    <span class="src-tag">${escapeHtml(e.source||'Fundacja')}</span>
  </div>`;
}
function formatDate(ds){
  const [y,m,d] = ds.split('-');
  const months=['sty','lut','mar','kwi','maj','cze','lip','sie','wrz','paź','lis','gru'];
  return `${parseInt(d)} ${months[parseInt(m)-1]}`;
}
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

function renderAgenda(){
  const title = $('#agendaTitle'); const list = $('#agendaList');
  if(!selectedDateStr){ title.textContent = 'Wybierz dzień'; list.innerHTML = '<div class="empty">Kliknij dzień w kalendarzu, aby zobaczyć wydarzenia.</div>'; return; }
  const items = eventsOnDay(selectedDateStr).filter(e=>activeCats.has(e.category));
  title.textContent = formatDate(selectedDateStr) + ' ' + viewYear;
  list.innerHTML = items.length ? items.map(eventItemHTML).join('') : '<div class="empty">Brak wydarzeń tego dnia.</div>';
}

function renderUpcoming(){
  const list = $('#upcomingList');
  const items = upcomingEvents().filter(e=>activeCats.has(e.category));
  list.innerHTML = items.length ? items.map(eventItemHTML).join('') : '<div class="empty">Brak nadchodzących wydarzeń w wybranych kategoriach.</div>';
}

$('#prevMonth').onclick = () => { viewMonth--; if(viewMonth<0){viewMonth=11;viewYear--;} renderCalendar(); };
$('#nextMonth').onclick = () => { viewMonth++; if(viewMonth>11){viewMonth=0;viewYear++;} renderCalendar(); };

$('#openAdd').onclick = () => $('#overlay').classList.add('open');
$('#cancelAdd').onclick = () => { $('#overlay').classList.remove('open'); $('#snippetBox').style.display='none'; };
$('#overlay').onclick = (e) => { if(e.target.id==='overlay'){ $('#overlay').classList.remove('open'); $('#snippetBox').style.display='none'; } };

$('#generateSnippet').onclick = () => {
  const title = $('#f-title').value.trim();
  const start = $('#f-start').value;
  if(!title || !start){ alert('Podaj przynajmniej nazwę i datę początku.'); return; }
  const newEvent = {
    id: 'manual-' + Date.now(),
    title,
    category: $('#f-category').value,
    start,
    end: $('#f-end').value || start,
    time: $('#f-time').value.trim(),
    location: $('#f-location').value.trim(),
    desc: $('#f-desc').value.trim()
  };
  $('#snippetCode').textContent = JSON.stringify(newEvent, null, 2) + ',';
  $('#snippetBox').style.display = 'block';
  $('#editLink').href = MANUAL_FILE_EDIT_URL;
};

(async function init(){
  const t = new Date();
  viewYear = t.getFullYear(); viewMonth = t.getMonth();
  await loadEvents();
  renderFilters();
  renderCalendar();
  renderUpcoming();
  renderAgenda();
})();
