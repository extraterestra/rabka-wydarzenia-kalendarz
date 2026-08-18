const CATS = {
  kultura:   {label:'Kultura',             color:'var(--teal)'},
  rozrywka:  {label:'Rozrywka',            color:'var(--plum)'},
  sport:     {label:'Sport',               color:'var(--amber)'},
  dzieci:    {label:'Dzieci i rodzina',    color:'var(--wood)'},
  historia:  {label:'Historia i tradycja', color:'#8B6B4A'},
  samorzad:  {label:'Samorząd',            color:'var(--slate)'}
};

const SOURCE_KEYS = ['Urząd Miejski', 'CKSiP', 'Rabcio', 'Fundacja'];

const SOURCE_HOME = {
  'Urząd Miejski': 'https://rabka.pl/kalendarz-wydarzen/',
  'CKSiP': 'https://centrum-kultury.rabka.pl/kalendarz',
  'Rabcio': 'https://teatr.rabcio.pl/repertuar-2025/',
  'Fundacja': 'https://frrr.pl/'
};

// Update these two if you fork / rename the repo.
const GITHUB_OWNER = 'extraterestra';
const GITHUB_REPO  = 'rabka-wydarzenia-kalendarz';
const MANUAL_FILE_EDIT_URL = `https://github.com/${GITHUB_OWNER}/${GITHUB_REPO}/edit/main/data/events-manual.json`;

let allEvents = [];
let activeCats = new Set(Object.keys(CATS));
let activeSources = new Set(SOURCE_KEYS);
let viewYear, viewMonth, selectedDateStr = null;

const $ = sel => document.querySelector(sel);
const pad = n => String(n).padStart(2,'0');
const dstr = (y,m,d) => `${y}-${pad(m+1)}-${pad(d)}`;
const todayStr = (()=>{const t=new Date();return dstr(t.getFullYear(),t.getMonth(),t.getDate());})();

