// === DEMO MODE APP.JS ===
// Modified version: no email scraping, no RFQ sending, rate limited, CTA popup

const API_URL = '';

const SUGGESTIONS = [
  'Inconel 718 forgings', 'Hastelloy C-276 tubing', 'titanium grade 5 bar stock',
  'Monel 400 seamless pipe', 'tungsten carbide blanks', 'beryllium copper spring wire',
  'Stellite 6 hardfacing rod', 'niobium sheet & foil', 'Invar 36 precision strip',
  'zirconium reactor components', 'cryogenic ball valves -320\u00B0F',
  'ceramic-lined knife gate valves', 'metal-seated triple offset butterfly valves',
  'Hastelloy diaphragm valves', 'high-pressure needle valves 60,000 PSI',
  'sanitary double-seat mix-proof valves', 'fire-safe fugitive emission valves API 641',
  'spiral wound gaskets with Flexitallic', 'PTFE spring-energized seals',
  'graphite die-formed packing rings', 'Kalrez O-rings FFKM 7075',
  'metallic C-ring seals for turbines', 'ceramic hybrid angular contact bearings',
  'hydrostatic spindle bearings', 'crossed roller bearings THK',
  'air bearings for metrology stages', 'magnetic levitation bearing assemblies',
  'Coriolis mass flow meters', 'vibrating fork level switches',
  'radar tank gauging systems', 'RTD thermowell assemblies 316L',
  'zirconia oxygen analyzers', 'servo-hydraulic actuators MTS',
  'proportional directional control valves', 'hydraulic power unit 5000 PSI',
];

// === STATE ===
let searchResults = [];
let allQuotes = [];
let activeFilter = 'all';
let suggestionInterval = null;
let rfqCart = [];

// === DOM REFS ===
const navBtns = document.querySelectorAll('.nav-btn');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchStatus = document.getElementById('search-status');
const resultsTable = document.getElementById('results-table');
const resultsBody = document.getElementById('results-body');
const quotesBody = document.getElementById('quotes-body');
const quotesStatus = document.getElementById('quotes-status');
const refreshQuotesBtn = document.getElementById('refresh-quotes-btn');
const cartBar = document.getElementById('rfq-cart-bar');
const cartCount = document.getElementById('rfq-cart-count');
const cartCheckoutBtn = document.getElementById('rfq-cart-checkout');

// === CART BAR ===
function updateCartBar() {
  if (rfqCart.length > 0) {
    cartBar.classList.remove('hidden');
    cartCount.textContent = rfqCart.length + ' supplier' + (rfqCart.length === 1 ? '' : 's') + ' selected';
  } else {
    cartBar.classList.add('hidden');
  }
  // Update selected state on email action icons
  document.querySelectorAll('.action-email[data-index]').forEach(btn => {
    const idx = parseInt(btn.dataset.index);
    const supplier = searchResults[idx];
    if (supplier && rfqCart.some(s => s.email === supplier.email && s.name === supplier.name)) {
      btn.classList.add('selected');
    } else {
      btn.classList.remove('selected');
    }
  });
}

function toggleCartSupplier(supplier) {
  const idx = rfqCart.findIndex(s => s.email === supplier.email && s.name === supplier.name);
  if (idx >= 0) {
    rfqCart.splice(idx, 1);
  } else {
    rfqCart.push(supplier);
  }
  updateCartBar();
}

cartCheckoutBtn.addEventListener('click', () => {
  showCtaPopup();
});

// === TAB NAVIGATION ===
navBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    navBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.remove('active');
      t.classList.add('hidden');
    });
    const tab = document.getElementById('tab-' + btn.dataset.tab);
    tab.classList.remove('hidden');
    tab.classList.add('active');
    if (btn.dataset.tab === 'quotes') loadQuotes();
  });
});

// === SEARCH ===
searchBtn.addEventListener('click', doSearch);
searchInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') doSearch();
});

let _searchPending = false;

