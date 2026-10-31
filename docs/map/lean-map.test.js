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
    const o = pos[f.outputs[0]], p = s.get(op);
    assert.ok(p.x + 7 < o.x - o.w / 2, op);
    assert.ok(Math.abs(p.y - o.y) + 7 <= o.h / 2, op);
  }
  const q = ['q_a', 'q_b', 'q_c'].map((op) => s.get(op).y);
  assert.equal(new Set(q).size, 3);
  assert.equal(s.get('pr').output, 'R');   // the first output in catalog order
  assert.equal(s.get('pr').y, pos.R.y);
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
    ['Lean theorem on Physlib definitions', 'A nonnegative OMAI', '>Lean declarations<', '>Physlib declarations cited<',
      '>Conditions<', '>Not covered<', 'axiom audit']);
  inOrder(L.leanPanel({kind: 'operator', id: 'solve_bte[bte_solver=direct_inverse]', layers, formal, FB}),
    ['Lean theorem on OMAI definitions', '>Lean declarations<', '>Conditions<', '>Not covered<', 'axiom audit']);
});

test('without the bindings file the panel still names the rung and the declarations', () => {
  const h = L.leanPanel({kind: 'node', id: 'Temperature', layers, formal: null, FB});
  assert.match(h, /Lean theorem on Physlib definitions/);
  assert.match(h, /absoluteTemperature_roundtrip/);
  assert.match(h, /did not load/);
});

test('a binding that only reads a quantity says so, and a conceptual one is a related concept', () => {
  const mv = L.leanPanel({kind: 'node', id: 'MolarVolume', layers, formal, FB});
  assert.match(mv, /No Lean theorem covers it/);
  assert.match(mv, /Uses it as an input/);
  const st = L.leanPanel({kind: 'node', id: 'Structure', layers, formal, FB});
  assert.match(st, /Related Physlib concept, no theorem/);
  assert.match(st, />Related Physlib declarations</);
  assert.doesNotMatch(st, />Physlib declarations cited</);
});

test('panel text from the data is escaped', () => {
  const f = structuredClone(formal);
  f.bindings.find((b) => b.id === 'absolute-temperature').statement = '<img src=x onerror=alert(1)>';
  const h = L.leanPanel({kind: 'node', id: 'Temperature', layers, formal: f, FB});
  assert.doesNotMatch(h, /<img/);
  assert.match(h, /&lt;img/);
});

test('a quantity outside its formulas\' theorems says why, and an excluded output is named as such', () => {
  const bm = L.leanPanel({kind: 'node', id: 'BulkModulus', layers, formal, FB});
  assert.match(bm, /No Lean theorem covers it\. Not every formula that produces it has a Lean theorem that includes this quantity\./);
  assert.match(bm, /Theorem about a formula that produces it, not about this quantity/);
  assert.match(L.leanPanel({kind: 'node', id: 'Frequency', layers, formal, FB}), /Not every formula that produces it/);
  const k = L.leanPanel({kind: 'node', id: 'ThermalConductivity[bte_solver=rta]', layers, formal, FB});
  assert.match(k, /whose binding includes this quantity\. Each statement below says whether the theorem is about the formula itself or a property of it\./);
  assert.match(L.leanPanel({kind: 'node', id: 'Temperature', layers, formal, FB}), /The bridge axiom audit finds no axiom beyond/);
});

test('the words never say proved and name the rungs by what the theorem rests on', () => {
  for (const v of Object.values(L.RUNG_WORDS)) assert.doesNotMatch(v, /prove/i);
  assert.deepEqual(L.RUNG_WORDS, {none: 'no Lean theorem covers it', stated: 'Physlib identification, no theorem',
    local: 'Lean theorem on OMAI definitions', physlib: 'Lean theorem on Physlib definitions'});
  const all = Object.keys(layers.quantities).map((id) => L.leanPanel({kind: 'node', id, layers, formal: null, FB})).join('');
  assert.doesNotMatch(all, /\bprove[sd]?\b/i);
});

