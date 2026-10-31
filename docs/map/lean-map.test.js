// The map's Lean helpers (lean-map.js) on the committed data and on a fixture of unusual shapes.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const L = require('./lean-map.js');
const graph = JSON.parse(fs.readFileSync(__dirname + '/../data/graph.json', 'utf8'));
const layers = JSON.parse(fs.readFileSync(__dirname + '/../data/map_layers.json', 'utf8'));

// Q has three formulas, P is produced with R by one two-output formula, S and T come from zero-input
// formulas, C is a parameter, and Z reads itself.
const box = (x, y) => ({x, y, w: 80, h: 44});
const pos = {S: box(100, 100), T: box(100, 200), C: box(100, 300), Q: box(400, 100), P: box(400, 200),
  R: box(700, 150), Z: box(700, 300)};
const fixture = {
  quantities: new Map(Object.keys(pos).map((id) => [id, {rung: 'none', bindings: []}])),
  formulas: new Map([
    ['provide_s', {inputs: [], outputs: ['S'], rung: 'none'}],
    ['provide_t', {inputs: [], outputs: ['T'], rung: 'none'}],
    ['q_a', {inputs: ['S'], outputs: ['Q'], rung: 'local'}],
    ['q_b', {inputs: ['T'], outputs: ['Q'], rung: 'none'}],
    ['q_c', {inputs: ['S', 'T'], outputs: ['Q'], rung: 'physlib'}],
    ['pr', {inputs: ['Q', 'R'], outputs: ['R', 'P'], rung: 'none'}],
    ['z', {inputs: ['Z', 'Q'], outputs: ['Z'], rung: 'none'}],
  ]),
};

test('a formula sits left of its first output, inside that output row', () => {
  const s = L.slots(fixture.formulas, pos);
  assert.equal(s.size, fixture.formulas.size);
  for (const [op, f] of fixture.formulas) {
    const o = pos[[...f.outputs].sort()[0]], p = s.get(op);
    assert.ok(p.x + 7 < o.x - o.w / 2, op);
    assert.ok(Math.abs(p.y - o.y) + 7 <= o.h / 2, op);
  }
  const q = ['q_a', 'q_b', 'q_c'].map((op) => s.get(op).y);
  assert.equal(new Set(q).size, 3);
  assert.equal(s.get('pr').y, pos.P.y);
});

test('wires join existing marks and a self-input draws none', () => {
  const s = L.slots(fixture.formulas, pos), ws = L.wires(fixture.formulas, pos, s);
  for (const w of ws) {
    const ends = w.kind === 'in' ? [w.from, w.to] : [w.to, w.from];
    assert.ok(pos[ends[0]] && fixture.formulas.has(ends[1]), JSON.stringify(w));
    assert.match(w.d, /^M[-\d.]+ [-\d.]+ [CL]/);
  }
  assert.ok(!ws.some((w) => w.op === 'z' && w.kind === 'in' && w.from === 'Z'));
  assert.equal(ws.filter((w) => w.op === 'pr' && w.kind === 'out').length, 2);
  assert.equal(ws.filter((w) => w.op === 'provide_s').length, 1);
});

test('a formula is lit when its result and one input are, or when it has no inputs', () => {
  const f = fixture.formulas;
  assert.equal(L.lit(f.get('q_c'), new Set(['Q', 'T'])), true);
  assert.equal(L.lit(f.get('q_c'), new Set(['Q'])), false);
  assert.equal(L.lit(f.get('q_c'), new Set(['S', 'T'])), false);
  assert.equal(L.lit(f.get('provide_s'), new Set(['S'])), true);
});

test('layers keep every mark on omai and the marks in Lean on lean', () => {
  for (const r of ['none', 'stated', 'local', 'physlib']) assert.equal(L.inLayer(r, 'omai'), true);
  assert.deepEqual(['none', 'stated', 'local', 'physlib'].map((r) => L.inLayer(r, 'lean')), [false, true, true, true]);
});