const URL_IN_TEXT_RE = /https?:\/\/[^\s<>"']+/i;
const TIME_IN_TEXT_RE = /(?:godz\.?|g\.)\s*(\d{1,2}[:.]\d{2})/i;

function firstUrlInText(text){
  const m = String(text||'').match(URL_IN_TEXT_RE);
  return m ? m[0] : '';
}
function firstTimeInText(text){
  const m = String(text||'').match(TIME_IN_TEXT_RE);
  return m ? m[1].replace('.', ':') : '';
}
function isPlausibleEvent(title, desc){
  const t = String(title||'').replace(/\u00a0/g,' ').replace(/\s+/g,' ').trim().replace(/^[.\s]+|[.\s]+$/g,'');
  if(t.length < 4) return false;

  const first = [...t].find(ch => /\p{L}|\d/u.test(ch));
  if(!first) return false;
  if(/\p{L}/u.test(first) && first !== first.toUpperCase() && !/[IVXLCDM]/.test(first)) return false;

  const months = 'stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia';
  const dateFragment = new RegExp(
    `^(?:\\d{1,2}\\s*(?:i|oraz|,|-|–|do|/)\\s*)+\\d{0,2}(?:\\s+(?:${months}))?(?:\\s*(?:i|oraz|,|-|–|do)\\s*\\d{0,2})*\\s*$`,
    'i'
  );
  if(dateFragment.test(t)) return false;

  const letters = (t.match(/\p{L}/gu) || []).length;
  const digits = (t.match(/\d/g) || []).length;
  if(letters < 4 || digits > letters) return false;
  if(/\b(?:już|od|oraz|natomiast|się|który|która|które|którym)\s*$/i.test(t)) return false;
  if(/(?:\s|^)(?:a|i|w|na|do|,)\s*$/i.test(t)) return false;
  if(/[,–-]$/.test(t)) return false;
  if(/^(już\s+od|gotowano|urmistrz|tradycyjnie|publiczność|amfiteatr stanie|odbędzie się|tego samego|dzi[sś]\b|nie był|jednym z|miłośnicy|prawdziwie|najmłodsi|sportowe zakończenie|pod koniec|na scenie|iwona gal)\b/i.test(t)) return false;
  // case-sensitive mid-word leftovers only (do not use /i — Roman numerals like XXXIII)
  if(/^[a-ząćęłńóśźż]{1,4}-?[A-ZĄĆĘŁŃÓŚŹŻ]/.test(t)) return false;

  const monthHits = (t.match(new RegExp(months, 'gi')) || []).length;
  if(monthHits && digits >= 2 && letters < 18) return false;

  const words = t.split(/\s+/);
  if(words.length >= 12 && !/[!?:]/.test(t) && /\b(odbędzie|odbyło|zapowiada|przyniesie|porwie|wystąpi|znajdą)\b/i.test(t)) return false;
  return true;
}

function enrichEvent(e, sourceLabel, fileMeta){
  const desc = e.desc || '';
  const url = e.url || firstUrlInText(desc) || fileMeta?.ticket_source || fileMeta?.source || SOURCE_HOME[sourceLabel] || '';
  const time = e.time || firstTimeInText(desc) || '';
  const cleanDesc = desc.replace(URL_IN_TEXT_RE, '').replace(/\s{2,}/g, ' ').replace(/\s*\.\s*$/, '.').trim();
  const category = guessCategory(e.title || '', cleanDesc, e.category);
  return {...e, source: sourceLabel, url, time, desc: cleanDesc, category};
}

function guessCategory(title, desc, fallback){
  const noise = /centrum\s+kultury,?\s+sportu\s+i\s+promocji|\bcksip\b/gi;
  const titleL = String(title||'').toLowerCase().replace(noise, ' ');
  const descL = String(desc||'').toLowerCase().replace(noise, ' ');
    const rules = [
    ['samorzad', [/\bsesj[aei]/i, /rady\s+miejsk/i, /rada\s+miejsk/i, /\burz[aą]d\b/i, /\buchwał/i, /\bkonsultacj/i, /\bburmistrz/i]],
    ['historia', [/\bpamięc/i, /\bpamięt/i, /\bholocaust/i, /\bmuze/i, /\bhistori(?!czn)/i, /\btradycj/i, /architektur[ay]\s+drewnian/i, /spacer\s+pamięci/i, /\bredyk\b/i]],
    ['sport', [/\bbike\b/i, /\brower/i, /\bbieg/i, /\bpuchar/i, /\bzawody\b/i, /\bturniej/i, /kalisten/i, /\blifting\b/i, /street\s+workout/i, /\bmecz\b/i, /\bwyścig/i, /\btour\b/i, /\bmma\b/i, /highlander/i, /sportow/i, /\bkolarsk/i, /\bszachy\b/i, /\bszachow/i]],
    ['dzieci', [/\bdzieck/i, /\bdzieci/i, /\brodzin/i, /\bprzedszkol/i, /\bmaluch/i, /tydzie[nń]\s+bardzo\s+małego/i, /\bspektakl/i, /\blalk/i, /teatr\s+lalek/i, /pch[lł]a\s+szachrajka/i]],
    ['rozrywka', [/\bkabaret/i, /\bkoncert/i, /stand[\s-]?up/i, /\brozrywk/i, /\bdisco\b/i, /\bbaciary\b/i, /\bimprez/i, /\bdyskotek/i, /jubileuszow\w*\s+program/i]]
  ];
  for(const text of [titleL, `${titleL} ${descL}`]){
    for(const [cat, patterns] of rules){
      if(patterns.some(re => re.test(text))) return cat;
    }
  }
  return (fallback && CATS[fallback]) ? fallback : 'kultura';
}

async function loadEvents(){
  const [autoRes, cksipRes, rabcioRes, manualRes] = await Promise.all([
    fetch('data/events-auto.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-cksip.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-rabcio.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]})),
    fetch('data/events-manual.json').then(r=>r.ok?r.json():{events:[]}).catch(()=>({events:[]}))
  ]);
  const auto = (autoRes.events||[]).map(e => enrichEvent(e, 'Urząd Miejski', autoRes)).filter(e => isPlausibleEvent(e.title, e.desc));
  const cksip = (cksipRes.events||[]).map(e => enrichEvent(e, 'CKSiP', cksipRes)).filter(e => isPlausibleEvent(e.title, e.desc));
  const rabcio = (rabcioRes.events||[]).map(e => enrichEvent(e, 'Rabcio', rabcioRes)).filter(e => isPlausibleEvent(e.title, e.desc));
  const manual = (manualRes.events||[])
    .filter(e => !e.id?.startsWith('manual-1') || e.title.indexOf('Przykładowe') === -1)
    .map(e => enrichEvent(e, 'Fundacja', manualRes))
    .filter(e => isPlausibleEvent(e.title, e.desc));

  // Keep all sources; de-dupe only among currently visible sources.
  allEvents = [...auto, ...cksip, ...rabcio, ...manual];
}

function visibleEvents(){
  const filtered = allEvents.filter(e =>
    activeSources.has(e.source) && activeCats.has(e.category)
  );
  const seen = new Set();
  return filtered.filter(e => {
    const key = (e.title||'').trim().toLowerCase() + '|' + e.start;
    if(seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function eventsOnDay(dateStr){
  return visibleEvents().filter(e => dateStr >= e.start && dateStr <= (e.end || e.start));
}
function upcomingEvents(){
  return visibleEvents().filter(e => (e.end || e.start) >= todayStr)
    .sort((a,b)=> a.start.localeCompare(b.start)).slice(0,6);
}

function syncSourceFiltersFromUI(){
  activeSources = new Set(
    [...document.querySelectorAll('#sourceFilters input[name="source"]:checked')]
      .map(el => el.value)
  );
}

function bindSourceFilters(){
  document.querySelectorAll('#sourceFilters input[name="source"]').forEach(input => {
    input.addEventListener('change', () => {
      syncSourceFiltersFromUI();
      renderCalendar();
      renderAgenda();
      renderUpcoming();
    });
  });
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
    const dayEvents = eventsOnDay(ds);
    cell.innerHTML = `<span>${d}</span><div class="dots">${dayEvents.slice(0,4).map(e=>`<span style="background:${(CATS[e.category]||CATS.kultura).color}"></span>`).join('')}</div>`;
    cell.onclick = () => { selectedDateStr = ds; renderCalendar(); renderAgenda(); };
    grid.appendChild(cell);
  }
}

function eventItemHTML(e){
  const c = CATS[e.category] || CATS.kultura;
  const dateLabel = e.start
    ? (e.start === e.end || !e.end ? formatDate(e.start) : `${formatDate(e.start)} – ${formatDate(e.end)}`)
    : '';
  const details = [];
  if(dateLabel) details.push(`<div class="detail"><span class="detail-label">Data:</span> ${escapeHtml(dateLabel)}</div>`);
  if(e.time) details.push(`<div class="detail"><span class="detail-label">Godzina:</span> ${escapeHtml(e.time)}</div>`);
  if(e.location) details.push(`<div class="detail"><span class="detail-label">Miejsce:</span> ${escapeHtml(e.location)}</div>`);
  if(e.url) details.push(`<div class="detail"><span class="detail-label">Źródło:</span> <a class="src-link" href="${escapeAttr(e.url)}" target="_blank" rel="noopener">${escapeHtml(e.source || 'otwórz')}</a></div>`);

  return `<div class="event-item" style="border-color:${c.color}">
    <div class="cat" style="color:${c.color}">${c.label}</div>
    <div class="title">${escapeHtml(e.title)}</div>
    ${details.length ? `<div class="details">${details.join('')}</div>` : ''}
    ${e.desc?`<div class="desc">${escapeHtml(e.desc)}</div>`:''}
    <span class="src-tag">${escapeHtml(e.source||'Fundacja')}</span>
  </div>`;
}
function formatDate(ds, withYear=true){
  const [y,m,d] = ds.split('-');
  const months=['sty','lut','mar','kwi','maj','cze','lip','sie','wrz','paź','lis','gru'];
  const base = `${parseInt(d)} ${months[parseInt(m)-1]}`;
  return withYear ? `${base} ${y}` : base;
}
function escapeHtml(s){
  return String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function escapeAttr(s){
  return escapeHtml(s).replace(/`/g, '&#96;');
}

function renderAgenda(){
  const title = $('#agendaTitle'); const list = $('#agendaList');
  if(!selectedDateStr){ title.textContent = 'Wybierz dzień'; list.innerHTML = '<div class="empty">Kliknij dzień w kalendarzu, aby zobaczyć wydarzenia.</div>'; return; }
  const items = eventsOnDay(selectedDateStr);
  title.textContent = formatDate(selectedDateStr, false) + ' ' + viewYear;
  list.innerHTML = items.length ? items.map(eventItemHTML).join('') : '<div class="empty">Brak wydarzeń tego dnia.</div>';
}

function renderUpcoming(){
  const list = $('#upcomingList');
  const items = upcomingEvents();
  list.innerHTML = items.length ? items.map(eventItemHTML).join('') : '<div class="empty">Brak nadchodzących wydarzeń w wybranych źródłach i kategoriach.</div>';
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
    url: $('#f-url').value.trim(),
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
  syncSourceFiltersFromUI();
  bindSourceFilters();
  renderFilters();
  renderCalendar();
  renderUpcoming();
  renderAgenda();
})();
