// Exercise the map's actual formal-navigation handlers with a small DOM double.
// Browser layout and visual interaction still require a browser check.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const FB = require('../lean/bridge/lib.js');
const LW = require('./lean-map.js');
const page = fs.readFileSync(__dirname + '/index.html','utf8');
const handlers = page.slice(page.indexOf('function selectOperator(id){'),page.indexOf("window.addEventListener('hashchange', applyHash);"));
function harness() {
  class Element {
    constructor(){ this.value=''; this.textContent=''; this.innerHTML=''; this.style={}; this.handlers={}; this.classes={}; this.classList={toggle:(key,value)=>{this.classes[key]=value;}}; }
    addEventListener(kind,fn){ this.handlers[kind]=fn; }
    focus(){ this.focused=true; }
    input(value){ this.value=value; this.handlers.input(); }
  }
  const elements = new Map();
  const document={getElementById:id=>{if(!elements.has(id)) elements.set(id,new Element());return elements.get(id);},querySelector:()=>new Element()};
  const source={module:'Physlib.Model',name:'Model.formula',kind:'def',source_url:'https://github.com/leanprover-community/physlib/blob/pin/Physlib/Model.lean#L1'};
  const binding={id:'reference',relation:'conditional',statement:'Source-only model relation.',targets:[{kind:'node',id:'Output'},{kind:'operator',id:'source_formula'}],sources:[source],evidence:{kind:'source_correspondence'}};
  const formalData={bindings:[binding],inventory:{nodes:[{id:'Input'},{id:'Output'}],operators:[{id:'source_formula',inputs:[],outputs:['Output'],formula_latex:'x',binding_ids:['reference']} ]}};
  const nodeElements=['Input','Output'].map(id=>{const e=new Element();e.dataset={id};return e;});
  const edgeElements=[];
  const location={hash:'',pathname:'/map/',search:''};
  const calls=[];
  const context={URLSearchParams,FB,LW,formalData,formalDeclarations:FB.declarationIndex(formalData),
    formulaBindings:{operators:{source_formula:formalData.inventory.operators[0]}},document,location,
    history:{replaceState:(_,__,hash)=>{location.hash=hash.startsWith('#')?hash:'';}},
    panelEl:new Element(),captionEl:{hidden:false},mapStatus:new Element(),depth:'overview',
    vp:{querySelectorAll:selector=>selector==='.node'?nodeElements:edgeElements},
    pos:{Input:{},Output:{}},nodeById:{Input:{id:'Input'},Output:{id:'Output'}},
    activeCode:null,codesData:{},clearDim:()=>{},closeBtn:()=>'<button>Close</button>',
    esc:FB.esc,attr:FB.esc,tex:s=>FB.esc(s),chip:id=>'<button>'+id+'</button>',
    fitTo:(ids,anchor)=>calls.push({type:'fit',ids,anchor}),
    selectNode:node=>calls.push({type:'node',id:node.id}),
    neighborhood:id=>[id],toggleCode:()=>{},picked:new Set(),};
  vm.createContext(context);new vm.Script(handlers).runInContext(context);
  return {context,elements,calls,nodeElements,formalData};
}
test('map toolbar opens the upstream navigator and leaves scientific records untouched',()=>{
  const h=harness(),snapshot=JSON.stringify(h.formalData);
  h.elements.get('physlibBtn').handlers.click();
  assert.equal(h.context.location.hash,'#physlib=1');
  assert.match(h.context.panelEl.innerHTML,/not computation edges or inverse proofs/);
  assert.equal(h.elements.get('formal-count').textContent,'1 of 1 referenced declarations');
  assert.match(h.elements.get('formal-results').innerHTML,/href="#operator=source_formula"/);
  assert.equal(JSON.stringify(h.formalData),snapshot);
});
test('exact upstream deep links and evidence filters do not broaden a missing declaration or module',()=>{
  const h=harness();
  h.context.location.hash=FB.fragment({declaration:'Model.formula',module:'Physlib.Missing'});
  h.context.applyHash();
  assert.equal(h.elements.get('formal-count').textContent,'0 of 1 referenced declarations');
  h.context.location.hash=FB.fragment({declaration:'Model.formula',module:'Physlib.Model'});
  h.context.applyHash();
  assert.equal(h.elements.get('formal-count').textContent,'1 of 1 referenced declarations');
  h.elements.get('formal-evidence').input('compiled_bridge');
  assert.equal(h.elements.get('formal-count').textContent,'0 of 1 referenced declarations');
  assert.equal(h.context.location.hash,'#physlib=1&module=Physlib.Model');
  h.elements.get('formal-evidence').input('source_correspondence');
  assert.match(h.elements.get('formal-results').innerHTML,/Source-only/);
  assert.doesNotMatch(h.elements.get('formal-results').innerHTML,/Compiled bridge/);
});
test('reverse operator links select a real zero-input operator and frame its output',()=>{
  const h=harness();
  h.context.location.hash='#operator=source_formula';h.context.applyHash();
  assert.equal(h.context.location.hash,'#operator=source_formula');
  assert.match(h.context.panelEl.innerHTML,/No input quantities/);
  assert.match(h.context.panelEl.innerHTML,/Source-only/);
  assert.match(h.context.panelEl.innerHTML,/#declaration=Model.formula&amp;module=Physlib.Model/);
  assert.equal(h.nodeElements[0].classes.dim,true);
  assert.equal(h.nodeElements[1].classes.sel,true);
  assert.equal(h.calls.at(-1).anchor,'Output');
});
test('unknown targets replace a previous selection instead of leaving stale evidence visible',()=>{
  const h=harness();
  h.context.location.hash='#operator=source_formula';h.context.applyHash();
  h.context.location.hash='#operator=source';h.context.applyHash();
  assert.match(h.context.panelEl.innerHTML,/No such OMAI operator: source/);
  assert.doesNotMatch(h.context.panelEl.innerHTML,/Source-only/);
  assert.equal(h.context.location.hash,'#operator=source');
  h.context.location.hash='#node=Missing';h.context.applyHash();
  assert.match(h.context.panelEl.innerHTML,/No such OMAI quantity: Missing/);
});
test('upstream target links return to the exact map quantity',()=>{
  const h=harness();
  h.context.location.hash='#node=Output';h.context.applyHash();
  assert.equal(h.calls.find(call=>call.type==='node').id,'Output');
});

test('an unknown variant cannot inherit the bare quantity proof',()=>{
  const h=harness();
  h.context.location.hash='#node=Output%5Bvariant%3Dmissing%5D';h.context.applyHash();
  assert.match(h.context.panelEl.innerHTML,/No such OMAI quantity: Output\[variant=missing\]/);
  assert.equal(h.calls.some(call=>call.type==='node'||call.type==='fit'),false);
  assert.equal(h.context.location.hash,'#node=Output%5Bvariant%3Dmissing%5D');
});

test('object prototype names are not scientific quantity IDs',()=>{
  for(const id of ['constructor','toString','__proto__']){
    const h=harness();
    h.context.location.hash='#node='+id;h.context.applyHash();
    assert.match(h.context.panelEl.innerHTML,new RegExp('No such OMAI quantity: '+id));
    assert.equal(h.calls.some(call=>call.type==='node'||call.type==='fit'),false);
    assert.equal(h.context.location.hash,'#node='+id);
  }
});