test('the hash carries layer and tag and reports what it cannot read', () => {
  const s = L.state('#layer=lean&node=Temperature');
  assert.equal(s.layer, 'lean');
  assert.equal(L.fragment(s.rest, s), '#layer=lean&node=Temperature');
  assert.equal(L.fragment('#node=Temperature', {layer: 'omai', tag: null}), '#node=Temperature');
  assert.equal(L.fragment({operator: 'solve_bte'}, {layer: 'lean', tag: 'paper:ptse2-2021-donadio'}),
    '#layer=lean&tag=paper:ptse2-2021-donadio&operator=solve_bte');
  assert.equal(L.fragment('', {layer: 'omai'}), '');
  const bad = L.state('#layer=bogus&tag=nope&node=X');
  assert.equal(bad.layer, 'omai');
  assert.equal(bad.tag, null);
  assert.deepEqual(bad.unknown, ['layer=bogus', 'tag=nope']);
  assert.equal(bad.rest.get('node'), 'X');
});

test('marks read every quantity and formula of the data', () => {
  const m = L.marks(graph, layers);
  assert.equal(m.quantities.size, graph.nodes.length);
  assert.equal(m.formulas.size, Object.keys(layers.formulas).length);
  assert.equal(m.quantities.get('Temperature').rung, layers.quantities.Temperature.rung);
});

test('Lean declaration names find their marks', () => {
  const ix = L.leanIndex(layers);
  assert.ok(L.searchLean(ix, 'absoluteTemperature_roundtrip').quantities.includes('Temperature'));
  assert.ok(L.searchLean(ix, 'OMAI.PhyslibBridge.absoluteTemperature_beta_pos').quantities.includes('Temperature'));
  assert.deepEqual(L.searchLean(ix, 'no such declaration'), {quantities: [], formulas: []});
  assert.deepEqual(L.searchLean(ix, 'Te'), {quantities: [], formulas: []});
});

test('the table lists every mark once, in tier order, with its rung in words', () => {
  const rows = L.tableRows(graph, layers);
  assert.equal(rows.length, graph.nodes.length + Object.keys(layers.formulas).length);
  assert.equal(new Set(rows.map((r) => r.kind + ':' + r.id)).size, rows.length);
  const order = graph.tiers.slice().sort((a, b) => a.order - b.order).map((t) => t.name);
  const seen = rows.map((r) => order.indexOf(r.tier));
  assert.deepEqual(seen, seen.slice().sort((a, b) => a - b));
  assert.deepEqual(Object.keys(L.RUNG_WORDS), ['none', 'stated', 'local', 'physlib']);
});

const FB = require('../lean/bridge/lib.js');
const formal = JSON.parse(fs.readFileSync(__dirname + '/../data/formula_bindings.json', 'utf8'));
const inOrder = (h, parts) => {
  const at = parts.map((s) => h.indexOf(s));
  assert.ok(at.every((i) => i >= 0), JSON.stringify(parts.filter((s, i) => at[i] < 0)));
  assert.deepEqual(at, at.slice().sort((a, b) => a - b));
};

test('the Lean panel reads rung, statement, declarations, conditions, what is not covered, axioms', () => {
  inOrder(L.leanPanel({kind: 'node', id: 'Temperature', layers, formal, FB}),
    ['Lean theorem citing Physlib', 'A nonnegative OMAI', '>Lean declarations<', '>Physlib declarations cited<',
      '>Conditions<', '>Not covered<', 'axioms']);
  inOrder(L.leanPanel({kind: 'operator', id: 'solve_bte[bte_solver=direct_inverse]', layers, formal, FB}),
    ['Lean theorem over Mathlib', '>Lean declarations<', '>Conditions<', '>Not covered<', 'axioms']);
});

test('without the bindings file the panel still names the rung and the declarations', () => {
  const h = L.leanPanel({kind: 'node', id: 'Temperature', layers, formal: null, FB});
  assert.match(h, /Lean theorem citing Physlib/);
  assert.match(h, /absoluteTemperature_roundtrip/);
  assert.match(h, /did not load/);
});

test('a binding that only reads a quantity says so, and a conceptual one is a related concept', () => {
  const mv = L.leanPanel({kind: 'node', id: 'MolarVolume', layers, formal, FB});
  assert.match(mv, /no reviewed Lean theorem/i);
  assert.match(mv, /Reads it as an input/);
  assert.match(L.leanPanel({kind: 'node', id: 'Structure', layers, formal, FB}), /Source-only: a related Physlib concept/);
});

test('panel text from the data is escaped', () => {
  const f = structuredClone(formal);
  f.bindings.find((b) => b.id === 'absolute-temperature').statement = '<img src=x onerror=alert(1)>';
  const h = L.leanPanel({kind: 'node', id: 'Temperature', layers, formal: f, FB});
  assert.doesNotMatch(h, /<img/);
  assert.match(h, /&lt;img/);
});
