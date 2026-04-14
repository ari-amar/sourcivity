// === CONFIG ===
const API_URL = '';
const DEMO_MODE = window.DEMO_MODE || false;

// === SUGGESTION ITEMS ===
const SUGGESTIONS = [
  'Inconel 718 forgings', 'Hastelloy C-276 tubing', 'titanium grade 5 bar stock',
  'Monel 400 seamless pipe', 'tungsten carbide blanks', 'beryllium copper spring wire',
  'Stellite 6 hardfacing rod', 'niobium sheet & foil', 'Invar 36 precision strip',
  'zirconium reactor components', 'cryogenic ball valves -320°F',
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
  'rodless pneumatic cylinders ORIGA', 'air-oil intensifier boosters',
  'plate & frame heat exchangers titanium', 'vacuum furnace hot zone molybdenum',
  'finned tube economizer coils', 'shell & tube condensers Hastelloy',
  'electric immersion heaters ATEX', 'helical bevel gearboxes FLENDER',
  'timing belt pulleys HTD 14M', 'overrunning clutch backstops',
  'disc pack couplings high-speed', 'variable frequency drives 480V',
  'chromium carbide overlay plate', 'polyurethane screen panels',
  'alumina ceramic wear tiles 92%', 'tungsten carbide TC rolls',
  'Ni-Hard white iron pump liners', 'explosive-bonded clad plate',
  'electropolished pharma vessels', 'spin-formed dished heads Inconel',
  'electron beam welding services', 'wire EDM cutting titanium',
];

// === STATE ===
let searchResults = [];
let allQuotes = [];
let activeFilter = 'all';
let selectedSupplier = null;
let suggestionInterval = null;
let rfqCart = [];
let searchRegion = 'north_america';

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

// RFQ/checkout modal refs — only present in full mode HTML
const rfqModal        = document.getElementById('rfq-modal');
const rfqClose        = document.getElementById('rfq-close');
const rfqSupplierInfo = document.getElementById('rfq-supplier-info');
const rfqPart         = document.getElementById('rfq-part');
const rfqQty          = document.getElementById('rfq-qty');
const rfqNotes        = document.getElementById('rfq-notes');
const rfqPreview      = document.getElementById('rfq-preview');
const rfqPreviewText  = document.getElementById('rfq-preview-text');
const rfqPreviewBtn   = document.getElementById('rfq-preview-btn');
const rfqSendBtn      = document.getElementById('rfq-send-btn');
const rfqStatus       = document.getElementById('rfq-status');

// === CART BAR ===
function updateCartBar() {
  if (rfqCart.length > 0) {
    cartBar.classList.remove('hidden');
    cartCount.textContent = rfqCart.length + ' supplier' + (rfqCart.length === 1 ? '' : 's') + ' selected';
  } else {
    cartBar.classList.add('hidden');
  }
  document.querySelectorAll('.action-email[data-index]').forEach(btn => {
    const idx = parseInt(btn.dataset.index);
    const supplier = searchResults[idx];
    if (supplier && rfqCart.some(s => s.name === supplier.name)) {
      btn.classList.add('selected');
    } else {
      btn.classList.remove('selected');
    }
  });
}

function toggleCartSupplier(supplier) {
  const idx = rfqCart.findIndex(s => s.name === supplier.name);
  if (idx >= 0) {
    rfqCart.splice(idx, 1);
  } else {
    rfqCart.push(supplier);
  }
  updateCartBar();
}

