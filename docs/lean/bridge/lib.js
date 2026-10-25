// Reference navigation is separate from the scientific graph and proof scope.
(function (root) {
  'use strict';
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function label(value) { return String(value || '').replace(/_/g, ' '); }
  function sourceHref(value) {
    try {
      var u = new URL(value);
      return u.protocol === 'https:' && u.hostname === 'github.com' && !u.port && !u.username && !u.password ? u.href : '';
    } catch (_) { return ''; }
  }
  function proofHref(path) {
    return /^lean\/bridge\/(?:[A-Za-z0-9_-]+\/)*[A-Za-z0-9_-]+\.(?:lean|json)$/.test(path || '') ?
      'https://github.com/openmaterials-ai/openmaterials-ai/blob/main/' + path : '';
  }
  function fragment(params) {
    var encoded = new URLSearchParams();
    Object.keys(params).forEach(function (key) { if (params[key]) encoded.set(key, params[key]); });
    return '#' + encoded.toString();
  }
  function parseFragment(hash) {
    var params = new URLSearchParams(String(hash || '').replace(/^#/, ''));
    if (params.has('node')) return { view: 'omai', kind: 'node', id: params.get('node') };
    if (params.has('operator')) return { view: 'omai', kind: 'operator', id: params.get('operator') };
    if (params.has('declaration') || params.has('module') || params.has('physlib')) {
      return { view: 'physlib', declaration: params.get('declaration') || '', module: params.get('module') || '' };
    }
    return { view: 'all' };
  }
  function provedTargets(binding, data) {
    if (binding.evidence.kind !== 'compiled_bridge') return [];
    if (binding.evidence.proved_targets) return binding.evidence.proved_targets;
    var operators = new Set((binding.targets || []).filter(function (t) { return t.kind === 'operator'; }).map(function (t) { return t.id; }));
    var outputs = new Set((((data || {}).inventory || {}).operators || []).filter(function (op) { return operators.has(op.id); }).flatMap(function (op) { return op.outputs; }));
    return (binding.targets || []).filter(function (t) { return t.kind === 'operator' || outputs.has(t.id); });
  }
  function index(data) {
    var bindings = {}, proved = new Set();
    (data.bindings || []).forEach(function (b) {
      bindings[b.id] = b;
      provedTargets(b, data).forEach(function (t) { proved.add(t.kind + ':' + t.id); });
    });
    return ['nodes', 'operators'].flatMap(function (key) {
      return ((data.inventory || {})[key] || []).map(function (row) {
        var kind = key === 'nodes' ? 'node' : 'operator';
        return Object.assign({}, row, { kind: kind, compiled: proved.has(kind + ':' + row.id),
          bindings: (row.binding_ids || []).map(function (id) { return bindings[id]; }).filter(Boolean) });
      });
    });
  }
  function select(rows, query, kind, status, evidence) {
    var q = (query || '').toLowerCase().trim();
    return rows.filter(function (row) {
      return (!kind || row.kind === kind) && (!status || row.status === status) &&
        (!evidence || (evidence === 'compiled' ? row.compiled : row.bindings.length && !row.compiled)) &&
        (!q || [row.id, row.domain || '', row.reason || '', JSON.stringify(row.bindings)].join(' ').toLowerCase().includes(q));
    });
  }
  function declarationIndex(data) {
    var declarations = new Map();
    (data.bindings || []).forEach(function (binding) {
      binding.sources.forEach(function (source) {
        var key = source.module + ':' + source.name;
        if (!declarations.has(key)) declarations.set(key, Object.assign({}, source, { bindings: [] }));
        var row = declarations.get(key);
        if (!row.bindings.some(function (b) { return b.id === binding.id; })) row.bindings.push(binding);
      });
    });
    return Array.from(declarations.values()).sort(function (a, b) { return (a.module + a.name).localeCompare(b.module + b.name); });
  }
  function selectDeclarations(rows, query, module, evidence, declaration) {
    var q = (query || '').toLowerCase().trim();
    return rows.map(function (row) {
      return Object.assign({}, row, {bindings:row.bindings.filter(function (b) { return !evidence || b.evidence.kind === evidence; })});
    }).filter(function (row) {
      return (!module || row.module === module) && (!declaration || row.name === declaration) &&
        row.bindings.length &&
        (!q || [row.name, row.module, JSON.stringify(row.bindings)].join(' ').toLowerCase().includes(q));
    });
  }
  function list(items) {
    return items && items.length ? '<ul>' + items.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '<p>None stated.</p>';
  }
  function sourceLink(source) {
    var href = sourceHref(source.source_url), name = esc(source.name);
    return href ? '<a href="' + esc(href) + '">' + name + '</a>' : name;
  }
  function targetLinks(targets, mapBase) {
    var seen = new Set();
    return targets.filter(function (t) {
      var key = t.kind + ':' + t.id;
      if (seen.has(key)) return false;
      seen.add(key); return true;
    }).map(function (target) {
      var params = {}; params[target.kind] = target.id;
      return '<li><span class="muted">' + (target.kind === 'node' ? 'Quantity' : 'Operator') + '</span> <a href="' +
        esc(mapBase + fragment(params)) + '">' + esc(target.id) + '</a></li>';
    }).join('');
  }
  function bindingHtml(b) {
    var compiled = b.evidence.kind === 'compiled_bridge';
    var sources = b.sources.map(function (s) {
      return '<li>' + sourceLink(s) + ' <span class="muted">(' + esc(s.kind) + ')</span> · <a href="' +
        esc(fragment({declaration: s.name, module: s.module})) + '">OMAI references</a></li>';
    }).join('');
    var conventions = Object.keys(b.conventions).map(function (key) {
      return '<div><dt>' + esc(label(key)) + '</dt><dd>' + esc(b.conventions[key]) + '</dd></div>';
    }).join('');
    var proof = compiled ? '<h4>Compiled declarations</h4>' + list(b.evidence.declarations) +
      '<p><a href="' + esc(proofHref(b.evidence.source_path)) + '">Bridge source</a> · ' +
      '<a href="' + esc(proofHref(b.evidence.build_record)) + '">Build record and axiom audit</a></p>' +
      '<p>The proof applies under the stated interpretation and hypotheses. It does not verify numerical implementations.</p>' :
      '<p class="notice gnote">Source correspondence only; this record contains no OMAI equivalence proof.</p>';
    return '<section class="binding"><h3>' + esc(b.id) + '</h3><p class="tags">' + esc(label(b.relation)) + ' · ' +
      (compiled ? 'Compiled bridge' : 'Source correspondence') + '</p><p>' + esc(b.statement) + '</p>' + proof +
      '<h4>Pinned upstream declarations</h4><ul>' + sources + '</ul><h4>Conditions</h4>' + list(b.conditions) +
      '<h4>Interpretation</h4><dl class="conventions">' + conventions + '</dl><h4>Remaining obligations</h4>' +
      list(b.remaining_obligations) + '</section>';
  }
  function rowHtml(row) {
    var details = row.bindings.map(bindingHtml).join('') || '<p class="notice gnote">' + esc(row.reason) + '</p>';
    var formula = row.formula_latex ? '<h3>Operator formula</h3><pre class="formula-source">' + esc(row.formula_latex) + '</pre>' : '';
    var params = {}; params[row.kind] = row.id;
    var link = '<p><a href="../../map/' + esc(fragment(params)) + '">Open ' + (row.kind === 'node' ? 'quantity' : 'operator') + ' on the map</a></p>';
    var status = row.status === 'gap' ? 'Gap' : row.compiled ? 'Compiled subject' : 'Referenced; not a compiled subject';
    var scope = !row.compiled && row.bindings.some(function (b) { return b.evidence.kind === 'compiled_bridge'; }) ?
      '<p class="notice gnote">This quantity participates in a compiled bridge, but its producing formula is not proved by that bridge.</p>' : '';
    return '<details class="inventory-row"><summary><span class="row-kind">' + (row.kind === 'node' ? 'Quantity' : 'Operator') + '</span> <strong>' + esc(row.id) +
      '</strong> <span class="row-status">' + status + '</span></summary><p class="uid">Scientific UID: <code>' + esc(row.uid) + '</code></p>' + link + scope + formula + details + '</details>';
  }
  function declarationHtml(row, options) {
    options = options || {};
    var mapBase = options.mapBase == null ? '../../map/' : options.mapBase;
    var bridgeBase = options.bridgeBase == null ? '' : options.bridgeBase;
    var records = row.bindings.map(function (b) {
      var compiled = b.evidence.kind === 'compiled_bridge';
      var first = b.targets[0], params = {}; params[first.kind] = first.id;
      return '<section class="binding"><h4>' + esc(b.id) + '</h4><p class="tags">' + esc(label(b.relation)) + ' · ' +
        (compiled ? 'Compiled bridge' : 'Source-only') + '</p><p>' + esc(b.statement) + '</p>' +
        '<ul>' + targetLinks(b.targets, mapBase) + '</ul><p><a href="' + esc(bridgeBase + fragment(params)) + '">Conditions and proof scope</a></p></section>';
    }).join('');
    return '<details class="inventory-row upstream-row"><summary><strong>' + esc(row.name) + '</strong> <span class="row-status">' +
      row.bindings.length + ' binding' + (row.bindings.length === 1 ? '' : 's') + '</span></summary><p class="uid">' + esc(row.module) + '</p><p>' +
      sourceLink(row) + ' <span class="muted">(' + esc(row.kind) + ')</span></p>' + records + '</details>';
  }
  function targetReferencesHtml(data, kind, id, bridgeBase) {
    var bindings = (data.bindings || []).filter(function (b) { return b.targets.some(function (t) { return t.kind === kind && t.id === id; }); });
    return bindings.map(function (binding) {
      var compiled = binding.evidence.kind === 'compiled_bridge';
      var subject = provedTargets(binding, data).some(function (t) { return t.kind === kind && t.id === id; });
      var badge = compiled ? (subject ? 'Compiled subject' : 'Input/reference in a compiled bridge') : 'Source-only';
      var params = {}; params[kind] = id;
      return '<section class="formal-binding"><p><strong>' + esc(binding.id) + '</strong><br><span class="formal-badge">' + badge + '</span></p><ul>' +
        binding.sources.map(function (s) { return '<li><a href="' + esc(fragment({declaration:s.name,module:s.module})) + '">' + esc(s.name) +
          '</a> · <a href="' + esc(sourceHref(s.source_url)) + '">source</a></li>'; }).join('') +
        '</ul><p><a href="' + esc(bridgeBase + fragment(params)) + '">Conditions and proof scope</a></p></section>';
    }).join('');
  }
  function mapSelection(hash, data) {
    var state = parseFragment(hash);
    if (state.view !== 'omai') return state;
    var key = state.kind === 'node' ? 'nodes' : 'operators';
    var row = (((data || {}).inventory || {})[key] || []).find(function (r) { return r.id === state.id; });
    if (!row) return {view:'missing',kind:state.kind,id:state.id};
    return Object.assign({}, state, {nodes:state.kind === 'node' ? [row.id] : row.outputs.slice(), row:row});
  }
  var api = { esc:esc, index:index, select:select, bindingHtml:bindingHtml, rowHtml:rowHtml,
    sourceHref:sourceHref, proofHref:proofHref, fragment:fragment, parseFragment:parseFragment,
    provedTargets:provedTargets, declarationIndex:declarationIndex, selectDeclarations:selectDeclarations,
    declarationHtml:declarationHtml, targetReferencesHtml:targetReferencesHtml, mapSelection:mapSelection };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FormulaBridge = api;
})(typeof self !== 'undefined' ? self : this);
