// The map's Lean layer, as pure functions over graph.json, map_layers.json and the quantity positions
// the map lays out: where each formula mark sits, the wires through it, which marks a layer keeps, the
// layer and tag in the hash, Lean declaration search, and the rows of the table view.
// docs/map/lean-map.test.js runs it under node:test.
(function (root) {
  'use strict';
  const LAYERS = ['omai', 'lean'];
  const TAG = /^(paper|code|project):\S+$/;
  const R = 7, STACK = 14, LANE = 14;
  const RUNG_WORDS = {none: 'not in Lean', stated: 'stated in Lean, not proved',
    local: 'proved by a local Lean proof', physlib: 'proved, citing Physlib'};
  const n = (v) => Math.round(v * 10) / 10;

  function marks(graph, layers) {
    const none = {rung: 'none', bindings: []};
    return {
      quantities: new Map(graph.nodes.map((q) => [q.id, layers.quantities[q.id] || none])),
      formulas: new Map(Object.keys(layers.formulas).sort().map((op) => [op, layers.formulas[op]])),
    };
  }

  // The output a formula sits before: its first output, in id order, that has a position.
  function anchor(f, pos) { return f.outputs.slice().sort().find((o) => pos[o]); }

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
    const tierOf = (q) => q.tier || 'Other';
    graph.nodes.forEach((q) => { if (!order.includes(tierOf(q))) order.push(tierOf(q)); });
    const rows = [];
    for (const tier of order) {
      graph.nodes.filter((q) => tierOf(q) === tier).forEach((q) =>
        rows.push({tier, kind: 'quantity', id: q.id, rung: (layers.quantities[q.id] || {rung: 'none'}).rung}));
      Object.keys(layers.formulas).sort().filter((op) => layers.formulas[op].tier === tier).forEach((op) =>
        rows.push({tier, kind: 'formula', id: op, rung: layers.formulas[op].rung}));
    }
    return rows;
  }

  const api = {RUNG_WORDS, marks, slots, wires, lit, inLayer, state, fragment, leanIndex, searchLean, tableRows};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LeanMap = api;
})(typeof self !== 'undefined' ? self : this);
