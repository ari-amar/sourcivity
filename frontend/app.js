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
let lastSearchQuery = '';

// === DOM REFS ===
const navBtns = document.querySelectorAll('.nav-btn');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const searchStatus = document.getElementById('search-status');
const resultsGrid = document.getElementById('results-grid');
const resultsMeta = document.getElementById('results-meta');
const resultsMetaCount = document.getElementById('results-meta-count');
const quotesBody = document.getElementById('quotes-body');
const quotesStatus = document.getElementById('quotes-status');
const refreshQuotesBtn = document.getElementById('refresh-quotes-btn');
const printQuotesBtn = document.getElementById('print-quotes-btn');
const locationInput = document.getElementById('location-input');
const themeToggle = document.getElementById('theme-toggle');
const themeColorMeta = document.getElementById('theme-color-meta');

// === THEME ===
function applyTheme(theme) {
  const next = theme === 'light' ? 'light' : 'dark';
  document.documentElement.dataset.theme = next;
  if (themeToggle) themeToggle.setAttribute('aria-label', next === 'light' ? 'Switch to dark mode' : 'Switch to light mode');
  if (themeColorMeta) themeColorMeta.setAttribute('content', next === 'light' ? '#f6f8fc' : '#0f1117');
}

const savedTheme = localStorage.getItem('sourcivity-theme');
const preferredTheme = window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
applyTheme(savedTheme || preferredTheme);

if (themeToggle) {
  themeToggle.addEventListener('click', () => {
    const next = document.documentElement.dataset.theme === 'light' ? 'dark' : 'light';
    localStorage.setItem('sourcivity-theme', next);
    applyTheme(next);
  });
}
// Floating RFQ cart
const cartFloat          = document.getElementById('rfq-cart-float');
const cartPill           = document.getElementById('rfq-cart-pill');
const cartPillCount      = document.getElementById('rfq-cart-pill-count');
const cartPanel          = document.getElementById('rfq-cart-panel');
const cartPanelItems     = document.getElementById('rfq-cart-items');
const cartPanelHeaderSub = document.getElementById('rfq-cart-header-sub');
const cartCollapseBtn    = document.getElementById('rfq-cart-collapse');
const cartClearBtn       = document.getElementById('rfq-cart-clear');
const cartCheckoutBtn    = document.getElementById('rfq-cart-checkout');
const cartCheckoutLabel  = document.getElementById('rfq-cart-checkout-label');
const newSearchBtn       = document.getElementById('new-search-btn');

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

// === FLOATING RFQ CART ===
let cartPanelOpen = false;

function setCartPanelOpen(open) {
  cartPanelOpen = open && rfqCart.length > 0;
  cartPill.classList.toggle('hidden',  cartPanelOpen);
  cartPanel.classList.toggle('hidden', !cartPanelOpen);
}

function renderCartPanelItems() {
  cartPanelItems.innerHTML = '';
  rfqCart.forEach((s, i) => {
    const item = document.createElement('div');
    item.className = 'rfq-cart-item';
    const nameHtml = s.website
      ? '<a class="rfq-cart-item-name" href="' + ensureHttp(esc(s.website)) + '" target="_blank" rel="noopener noreferrer">' + esc(s.name || '—') + '</a>'
      : '<span class="rfq-cart-item-name">' + esc(s.name || '—') + '</span>';
    const loc = s.state || s.location || '';
    const metaBits = [];
    if (loc) metaBits.push(esc(loc));
    if (s.email) metaBits.push(esc(s.email));
    item.innerHTML =
      nameHtml +
      '<div class="rfq-cart-item-meta">' + (metaBits.join(' · ') || '&nbsp;') + '</div>' +
      '<button type="button" class="rfq-cart-item-remove" data-cart-index="' + i + '" aria-label="Remove ' + esc(s.name || '') + '">&times;</button>';
    cartPanelItems.appendChild(item);
  });
  cartPanelItems.querySelectorAll('[data-cart-index]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const idx = parseInt(btn.dataset.cartIndex, 10);
      if (!isNaN(idx)) {
        rfqCart.splice(idx, 1);
        updateCartBar();
      }
    });
  });
}