async function doSearch() {
  const query = searchInput.value.trim();
  if (!query || _searchPending) return;

  _searchPending = true;
  searchBtn.disabled = true;
  searchBtn.textContent = 'Searching...';
  showStatus(searchStatus, 'loading', 'Searching for suppliers...');
  resultsTable.classList.add('hidden');
  resultsBody.innerHTML = '';
  searchResults = [];

  try {
    const res = await fetch(API_URL + '/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.slice(0, 500) })
    });

    let data;
    try {
      data = await res.json();
    } catch (parseErr) {
      showStatus(searchStatus, 'error', 'Server error — please try again.');
      return;
    }

    if (data.error) {
      showStatus(searchStatus, 'error', data.error);
    } else {
      searchResults = Array.isArray(data.suppliers) ? data.suppliers : [];
      if (searchResults.length === 0) {
        showStatus(searchStatus, 'error', 'No suppliers found. Try a different search term.');
      } else {
        renderSearchResults(searchResults);
        hideStatus(searchStatus);
        // Poll for reputation enrichment updates
        if (data.status === 'enriching' && data.searchId) {
          pollForUpdates(data.searchId);
        }
      }
    }
  } catch (err) {
    const msg = (err.message || '').includes('Failed to fetch')
      ? 'Unable to reach server — check your connection and try again.'
      : 'Search failed — please try again.';
    showStatus(searchStatus, 'error', msg);
  } finally {
    searchBtn.disabled = false;
    searchBtn.textContent = 'Search';
    _searchPending = false;
  }
}

let _pollInterval = null;

function pollForUpdates(searchId) {
  if (_pollInterval) clearInterval(_pollInterval);
  _pollInterval = setInterval(async () => {
    try {
      const res = await fetch(API_URL + '/api/search/status?id=' + searchId);
      const data = await res.json();
      if (data.suppliers && data.suppliers.length > 0) {
        searchResults = data.suppliers;
        renderSearchResults(searchResults);
      }
      if (data.status === 'done') {
        clearInterval(_pollInterval);
        _pollInterval = null;
      }
    } catch (err) {
      clearInterval(_pollInterval);
      _pollInterval = null;
    }
  }, 1500);
}

