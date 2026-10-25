// Pure presentation logic for the reviewed correspondence ledger. A mapping is
// never counted as a proof merely because its source declaration is a theorem.
(function (root) {
  'use strict';
  function esc(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function label(value) { return String(value || '').replace(/_/g, ' '); }
  function index(data) {
    var bindings = {};
    (data.bindings || []).forEach(function (b) { bindings[b.id] = b; });
    return ['nodes', 'operators'].flatMap(function (key) {
      return ((data.inventory || {})[key] || []).map(function (row) {
        return Object.assign({}, row, { kind: key === 'nodes' ? 'node' : 'operator',
          bindings: (row.binding_ids || []).map(function (id) { return bindings[id]; }).filter(Boolean) });
      });
    });
  }
  function select(rows, query, kind, status) {
    var q = (query || '').toLowerCase().trim();
    return rows.filter(function (row) {
      return (!kind || row.kind === kind) && (!status || row.status === status) &&
        (!q || [row.id, row.domain || '', row.reason || '', JSON.stringify(row.bindings)].join(' ').toLowerCase().includes(q));
    });
  }
  function list(items) {
    return items && items.length ? '<ul>' + items.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('') + '</ul>' : '<p>None stated.</p>';
  }
  function bindingHtml(b) {
    var compiled = b.evidence.kind === 'compiled_bridge';
    var sources = b.sources.map(function (s) {
      var name = esc(s.name);
      return '<li>' + (/^https:\/\/github\.com\//.test(s.source_url) ? '<a href="' + esc(s.source_url) + '">' + name + '</a>' : name) +
        ' <span class="muted">(' + esc(s.kind) + ')</span></li>';
    }).join('');
    var conventions = Object.keys(b.conventions).map(function (key) {
      return '<div><dt>' + esc(label(key)) + '</dt><dd>' + esc(b.conventions[key]) + '</dd></div>';
    }).join('');
    var proof = compiled ? '<h4>Compiled declarations</h4>' + list(b.evidence.declarations) +
      '<p><a href="https://github.com/openmaterials-ai/openmaterials-ai/blob/1a382762b5eb6f0a82bdfe3c18eda3f94a720b44/' + esc(b.evidence.source_path) + '">Bridge source</a> · ' +
      '<a href="https://github.com/openmaterials-ai/openmaterials-ai/blob/1a382762b5eb6f0a82bdfe3c18eda3f94a720b44/' + esc(b.evidence.build_record) + '">Build record and axiom audit</a></p>' +
      '<p>The proof applies under the stated interpretation and hypotheses. It does not cover arbitrary tensors or verify numerical implementations.</p>' :
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
    var uid = '<p class="uid">Scientific UID: <code>' + esc(row.uid) + '</code></p>';
    var link = row.kind === 'node' ? '<p><a href="../../map/#node=' + encodeURIComponent(row.id) + '">Open quantity on the map</a></p>' : '';
    return '<details class="inventory-row"><summary><span class="row-kind">' + esc(row.kind) + '</span> <strong>' + esc(row.id) +
      '</strong> <span class="row-status">' + (row.status === 'gap' ? 'Gap' : row.bindings.length + ' correspondence' + (row.bindings.length === 1 ? '' : 's')) +
      '</span></summary>' + uid + link + formula + details + '</details>';
  }
  var api = { esc: esc, index: index, select: select, bindingHtml: bindingHtml, rowHtml: rowHtml };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FormulaBridge = api;
})(typeof self !== 'undefined' ? self : this);
