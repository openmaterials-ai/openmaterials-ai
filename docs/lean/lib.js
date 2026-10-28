// Pure, DOM-free logic for the Lean overview page. Shared by the browser and
// Node tests. Everything here reads the published docs/data/lean.json and
// docs/data/formula_bindings.json; nothing fetches, nothing touches the DOM.
(function (root) {
  'use strict';

  // Physlib ISQDimensionBase order, as omai.physlib_dimensions emits it.
  var BASES = ['mass', 'length', 'time', 'temperature', 'amount', 'current', 'luminousIntensity'];
  var SYMBOL = { mass: 'M', length: 'L', time: 'T', temperature: 'Θ', amount: 'N', current: 'I', luminousIntensity: 'J' };
  var SUP = { '-': '⁻', '/': 'ᐟ', '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹' };

  function superscript(n) {
    return String(n).split('').map(function (ch) { return SUP[ch] || ch; }).join('');
  }

  // [1, 2, -2, 0, 0, 0, 0] -> "M L² T⁻²"; all zero -> "1" (dimensionless).
  function formatDimension(exponents) {
    if (!Array.isArray(exponents) || exponents.length !== BASES.length) return null;
    var parts = [];
    BASES.forEach(function (base, i) {
      var e = exponents[i];
      if (e === 0 || e === '0') return;
      parts.push(SYMBOL[base] + (String(e) === '1' ? '' : superscript(e)));
    });
    return parts.length ? parts.join(' ') : '1';
  }

  // One row per encoded field, sorted by node id then field order.
  function nodeRows(lean) {
    var nodes = (lean && lean.nodes) || {};
    var rows = [];
    Object.keys(nodes).sort().forEach(function (id) {
      (nodes[id].fields || []).forEach(function (f) {
        rows.push({ node: id, field: f.field, declaration: f.declaration,
          dimension: formatDimension(f.exponents) });
      });
    });
    return rows;
  }

  // Counts straight from the published files; never hardcoded.
  function computeStats(lean, graph, bindings) {
    var cov = (bindings && bindings.coverage) || {};
    return {
      nodes: Object.keys((lean && lean.nodes) || {}).length,
      graphNodes: graph && Array.isArray(graph.nodes) ? graph.nodes.length : null,
      operatorsCompiled: cov.operators_proved !== undefined ? cov.operators_proved
        : cov.operators_compiled === undefined ? null : cov.operators_compiled,
      operatorsAnchored: cov.operators_compiled === undefined ? null : cov.operators_compiled,
      operatorsLocal: cov.operators_compiled_local === undefined ? 0 : cov.operators_compiled_local,
      operatorsTotal: cov.operators_total === undefined ? null : cov.operators_total,
      physlibRev: (lean && lean.physlib_rev) || null,
      toolchain: (lean && lean.lean_toolchain) || null,
      version: (lean && lean.version) || null
    };
  }

  var api = {
    BASES: BASES,
    formatDimension: formatDimension,
    nodeRows: nodeRows,
    computeStats: computeStats
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LeanLib = api;
})(typeof self !== 'undefined' ? self : this);