function updateCartBar() {
  const n = rfqCart.length;
  if (n > 0) {
    cartFloat.classList.remove('hidden');
    cartPillCount.textContent = String(n);
    if (cartPanelHeaderSub) cartPanelHeaderSub.textContent = n + ' item' + (n === 1 ? '' : 's');
    if (cartCheckoutLabel) cartCheckoutLabel.textContent = 'Submit RFQ (' + n + ')';
    if (cartPanelOpen) renderCartPanelItems();
  } else {
    cartFloat.classList.add('hidden');
    setCartPanelOpen(false);
  }
  // Sync selected state on any visible supplier cards
  document.querySelectorAll('.action-email[data-index], .rfq-add-btn[data-index]').forEach(btn => {
    const idx = parseInt(btn.dataset.index, 10);
    const supplier = searchResults[idx];
    const inCart = supplier && rfqCart.some(s => s.name === supplier.name);
    btn.classList.toggle('selected', !!inCart);
    btn.classList.toggle('added', !!inCart && btn.classList.contains('rfq-add-btn'));
  });
}

function toggleCartSupplier(supplier) {
  const idx = rfqCart.findIndex(s => s.name === supplier.name);
  if (idx >= 0) rfqCart.splice(idx, 1);
  else rfqCart.push(supplier);
  updateCartBar();
}

if (cartPill) {
  cartPill.addEventListener('click', () => {
    renderCartPanelItems();
    setCartPanelOpen(true);
  });
}
if (cartCollapseBtn) {
  cartCollapseBtn.addEventListener('click', () => setCartPanelOpen(false));
}
if (cartClearBtn) {
  cartClearBtn.addEventListener('click', () => {
    rfqCart = [];
    updateCartBar();
  });
}

cartCheckoutBtn.addEventListener('click', () => {
  setCartPanelOpen(false);
  if (DEMO_MODE) showCtaPopup();
  else openCheckoutModal();
});

