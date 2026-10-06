/* openmaterials.ai shell (spec 2.3 to 2.5): header, footer, theme toggle, version stamp, copy
   buttons. A page places <div data-site-header></div> (data-variant="app" on the four tool pages)
   and <div data-site-footer></div>, then loads this script. Links resolve against the assets/
   directory the script lives in, so one file serves every page depth. */
(function () {
  'use strict';

  var self = document.currentScript || document.querySelector('script[src*="assets/site.js"]');
  var assets = new URL('.', self.src).href;   // .../assets/
  var root = new URL('..', assets).href;      // the site root
  function site(p) { return /^https?:/.test(p) ? p : new URL(p, root).href; }

  var REPO = 'https://github.com/openmaterials-ai/openmaterials-ai';
  var BLOB = REPO + '/blob/main/';
  // Static fallback, shown until data/version.json answers (or if it cannot be read).
  var VERSION = '9eb62e10a91b';

  var NAV = [['Map', 'map/'], ['Playground', 'play/'], ['Guide', 'guide/'], ['Document', 'document/']];
  // The nav item each section marks with aria-current: Map covers the three map views.
  var ACTIVE = { 'map/': 'map/', 'map-3d/': 'map/', 'map-trace/': 'map/', 'play/': 'play/', 'guide/': 'guide/', 'document/': 'document/' };
  var FOOTER = [
    ['Map', [['Map', 'map/'], ['Map in 3D', 'map-3d/'], ['Tracer', 'map-trace/'], ['Playground', 'play/'], ['Learn a paper', 'play/#tab=learn']]],
    ['Evidence', [['Cross-code agreement', 'agreement/'], ['Lineage tour', 'lineage/'], ['Verified layer', 'lean/'], ['Formalization roadmap', 'lean/roadmap/']]],
    ['Reference', [['Guide', 'guide/'], ['Document', 'document/'], ['PDF', 'openmaterials.pdf'], ['Codes', 'codes/']]],
    ['Project', [['GitHub', REPO], ['Contribute a value', '#contribute'], ['Contribution guide', BLOB + 'CONTRIBUTING.md'], ['Governance', BLOB + 'GOVERNANCE.md'], ['Citation', '#cite']]]
  ];
  var THEMES = [
    ['system', 'System', '<rect x="2" y="3" width="12" height="8" rx="1"/><path d="M6 14h4M8 11v3"/>'],
    ['light', 'Light', '<circle cx="8" cy="8" r="3"/><path d="M8 1v2M8 13v2M1 8h2M13 8h2M3 3l1.5 1.5M11.5 11.5 13 13M3 13l1.5-1.5M11.5 4.5 13 3"/>'],
    ['dark', 'Dark', '<path d="M13 9.5A5.5 5.5 0 1 1 6.5 3 4.5 4.5 0 0 0 13 9.5z"/>']
  ];

  function section() {
    var here = location.href.split('#')[0].split('?')[0];
    return here.indexOf(root) === 0 ? here.slice(root.length).split('/')[0] + '/' : '';
  }
  function mark() {
    return '<img class="om-mark" src="' + assets + 'logo.svg" alt="" width="20" height="20">openmaterials.ai';
  }
  // Radios that share a name form one group, so each fieldset gets its own name.
  function themeField(name) {
    return '<fieldset class="theme"><legend class="sr-only">Theme</legend>' + THEMES.map(function (t) {
      return '<label><input type="radio" name="' + name + '" value="' + t[0] + '">' +
        '<svg viewBox="0 0 16 16" aria-hidden="true" focusable="false">' + t[2] + '</svg>' +
        '<span class="sr-only">' + t[1] + '</span></label>';
    }).join('') + '</fieldset>';
  }

  function header(app) {
    var cur = ACTIVE[section()];
    var links = NAV.map(function (n) {
      return '<a href="' + site(n[1]) + '"' + (n[1] === cur ? ' aria-current="page"' : '') + '>' + n[0] + '</a>';
    }).join('');
    return '<header class="site-header"><div class="wrap">' +
      '<a class="wordmark" href="' + root + '" aria-label="OpenMaterials home">' + mark() + '</a>' +
      '<nav class="site-nav" aria-label="Primary">' + links + '</nav>' +
      '<a class="pill pill--mono at-961" id="om-version" href="' + site('#cite') + '">map ' + VERSION + '</a>' +
      (app ? themeField('theme') : '') +
      '<a class="btn btn--secondary btn--sm" href="' + REPO + '">GitHub</a>' +
      '<details class="menu"><summary class="btn btn--ghost btn--sm">Menu</summary>' +
      '<nav aria-label="Menu">' + links + '<a href="' + REPO + '">GitHub</a>' + (app ? themeField('theme-menu') : '') + '</nav></details>' +
      '</div></header>';
  }

  function footer() {
    var groups = FOOTER.map(function (g) {
      return '<div><h2>' + g[0] + '</h2><ul>' + g[1].map(function (l) {
        return '<li><a href="' + site(l[1]) + '">' + l[0] + '</a></li>';
      }).join('') + '</ul></div>';
    }).join('');
    return '<footer class="site-footer"><div class="wrap">' +
      '<div class="footer-dir"><div class="footer-id"><a class="wordmark" href="' + root + '">' + mark() + '</a>' +
      '<p>OpenMaterials is a versioned, content-addressed map of physical quantities and formulas.</p></div>' + groups + '</div>' +
      '<div class="footer-legal">' +
      '<p>OpenMaterials is stewarded by OpenMaterials-AI, a foundation in formation.</p>' +
      '<p>Map data is <a href="' + BLOB + 'LICENSE-DATA">CC BY 4.0</a> and code is <a href="' + BLOB + 'LICENSE">Apache 2.0</a>.</p>' +
      '<p>The site and its tools are built by <a href="https://dvnclabs.com">Da Vinci Labs</a>, Berkeley.</p></div>' +
      '<div class="footer-row"><span id="om-stamp" class="mono">' + stampHtml(VERSION) + '</span>' + themeField('theme') + '</div>' +
      '</div></footer>';
  }
  function stampHtml(v) {
    return 'map <a href="' + site('#cite') + '">' + v + '</a>';
  }

  function wireTheme() {
    var html = document.documentElement;
    var inputs = document.querySelectorAll('.theme input');
    function sync() {
      var cur = html.dataset.theme || 'system';
      for (var i = 0; i < inputs.length; i++) inputs[i].checked = inputs[i].value === cur;
    }
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].addEventListener('change', function (e) {
        var v = e.target.value;
        if (v === 'system') delete html.dataset.theme; else html.dataset.theme = v;
        try { if (v === 'system') localStorage.removeItem('theme'); else localStorage.setItem('theme', v); } catch (err) { /* storage blocked: the choice lasts for this view */ }
        sync();
      });
    }
    sync();
  }

  // One fetch of data/version.json fills the header pill and the footer stamp.
  function loadVersion() {
    fetch(site('data/version.json')).then(function (r) { return r.json(); }).then(function (v) {
      var hex = /^[0-9a-f]{12,64}$/;
      if (!v || !hex.test(v.version)) return;
      var v12 = v.version.slice(0, 12);
      var pill = document.getElementById('om-version');
      if (pill) pill.textContent = 'map ' + v12;
      var st = document.getElementById('om-stamp');
      if (st) st.innerHTML = stampHtml(v12);
      bustDocumentLinks(v12);
    }).catch(function () { /* keep the static stamp */ });
  }

  // The PDF sits behind a long edge cache; stamping the map version onto its links makes every
  // new version fetch a fresh copy.
  function bustDocumentLinks(v) {
    var links = document.querySelectorAll('a[href$="openmaterials.pdf"]');
    for (var i = 0; i < links.length; i++) links[i].href += '?v=' + v;
  }

  // A Copy button on every code block head; it reads "Copied" for 1.5 s.
  function wireCopy() {
    var heads = document.querySelectorAll('.code > figcaption, .snippet-head, .recipe-head');
    Array.prototype.forEach.call(heads, function (head) {
      var pre = head.parentNode.querySelector('pre');
      if (!pre || head.querySelector('.copy')) return;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn btn--ghost btn--sm copy';
      b.setAttribute('aria-live', 'polite');
      b.textContent = 'Copy';
      b.addEventListener('click', function () {
        if (!navigator.clipboard) return;
        navigator.clipboard.writeText(pre.textContent).then(function () {
          b.textContent = 'Copied';
          setTimeout(function () { b.textContent = 'Copy'; }, 1500);
        }, function () {});
      });
      head.appendChild(b);
    });
  }

  function mount() {
    var h = document.querySelector('[data-site-header]');
    if (h) h.innerHTML = header(h.getAttribute('data-variant') === 'app');
    var f = document.querySelector('[data-site-footer]');
    if (f) f.innerHTML = footer();
    var menu = document.querySelector('.menu');
    if (menu) menu.addEventListener('click', function (e) { if (e.target.closest('a')) menu.open = false; });
    wireTheme();
    wireCopy();
    loadVersion();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