cartCheckoutBtn.addEventListener('click', () => {
  if (DEMO_MODE) showCtaPopup();
  else openCheckoutModal();
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

const regionSwitchInput = document.getElementById('region-switch-input');
if (regionSwitchInput) {
  regionSwitchInput.addEventListener('change', () => {
    searchRegion = regionSwitchInput.checked ? 'global' : 'north_america';
    document.getElementById('region-emoji-na').style.opacity = regionSwitchInput.checked ? '0.35' : '1';
    document.getElementById('region-emoji-global').style.opacity = regionSwitchInput.checked ? '1' : '0.35';
  });
}

let _pollInterval = null;
let _searchPending = false;

async function doSearch() {
  const query = searchInput.value.trim();
  if (!query || _searchPending) return;

  if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }

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
      body: JSON.stringify({ query: query.slice(0, 500), region: searchRegion })
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

function getContactType(s) {
  const email = (s.email || '').toLowerCase();
  if (email.match(/[\w.-]+@[\w.-]+\.\w+/)) return 'email';
  return 'none';
}

function renderSearchResults(results) {
  resultsBody.innerHTML = '';
  results.forEach((s, i) => {
    const tr = document.createElement('tr');
    const nameCell = s.website
      ? '<a href="' + ensureHttp(esc(s.website)) + '" target="_blank">' + esc(s.name || '—') + '</a>'
      : esc(s.name || '—');

    const emailIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13 2 4"/></svg>';
    const linkIcon = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>';
    const spinnerIcon = '<svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>';

    let actionCell;
    if (DEMO_MODE) {
      // Demo: always show selectable email icon — clicking adds to cart / shows CTA
      actionCell = '<button class="action-icon action-email" data-index="' + i + '" title="Select for RFQ">' + emailIcon + '</button>';
    } else {
      const contactType = getContactType(s);
      if (contactType === 'email') {
        actionCell = '<button class="action-icon action-email" data-index="' + i + '" title="Send RFQ">' + emailIcon + '</button>';
      } else if (s._enriching) {
        actionCell = '<span class="action-icon action-spin" title="Finding email...">' + spinnerIcon + '</span>';
      } else {
        const contactUrl = s.website ? ensureHttp(esc(s.website)) + '/contact' : '#';
        actionCell = '<a href="' + contactUrl + '" target="_blank" class="action-icon action-link" title="Visit Website">' + linkIcon + '</a>';
      }
    }

    const pendingCell = '<span class="action-icon action-spin" style="opacity:0.4">' +
      '<svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg></span>';

    const repParts = [];
    if (s.yearsInBusiness) repParts.push(esc(s.yearsInBusiness));
    if (s.employees) repParts.push(esc(s.employees) + ' emp');
    if (s.revenue) repParts.push(esc(s.revenue));
    const repCell = s._enriching ? pendingCell
      : (repParts.length > 0 ? '<span class="rep-text">' + repParts.join(' · ') + '</span>' : '—');

    const rawCerts = s.certifications || s.certs || '';
    const fixCertCase = (c) => {
      return c.replace(/\b(iso|as|itar|nadcap|nist|astm|fda|gmp|rohs|ul|ce|sae|iatf|ohsas)\b/gi, m => m.toUpperCase())
              .replace(/\b(sp)\b/gi, m => m.toUpperCase());
    };
    const certCell = s._enriching ? pendingCell
      : (rawCerts && rawCerts !== 'N/A'
          ? rawCerts.split(/[,;]/).map(c => '<span class="info-pill cert-pill">' + esc(fixCertCase(c.trim())) + '</span>').join(' ')
          : '—');

    const stateVal = s._enriching ? '' : (s.state || s.location || '');
    const US_STATES = new Set(['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']);
    // Normalize ISO 3166-2 format (e.g. "US-PA" → "PA")
    const normalizedState = stateVal.startsWith('US-') ? stateVal.slice(3) : stateVal;
    const isUS = !stateVal || stateVal === 'US' || US_STATES.has(stateVal) || US_STATES.has(normalizedState);
    // Display the clean value — never show raw "US-XX" or bare "US"
    const displayVal = isUS ? (normalizedState === 'US' || normalizedState === '' ? '' : normalizedState) : stateVal;
    // Map common country names → ISO 2-letter for flag emoji
    const COUNTRY_FLAG_MAP = {
      'UK':'GB','UNITED KINGDOM':'GB',
      'CHINA':'CN','INDIA':'IN','CANADA':'CA','GERMANY':'DE',
      'FRANCE':'FR','JAPAN':'JP','KOREA':'KR','TAIWAN':'TW',
      'SINGAPORE':'SG','AUSTRALIA':'AU','BRAZIL':'BR','MEXICO':'MX'
    };
    const countryFlag = code => {
      const iso2 = COUNTRY_FLAG_MAP[code.toUpperCase()] || (/^[A-Za-z]{2}$/.test(code) ? code.toUpperCase() : null);
      return iso2 ? [...iso2].map(c => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65)).join('') : '';
    };
    const flagEmoji = isUS ? '🇺🇸' : countryFlag(stateVal);
    const stateCell = s._enriching ? pendingCell
      : (stateVal ? '<span class="info-pill state-pill">' + flagEmoji + (displayVal ? ' ' + esc(displayVal) : '') + '</span>' : '—');

    const isInCart = rfqCart.some(c => c.name === s.name);

    tr.innerHTML = `
      <td>${i + 1}</td>
      <td><strong>${nameCell}</strong></td>
      <td>${stateCell}</td>
      <td>${esc(s.products || '—')}</td>
      <td>${certCell}</td>
      <td>${repCell}</td>
      <td>${esc(s.matchReason || '—')}</td>
      <td>${actionCell}</td>
    `;

    if (isInCart) {
      const emailBtn = tr.querySelector('.action-email[data-index]');
      if (emailBtn) emailBtn.classList.add('selected');
    }

    resultsBody.appendChild(tr);
  });

  resultsTable.classList.remove('hidden');

  document.querySelectorAll('.action-email[data-index]').forEach(btn => {
    btn.addEventListener('click', () => {
      const supplier = searchResults[parseInt(btn.dataset.index)];
      if (DEMO_MODE) {
        toggleCartSupplier(supplier);
      } else {
        if (getContactType(supplier) === 'email') {
          openRfqModal(supplier);
        } else {
          toggleCartSupplier(supplier);
        }
      }
    });
  });
}

// === CTA POPUP (demo only — shown instead of actual RFQ sending) ===
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
  overlay.querySelector('.cta-dismiss').addEventListener('click', () => overlay.remove());
  overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
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
    if (!DEMO_MODE && data.warnings && data.warnings.length > 0) {
      showStatus(quotesStatus, 'error', 'CSV column mismatch: ' + data.warnings.join('; '));
    } else {
      hideStatus(quotesStatus);
    }
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
    if (!groupMap[cat]) { groupMap[cat] = []; groups.push(cat); }
    groupMap[cat].push(q);
  });

  groups.forEach(cat => {
    const groupId = 'cat-' + cat.replace(/[^a-zA-Z0-9]/g, '-').toLowerCase();
    const count = groupMap[cat].length;

    const headerTr = document.createElement('tr');
    headerTr.className = 'category-header collapsed';
    headerTr.dataset.group = groupId;
    headerTr.innerHTML = '<td colspan="11"><span class="cat-arrow">&#9660;</span> ' + esc(cat) + ' <span class="cat-count">(' + count + ')</span></td>';
    headerTr.addEventListener('click', () => {
      const isCollapsed = headerTr.classList.toggle('collapsed');
      document.querySelectorAll('tr[data-cat="' + groupId + '"]').forEach(r => r.classList.toggle('hidden', isCollapsed));
    });
    quotesBody.appendChild(headerTr);

    groupMap[cat].forEach(q => {
      const tr = document.createElement('tr');
      tr.dataset.cat = groupId;
      tr.classList.add('hidden');
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
  if (!status) return '<span class="badge">—</span>';
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

// === RFQ MODAL (full mode only) ===
if (!DEMO_MODE && rfqModal) {
  function openRfqModal(supplier) {
    if (!emailConfigured) {
      alert('Email is not configured yet. Please contact ari@sourcivity.io with your Gmail address and app password to enable RFQ sending.');
      return;
    }
    selectedSupplier = supplier;
    rfqSupplierInfo.textContent = 'Sending RFQ to: ' + (supplier.name || 'Unknown') + (supplier.email ? ' (' + supplier.email + ')' : ' (no email found)');
    rfqPart.value = '';
    rfqQty.value = '';
    rfqNotes.value = '';
    rfqPreview.classList.add('hidden');
    rfqSendBtn.classList.add('hidden');
    hideStatus(rfqStatus);
    rfqModal.classList.remove('hidden');
  }

  rfqClose.addEventListener('click', () => rfqModal.classList.add('hidden'));
  rfqModal.addEventListener('click', (e) => { if (e.target === rfqModal) rfqModal.classList.add('hidden'); });

  rfqPreviewBtn.addEventListener('click', async () => {
    if (!rfqPart.value.trim()) {
      showStatus(rfqStatus, 'error', 'Please enter a part/service description.');
      return;
    }
    showStatus(rfqStatus, 'loading', 'Generating email preview...');
    try {
      const res = await fetch(API_URL + '/api/rfq/draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier: selectedSupplier,
          part: rfqPart.value.trim(),
          qty: rfqQty.value.trim(),
          notes: rfqNotes.value.trim()
        })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const lines = data.email_text.split('\n');
      let toAddr = '', subject = '', bodyLines = [];
      let pastHeaders = false;
      for (const line of lines) {
        const trimmed = line.trim();
        if (!pastHeaders && trimmed.toLowerCase().startsWith('subject:')) {
          subject = trimmed.substring(8).trim();
        } else if (!pastHeaders && trimmed.toLowerCase().startsWith('to:')) {
          toAddr = trimmed.substring(3).trim();
        } else if (!pastHeaders && trimmed.toLowerCase().startsWith('from:')) {
          continue;
        } else if (!pastHeaders && trimmed === '') {
          pastHeaders = true;
        } else {
          pastHeaders = true;
          bodyLines.push(line);
        }
      }
      document.getElementById('rfq-to').value = toAddr || selectedSupplier?.email || '';
      document.getElementById('rfq-subject').value = subject || 'Request for Quote';
      document.getElementById('rfq-body').value = bodyLines.join('\n').trim();
      rfqPreview.classList.remove('hidden');
      rfqSendBtn.classList.remove('hidden');
      hideStatus(rfqStatus);
    } catch (err) {
      showStatus(rfqStatus, 'error', 'Preview failed: ' + err.message);
    }
  });

  rfqSendBtn.addEventListener('click', async () => {
    showStatus(rfqStatus, 'loading', 'Sending RFQ...');
    rfqSendBtn.disabled = true;
    try {
      const res = await fetch(API_URL + '/api/rfq/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          supplier: selectedSupplier,
          email_text: `Subject: ${document.getElementById('rfq-subject').value}\nTo: ${document.getElementById('rfq-to').value}\n\n${document.getElementById('rfq-body').value}`,
          part: rfqPart.value.trim()
        })
      });
      const data = await res.json();
      if (data.success) {
        showStatus(rfqStatus, 'success', data.message || 'RFQ sent successfully!');
        rfqSendBtn.classList.add('hidden');
        setTimeout(() => {
          rfqModal.classList.add('hidden');
          switchToTab('quotes');
          loadQuotes();
        }, 2000);
      } else {
        showStatus(rfqStatus, 'error', data.error || 'Send failed');
        rfqSendBtn.disabled = false;
      }
    } catch (err) {
      showStatus(rfqStatus, 'error', 'Send failed: ' + err.message);
      rfqSendBtn.disabled = false;
    }
  });
}

