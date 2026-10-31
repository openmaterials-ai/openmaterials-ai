// The map's Lean layer, as pure functions over graph.json, map_layers.json and the quantity positions
// the map lays out: where each formula mark sits, the wires through it, which marks a layer keeps, the
// layer and tag in the hash, Lean declaration search, and the rows of the table view.
// docs/map/lean-map.test.js runs it under node:test.
(function (root) {
  'use strict';
  const LAYERS = ['omai', 'lean'];
  const TAG = /^(paper|code|project):\S+$/;
  const R = 7, STACK = 14, LANE = 14;
  // A theorem may state a property of a formula rather than the formula; the binding's statement says which.
  const RUNG_WORDS = {none: 'no Lean theorem covers it', stated: 'Physlib identification, no theorem',
    local: 'Lean theorem on OMAI definitions', physlib: 'Lean theorem on Physlib definitions'};
  const rungOf = (r) => (r && Object.prototype.hasOwnProperty.call(RUNG_WORDS, r) ? r : 'none');
  const n = (v) => Math.round(v * 10) / 10;

  // Quantities from graph.json with their Lean rungs; formulas from map_layers.json, or, when that file is
  // missing, from the graph's computation links grouped by operator, all at rung none.
  function marks(graph, layers) {
    const q = (id) => { const r = layers.quantities[id] || {}; return Object.assign({bindings: [], related: []}, r, {rung: rungOf(r.rung)}); };
    let formulas = Object.keys(layers.formulas).sort().map((op) => [op, Object.assign({}, layers.formulas[op], {rung: rungOf(layers.formulas[op].rung)})]);
    if (!formulas.length) {
      const by = new Map(), tier = new Map(graph.nodes.map((n) => [n.id, n.tier || 'Other']));
      for (const l of graph.links) {
        if (l.kind === 'param' || !l.op) continue;
        const f = by.get(l.op) || by.set(l.op, {inputs: [], outputs: [], rung: 'none', bindings: []}).get(l.op);
        if (!f.inputs.includes(l.source)) f.inputs.push(l.source);
        if (!f.outputs.includes(l.target)) f.outputs.push(l.target);
      }
      formulas = [...by.keys()].sort().map((op) => [op, Object.assign(by.get(op), {tier: tier.get(by.get(op).outputs[0])})]);
    }
    return {quantities: new Map(graph.nodes.map((n) => [n.id, q(n.id)])), formulas: new Map(formulas)};
  }

  // The output a formula sits before: its first output, in catalog order, that has a position.
  function anchor(f, pos) { return f.outputs.find((o) => pos[o]); }

  // Formula i of the k that produce one quantity sits LANE left of its box, the k stacked about its center.
  function slots(formulas, pos) {
    const by = new Map();
    for (const [op, f] of formulas) {
      const a = anchor(f, pos);
      if (a) (by.get(a) || by.set(a, []).get(a)).push(op);
    }
    const out = new Map();
    for (const [a, ops] of by) {
      const p = pos[a];
      ops.sort().forEach((op, i) => out.set(op, {x: n(p.x - p.w / 2 - LANE), y: n(p.y + (i - (ops.length - 1) / 2) * STACK), output: a}));
    }
    return out;
  }

  function curve(x0, y0, x1, y1) {
    if (x1 >= x0) {
      const dx = Math.max(24, (x1 - x0) * 0.5);
      return 'M' + n(x0) + ' ' + n(y0) + ' C' + n(x0 + dx) + ' ' + n(y0) + ' ' + n(x1 - dx) + ' ' + n(y1) + ' ' + n(x1) + ' ' + n(y1);
    }
    const my = (y0 + y1) / 2 - Math.max(50, Math.abs(y1 - y0) * 0.3 + 50);
    return 'M' + n(x0) + ' ' + n(y0) + ' C' + n(x0 + 70) + ' ' + n(my) + ' ' + n(x1 - 70) + ' ' + n(my) + ' ' + n(x1) + ' ' + n(y1);
  }

  // Inputs run into the circle, the circle into each result. An input to the right of its formula
  // leaves its box on the left and enters the circle from above or below.
  function wires(formulas, pos, slot) {
    const out = [];
    for (const [op, f] of formulas) {
      const s = slot.get(op);
      if (!s) continue;
      for (const i of new Set(f.inputs)) {
        const a = pos[i];
        if (!a || f.outputs.includes(i)) continue;
        let d;
        if (s.x - R >= a.x + a.w / 2) d = curve(a.x + a.w / 2, a.y, s.x - R, s.y);
        else {
          const x0 = a.x - a.w / 2, sg = a.y < s.y ? -1 : 1;
          d = 'M' + n(x0) + ' ' + n(a.y) + ' C' + n(x0 - 40) + ' ' + n(a.y) + ' ' + n(s.x) + ' ' + n(s.y + sg * 45) + ' ' + n(s.x) + ' ' + n(s.y + sg * R);
        }
        out.push({op, from: i, to: op, kind: 'in', d});
      }
      for (const o of f.outputs) {
        const b = pos[o];
        if (!b) continue;
        const d = o === s.output ? 'M' + n(s.x + R) + ' ' + n(s.y) + ' L' + n(b.x - b.w / 2) + ' ' + n(b.y)
          : curve(s.x + R, s.y, b.x - b.w / 2, b.y);
        out.push({op, from: op, to: o, kind: 'out', d});
      }
    }
    return out;
  }

  // The share rule, loosened to one input: a formula lights with its result and one of its inputs.
  function lit(f, ids) {
    return f.outputs.some((o) => ids.has(o)) && (!f.inputs.length || f.inputs.some((i) => ids.has(i)));
  }

  function inLayer(rung, layer) { return layer !== 'lean' || rung !== 'none'; }

  // {layer, tag, rest, unknown}: rest holds every other parameter, unknown what could not be read.
  function state(hash) {
    const rest = new URLSearchParams(String(hash || '').replace(/^#/, '')), unknown = [];
    let layer = 'omai', tag = null;
    if (rest.has('layer')) {
      const v = rest.get('layer');
      if (LAYERS.includes(v)) layer = v; else unknown.push('layer=' + v);
      rest.delete('layer');
    }
    if (rest.has('tag')) {
      const v = rest.get('tag');
      if (TAG.test(v)) tag = v; else unknown.push('tag=' + v);
      rest.delete('tag');
    }
    return {layer, tag, rest, unknown};
  }

  // A fragment with the layer and tag first; the default layer and empty values are left out.
  function fragment(base, s) {
    const p = new URLSearchParams();
    if (s && s.layer && s.layer !== 'omai') p.set('layer', s.layer);
    if (s && s.tag) p.set('tag', s.tag);
    const rest = base instanceof URLSearchParams ? base
      : typeof base === 'string' ? new URLSearchParams(base.replace(/^#/, ''))
      : new URLSearchParams(Object.entries(base || {}).filter(([, v]) => v));
    rest.forEach((v, k) => { if (k !== 'layer' && k !== 'tag' && v) p.append(k, v); });
    const q = p.toString().replace(/%3A/gi, ':');
    return q ? '#' + q : '';
  }

  // Every Lean declaration a binding names, with the marks that binding proves or names.
  function leanIndex(layers) {
    const ix = new Map();
    const own = (kind, id) => (layers[kind][id].bindings || []);
    for (const [b, entry] of Object.entries(layers.bindings)) {
      const qs = Object.keys(layers.quantities).filter((id) => own('quantities', id).includes(b));
      const fs = Object.keys(layers.formulas).filter((id) => own('formulas', id).includes(b));
      for (const d of entry.physlib.concat(entry.bridge)) {
        const row = ix.get(d.name) || ix.set(d.name, {key: d.name.toLowerCase(), quantities: new Set(), formulas: new Set()}).get(d.name);
        qs.forEach((id) => row.quantities.add(id));
        fs.forEach((id) => row.formulas.add(id));
      }
    }
    return [...ix.values()];
  }

  function searchLean(ix, q) {
    const v = String(q || '').trim().toLowerCase(), quantities = new Set(), formulas = new Set();
    if (v.length >= 3) for (const row of ix) if (row.key.includes(v)) {
      row.quantities.forEach((id) => quantities.add(id));
      row.formulas.forEach((id) => formulas.add(id));
    }
    return {quantities: [...quantities], formulas: [...formulas]};
  }

  // One row per quantity and formula, by tier in map order, quantities first within a tier.
  function tableRows(graph, layers) {
    const order = graph.tiers.slice().sort((a, b) => a.order - b.order).map((t) => t.name);
    const known = new Set(order), tierOf = (q) => (known.has(q.tier) ? q.tier : 'Other');
    if (graph.nodes.some((q) => tierOf(q) === 'Other') && !known.has('Other')) order.push('Other');
    const rows = [];
    for (const tier of order) {
      graph.nodes.filter((q) => tierOf(q) === tier).forEach((q) =>
        rows.push({tier, kind: 'quantity', id: q.id, rung: rungOf((layers.quantities[q.id] || {}).rung)}));
      Object.keys(layers.formulas).sort().filter((op) => (known.has(layers.formulas[op].tier) ? layers.formulas[op].tier : 'Other') === tier).forEach((op) =>
        rows.push({tier, kind: 'formula', id: op, rung: rungOf(layers.formulas[op].rung)}));
    }
    return rows;
  }

  const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const link = (u, inner) => (/^https:\/\//.test(u || '') ? '<a href="' + esc(u) + '">' + inner + '</a>' : inner);
  const items = (xs) => (xs && xs.length ? '<ul>' + xs.map((x) => '<li>' + x + '</li>').join('') + '</ul>' : '');
  const VIA = {formulas: 'Every formula that produces it has a Lean theorem whose binding includes this quantity. ' +
      'Each statement below says whether the theorem is about the formula itself or a property of it.',
    quantity: 'A Lean theorem is about this quantity.',
    partial: 'Not every formula that produces it has a Lean theorem that includes this quantity.'};
  const ROLE = {stated: 'Identifies a Physlib declaration, no theorem', output: 'Theorem about a formula that produces it, not about this quantity',
    reads: 'Uses it as an input', related: 'Related Physlib concept, no theorem'};
  function joinAnd(xs) { return xs.length < 2 ? xs.join('') : xs.slice(0, -1).join(', ') + ' and ' + xs[xs.length - 1]; }

  // The Lean block of a quantity's or formula's panel: its rung, then every binding that names it, each
  // with its statement, Lean declarations, cited Physlib declarations, conditions and what it leaves
  // open, then the audited axioms. Statements and conditions come from formula_bindings.json (formal);
  // without it the rung and the declarations still show. FB is docs/lean/bridge/lib.js.
  function leanPanel({kind, id, layers, formal, FB, bridgeBase = '../lean/bridge/'}) {
    const m0 = (kind === 'node' ? layers.quantities : layers.formulas)[id] || {};
    const mark = Object.assign({bindings: [], related: []}, m0, {rung: rungOf(m0.rung)});
    const makes = (op) => kind === 'node' && ((layers.formulas[op] || {}).outputs || []).includes(id);
    const own = new Set(mark.bindings || []), related = new Set(mark.related || []);
    const byId = new Map(((formal && formal.bindings) || []).map((b) => [b.id, b]));
    const named = formal ? formal.bindings.filter((b) => b.targets.some((t) => t.kind === kind && t.id === id)).map((b) => b.id)
      : [...own, ...related];
    const role = (b) => {
      const e = layers.bindings[b] || {}, f = byId.get(b);
      const ev = e.evidence || (f && f.evidence.kind), rel = e.relation || (f && f.relation);
      if (related.has(b) || (ev === 'source_correspondence' && rel === 'conceptual')) return 'related';
      if (ev === 'source_correspondence') return 'stated';
      if (own.has(b)) return rel === 'local' ? 'local' : 'physlib';
      if (f && FB.provedTargets(f, formal).some((t) => t.kind === 'operator' && makes(t.id))) return 'output';
      return 'reads';
    };
    const rank = {physlib: 0, local: 1, stated: 2, output: 3, reads: 4, related: 5};
    const partial = kind === 'node' && mark.rung === 'none' &&
      Object.keys(layers.formulas).some((op) => makes(op) && ['local', 'physlib'].includes(rungOf(layers.formulas[op].rung)));
    const ids = [...new Set(named)].sort((a, b) => rank[role(a)] - rank[role(b)] || (a < b ? -1 : 1));
    let h = '<div class="om-panel-label">Lean</div><p class="lean-rung"><i class="sw rung-' + mark.rung + '"></i> ' +
      esc(RUNG_WORDS[mark.rung].charAt(0).toUpperCase() + RUNG_WORDS[mark.rung].slice(1)) + '.' +
      (kind === 'node' && VIA[partial ? 'partial' : mark.via] ? ' ' + VIA[partial ? 'partial' : mark.via] : '') + '</p>';
    if (!formal) h += '<p class="muted">Statements and conditions did not load (formula_bindings.json).</p>';
    for (const b of ids) {
      const e = layers.bindings[b] || {physlib: [], bridge: []}, f = byId.get(b), r = role(b);
      h += '<section class="lean-binding"><p><strong>' + esc(b) + '</strong><br><span class="formal-badge">' +
        esc(ROLE[r] || RUNG_WORDS[r].charAt(0).toUpperCase() + RUNG_WORDS[r].slice(1)) + '</span></p>';
      if (f) h += '<p>' + esc(f.statement) + '</p>';
      const bridge = e.bridge.length ? e.bridge.map((d) => link(d.url, '<code>' + esc(d.name) + '</code>') + ' <span class="muted">' + esc(d.module) + '</span>')
        : ((f && f.evidence.declarations) || []).map((n) => '<code>' + esc(n) + '</code>');
      if (bridge.length) h += '<div class="om-panel-label">Lean declarations</div>' + items(bridge);
      const cited = (e.physlib.length ? e.physlib : ((f && f.sources) || []).map((x) => ({name: x.name, module: x.module, url: x.source_url})))
        .map((d) => '<a href="' + esc(FB.fragment({declaration: d.name, module: d.module})) + '"><code>' + esc(d.name) + '</code></a> · ' +
          link(d.url, 'source') + ' <span class="muted">' + esc(d.module) + '</span>');
      if (cited.length) h += '<div class="om-panel-label">' + (r === 'stated' || r === 'related' ? 'Related Physlib declarations' : 'Physlib declarations cited') + '</div>' + items(cited);
      if (f) h += (items((f.conditions || []).map(esc)) ? '<div class="om-panel-label">Conditions</div>' + items(f.conditions.map(esc)) : '') +
        (items((f.remaining_obligations || []).map(esc)) ? '<div class="om-panel-label">Not covered</div>' + items(f.remaining_obligations.map(esc)) : '');
      h += '</section>';
    }
    if (ids.some((b) => (layers.bindings[b] || {bridge: []}).bridge.length) && layers.axioms)
      h += '<p class="muted">The bridge axiom audit finds no axiom beyond ' + joinAnd(layers.axioms.map((a) => '<code>' + esc(a) + '</code>')) + ' in the Lean declarations above, and no sorry.</p>';
    if (!ids.length) h += '<p class="muted">No reviewed Lean binding names it.</p>';
    const params = {}; params[kind] = id;
    h += '<p><a href="' + esc(bridgeBase + FB.fragment(params)) + '">Conditions and coverage</a> · <a href="#physlib=1">Browse upstream declarations</a></p>';
    return h;
  }

  // A tag's area: a paper's or project's reported quantities with the quantities its curated formulas touch,
  // or a code's represented quantities with the formulas whose results and inputs it all represents.
  // null for an unknown tag or an empty area.
  function area(key, layers, codes, graph) {
    const m = /^(paper|project|code):(.+)$/.exec(key || ''), ids = new Set(graph.nodes.map((n) => n.id));
    if (!m) return null;
    const quantities = new Set(), formulas = new Set();
    if (m[1] === 'code') {
      if (!codes[m[2]]) return null;
      Object.keys(codes[m[2]]).filter((id) => ids.has(id)).forEach((id) => quantities.add(id));
      for (const [op, f] of Object.entries(layers.formulas))
        if (f.outputs.every((o) => quantities.has(o)) && f.inputs.every((i) => quantities.has(i))) formulas.add(op);
    } else {
      const t = (layers.tags || {})[key];
      if (!t) return null;
      t.quantities.filter((id) => ids.has(id)).forEach((id) => quantities.add(id));
      for (const op of t.formulas) {
        const f = layers.formulas[op];
        if (!f) continue;
        formulas.add(op);
        f.inputs.concat(f.outputs).filter((id) => ids.has(id)).forEach((id) => quantities.add(id));
      }
    }
    return quantities.size || formulas.size ? {quantities, formulas} : null;
  }

  // The box around an area's quantity boxes and formula circles, with 24 units of margin; null when none is placed.
  function frame(a, pos, slot) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const id of a.quantities) { const p = pos[id]; if (!p) continue;
      x0 = Math.min(x0, p.x - p.w / 2); y0 = Math.min(y0, p.y - p.h / 2); x1 = Math.max(x1, p.x + p.w / 2); y1 = Math.max(y1, p.y + p.h / 2); }
    for (const op of a.formulas) { const c = slot.get(op); if (!c) continue;
      x0 = Math.min(x0, c.x - R); y0 = Math.min(y0, c.y - R); x1 = Math.max(x1, c.x + R); y1 = Math.max(y1, c.y + R); }
    return x1 < x0 ? null : {x: x0 - 24, y: y0 - 24, w: x1 - x0 + 48, h: y1 - y0 + 48};
  }

  // The words on the frame's tab: kind, name, what the tag reports, and its formulas with a Lean theorem.
  function tabText(key, tag, a, formulas) {
    const kind = key.split(':')[0], label = Array.from(tag.label || key);
    const parts = [kind, label.length > 48 ? label.slice(0, 47).join('').trimEnd() + '…' : label.join('')];
    if (tag.values != null) parts.push(tag.values + (tag.values === 1 ? ' value' : ' values'));
    else if (kind === 'code') parts.push(a.quantities.size + (a.quantities.size === 1 ? ' quantity' : ' quantities'));
    if (a.formulas.size) {
      const with_ = [...a.formulas].filter((op) => ['local', 'physlib'].includes((formulas.get(op) || {}).rung)).length;
      parts.push(with_ + ' / ' + a.formulas.size + ' formulas with a Lean theorem');
    }
    return parts.join(' · ');
  }

  const api = {RUNG_WORDS, marks, slots, wires, lit, inLayer, state, fragment, leanIndex, searchLean, tableRows, leanPanel, area, frame, tabText};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LeanMap = api;
})(typeof self !== 'undefined' ? self : this);
