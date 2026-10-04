/* How the sources page (experiment/) and the agreement page name a source, a quantity, a run and
   its conditions. Nothing here prints repo paths, hashes or curator notes. */
var Sources = (function () {
  'use strict';

  // A paper record's detail reads "<quote> (p. N). <citation>, doi:..., arXiv:..."; a measurement's
  // may open with its citation ("Glassbrenner and Slack, Phys. Rev. 134, A1058 (1964); ...").
  // Bracketed curator notes never render.
  function parts(detail) {
    var d = String(detail == null ? '' : detail).replace(/\s+/g, ' ').replace(/ ?\[[A-Z]{2,}[^\]]*\]/g, '').trim();
    var m = /^(.*\([^()]*\bp\. ?\d+[^()]*\))\.? (.+)$/.exec(d);
    if (m) return { quote: m[1], cite: m[2].replace(/,? (?:doi|arXiv):.*$/, '').replace(/\.$/, '') };
    m = /^([^;()]*\(\d{4}\))(?:; (.*))?$/.exec(d);
    if (m) return { quote: m[2] || '', cite: m[1] };
    return { quote: d, cite: '' };
  }

  // A code's display name: codes.json `name` once the commons adds it, else its key.
  function codeName(key, codes) {
    var e = codes && codes[key];
    return e && typeof e.name === 'string' ? e.name : key;
  }

  // A source's title: the shortest citation its records carry (a curator note that precedes a
  // citation makes that record's longer); a code's own runs read "<code> run"; otherwise ''.
  function titleOf(recs, codes) {
    var best = '';
    recs.forEach(function (r) {
      var c = parts(r.source && r.source.detail).cite;
      if (c && (!best || c.length < best.length)) best = c;
    });
    var ref = recs.length && recs[0].source ? recs[0].source.ref : '';
    return best || (codes && codes[ref] ? codeName(ref, codes) + ' run' : '');
  }

  // Refs that differ only in a numbered suffix (ethanol-bond0 to -bond7) are one source.
  function family(ref) { return String(ref).replace(/-[a-z]+\d+$/i, ''); }

  // A quantity in words: ThermalConductivity[bte_solver=direct_inverse] -> "Thermal conductivity (direct inverse)".
  var NAMES = { YoungsModulus: "Young's modulus" };
  var WORDS = { rta: 'RTA', qhgk: 'QHGK', green_kubo: 'Green-Kubo', neb_mep: 'NEB MEP', landauer: 'Landauer', nan: 'Nan' };
  function nodeName(id) {
    var base = String(id).replace(/\[.*$/, ''), q = /\[(.*)\]$/.exec(id);
    var name = NAMES[base] || base.replace(/([a-z0-9])([A-Z])/g, '$1 $2').replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
      .split(' ').map(function (w, i) { return /^[A-Z0-9]{2,}$/.test(w) ? w : (i ? w.toLowerCase() : w); }).join(' ');
    return name + (q ? ' (' + q[1].split(',').map(function (kv) {
      var v = kv.replace(/^[^=]*=/, '');
      return WORDS[v] || v.replace(/_/g, ' ');
    }).join(', ') + ')' : '');
  }

  // Conditions in words: T reads in kelvin; a curator note in parentheses and a hash never print
  // ("(solver unstated: ...)" reads ", solver not stated").
  function clean(v) {
    return typeof v !== 'string' ? v :
      v.replace(/ \((\w[\w ]*?) unstated:[^()]*\)/g, ', $1 not stated').replace(/ ?\([^()]*[:;][^()]*\)/g, '');
  }
  function condText(c, sep) {
    if (!c || typeof c !== 'object') return '';
    return Object.keys(c).filter(function (k) { return !/^[0-9a-f]{64}$/.test(c[k]); }).map(function (k) {
      return k === 'T' ? 'T ' + c[k] + (typeof c[k] === 'number' ? ' K' : '') : k + ' = ' + clean(c[k]);
    }).join(sep || ' · ');
  }

  // A run's one plain method line, from its structured fields: code and version, material, and the
  // potential or model. '' when the record names neither a code nor a potential or model.
  function methodLine(r, codes) {
    var c = r.conditions || {}, ref = r.source ? r.source.ref : '';
    var key = c.code || (codes && codes[ref] ? ref : '');
    var code = key ? codeName(key, codes) + (c.code_version ? ' ' + c.code_version : '') : '';
    var model = c.potential || c.potential_name || c.potential_file || c.model || '';
    if (!code && !model) return '';
    return (code ? code + ' run of ' : '') + r.material + (model ? ', ' + model : '');
  }

  return { parts: parts, codeName: codeName, titleOf: titleOf, family: family, nodeName: nodeName,
    condText: condText, methodLine: methodLine };
})();