// === CONTACT FORM POPUP (full mode only) ===
let contactFormPopup = null;

if (!DEMO_MODE) {
  async function openContactFormPopup(supplier) {
    const website = supplier.website ? ensureHttp(supplier.website) : null;
    if (!website) return;
    const formUrl = supplier.contactUrl ? ensureHttp(supplier.contactUrl) : website + '/contact';

    showStatus(searchStatus, 'loading', 'Detecting contact forms on ' + supplier.name + '...');
    try {
      const res = await fetch(API_URL + '/api/browser/detect-forms', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: formUrl}),
      });
      const data = await res.json();
      const forms = data.forms || [];

      if (forms.length > 0 && !forms[0].error) {
        showStatus(searchStatus, 'loading', 'Generating form values...');
        const searchQuery = searchInput.value.trim();
        const actualUrl = forms[0].source_url || formUrl;
        try {
          const afRes = await fetch(API_URL + '/api/browser/autofill', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ fields: forms[0].fields, supplier, part: searchQuery, qty: '', notes: '' }),
          });
          const afData = await afRes.json();
          forms[0]._autofill = afData.values || {};
        } catch (e) {
          forms[0]._autofill = {};
        }
        hideStatus(searchStatus);
        showFormFillModal(supplier, actualUrl, forms[0]);
      } else {
        const errMsg = (forms.length > 0 && forms[0].error)
          ? 'Form detection failed: ' + forms[0].error + '. Opening contact page...'
          : 'No contact form detected. Opening contact page...';
        showStatus(searchStatus, 'error', errMsg);
        setTimeout(() => hideStatus(searchStatus), 4000);
        const w = 960, h = 750;
        const left = window.screenX + window.outerWidth - 50;
        const top = window.screenY + 50;
        if (contactFormPopup && !contactFormPopup.closed) contactFormPopup.close();
        contactFormPopup = window.open(formUrl, 'contactForm', 'width=' + w + ',height=' + h + ',left=' + left + ',top=' + top + ',scrollbars=yes,resizable=yes');
      }
    } catch (err) {
      hideStatus(searchStatus);
      window.open(formUrl, '_blank');
    }
  }

  function showFormFillModal(supplier, url, form) {
    let fieldsHtml = '';
    const autofill = form._autofill || {};
    form.fields.forEach(f => {
      const fieldName = f.name || f.label.toLowerCase().replace(/\s+/g, '_');
      const defaultVal = autofill[fieldName] || autofill[f.name] || '';
      if (f.tag === 'textarea' || fieldName.toLowerCase().includes('message') || fieldName.toLowerCase().includes('comment')) {
        fieldsHtml += '<div class="form-field"><label>' + esc(f.label || fieldName) + (f.required ? ' *' : '') + '</label>'
          + '<textarea name="' + esc(fieldName) + '" rows="4">' + esc(defaultVal) + '</textarea></div>';
      } else {
        fieldsHtml += '<div class="form-field"><label>' + esc(f.label || fieldName) + (f.required ? ' *' : '') + '</label>'
          + '<input type="' + (f.type || 'text') + '" name="' + esc(fieldName) + '" value="' + esc(defaultVal) + '"></div>';
      }
    });

    const modal = document.getElementById('rfq-modal');
    const content = modal.querySelector('.modal-content') || modal;
    content.innerHTML = '<h3>Contact Form: ' + esc(supplier.name) + '</h3>'
      + '<p class="form-url">Submitting to: ' + esc(url) + '</p>'
      + '<div class="form-fields">' + fieldsHtml + '</div>'
      + '<div class="modal-actions">'
      + '<button id="formSubmitBtn" class="rfq-btn">Submit Form</button>'
      + '<button id="formCancelBtn" class="rfq-btn rfq-btn-visit">Cancel</button>'
      + '</div>';
    modal.classList.remove('hidden');

    document.getElementById('formCancelBtn').addEventListener('click', () => modal.classList.add('hidden'));
    document.getElementById('formSubmitBtn').addEventListener('click', async () => {
      const fields = {};
      content.querySelectorAll('input, textarea').forEach(el => { if (el.name) fields[el.name] = el.value; });
      showStatus(searchStatus, 'loading', 'Submitting form...');
      try {
        const res = await fetch(API_URL + '/api/browser/fill-form', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url, form_index: form.index, fields}),
        });
        const data = await res.json();
        if (data.success) {
          showStatus(searchStatus, 'success', 'Form submitted to ' + supplier.name);
          modal.classList.add('hidden');
        } else {
          showStatus(searchStatus, 'error', 'Form submission failed: ' + (data.error || 'Unknown error'));
        }
      } catch (err) {
        showStatus(searchStatus, 'error', 'Form submission failed: ' + err.message);
      }
    });
  }
}

