/* How the datasheet, the sources page (experiment/), the agreement page and the map panels read a
   record's source, run, conditions and units. Nothing here prints repo paths, hashes or curator
   notes; the hashed data keeps them. Quantity names come from map-words.js. */
var Sources = (function () {
  'use strict';

  // A paper record's detail reads "<quote> (p. N). <citation>, doi:..., arXiv:..."; a measurement's
  // may open with its citation ("Glassbrenner and Slack, Phys. Rev. 134, A1058 (1964); <method>").
  // Bracketed curator notes never render.
  function parts(detail) {
    var d = String(detail == null ? '' : detail).replace(/\s+/g, ' ').replace(/ ?\[[A-Z]{2,}[^\]]*\]/g, '').trim();
    var doi = /\bdoi:\s*(10\.[^\s;,]+[^\s;,.])/i.exec(d), arx = /\barXiv:\s*([^\s;,]+[^\s;,.])/i.exec(d);
    var out = { quote: '', where: '', cite: '', method: '', doi: doi ? doi[1] : '', arxiv: arx ? arx[1] : '' };
    var m = /^(.+?) ?\(([^()]*\bp\. ?\d+[^()]*)\)\.? (.+)$/.exec(d);
    if (m) {
      // one quoted passage loses its marks (the page adds them); several keep theirs, paired and joined by "and"
      out.marked = !/^["“][^"“”]*["”]$/.test(m[1]) && /["“”]/.test(m[1]);
      out.quote = out.marked ? m[1].replace(/"([^"]*)"/g, '“$1”').replace(/; [a-z]+: /g, ' and ')
        : m[1].replace(/^["“]|["”]$/g, '');
      out.where = m[2].split(';')[0].trim();
      out.cite = m[3].replace(/,? (?:doi|arXiv):.*$/, '').replace(/\.$/, '');
      return out;
    }
    m = /^([^;()]*\(\d{4}\))(?:; (.*))?$/.exec(d);
    if (m) { out.cite = m[1]; out.method = m[2] || ''; }
    return out;
  }

  // A code's display name: the `name` its codes.json node entries carry, else its key. Every
  // code-name read on the site goes through here.
  function codeName(key, codes) {
    return (Object.values((codes && codes[key]) || {})[0] || {}).name || key;
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
  // Records grouped by source: a family of two or more refs shares its family key; any other ref
  // is its own key.
  function groups(records) {
    var byRef = {}, fams = {}, out = {};
    records.forEach(function (r) {
      var ref = (r.source && r.source.ref) || '(unsourced)';
      (byRef[ref] = byRef[ref] || []).push(r);
    });
    Object.keys(byRef).forEach(function (ref) { (fams[family(ref)] = fams[family(ref)] || []).push(ref); });
    Object.keys(fams).forEach(function (f) {
      var refs = fams[f];
      if (refs.length === 1) out[refs[0]] = byRef[refs[0]];
      else out[f] = [].concat.apply([], refs.map(function (r) { return byRef[r]; }));
    });
    return out;
  }

  // Curator text as a reader sees it, for conditions and codes.json api strings: a 64-hex value
  // prints nothing; "(solver unstated: ...)" reads ", solver not stated"; an aside that names a
  // commit, cites file:line or carries a note (":" or ";") is cut, and so are a leading code file
  // or repo path and a "; file:line ..." clause.
  var ASIDE = / \((?:[^()]|\([^()]*\))*?(?:[:;]|\bcommit\b)(?:[^()]|\([^()]*\))*\)/g;
  function clean(v) {
    if (typeof v !== 'string') return v;
    if (/^[0-9a-f]{64}$/.test(v)) return '';
    return v.replace(/ \((\w[\w ]*?) unstated:[^()]*\)/g, ', $1 not stated').replace(ASIDE, '')
      .replace(/^(?:[\w.-]+\/)*[\w.-]+\.(?:py|js|ts|sh)(?::[\d,-]+)? /, '')
      .replace(/; ?[\w./-]+\.\w+:\d[^;]*/g, '').trim();
  }
  // One condition for display: T in kelvin when numeric, everything else cleaned; '' to skip.
  function condValue(k, v) {
    if (k === 'T' && typeof v === 'number') return v + ' K';
    v = clean(v);
    return v == null ? '' : v;
  }
  function condText(c, sep) {
    if (!c || typeof c !== 'object') return '';
    return Object.keys(c).map(function (k) {
      var v = condValue(k, c[k]);
      return v === '' ? '' : (k === 'T' ? 'T ' + v : k + ' = ' + (typeof v === 'object' ? JSON.stringify(v) : v));
    }).filter(Boolean).join(sep || ' · ');
  }

  // A run's one plain method line from its structured fields: code and version, material, the
  // potential or model ("kaldo 2.2.1 run of Si with the Tersoff potential"). Without a code it
  // reads "Computed with <model>", the same for every record of the source; '' when the record
  // names no code, potential or model. Takes a flat instance or a lineage record.
  function methodLine(r, codes) {
    var lin = r.lineage || r, c = lin.conditions || {}, ref = r.source ? r.source.ref : '';
    var cv = String(c.code || '').split(' ');
    var key = codes && codes[cv[0]] ? cv[0] : (codes && codes[ref] ? ref : cv[0]);
    var who = key ? [codeName(key, codes), c.code_version || cv.slice(1).join(' ')].filter(Boolean).join(' ') : '';
    var pot = c.potential || c.potential_name || c.potential_file;
    var how = pot ? 'the ' + String(pot).replace(/^[A-Z][a-z]?\./, '').replace(/^./, function (x) { return x.toUpperCase(); }) + ' potential'
      : (c.model || '');
    var mat = lin.material && typeof lin.material === 'object' ? lin.material.name : lin.material;
    if (who) return who + ' run' + (mat ? ' of ' + mat : '') + (how ? ' with ' + how : '');
    return how ? 'Computed with ' + how : '';
  }

  // A unit as a reader writes it: W_per_m_per_K -> "W/(m K)", linear_THz -> "THz". Units sit in the
  // hashed data, so the map is applied at render time; a unit already in writing stays.
  var UNIT = { linear_THz: 'THz', 'linear_THz (Gamma optical)': 'THz (Gamma, optical)', angular_THz: 'angular THz',
    angstrom_linear_THz: 'Å THz', mu_B: 'μB', 'A^2': 'Å²', inverse_cm: 'cm⁻¹', s_per_m: 'S/m', ms_per_cm: 'mS/cm' };
  var TOKEN = { ev: 'eV', ry: 'Ry', kelvin: 'K', k: 'K', volt: 'V', v: 'V', gram: 'g', a: 'Å', angstrom: 'Å', muv: 'μV' };
  var SUP = { 2: '²', 3: '³' };
  function unit(u) {
    u = String(u == null ? '' : u).replace(/[\u2014\u2013]/g, ' ');
    if (UNIT[u]) return UNIT[u];
    if (!/^[A-Za-z0-9]+(?:_[A-Za-z0-9]+)+$|^(?:ev|ry|kelvin|volt)$/.test(u))
      return u.replace(/\^([23])/g, function (_, d) { return SUP[d]; });
    var tok = function (t) {
      var m = /^([A-Za-z]+)([23])?$/.exec(t);
      return m ? (TOKEN[m[1].toLowerCase()] || m[1]) + (m[2] ? SUP[m[2]] : '') : t;
    };
    var g = ('_' + u).split('_per_'), num = g.shift().slice(1);   // '' when the unit opens with per_
    var den = [].concat.apply([], g.map(function (x) { return x.split('_').map(tok); }));
    num = num ? num.split('_').map(tok).join(' ') : '1';
    return den.length ? num + '/' + (den.length > 1 ? '(' + den.join(' ') + ')' : den[0]) : num;
  }

  return { parts: parts, codeName: codeName, titleOf: titleOf, family: family, groups: groups,
    clean: clean, condValue: condValue, condText: condText, methodLine: methodLine, unit: unit };
})();