function renderSearchResults(results) {
  resultsBody.innerHTML = '';
  results.forEach((s, i) => {
    const tr = document.createElement('tr');
    const nameCell = s.website
      ? '<a href="' + ensureHttp(esc(s.website)) + '" target="_blank">' + esc(s.name || '\u2014') + '</a>'
      : esc(s.name || '\u2014');

    // Demo: always show email icon for all suppliers — clicking adds to cart
    const emailIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13 2 4"/></svg>';
    const actionCell = '<button class="action-icon action-email" data-index="' + i + '" title="Select for RFQ">' + emailIcon + '</button>';

    const repParts = [];
    if (s.yearsInBusiness) repParts.push(esc(s.yearsInBusiness));
    if (s.employees) repParts.push(esc(s.employees) + ' emp');
    if (s.revenue) repParts.push(esc(s.revenue));
    const repCell = repParts.length > 0 ? '<span class="rep-text">' + repParts.join(' &middot; ') + '</span>' : '\u2014';

    const rawCerts = s.certifications || s.certs || '';
    const fixCertCase = (c) => {
      return c.replace(/\b(iso|as|itar|nadcap|nist|astm|fda|gmp|rohs|ul|ce|sae|iatf|ohsas)\b/gi, m => m.toUpperCase())
              .replace(/\b(sp)\b/gi, m => m.toUpperCase());
    };
    const certCell = rawCerts && rawCerts !== 'N/A'
      ? rawCerts.split(/[,;]/).map(c => '<span class="info-pill cert-pill">' + esc(fixCertCase(c.trim())) + '</span>').join(' ')
      : '\u2014';

    // State / country pill
    const stateVal = s.state || s.location || '';
    const US_STATES = new Set(['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']);
    const isUS = !stateVal || stateVal === 'US' || US_STATES.has(stateVal);
    const stateCell = stateVal ? '<span class="info-pill state-pill">' + (isUS ? '\ud83c\uddfa\ud83c\uddf8 ' : '') + esc(stateVal) + '</span>' : '\u2014';

    const isInCart = rfqCart.some(c => c.email === s.email && c.name === s.name);

    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><strong>${nameCell}</strong></td>
      <td>${stateCell}</td>
      <td>${esc(s.products || '\u2014')}</td>
      <td>${certCell}</td>
      <td>${repCell}</td>
      <td>${esc(s.matchReason || '\u2014')}</td>
      <td>${actionCell}</td>
    `;

    if (isInCart) {
      const emailBtn = tr.querySelector('.action-email[data-index]');
      if (emailBtn) emailBtn.classList.add('selected');
    }

    resultsBody.appendChild(tr);
  });

  resultsTable.classList.remove('hidden');

  // Email icons: click to toggle cart selection
  document.querySelectorAll('.action-email[data-index]').forEach(btn => {
    btn.addEventListener('click', () => {
      toggleCartSupplier(searchResults[parseInt(btn.dataset.index)]);
    });
  });
}

// === CTA POPUP (demo — shown instead of actual RFQ sending) ===
function showCtaPopup() {
  const count = rfqCart.length;
  const overlay = document.createElement('div');
  overlay.className = 'demo-cta-popup';
  overlay.innerHTML = `
    <div class="demo-cta-box">
      <h3>Ready to send RFQs?</h3>
      <p>You've selected ${count} supplier${count === 1 ? '' : 's'}. The demo lets you search and explore suppliers. To send RFQs, track quotes, and manage your procurement workflow — get started with a full Sourcivity account.</p>
      <a class="cta-link" href="mailto:ari@sourcivity.io?subject=Sourcivity%20Access%20Request&body=Hi%20Ari%2C%0A%0AI%20tried%20the%20Sourcivity%20demo%20and%20I%27d%20like%20to%20get%20full%20access.%0A%0AThanks!">Contact ari@sourcivity.io</a>
      <button class="cta-dismiss">Continue browsing</button>
    </div>
  `;
  document.body.appendChild(overlay);

  overlay.querySelector('.cta-dismiss').addEventListener('click', () => {
    overlay.remove();
  });
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) overlay.remove();
  });
}

// === QUOTE TRACKER ===
async function loadQuotes() {
  showStatus(quotesStatus, 'loading', 'Loading quotes...');
  try {
    const res = await fetch(API_URL + '/api/quotes');
    if (!res.ok) throw new Error('API error ' + res.status);
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    allQuotes = data.quotes || [];
    renderQuotes(allQuotes);
    hideStatus(quotesStatus);
  } catch (err) {
    showStatus(quotesStatus, 'error', 'Failed to load quotes: ' + err.message);
  }
}

function fmtDate(d) {
  if (!d) return '';
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const parts = d.split('-');
  if (parts.length !== 3) return d;
  const m = parseInt(parts[1], 10) - 1;
  const day = parseInt(parts[2], 10);
  return months[m] + ' ' + day;
}

function matchesFilter(status) {
  if (activeFilter === 'all') return true;
  const s = (status || '').toLowerCase();
  if (activeFilter === 'sent') return s.includes('sent') && !s.includes('bounced');
  if (activeFilter === 'responded') return s.includes('responded');
  if (activeFilter === 'overdue') return s.includes('overdue');
  if (activeFilter === 'received') return s.includes('quote received');
  if (activeFilter === 'bounced') return s.includes('bounced');
  return true;
}

function renderQuotes(quotes) {
  quotesBody.innerHTML = '';
  const filtered = quotes.filter(q => matchesFilter(q.status));

  if (filtered.length === 0) {
    quotesBody.innerHTML = '<tr><td colspan="11" class="empty-state"><p>' +
      (quotes.length === 0 ? 'No quotes tracked yet.' : 'No quotes match this filter.') +
      '</p></td></tr>';
    return;
  }

  const groups = [];
  const groupMap = {};
  filtered.forEach(q => {
    const cat = q.category || 'Uncategorized';
    if (!groupMap[cat]) {
      groupMap[cat] = [];
      groups.push(cat);
    }
    groupMap[cat].push(q);
  });

  groups.forEach(cat => {
    const groupId = 'cat-' + cat.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
    const count = groupMap[cat].length;

    const headerTr = document.createElement('tr');
    headerTr.className = 'category-header';
    headerTr.dataset.group = groupId;
    headerTr.innerHTML = '<td colspan="11"><span class="cat-arrow">&#9660;</span> ' + esc(cat) + ' <span class="cat-count">(' + count + ')</span></td>';
    headerTr.addEventListener('click', () => {
      const isCollapsed = headerTr.classList.toggle('collapsed');
      document.querySelectorAll('tr[data-cat="' + groupId + '"]').forEach(r => {
        r.classList.toggle('hidden', isCollapsed);
      });
    });
    quotesBody.appendChild(headerTr);

    groupMap[cat].forEach(q => {
      const tr = document.createElement('tr');
      tr.dataset.cat = groupId;
      tr.innerHTML = `
        <td>${fmtDate(q.date)}</td>
        <td><strong>${esc(q.supplier || '')}</strong></td>
        <td>${esc(q.partService || '')}</td>
        <td>${esc(q.quotedPrice || '')}</td>
        <td>${esc(q.unit || '')}</td>
        <td>${esc(q.leadTime || '')}</td>
        <td>${esc(q.moq || '')}</td>
        <td>${esc(q.paymentTerms || '')}</td>
        <td>${fmtDate(q.validUntil)}</td>
        <td>${statusBadge(q.status)}</td>
        <td class="notes-cell">${esc(q.notes || '')}</td>
      `;
      quotesBody.appendChild(tr);
    });
  });
}

function statusBadge(status) {
  if (!status) return '<span class="badge">\u2014</span>';
  const s = status.trim().toLowerCase();
  let cls = '';
  if (s.includes('bounced')) cls = 'badge-bounced';
  else if (s.includes('overdue')) cls = 'badge-overdue';
  else if (s.includes('follow-up') || s.includes('follow')) cls = 'badge-followup';
  else if (s.includes('quote received')) cls = 'badge-received';
  else if (s.includes('responded')) cls = 'badge-responded';
  else if (s.includes('sent')) cls = 'badge-sent';
  else if (s.includes('pending')) cls = 'badge-pending';
  else if (s.includes('accepted')) cls = 'badge-accepted';
  else if (s.includes('declined')) cls = 'badge-declined';
  else if (s.includes('expired')) cls = 'badge-expired';
  return '<span class="badge ' + cls + '">' + esc(status.trim()) + '</span>';
}

refreshQuotesBtn.addEventListener('click', loadQuotes);

// === STATUS FILTERS ===
document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderQuotes(allQuotes);
  });
});

// === HELPERS ===
function showStatus(el, type, msg) {
  el.className = 'status-msg ' + type;
  el.innerHTML = (type === 'loading' ? '<span class="spinner"></span>' : '') + msg;
  el.classList.remove('hidden');
}

function hideStatus(el) {
  el.classList.add('hidden');
}

function esc(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function ensureHttp(url) {
  if (!url.startsWith('http')) return 'https://' + url;
  return url;
}

// === SUGGESTION CHIPS ===
const suggestionChips = document.getElementById('suggestion-chips');

function pickRandom(arr, count) {
  const shuffled = [...arr].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, count);
}

function renderSuggestions() {
  const picks = pickRandom(SUGGESTIONS, 4);
  suggestionChips.innerHTML = '';
  picks.forEach(text => {
    const chip = document.createElement('button');
    chip.className = 'suggestion-chip fade-in';
    chip.textContent = text;
    chip.addEventListener('click', () => {
      searchInput.value = text;
      doSearch();
    });
    suggestionChips.appendChild(chip);
  });
}

renderSuggestions();
suggestionInterval = setInterval(renderSuggestions, 8000);

searchInput.addEventListener('focus', () => {
  clearInterval(suggestionInterval);
});

searchInput.addEventListener('blur', () => {
  if (!searchInput.value.trim()) {
    suggestionInterval = setInterval(renderSuggestions, 8000);
  }
});