// === CHECKOUT MODAL (full mode only) ===
if (!DEMO_MODE) {
  const checkoutModal       = document.getElementById('checkout-modal');
  const checkoutClose       = document.getElementById('checkout-close');
  const checkoutSuppliers   = document.getElementById('checkout-suppliers');
  const checkoutPart        = document.getElementById('checkout-part');
  const checkoutQty         = document.getElementById('checkout-qty');
  const checkoutNotes       = document.getElementById('checkout-notes');
  const checkoutPreviews    = document.getElementById('checkout-previews');
  const checkoutStatus      = document.getElementById('checkout-status');
  const checkoutGenerateBtn = document.getElementById('checkout-generate-btn');
  const checkoutSendBtn     = document.getElementById('checkout-send-btn');

  function openCheckoutModal() {
    if (!emailConfigured) {
      alert('Email is not configured yet. Please contact ari@sourcivity.io with your Gmail address and app password to enable RFQ sending.');
      return;
    }
    if (rfqCart.length === 0) return;
    checkoutPart.value = '';
    checkoutQty.value = '';
    checkoutNotes.value = '';
    checkoutPreviews.classList.add('hidden');
    checkoutPreviews.innerHTML = '';
    checkoutSendBtn.classList.add('hidden');
    checkoutGenerateBtn.disabled = false;
    checkoutGenerateBtn.textContent = 'Generate & Preview Emails';
    hideStatus(checkoutStatus);
    renderCheckoutSuppliers();
    checkoutModal.classList.remove('hidden');
  }

  function renderCheckoutSuppliers() {
    checkoutSuppliers.innerHTML = '';
    rfqCart.forEach((s, i) => {
      const chip = document.createElement('span');
      chip.className = 'checkout-supplier-chip';
      chip.innerHTML = esc(s.name) + ' <button class="checkout-supplier-remove" data-index="' + i + '">&times;</button>';
      checkoutSuppliers.appendChild(chip);
    });
    document.querySelectorAll('.checkout-supplier-remove').forEach(btn => {
      btn.addEventListener('click', () => {
        rfqCart.splice(parseInt(btn.dataset.index), 1);
        updateCartBar();
        if (rfqCart.length === 0) checkoutModal.classList.add('hidden');
        else renderCheckoutSuppliers();
      });
    });
  }

  checkoutClose.addEventListener('click', () => checkoutModal.classList.add('hidden'));
  checkoutModal.addEventListener('click', (e) => { if (e.target === checkoutModal) checkoutModal.classList.add('hidden'); });

  checkoutGenerateBtn.addEventListener('click', async () => {
    if (!checkoutPart.value.trim()) {
      showStatus(checkoutStatus, 'error', 'Please enter a part/service description.');
      return;
    }
    if (rfqCart.length === 0) return;
    checkoutGenerateBtn.disabled = true;
    checkoutGenerateBtn.textContent = 'Generating...';
    showStatus(checkoutStatus, 'loading', 'Generating ' + rfqCart.length + ' email previews...');
    checkoutPreviews.classList.add('hidden');
    checkoutSendBtn.classList.add('hidden');
    try {
      const res = await fetch(API_URL + '/api/rfq/batch-draft', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ suppliers: rfqCart, part: checkoutPart.value.trim(), qty: checkoutQty.value.trim(), notes: checkoutNotes.value.trim() })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      checkoutPreviews.innerHTML = '';
      (data.emails || []).forEach((email, i) => {
        if (email.error) {
          const card = document.createElement('div');
          card.className = 'checkout-preview-card';
          card.innerHTML = '<h4>' + esc(email.supplier_name) + '</h4><p style="color:#f85149;">Error: ' + esc(email.error) + '</p>';
          checkoutPreviews.appendChild(card);
          return;
        }
        const lines = email.email_text.split('\n');
        let toAddr = '', subject = '', bodyLines = [];
        let pastHeaders = false;
        for (const line of lines) {
          const trimmed = line.trim();
          if (!pastHeaders && trimmed.toLowerCase().startsWith('subject:')) subject = trimmed.substring(8).trim();
          else if (!pastHeaders && trimmed.toLowerCase().startsWith('to:')) toAddr = trimmed.substring(3).trim();
          else if (!pastHeaders && trimmed.toLowerCase().startsWith('from:')) continue;
          else if (!pastHeaders && trimmed === '') pastHeaders = true;
          else { pastHeaders = true; bodyLines.push(line); }
        }
        const card = document.createElement('div');
        card.className = 'checkout-preview-card';
        card.dataset.supplierIndex = i;
        card.innerHTML = `
          <h4>${esc(email.supplier_name)}</h4>
          <div class="rfq-email-fields">
            <label>To:</label><input type="text" class="checkout-to" value="${esc(toAddr || email.supplier_email || '')}">
            <label>Subject:</label><input type="text" class="checkout-subject" value="${esc(subject || 'Request for Quote')}">
            <label>Body:</label><textarea class="checkout-body" rows="8">${esc(bodyLines.join('\n').trim())}</textarea>
          </div>
        `;
        checkoutPreviews.appendChild(card);
      });
      checkoutPreviews.classList.remove('hidden');
      checkoutSendBtn.classList.remove('hidden');
      hideStatus(checkoutStatus);
    } catch (err) {
      showStatus(checkoutStatus, 'error', 'Preview failed: ' + err.message);
    } finally {
      checkoutGenerateBtn.disabled = false;
      checkoutGenerateBtn.textContent = 'Generate & Preview Emails';
    }
  });

  checkoutSendBtn.addEventListener('click', async () => {
    const cards = checkoutPreviews.querySelectorAll('.checkout-preview-card');
    const items = [];
    cards.forEach((card) => {
      const toInput = card.querySelector('.checkout-to');
      if (!toInput) return;
      const supplier = rfqCart[parseInt(card.dataset.supplierIndex)];
      items.push({
        supplier,
        email_text: 'Subject: ' + card.querySelector('.checkout-subject').value + '\nTo: ' + toInput.value + '\n\n' + card.querySelector('.checkout-body').value,
        part: checkoutPart.value.trim(),
        category: ''
      });
    });
    if (items.length === 0) return;

    checkoutSendBtn.disabled = true;
    checkoutSendBtn.textContent = 'Sending...';
    showStatus(checkoutStatus, 'loading', 'Sending ' + items.length + ' emails...');
    try {
      const res = await fetch(API_URL + '/api/rfq/batch-send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      const results = data.results || [];
      let successCount = 0;
      let progressHtml = '<div class="checkout-progress">';
      results.forEach(r => {
        if (r.success) { successCount++; progressHtml += '<div class="checkout-progress-item success">✓ ' + esc(r.supplier_name) + ' — ' + esc(r.message) + '</div>'; }
        else { progressHtml += '<div class="checkout-progress-item error">✗ ' + esc(r.supplier_name) + ' — ' + esc(r.error) + '</div>'; }
      });
      progressHtml += '</div>';
      checkoutPreviews.innerHTML = progressHtml;

      if (successCount > 0) {
        showStatus(checkoutStatus, 'success', successCount + ' of ' + results.length + ' emails sent successfully!');
        checkoutSendBtn.classList.add('hidden');
        setTimeout(() => {
          rfqCart = [];
          updateCartBar();
          checkoutModal.classList.add('hidden');
          switchToTab('quotes');
          loadQuotes();
        }, 3000);
      } else {
        showStatus(checkoutStatus, 'error', 'All sends failed. Check errors above.');
        checkoutSendBtn.disabled = false;
        checkoutSendBtn.textContent = 'Send All';
      }
    } catch (err) {
      showStatus(checkoutStatus, 'error', 'Send failed: ' + err.message);
      checkoutSendBtn.disabled = false;
      checkoutSendBtn.textContent = 'Send All';
    }
  });
}