if (newSearchBtn) {
  newSearchBtn.addEventListener('click', () => {
    switchToTab('search');
    if (searchInput) {
      searchInput.value = '';
      searchInput.focus();
    }
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
}

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
const US_LOCATION_TERMS = new Set(['', 'any', 'us', 'usa', 'u.s.', 'united states', 'united states of america', 'north america',
  'alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho',
  'illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota',
  'mississippi','missouri','montana','nebraska','nevada','new hampshire','new jersey','new mexico','new york','north carolina',
  'north dakota','ohio','oklahoma','oregon','pennsylvania','rhode island','south carolina','south dakota','tennessee','texas',
  'utah','vermont','virginia','washington','west virginia','wisconsin','wyoming',
  'al','ak','az','ar','ca','co','ct','de','fl','ga','hi','id','il','in','ia','ks','ky','la','me','md','ma','mi','mn','ms','mo',
  'mt','ne','nv','nh','nj','nm','ny','nc','nd','oh','ok','or','pa','ri','sc','sd','tn','tx','ut','vt','va','wa','wv','wi','wy']);

function setSearchRegion(region) {
  searchRegion = region === 'global' ? 'global' : 'north_america';
  if (regionSwitchInput) regionSwitchInput.checked = searchRegion === 'global';
  const naEmoji = document.getElementById('region-emoji-na');
  const globalEmoji = document.getElementById('region-emoji-global');
  if (naEmoji) naEmoji.style.opacity = searchRegion === 'global' ? '0.35' : '1';
  if (globalEmoji) globalEmoji.style.opacity = searchRegion === 'global' ? '1' : '0.35';
}

function regionFromLocation(location) {
  const value = (location || '').trim().toLowerCase();
  if (!value) return searchRegion;
  if (US_LOCATION_TERMS.has(value)) return 'north_america';
  return 'global';
}

if (regionSwitchInput) {
  regionSwitchInput.addEventListener('change', () => {
    setSearchRegion(regionSwitchInput.checked ? 'global' : 'north_america');
  });
}
if (locationInput) {
  locationInput.addEventListener('change', () => setSearchRegion(regionFromLocation(locationInput.value)));
  locationInput.addEventListener('blur', () => setSearchRegion(regionFromLocation(locationInput.value)));
}
setSearchRegion(searchRegion);

let _pollInterval = null;
let _searchPending = false;

async function doSearch() {
  const query = searchInput.value.trim();
  if (!query || _searchPending) return;
  const location = locationInput ? locationInput.value.trim() : '';
  setSearchRegion(regionFromLocation(location));
  lastSearchQuery = query;

  if (_pollInterval) { clearInterval(_pollInterval); _pollInterval = null; }

  _searchPending = true;
  searchBtn.disabled = true;
  searchBtn.textContent = 'Searching...';
  showStatus(searchStatus, 'loading', 'Searching for suppliers...');
  resultsGrid.classList.add('hidden');
  resultsMeta.classList.add('hidden');
  resultsGrid.innerHTML = '';
  searchResults = [];

  try {
    const res = await fetch(API_URL + '/api/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: query.slice(0, 500), region: searchRegion, location: location.slice(0, 80) })
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
        renderSearchResults(searchResults, { fresh: true });
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
      const suppliers = Array.isArray(data.suppliers) ? data.suppliers : null;
      const isDone = data.status === 'done';
      if (suppliers) {
        searchResults = suppliers;
        renderSearchResults(searchResults);
      }
      if (isDone) {
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

// Country/state helpers (hoisted — used by card renderer)
const US_STATES = new Set(['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']);
const US_STATE_NAME_TO_ABBR = {
  'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA',
  'colorado':'CO','connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA',
  'hawaii':'HI','idaho':'ID','illinois':'IL','indiana':'IN','iowa':'IA',
  'kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD',
  'massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS',
  'missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','new hampshire':'NH',
  'new jersey':'NJ','new mexico':'NM','new york':'NY','north carolina':'NC',
  'north dakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA',
  'rhode island':'RI','south carolina':'SC','south dakota':'SD','tennessee':'TN',
  'texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA',
  'west virginia':'WV','wisconsin':'WI','wyoming':'WY',
};
const COUNTRY_NAME_TO_ISO2 = {
  'India':'IN','Germany':'DE','Israel':'IL','Colombia':'CO','Argentina':'AR',
  'Albania':'AL','Gabon':'GA','Indonesia':'ID','Montenegro':'ME',
  'Austria':'AT','France':'FR','Italy':'IT','Spain':'ES','Netherlands':'NL',
  'Switzerland':'CH','Belgium':'BE','Portugal':'PT','Sweden':'SE','Denmark':'DK',
  'Finland':'FI','Norway':'NO','Poland':'PL','Czechia':'CZ','Czech Republic':'CZ',
  'Slovakia':'SK','Hungary':'HU','Romania':'RO','Bulgaria':'BG','Greece':'GR',
  'Ukraine':'UA','Turkey':'TR','Russia':'RU','Belarus':'BY','Moldova':'MD',
  'Serbia':'RS','Croatia':'HR','Slovenia':'SI','Bosnia':'BA','Bosnia and Herzegovina':'BA',
  'North Macedonia':'MK','Kosovo':'XK','Cyprus':'CY','Malta':'MT','Iceland':'IS',
  'Ireland':'IE','Luxembourg':'LU','Lithuania':'LT','Latvia':'LV','Estonia':'EE',
  'China':'CN','Japan':'JP','Korea':'KR','South Korea':'KR','North Korea':'KP',
  'Taiwan':'TW','Singapore':'SG','Vietnam':'VN','Thailand':'TH','Malaysia':'MY',
  'Philippines':'PH','Myanmar':'MM','Cambodia':'KH','Laos':'LA',
  'Australia':'AU','New Zealand':'NZ','Canada':'CA','Brazil':'BR','Mexico':'MX',
  'Chile':'CL','Peru':'PE','Venezuela':'VE',
  'Ecuador':'EC','Bolivia':'BO','Paraguay':'PY','Uruguay':'UY',
  'United Kingdom':'GB','UK':'GB','UAE':'AE','United Arab Emirates':'AE',
  'Saudi Arabia':'SA','Qatar':'QA','Kuwait':'KW','Bahrain':'BH','Oman':'OM',
  'Jordan':'JO','Iraq':'IQ','Iran':'IR','Lebanon':'LB','Syria':'SY',
  'Egypt':'EG','Morocco':'MA','Algeria':'DZ','Tunisia':'TN','Libya':'LY',
  'South Africa':'ZA','Nigeria':'NG','Kenya':'KE','Ghana':'GH','Ethiopia':'ET',
  'Tanzania':'TZ','Uganda':'UG','Zimbabwe':'ZW','Mozambique':'MZ',
  'Hong Kong':'HK','Pakistan':'PK','Bangladesh':'BD','Sri Lanka':'LK',
  'Nepal':'NP','Kazakhstan':'KZ','Azerbaijan':'AZ','Georgia':'GE','Armenia':'AM',
  'Palestine':'PS',
};
const COUNTRY_FLAG_MAP = {'UK':'GB','UAE':'AE'};

function countryFlagFromCode(code) {
  if (!code) return '';
  const iso2 = COUNTRY_FLAG_MAP[code.toUpperCase()] || (/^[A-Za-z]{2}$/.test(code) ? code.toUpperCase() : null);
  return iso2 ? [...iso2].map(c => String.fromCodePoint(0x1F1E6 + c.charCodeAt(0) - 65)).join('') : '';
}

function resolveLocationTag(rawState) {
  const stateVal = (rawState || '').trim();
  // No state yet (e.g. enriching) — render nothing rather than defaulting to a flag.
  if (!stateVal) return { flag: '', label: '' };
  const cleanStateVal = stateVal.replace(/\s*\(.*?\)\s*$/, '').trim();
  if (['N/A', 'NA', 'UNKNOWN'].includes(cleanStateVal.toUpperCase())) {
    return { flag: '', label: '' };
  }
  const normalizedState = cleanStateVal.startsWith('US-') ? cleanStateVal.slice(3) : cleanStateVal;
  const stateNameAbbr = US_STATE_NAME_TO_ABBR[cleanStateVal.toLowerCase()] || '';
  const isUS = cleanStateVal === 'US' || US_STATES.has(cleanStateVal) || US_STATES.has(normalizedState) || !!stateNameAbbr;
  const resolvedISO2 = COUNTRY_NAME_TO_ISO2[cleanStateVal] || COUNTRY_NAME_TO_ISO2[stateVal] || null;
  const rawIs2Letter = !isUS && /^[A-Za-z]{2}$/.test(cleanStateVal);
  const effectiveCode = resolvedISO2 || (rawIs2Letter ? cleanStateVal.toUpperCase() : null);
  const flag = isUS ? '🇺🇸' : countryFlagFromCode(effectiveCode || cleanStateVal);
  const label = isUS
    ? (stateNameAbbr || (normalizedState === 'US' ? '' : normalizedState))
    : (effectiveCode || '');
  return { flag, label };
}

function fixCertCase(c) {
  return c.replace(/\b(iso|as|itar|nadcap|nist|astm|fda|gmp|rohs|ul|ce|sae|iatf|ohsas)\b/gi, m => m.toUpperCase())
          .replace(/\b(sp)\b/gi, m => m.toUpperCase());
}

const ICON_EMAIL   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 4L12 13 2 4"/></svg>';
const ICON_LINK    = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>';
const ICON_SPIN    = '<svg class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>';
const ICON_CHECK   = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>';

function computeCardSections(s, i) {
  const titleHtml = s.website
    ? '<a class="card-title" href="' + ensureHttp(esc(s.website)) + '" target="_blank" rel="noopener noreferrer">' + esc(s.name || '—') + '</a>'
    : '<span class="card-title">' + esc(s.name || '—') + '</span>';

  const stateVal = s._enriching ? '' : (s.state || s.location || '');
  const { flag, label } = resolveLocationTag(stateVal);
  const flagHtml = flag ? '<span class="card-flag" title="' + esc(stateVal || '') + '">' + flag + '</span>' : '';
  const locationPillHtml = label ? '<span class="card-pill">' + esc(label) + '</span>' : '';
  const tagRowHtml = flagHtml + locationPillHtml;

  const rawCerts = s.certifications || s.certs || '';
  let certsHtml;
  if (s._enriching) {
    certsHtml = '<span class="skeleton skeleton-pill" style="width:48px"></span>' +
                '<span class="skeleton skeleton-pill" style="width:68px"></span>' +
                '<span class="skeleton skeleton-pill" style="width:40px"></span>';
  } else if (rawCerts && rawCerts !== 'N/A') {
    certsHtml = rawCerts.split(/[,;]/).map(c => '<span class="info-pill cert-pill">' + esc(fixCertCase(c.trim())) + '</span>').join(' ');
  } else {
    certsHtml = '—';
  }

  const repParts = [];
  if (s.yearsInBusiness) repParts.push(esc(s.yearsInBusiness));
  if (s.employees) repParts.push(esc(s.employees) + ' emp');
  if (s.revenue) repParts.push(esc(s.revenue));
  const repHtml = s._enriching
    ? '<span class="skeleton skeleton-line" style="width:140px"></span>'
    : (repParts.length ? repParts.join(' · ') : '—');

  const productsHtml = esc(s.products || '—');
  const matchHtml = esc(s.matchReason || '—');
  const indexHtml = '#' + (i + 1);

  const inCart = rfqCart.some(c => c.name === s.name);
  let actionHtml;
  if (DEMO_MODE) {
    actionHtml = '<button class="rfq-add-btn' + (inCart ? ' added' : '') +
      '" data-index="' + i + '" title="Select for RFQ" type="button">' +
      (inCart ? ICON_CHECK + ' Added' : '+ RFQ') + '</button>';
  } else {
    const contactType = getContactType(s);
    if (contactType === 'email') {
      actionHtml = '<button class="action-icon action-email' + (inCart ? ' selected' : '') +
        '" data-index="' + i + '" title="Send RFQ" type="button">' + ICON_EMAIL + '</button>';
    } else if (s._enriching) {
      actionHtml = '<span class="action-icon action-spin" title="Finding email...">' + ICON_SPIN + '</span>';
    } else {
      const contactUrl = s.contactUrl ? ensureHttp(esc(s.contactUrl)) : (s.website ? ensureHttp(esc(s.website)) + '/contact' : '#');
      actionHtml = '<a href="' + contactUrl + '" target="_blank" rel="noopener noreferrer" class="action-icon action-link" title="Visit Website">' + ICON_LINK + '</a>';
    }
  }

  const footerLeftHtml = s._enriching
    ? '<span class="finding-email"><span class="dot-pulse"></span>Finding email…</span>'
    : '';

  return { titleHtml, tagRowHtml, productsHtml, certsHtml, repHtml, matchHtml, actionHtml, footerLeftHtml, indexHtml };
}

function buildCardHTML(p) {
  return (
    '<div class="card-header">' +
      '<div class="card-title-group">' +
        '<div class="card-index" data-role="index">' + p.indexHtml + '</div>' +
        '<div class="card-title-wrap" data-role="title">' + p.titleHtml + '</div>' +
      '</div>' +
      '<div class="card-tag-row" data-role="tag-row">' + p.tagRowHtml + '</div>' +
    '</div>' +
    '<div class="card-specs">' +
      '<div class="card-spec">' +
        '<div class="card-spec-label">Products / Services</div>' +
        '<div class="card-spec-value" data-role="products">' + p.productsHtml + '</div>' +
      '</div>' +
      '<div class="card-spec">' +
        '<div class="card-spec-label">Certifications</div>' +
        '<div class="card-spec-value" data-role="certs">' + p.certsHtml + '</div>' +
      '</div>' +
      '<div class="card-spec">' +
        '<div class="card-spec-label">Reputation</div>' +
        '<div class="card-spec-value" data-role="rep">' + p.repHtml + '</div>' +
      '</div>' +
      '<div class="card-spec full-width">' +
        '<div class="card-spec-label">Match</div>' +
        '<div class="card-spec-value" data-role="match">' + p.matchHtml + '</div>' +
      '</div>' +
    '</div>' +
    '<div class="card-footer">' +
      '<div class="card-footer-meta" data-role="footer-meta">' + p.footerLeftHtml + '</div>' +
      '<div class="card-action-wrap" data-role="action">' + p.actionHtml + '</div>' +
    '</div>'
  );
}

function patchCardInPlace(card, p) {
  const roles = ['index','title','tag-row','products','certs','rep','match','action','footer-meta'];
  const values = {
    'index': p.indexHtml, 'title': p.titleHtml, 'tag-row': p.tagRowHtml,
    'products': p.productsHtml, 'certs': p.certsHtml, 'rep': p.repHtml,
    'match': p.matchHtml, 'action': p.actionHtml, 'footer-meta': p.footerLeftHtml,
  };
  for (const role of roles) {
    const el = card.querySelector('[data-role="' + role + '"]');
    if (!el) continue;
    const next = values[role];
    if (el._lastHtml === next) continue;
    el._lastHtml = next;
    el.innerHTML = next;
  }
}

function renderSearchResults(results, opts) {
  const fresh = opts && opts.fresh;
  const byName = new Map();
  Array.from(resultsGrid.children).forEach(c => byName.set(c.dataset.supplierName, c));

  results.forEach((s, i) => {
    const name = s.name || '';
    const p = computeCardSections(s, i);
    let card = byName.get(name);
    if (!card) {
      card = document.createElement('div');
      card.className = 'supplier-card' + (fresh ? ' fresh' : '');
      card.dataset.supplierName = name;
      card.innerHTML = buildCardHTML(p);
      card.querySelectorAll('[data-role]').forEach(el => {
        el._lastHtml = ({
          'index': p.indexHtml, 'title': p.titleHtml, 'tag-row': p.tagRowHtml,
          'products': p.productsHtml, 'certs': p.certsHtml, 'rep': p.repHtml,
          'match': p.matchHtml, 'action': p.actionHtml, 'footer-meta': p.footerLeftHtml,
        })[el.dataset.role];
      });
    } else {
      patchCardInPlace(card, p);
      byName.delete(name);
    }
    if (resultsGrid.children[i] !== card) {
      resultsGrid.insertBefore(card, resultsGrid.children[i] || null);
    }
  });
  byName.forEach(c => c.remove());

  resultsMetaCount.innerHTML = '<strong>' + results.length + '</strong> supplier' + (results.length === 1 ? '' : 's') + ' found';
  resultsMeta.classList.toggle('hidden', results.length === 0);
  resultsGrid.classList.toggle('hidden', results.length === 0);

  if (!resultsGrid._actionDelegated) {
    resultsGrid.addEventListener('click', (e) => {
      const btn = e.target.closest('.action-email[data-index], .rfq-add-btn[data-index]');
      if (!btn || !resultsGrid.contains(btn)) return;
      const supplier = searchResults[parseInt(btn.dataset.index, 10)];
      if (!supplier) return;
      if (DEMO_MODE) {
        toggleCartSupplier(supplier);
      } else if (getContactType(supplier) === 'email') {
        openRfqModal(supplier);
      } else {
        toggleCartSupplier(supplier);
      }
    });
    resultsGrid._actionDelegated = true;
  }
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
    quotesBody.innerHTML = '<tr><td colspan="13" class="empty-state"><p>' +
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
    headerTr.className = 'category-header';
    headerTr.dataset.group = groupId;
    headerTr.innerHTML = '<td colspan="13"><span class="cat-arrow">&#9660;</span> ' + esc(cat) + ' <span class="cat-count">(' + count + ')</span></td>';
    headerTr.addEventListener('click', () => {
      const isCollapsed = headerTr.classList.toggle('collapsed');
      document.querySelectorAll('tr[data-cat="' + groupId + '"]').forEach(r => r.classList.toggle('hidden', isCollapsed));
    });
    quotesBody.appendChild(headerTr);

    groupMap[cat].forEach(q => {
      const tr = document.createElement('tr');
      tr.dataset.cat = groupId;
      tr.innerHTML = `
        <td data-label="Date">${fmtDate(q.date)}</td>
        <td data-label="Supplier"><strong>${esc(q.supplier || '')}</strong></td>
        <td data-label="Email">${q.email ? '<a href="mailto:' + esc(q.email) + '">' + esc(q.email) + '</a>' : ''}</td>
        <td data-label="Part / Service">${esc(q.partService || '')}</td>
        <td data-label="Quoted Price">${esc(q.quotedPrice || '')}</td>
        <td data-label="Unit">${esc(q.unit || '')}</td>
        <td data-label="Lead Time">${esc(q.leadTime || '')}</td>
        <td data-label="MOQ">${esc(q.moq || '')}</td>
        <td data-label="Payment Terms">${esc(q.paymentTerms || '')}</td>
        <td data-label="Valid Until">${fmtDate(q.validUntil)}</td>
        <td data-label="Status">${statusBadge(q.status)}</td>
        <td data-label="Latest" class="notes-cell">${esc(q.notes || '')}</td>
        <td data-label="Action">${followupButton(q)}</td>
      `;
      quotesBody.appendChild(tr);
    });
  });
}

function followupButton(q) {
  if (DEMO_MODE) return '';
  const s = (q.status || '').toLowerCase();
  const eligible = s.includes('sent') && !s.includes('bounced') || s.includes('overdue') || s.includes('follow');
  if (!eligible) return '';
  if (!q.email) return '<span class="followup-hint" title="No email on file for this supplier">—</span>';
  return '<button class="btn-followup" data-supplier="' + esc(q.supplier || '') + '">Follow up</button>';
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
if (printQuotesBtn) {
  printQuotesBtn.addEventListener('click', () => {
    if (!allQuotes.length) loadQuotes().finally(() => window.print());
    else window.print();
  });
}

// === FOLLOW-UP BUTTON (delegated) ===
quotesBody.addEventListener('click', async (e) => {
  const btn = e.target.closest('.btn-followup');
  if (!btn) return;
  const supplier = btn.dataset.supplier;
  if (!supplier) return;
  if (!confirm('Send a follow-up email to ' + supplier + '?')) return;
  const origText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Sending...';
  try {
    const res = await fetch(API_URL + '/api/rfq/followup', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({supplier})
    });
    const data = await res.json();
    if (data.success) {
      showStatus(quotesStatus, 'success', data.message || 'Follow-up sent.');
      setTimeout(() => hideStatus(quotesStatus), 4000);
      loadQuotes();
    } else {
      showStatus(quotesStatus, 'error', data.error || 'Follow-up failed.');
      btn.disabled = false;
      btn.textContent = origText;
    }
  } catch (err) {
    showStatus(quotesStatus, 'error', 'Follow-up failed: ' + err.message);
    btn.disabled = false;
    btn.textContent = origText;
  }
});

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
      alert('Email is not configured yet. Please contact ari@sourcivity.io with your email address (Gmail or Outlook) and app password to enable RFQ sending.');
      return;
    }
    selectedSupplier = supplier;
    rfqSupplierInfo.textContent = 'Sending RFQ to: ' + (supplier.name || 'Unknown') + (supplier.email ? ' (' + supplier.email + ')' : ' (no email found)');
    rfqPart.value = lastSearchQuery || searchInput.value.trim();
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
      alert('Email is not configured yet. Please contact ari@sourcivity.io with your email address (Gmail or Outlook) and app password to enable RFQ sending.');
      return;
    }
    if (rfqCart.length === 0) return;
    checkoutPart.value = lastSearchQuery || searchInput.value.trim();
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
