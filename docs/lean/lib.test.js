const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const L = require('./lib.js');

const DATA = path.join(__dirname, '..', 'data');
const read = name => JSON.parse(fs.readFileSync(path.join(DATA, name), 'utf8'));

test('formatDimension writes ISQ exponents as a monomial in base order', () => {
  assert.strictEqual(L.formatDimension([1, 2, -2, 0, 0, 0, 0]), 'M L² T⁻²');
  assert.strictEqual(L.formatDimension([1, 2, -3, 0, 0, -1, 0]), 'M L² T⁻³ I⁻¹');
  assert.strictEqual(L.formatDimension([1, 2, -2, -1, -1, 0, 0]), 'M L² T⁻² Θ⁻¹ N⁻¹');
  assert.strictEqual(L.formatDimension([0, 0, 0, 0, 0, 0, 0]), '1');
  assert.strictEqual(L.formatDimension([1, 2]), null);
});

test('nodeRows gives one row per encoded field, sorted by node', () => {
  const rows = L.nodeRows({ nodes: {
    B: { fields: [{ field: 'x', declaration: 'D.b', exponents: [0, 1, 0, 0, 0, 0, 0] }] },
    A: { fields: [{ field: 'r', declaration: 'D.r', exponents: [0, 1, 0, 0, 0, 0, 0] },
                  { field: 'v', declaration: 'D.v', exponents: [0, 1, -1, 0, 0, 0, 0] }] } } });
  assert.deepStrictEqual(rows.map(r => [r.node, r.field, r.dimension]),
    [['A', 'r', 'L'], ['A', 'v', 'L T⁻¹'], ['B', 'x', 'L']]);
});

test('computeStats counts what the files hold, nothing more', () => {
  const s = L.computeStats(
    { version: 'abc', physlib_rev: 'r', lean_toolchain: 't', nodes: { A: {}, B: {} } },
    { nodes: [1, 2, 3] }, { coverage: { operators_compiled: 4, operators_total: 9 } });
  assert.deepStrictEqual(s, { nodes: 2, graphNodes: 3, operatorsCompiled: 4, operatorsTotal: 9,
    physlibRev: 'r', toolchain: 't', version: 'abc' });
});

test('the published lean.json carries one pin and the bridge declarations', () => {
  const lean = read('lean.json');
  const dims = read('physlib_dimensions.json');
  assert.strictEqual(lean.physlib_rev, dims.physlib_rev);
  assert.strictEqual(lean.lean_toolchain, dims.lean_toolchain);
  assert.strictEqual(read('formula_bindings.json').upstream.revision, lean.physlib_rev);
  assert.deepStrictEqual(Object.keys(lean).sort(),
    ['lean_toolchain', 'nodes', 'physlib_rev', 'source', 'version']);
  const source = fs.readFileSync(path.join(__dirname, '..', '..', lean.source), 'utf8');
  const rows = L.nodeRows(lean);
  assert.strictEqual(rows.length, dims.encoded_fields);
  for (const row of rows) {
    assert.ok(row.dimension, row.node + ' has seven exponents');
    const name = row.declaration.split('.').pop();
    assert.ok(source.includes('def ' + name + ' : Dimension ISQDimensionBase'), name + ' is in the bridge');
  }
  for (const id of Object.keys(lean.nodes)) {
    for (const block of lean.nodes[id].lean.split(/\n(?=def )/)) {
      assert.ok(source.includes(block), id + ' text matches the bridge source');
    }
  }
});