// === HELPERS ===
function switchToTab(tabName) {
  navBtns.forEach(b => {
    b.classList.remove('active');
    if (b.dataset.tab === tabName) b.classList.add('active');
  });
  document.querySelectorAll('.tab').forEach(t => { t.classList.remove('active'); t.classList.add('hidden'); });
  const tab = document.getElementById('tab-' + tabName);
  if (tab) { tab.classList.remove('hidden'); tab.classList.add('active'); }
}

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
    chip.addEventListener('click', () => { searchInput.value = text; doSearch(); });
    suggestionChips.appendChild(chip);
  });
}

renderSuggestions();
suggestionInterval = setInterval(renderSuggestions, 8000);
searchInput.addEventListener('focus', () => clearInterval(suggestionInterval));
searchInput.addEventListener('blur', () => {
  if (!searchInput.value.trim()) suggestionInterval = setInterval(renderSuggestions, 8000);
});

// === EMAIL CONFIG CHECK (full mode only) ===
let emailConfigured = true;
if (!DEMO_MODE) {
  (async function checkConfig() {
    try {
      const res = await fetch(API_URL + '/api/config');
      const cfg = await res.json();
      emailConfigured = cfg.email_configured;
      if (!emailConfigured) {
        const banner = document.getElementById('email-setup-banner');
        if (banner) banner.classList.remove('hidden');
      }
    } catch (e) { /* ignore */ }
  })();
}
