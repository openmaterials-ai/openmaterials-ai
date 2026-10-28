const test = require('node:test');
const assert = require('node:assert/strict');
const F = require('./lib.js');
const source = {
  id: 'candidate', relation: 'conditional', statement: 'candidate <not proved>',
  evidence: {kind: 'source_correspondence'}, conditions: ['T > 0'],
  sources: [{name: 'Ensemble.theorem', kind: 'theorem', source_url: 'https://github.com/a/b/blob/sha/A.lean#L1'}],
  conventions: {model_scope:'one mode'}, remaining_obligations:['Identify the ensemble']
};
test('upstream theorem references never render as compiled OMAI proofs', () => {
  const html=F.bindingHtml(source);
  assert.match(html,/Source correspondence only/);
  assert.doesNotMatch(html,/Compiled bridge/);
  assert.match(html,/candidate &lt;not proved&gt;/);
  assert.match(html,/Identify the ensemble/);
});
test('untrusted source text is escaped and non-HTTPS source links are not activated', () => {
  const b=structuredClone(source);
  b.sources[0].source_url='javascript:alert(1)';
  b.conditions=['<img src=x onerror="alert(1)">'];
  const html=F.bindingHtml(b);
  assert.doesNotMatch(html,/javascript:|<img/);
  assert.match(html,/&lt;img/);
});
test('inventory retains unmapped and zero-input operators and filters gaps', () => {
  const data={bindings:[source],inventory:{nodes:[{id:'A',binding_ids:['candidate'],status:'mapped'}],operators:[{id:'provide_temperature',inputs:[],binding_ids:[],status:'gap',reason:'Not identified'}]}};
  const rows=F.index(data);
  assert.equal(rows.length,2);
  assert.equal(F.select(rows,'temperature','operator','gap')[0].id,'provide_temperature');
  assert.equal(F.select(rows,'','node','gap').length,0);
  assert.match(F.rowHtml(rows[1]),/Not identified/);
});

