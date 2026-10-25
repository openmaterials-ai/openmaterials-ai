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