test('an unknown rung reads as none, and without map_layers the formulas come from the graph', () => {
  const bad = structuredClone(layers);
  bad.quantities.Temperature.rung = 'bogus';
  assert.equal(L.marks(graph, bad).quantities.get('Temperature').rung, 'none');
  const bare = L.marks(graph, {quantities: {}, formulas: {}, tiers: [], bindings: {}});
  const ops = new Set(graph.links.filter((l) => l.kind !== 'param').map((l) => l.op));
  assert.equal(bare.formulas.size, ops.size);
  assert.ok([...bare.formulas.values()].every((f) => f.rung === 'none' && f.outputs.length && f.tier));
});

test('a quantity with a tier the map does not list sits under Other in the table', () => {
  const g = structuredClone(graph);
  g.nodes[0].tier = 'Nowhere';
  assert.equal(L.tableRows(g, layers).find((r) => r.id === g.nodes[0].id).tier, 'Other');
});

const codes = JSON.parse(fs.readFileSync(__dirname + '/../data/codes.json', 'utf8'));

test('a paper area is its reported quantities, its formulas\' results, and only the inputs its formulas produce', () => {
  const lay = structuredClone(layers);
  const kappa = 'contract_kappa[bte_solver=rta]', solve = 'solve_bte[bte_solver=rta]';
  lay.tags['paper:x'] = {label: 'X', values: 1, quantities: ['ThermalConductivity'], formulas: [kappa, solve]};
  const a = L.area('paper:x', lay, codes, graph);
  assert.deepEqual([...a.formulas].sort(), [kappa, solve]);
  for (const o of lay.formulas[kappa].outputs.concat(lay.formulas[solve].outputs)) assert.ok(a.quantities.has(o), o);
  for (const i of lay.formulas[kappa].inputs) assert.equal(a.quantities.has(i), lay.formulas[solve].outputs.includes(i) || i === 'ThermalConductivity', i);
  const pt = L.area('paper:ptse2-2021-donadio', layers, codes, graph);
  assert.ok(!pt.quantities.has('Linewidth[channel=isotope]') && !pt.quantities.has('Linewidth[channel=boundary]'));
});

test('a code area keeps the formulas whose results and inputs the code all represents', () => {
  const a = L.area('code:kaldo', layers, codes, graph);
  assert.equal(a.quantities.size, Object.keys(codes.kaldo).filter((id) => graph.nodes.some((n) => n.id === id)).length);
  assert.ok(a.formulas.size > 0);
  for (const op of a.formulas) {
    const f = layers.formulas[op];
    assert.ok(f.outputs.every((o) => a.quantities.has(o)) && f.inputs.every((i) => a.quantities.has(i)), op);
  }
});

test('an unknown tag has no area', () => {
  assert.equal(L.area('paper:nope', layers, codes, graph), null);
  assert.equal(L.area('code:nope', layers, codes, graph), null);
  assert.equal(L.area('bogus', layers, codes, graph), null);
});

test('the frame encloses the area with 24 units of margin', () => {
  const s = L.slots(fixture.formulas, pos);
  const f = L.frame({quantities: new Set(['S', 'Q']), formulas: new Set(['q_a'])}, pos, s);
  assert.deepEqual(f, {x: 100 - 40 - 24, y: 100 - 22 - 24, w: (400 + 40) - (100 - 40) + 48, h: 44 + 48});
  assert.equal(L.frame({quantities: new Set(['nowhere']), formulas: new Set()}, pos, s), null);
});

test('the tab names the tag, its values and its Lean theorems on OMAI formulas; a code tab counts no theorems', () => {
  const f = new Map([['f1', {rung: 'local'}], ['f2', {rung: 'none'}]]);
  assert.equal(L.tabText('paper:x', {label: 'Short title', values: 3}, {quantities: new Set(['A']), formulas: new Set(['f1', 'f2'])}, f),
    'paper · Short title · 3 values · Lean theorems on 1 / 2 OMAI formulas');
  assert.equal(L.tabText('code:k', {label: 'kALDo'}, {quantities: new Set(['A', 'B']), formulas: new Set(['f1'])}, f), 'code · kALDo · 2 quantities');
  const t = 'Phonon dynamics and thermal conductivity of PtSe2 thin films: Impact of crystallinity and film thickness';
  const long = L.tabText('paper:y', {label: t, values: 1}, {quantities: new Set(['A']), formulas: new Set()}, f);
  assert.ok(long.includes('PtSe2') && long.length < 90 && !long.includes('\u2014'), long);
});
