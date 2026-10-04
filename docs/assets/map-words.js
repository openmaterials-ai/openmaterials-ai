/* Words for the map pages (2D, 3D, tracer, playground): plain names for node and
   operator ids, and the label resolver, a mirror of omai/semantics.resolve. */

// The ids spell acronyms and proper names in lowercase (compute_qha_gibbs); these restore them.
var WORDS = {
  '3ph': 'three-phonon', bte: 'BTE', calphad: 'CALPHAD', dos: 'DOS', eos: 'EOS', fc2: 'FC2',
  hf: 'HF', hnemd: 'HNEMD', homo: 'HOMO', lumo: 'LUMO', md: 'MD', mep: 'MEP', mfp: 'MFP',
  msd: 'MSD', nac: 'NAC', neb: 'NEB', nemd: 'NEMD', pimd: 'PIMD', pmf: 'PMF', qha: 'QHA',
  qhgk: 'QHGK', rta: 'RTA', zt: 'ZT', arrhenius: 'Arrhenius', fourier: 'Fourier', gibbs: 'Gibbs',
  green: 'Green', gruneisen: 'Gruneisen', hasselman: 'Hasselman', helmholtz: 'Helmholtz',
  johnson: 'Johnson', kubo: 'Kubo', landauer: 'Landauer', nan: 'Nan', poisson: 'Poisson',
  seebeck: 'Seebeck', wigner: 'Wigner', youngs: "Young's"
};
// Phrases that read better whole, applied after WORDS.
var PHRASES = [
  [/\bGreen Kubo\b/g, 'Green-Kubo'], [/\bHOMO LUMO\b/g, 'HOMO-LUMO'], [/\bHasselman Johnson\b/g, 'Hasselman-Johnson'],
  [/\bNan effective kappa\b/g, 'Nan effective-medium kappa'], [/\bNan, /g, 'Nan effective medium, '],
  [/\bphase space 3phonon\b/g, 'three-phonon phase space'], [/\bheat capacity p\b/g, 'heat capacity at constant pressure'],
  [/ (QHA|EOS)$/, ' ($1)'], [/\bidentity dm\b/g, 'identity (dynamical matrix)'], [/\bforces HF\b/g, 'forces (Hellmann-Feynman)'],
  [/\bGibbs hts\b/g, 'Gibbs energy (G = H - TS)'], [/\bNAC correction\b/g, 'non-analytic correction']
];
function plainWords(s){
  s = String(s).replace(/[A-Za-z0-9]+/g, function(w){ return WORDS[w.toLowerCase()] || w; });
  PHRASES.forEach(function(p){ s = s.replace(p[0], p[1]); });
  return s;
}

// Curated names for the common families; every other id is de-camelCased.
var HUMAN_PROP = {
  'ThermalConductivity': 'Thermal conductivity',
  'ThermalConductance': 'Thermal conductance',
  'ElectronicThermalConductivity': 'Electronic thermal conductivity',
  'ThermalExpansion': 'Thermal expansion',
  'ThermalGruneisen': 'Thermal Gruneisen parameter',
  'BulkModulus': 'Bulk modulus',
  'ShearModulus': 'Shear modulus',
  'ElasticConstants': 'Elastic constants',
  'PhononDOS': 'Phonon density of states',
  'ElectronicDOS': 'Electronic density of states',
  'HeatCapacity': 'Heat capacity',
  'HeatCapacityConstantP': 'Heat capacity at constant pressure',
  'HOMOLUMOGap': 'HOMO-LUMO gap',
  'PhaseSpace3Phonon': 'Three-phonon phase space',
  'Frequency': 'Phonon frequencies',
  'BandGap': 'Band gap',
  'Structure': 'Atomic structure'
};
// De-camelCase an id, acronyms kept: MolarGibbsEnergy -> "Molar Gibbs energy".
function humanizeId(id){
  var w = String(id).replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
    .replace(/[_-]+/g, ' ').trim().split(/\s+/).map(function(x, i){
      return /^[A-Z0-9]{2,}$/.test(x) ? x : (i ? x.toLowerCase() : x.charAt(0).toUpperCase() + x.slice(1).toLowerCase());
    }).join(' ');
  return w ? plainWords(w) : 'Property';
}
// A node's plain name, its route in words: ThermalConductivity[bte_solver=rta] -> "Thermal conductivity (RTA)".
function nodeName(id){
  var base = String(id || '').replace(/\[.*$/, ''), q = /\[(.*)\]$/.exec(id || '');
  return (HUMAN_PROP[base] || humanizeId(base)) +
    (q ? ' (' + plainWords(q[1].replace(/\w+=/g, '').replace(/_/g, ' ').replace(/,/g, ', ')) + ')' : '');
}
// An operator's plain name: compute_bulk_modulus_qha -> "compute bulk modulus (QHA)".
function opName(op){
  var s = String(op || '').replace(/\[.*?\]/g, '').replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/_/g, ' ').trim().toLowerCase();
  return s ? plainWords(s) : 'operation';
}

// The label resolver over semantics.json entries indexed by id: curated aliases, then exact
// labels, then token containment, scored and rounded as omai/semantics.py does.
function normLabel(s){ return String(s).replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/[-_]/g, ' ').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim(); }
var STOP_WORDS = { calculation: 1, estimation: 1, computation: 1, analysis: 1, the: 1, a: 1, an: 1, of: 1, and: 1 };
function tokset(s){ var out = {}; normLabel(s).split(' ').forEach(function(t){ if (t && !STOP_WORDS[t]) out[t] = 1; }); return out; }
function resolveLabels(q, index){
  var nq = normLabel(q); if (!nq) return [];
  var qt = tokset(q), n = Object.keys(qt).length, out = [];
  for (var id in index){
    var e = index[id], score = 0;
    if ((e.curated || []).some(function(c){ return normLabel(c) === nq; })) score = 1.0;
    else if ((e.labels || []).some(function(l){ return normLabel(l) === nq; })) score = 0.9;
    else if (n) {
      var es = tokset((e.labels || []).join(' ') + ' ' + id), all = true;
      for (var t in qt){ if (!es[t]) { all = false; break; } }
      if (all) score = Math.round((0.6 + Math.min(0.2, 0.2 * n / Math.max(1, Object.keys(tokset(id)).length))) * 1000) / 1000;
    }
    if (score) out.push({ id: id, kind: e.kind, score: score });
  }
  return out.sort(function(a, b){ return b.score - a.score || a.id.localeCompare(b.id); });
}
// The quantities a query names, best first: resolved labels, else an id or symbol substring.
// An empty list means no match.
function findNodes(q, index, nodes){
  var hits = resolveLabels(q, index).filter(function(r){ return r.kind === 'node' && nodes[r.id]; }).map(function(r){ return r.id; });
  if (hits.length) return hits;
  var v = String(q).trim().toLowerCase();
  if (!v) return [];
  return Object.keys(nodes).filter(function(id){ return (id + ' ' + (nodes[id].symbol || '')).toLowerCase().indexOf(v) !== -1; })
    .sort(function(a, b){ return a.toLowerCase().indexOf(v) - b.toLowerCase().indexOf(v); });
}