const makeData = () => {
  const input = {id:'LatticeThermalConductivity',uid:'input-id',binding_ids:['total'],status:'mapped'};
  const output = {id:'TotalThermalConductivity',uid:'output-id',binding_ids:['total'],status:'mapped'};
  const op = {id:'sum_conductivities',uid:'operator-id',inputs:[input.id],outputs:[output.id],binding_ids:['total'],status:'mapped'};
  const b = structuredClone(source);
  b.id='total'; b.sources[0].module='Physlib.Thermoelectric';
  b.targets=[{kind:'node',id:input.id},{kind:'node',id:output.id},{kind:'operator',id:op.id}];
  b.evidence={kind:'compiled_bridge',declarations:['Bridge.total'],source_path:'lean/bridge/Proof.lean',build_record:'lean/bridge/build-evidence.json'};
  const reference=structuredClone(b); reference.id='reference'; reference.evidence={kind:'source_correspondence'};
  reference.targets=[{kind:'node',id:input.id}]; input.binding_ids.push('reference');
  return {bindings:[b,reference],inventory:{nodes:[input,output],operators:[op]}};
};
test('reverse index deduplicates upstream declarations but retains each binding once', () => {
  const data=makeData(); data.bindings[0].sources.push(structuredClone(data.bindings[0].sources[0]));
  const rows=F.declarationIndex(data);
  assert.equal(rows.length,1);
  assert.deepEqual(rows[0].bindings.map(b=>b.id),['total','reference']);
  assert.equal(F.selectDeclarations(rows,'Lattice','Physlib.Thermoelectric','compiled_bridge').length,1);
  assert.equal(F.selectDeclarations(rows,'','Physlib.Thermoelectric.Other').length,0);
  assert.equal(F.selectDeclarations(rows,'','','','theorem').length,0);
  assert.equal(F.selectDeclarations(rows,'','','source_correspondence','Ensemble.theorem').length,1);
});
test('compiled subject filters do not turn a lattice input into a proved producing formula', () => {
  const rows=F.index(makeData());
  assert.deepEqual(F.select(rows,'','','','compiled').map(r=>r.id),['TotalThermalConductivity','sum_conductivities']);
  const input=rows.find(r=>r.id==='LatticeThermalConductivity');
  assert.equal(input.compiled,false);
  assert.match(F.rowHtml(input),/producing formula is not proved/);
  assert.deepEqual(F.select(rows,'','','','source').map(r=>r.id),['LatticeThermalConductivity']);
});
test('explicit standalone interpretation subjects do not imply other input proofs', () => {
  const data=makeData();
  data.bindings[0].evidence.proved_targets=[{kind:'node',id:'TotalThermalConductivity'}];
  assert.deepEqual(F.select(F.index(data),'','','','compiled').map(r=>r.id),['TotalThermalConductivity']);
});
test('declaration cards link quantities and real operators back to map selection with escaped fragments', () => {
  const row=F.declarationIndex(makeData())[0];
  const html=F.declarationHtml(row,{mapBase:'/map/',bridgeBase:'/lean/bridge/'});
  assert.match(html,/href="\/map\/#node=LatticeThermalConductivity"/);
  assert.match(html,/href="\/map\/#operator=sum_conductivities"/);
  assert.match(html,/Compiled bridge/); assert.match(html,/Source-only/);
  assert.match(html,/Conditions and proof scope/);
  assert.match(html,/https:\/\/github.com\/a\/b\/blob\/sha\/A.lean#L1/);
  row.bindings[0].targets[0].id='A&node=Injected"<';
  const encoded=F.declarationHtml(row,{mapBase:'/map/'});
  assert.match(encoded,/#node=A%26node%3DInjected%22%3C/);
  assert.doesNotMatch(encoded,/href="[^"]*<|<Injected/);
});
test('map reference navigation preserves exact declaration and module, including Unicode', () => {
  const hash=F.fragment({declaration:'Quantum.ψ',module:'Physlib.Quantum'});
  assert.deepEqual(F.parseFragment(hash),{view:'physlib',declaration:'Quantum.ψ',module:'Physlib.Quantum'});
  assert.deepEqual(F.mapSelection('#operator=sum_conductivities',makeData()).nodes,['TotalThermalConductivity']);
  assert.equal(F.mapSelection('#operator=sum',makeData()).view,'missing');
  assert.equal(F.mapSelection('#node=LatticeThermalConductivity',makeData()).id,'LatticeThermalConductivity');
  assert.doesNotThrow(()=>F.parseFragment('#node=%broken'));
  assert.deepEqual(F.parseFragment('#physlib=1'),{view:'physlib',declaration:'',module:''});
});
test('map quantity references distinguish proof subject from compiled input association', () => {
  const data=makeData();
  const input=F.targetReferencesHtml(data,'node','LatticeThermalConductivity','/lean/bridge/');
  const output=F.targetReferencesHtml(data,'node','TotalThermalConductivity','/lean/bridge/');
  assert.match(input,/Input\/reference in a compiled bridge/);
  assert.doesNotMatch(input,/Compiled subject/);
  assert.match(output,/Compiled subject/);
  assert.match(output,/declaration=Ensemble.theorem&amp;module=Physlib.Thermoelectric/);
});
test('proof and upstream links reject local paths, traversal, credentials, and lookalike hosts', () => {
  ['file:///tmp/source','http://github.com/a/b','https://github.com.evil/a','https://u:p@github.com/a'].forEach(url=>assert.equal(F.sourceHref(url),''));
  ['../secret','lean/bridge/../../evil.lean','/tmp/Proof.lean','lean/bridge/Proof.lean" onload="x'].forEach(path=>assert.equal(F.proofHref(path),''));
  assert.equal(F.proofHref('lean/bridge/Proof.lean'),'https://github.com/openmaterials-ai/openmaterials-ai/blob/27f71197ccfac0bbfed535a4376e941113bb567b/lean/bridge/Proof.lean');
});
test('rendered repeated bindings do not create duplicate DOM identifiers', () => {
  const html=F.index(makeData()).map(F.rowHtml).join('')+F.declarationIndex(makeData()).map(row=>F.declarationHtml(row)).join('');
  assert.doesNotMatch(html,/\sid=/);
});

test('reviewed Cp data links only the identity route and its output as new proof subjects', () => {
  const data = require('../../data/formula_bindings.json');
  const binding = data.bindings.find(b => b.id === 'harmonic-static-cp-identity');
  assert.ok(binding);
  assert.deepEqual(new Set(F.provedTargets(binding, data).map(t => t.kind + ':' + t.id)),
    new Set(['operator:contract_heat_capacity_p_identity', 'node:HeatCapacityConstantP']));
  const rows = F.index(data);
  assert.equal(rows.find(r => r.kind === 'operator' && r.id === 'contract_heat_capacity_p_identity').compiled, true);
  assert.equal(rows.find(r => r.kind === 'node' && r.id === 'HeatCapacityConstantP').compiled, true);
  // contract_thermal_gruneisen_identity, compute_heat_capacity_p and contract_thermal_gruneisen are
  // compiled by separate later bindings; the exact Cp provedTargets set above excludes them.
  for (const id of ['contract_molar_volume', 'compute_gruneisen']) {
    assert.equal(rows.find(r => r.kind === 'operator' && r.id === id).compiled, false);
  }
  const selected = F.mapSelection('#operator=contract_heat_capacity_p_identity', data);
  assert.deepEqual(selected.nodes, ['HeatCapacityConstantP']);
  assert.deepEqual(F.parseFragment('#operator=contract_heat_capacity_p_identity'),
    {view:'omai', kind:'operator', id:'contract_heat_capacity_p_identity'});
  const upstream = F.declarationIndex(data).find(r => r.name === 'CanonicalEnsemble.meanEnergyT');
  assert.ok(upstream.bindings.some(b => b.id === binding.id));
  assert.match(F.bindingHtml(binding), /OMAIPhyslibHarmonicResponse\.lean/);
  assert.doesNotMatch(F.targetReferencesHtml(data, 'operator', 'compute_heat_capacity_p', '/lean/bridge/'),
    /harmonic-static-cp-identity/);
});

test('reviewed thermal Gruneisen data links only the identity route and ThermalGruneisen as new proof subjects', () => {
  const data = require('../../data/formula_bindings.json');
  const binding = data.bindings.find(b => b.id === 'harmonic-static-thermal-gruneisen-identity');
  assert.ok(binding);
  assert.deepEqual(new Set(F.provedTargets(binding, data).map(t => t.kind + ':' + t.id)),
    new Set(['operator:contract_thermal_gruneisen_identity', 'node:ThermalGruneisen']));
  const rows = F.index(data);
  assert.equal(rows.find(r => r.kind === 'operator' && r.id === 'contract_thermal_gruneisen_identity').compiled, true);
  assert.equal(rows.find(r => r.kind === 'node' && r.id === 'ThermalGruneisen').compiled, true);
  assert.equal(rows.find(r => r.kind === 'operator' && r.id === 'compute_gruneisen').compiled, false);
  assert.equal(rows.find(r => r.kind === 'node' && r.id === 'Gruneisen').compiled, false);
  const selected = F.mapSelection('#operator=contract_thermal_gruneisen_identity', data);
  assert.deepEqual(selected.nodes, ['ThermalGruneisen']);
  const upstream = F.declarationIndex(data).find(r => r.name === 'CanonicalEnsemble.heatCapacity');
  assert.ok(upstream.bindings.some(b => b.id === binding.id));
  assert.match(F.bindingHtml(binding), /OMAIPhyslibThermalGruneisen\.lean/);
  assert.doesNotMatch(F.bindingHtml(binding), /OMAIPhyslibGruneisenWitness/);
  assert.equal(F.targetReferencesHtml(data, 'node', 'Gruneisen', '/lean/bridge/'), '');
  assert.doesNotMatch(F.targetReferencesHtml(data, 'operator', 'contract_thermal_gruneisen', '/lean/bridge/'),
    /harmonic-static-thermal-gruneisen-identity/);
});

test('reviewed QHA data compiles each producer and its output, not mode-Gruneisen or molar-volume producers', () => {
  const data = require('../../data/formula_bindings.json');
  const expected = {
    'harmonic-qha-gibbs-energy': ['compute_qha_gibbs', 'QHAGibbsEnergy'],
    'harmonic-qha-heat-capacity-p': ['compute_heat_capacity_p', 'HeatCapacityConstantP'],
    'harmonic-qha-thermal-expansion': ['compute_thermal_expansion', 'ThermalExpansion'],
    'harmonic-qha-bulk-modulus': ['compute_bulk_modulus_qha', null],
    'harmonic-qha-thermal-gruneisen-contraction': ['contract_thermal_gruneisen', 'ThermalGruneisen'],
  };
  const rows = F.index(data);
  for (const [id, [operator, output]] of Object.entries(expected)) {
    const binding = data.bindings.find(b => b.id === id);
    assert.ok(binding, id);
    assert.deepEqual(new Set(F.provedTargets(binding, data).map(t => t.kind + ':' + t.id)),
      new Set(['operator:' + operator, ...(output ? ['node:' + output] : [])]));
    assert.equal(rows.find(r => r.kind === 'operator' && r.id === operator).compiled, true);
    if (output) assert.equal(rows.find(r => r.kind === 'node' && r.id === output).compiled, true);
    assert.match(F.bindingHtml(binding), /OMAIPhyslibQHA\.lean/);
    assert.doesNotMatch(F.bindingHtml(binding), /OMAIPhyslibQHAWitness/);
  }
  for (const id of ['compute_gruneisen', 'contract_molar_volume']) {
    assert.equal(rows.find(r => r.kind === 'operator' && r.id === id).compiled, false);
  }
  assert.equal(rows.find(r => r.kind === 'node' && r.id === 'Gruneisen').compiled, false);
  // BulkModulus is the Voigt average of the elastic tensor: an output association only.
  assert.equal(rows.find(r => r.kind === 'node' && r.id === 'BulkModulus').compiled, false);
  assert.equal(F.targetReferencesHtml(data, 'node', 'Gruneisen', '/lean/bridge/'), '');
  const upstream = F.declarationIndex(data).find(r => r.name === 'CanonicalEnsemble.thermodynamicEntropy');
  assert.ok(upstream.bindings.some(b => b.id === 'harmonic-qha-gibbs-energy'));
});
