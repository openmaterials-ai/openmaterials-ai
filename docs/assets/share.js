// Share links, /m/<snapshot>/<selection>: the encoding and what a page says about a selection. Pure:
// no DOM, no fetch. The landing page (docs/share/), the map and the site Worker import it, so the page,
// its card and its meta tags agree. A selection is a bitset over the snapshot's nodes in order: node 0
// is the high bit of the first hex digit, lowercase hex, whole bytes, trailing zero bytes trimmed, at
// least one bit set. omai/snapshots.py holds the same encoding.

export const SITE = "https://openmaterials.ai";
export const PREFIX = 12;
const PREFIX_RE = /^[0-9a-f]{8,64}$/;
const SEL_RE = /^(?:[0-9a-f]{2})+$/;

export function encode(snap, ids) {
  const order = new Map(snap.nodes.map((n, i) => [n.id, i]));
  const bits = ids.filter((i) => order.has(i)).map((i) => order.get(i));
  if (!bits.length) throw new Error("an empty selection has no link");
  const buf = new Uint8Array((Math.max(...bits) >> 3) + 1);
  for (const b of bits) buf[b >> 3] |= 0x80 >> (b & 7);
  return Array.from(buf, (x) => x.toString(16).padStart(2, "0")).join("");
}

// {ok: true, ids} in snapshot order, or {ok: false, reason}
export function decode(snap, hex) {
  if (!SEL_RE.test(hex || "") || hex.endsWith("00")) return { ok: false, reason: "it is malformed" };
  const ids = [];
  for (let i = 0; i < hex.length * 4; i++) {
    if (parseInt(hex.slice((i >> 3) * 2, (i >> 3) * 2 + 2), 16) & (0x80 >> (i & 7))) {
      if (i >= snap.nodes.length) return { ok: false, reason: `it names quantity ${i + 1}, but the snapshot has ${snap.nodes.length}` };
      ids.push(snap.nodes[i].id);
    }
  }
  return { ok: true, ids };
}

// "/m/<prefix>/<hex>" or "#<prefix>/<hex>" to {snapshot, selection}, else null
export function parseShare(s) {
  const m = /^(?:\/m\/|#)([^/]+)\/([^/?#]+)$/.exec(s || "");
  return m && PREFIX_RE.test(m[1]) ? { snapshot: m[1], selection: m[2] } : null;
}

export function resolveSnapshot(index, prefix) {
  const hits = ((index && index.snapshots) || []).filter((h) => h.startsWith(prefix));
  return hits.length === 1 ? { ok: true, hash: hits[0] } : { ok: false, reason: hits.length ? "ambiguous" : "unknown" };
}

export const shareURL = (hash, hex, origin = SITE) => `${origin}/m/${hash.slice(0, PREFIX)}/${hex}`;

const byId = (snap) => new Map(snap.nodes.map((n) => [n.id, n]));
const tierRank = (snap) => new Map(snap.tiers.map((t, i) => [t.name, t.order ?? i]));
const sameSet = (a, b) => a.size === b.size && [...a].every((x) => b.has(x));
const list = (xs) => (xs.length < 2 ? xs.join("") : xs.slice(0, -1).join(", ") + " and " + xs[xs.length - 1]);
const plural = (n, one, many) => `${n} ${n === 1 ? one : many}`;

export function tiersOf(snap, ids) {
  const nodes = byId(snap), rank = tierRank(snap);
  return [...new Set(ids.map((i) => nodes.get(i).tier))].sort((a, b) => (rank.get(a) ?? 1e6) - (rank.get(b) ?? 1e6) || (a < b ? -1 : 1));
}

// The codes whose quantities are exactly the selection (two codes can represent the same set)
export function codesOf(snap, ids) {
  const sel = new Set(ids);
  return Object.keys(snap.codes).sort().filter((k) => sameSet(new Set(snap.codes[k].nodes), sel));
}

// One source and one sink, connected, more than one node: [sourceId, sinkId]; else null
export function chainOf(snap, ids) {
  if (ids.length < 2) return null;
  const sel = new Set(ids), adj = new Map(ids.map((i) => [i, new Set()]));
  const hasIn = new Set(), hasOut = new Set();
  for (const [s, t] of snap.links) {
    if (s !== t && sel.has(s) && sel.has(t)) { hasOut.add(s); hasIn.add(t); adj.get(s).add(t); adj.get(t).add(s); }
  }
  const sources = ids.filter((i) => !hasIn.has(i)), sinks = ids.filter((i) => !hasOut.has(i));
  if (sources.length !== 1 || sinks.length !== 1) return null;
  const seen = new Set([ids[0]]), todo = [ids[0]];
  while (todo.length) for (const j of adj.get(todo.pop())) if (!seen.has(j)) { seen.add(j); todo.push(j); }
  return seen.size === ids.length ? [sources[0], sinks[0]] : null;
}

export function title(snap, ids) {
  const nodes = byId(snap);
  const codes = codesOf(snap, ids);
  if (codes.length) return list(codes.map((k) => snap.codes[k].name));
  if (ids.length === 1) return nodes.get(ids[0]).name;
  const chain = chainOf(snap, ids);
  if (chain) return `${nodes.get(chain[0]).name} to ${nodes.get(chain[1]).name}`;
  const tiers = tiersOf(snap, ids);
  return tiers.length <= 3 ? `${ids.length} quantities in ${list(tiers)}` : `${ids.length} quantities across ${tiers.length} tiers`;
}

export function codesCovering(snap, ids) {
  const sel = new Set(ids);
  return Object.keys(snap.codes).map((key) => ({ key, name: snap.codes[key].name, count: snap.codes[key].nodes.filter((i) => sel.has(i)).length }))
    .filter((c) => c.count > 0).sort((a, b) => b.count - a.count || (a.key < b.key ? -1 : 1));
}

// Codes by the overlap (Jaccard) of their quantities with the selection
export function relatedCodes(snap, ids, exclude = []) {
  const sel = new Set(ids), skip = new Set(exclude);
  return Object.keys(snap.codes).filter((k) => !skip.has(k)).map((key) => {
    const own = snap.codes[key].nodes, inter = own.filter((i) => sel.has(i)).length;
    return { key, name: snap.codes[key].name, score: inter / (own.length + sel.size - inter) };
  }).filter((c) => c.score > 0).sort((a, b) => b.score - a.score || (a.key < b.key ? -1 : 1)).slice(0, 5);
}

// Quantities one edge from the selection, by tier then name
export function nextSteps(snap, ids, limit = 12) {
  const sel = new Set(ids), nodes = byId(snap), rank = tierRank(snap), out = new Map();
  for (const [s, t] of snap.links) {
    if (sel.has(s) && !sel.has(t) && !out.has(t)) out.set(t, "output");
    else if (sel.has(t) && !sel.has(s) && !out.has(s)) out.set(s, "input");
  }
  return [...out].map(([id, via]) => ({ id, name: nodes.get(id).name, tier: nodes.get(id).tier, via }))
    .sort((a, b) => (rank.get(a.tier) ?? 1e6) - (rank.get(b.tier) ?? 1e6) || (a.name < b.name ? -1 : a.name > b.name ? 1 : 0))
    .slice(0, limit);
}

// The counts line under a title. A code's entries on the map are its representation: they record that the
// code reads or returns a quantity, not that it computes it, so the line says "represented".
export function counts(snap, ids) {
  const tiers = tiersOf(snap, ids), n = codesCovering(snap, ids).length, own = codesOf(snap, ids);
  const inTiers = `in ${plural(tiers.length, "tier", "tiers")}`;
  if (own.length) {
    const names = list(own.map((k) => snap.codes[k].name));
    return `The ${plural(ids.length, "quantity", "quantities")} ${names} ${own.length > 1 ? "represent" : "represents"} on the map, ${inTiers}.`;
  }
  const where = n ? `, represented in ${plural(n, "code", "codes")}` : "";
  return title(snap, ids).startsWith(`${ids.length} quantities`)
    ? (n ? `Represented in ${plural(n, "code", "codes")}.` : "No code on the map represents them.")
    : `${plural(ids.length, "quantity", "quantities")} ${inTiers}${where}.`;
}

export function describe(snap, ids) {
  const nodes = byId(snap);
  const names = ids.slice(0, 3).map((i) => nodes.get(i).name);
  const more = ids.length > 3 ? ` and ${ids.length - 3} more` : "";
  return `${counts(snap, ids)} On the OpenMaterials map: ${names.join(", ")}${more}.`;
}

// The snapshot with only the codes the live registry still lists as public: a code made private after a
// snapshot was frozen drops out of every page that reads it.
export function withPublicCodes(snap, registry) {
  const reg = (registry && registry.code) || {};
  const codes = {};
  for (const k of Object.keys(snap.codes)) {
    const e = reg[k];
    if (e && (e.visibility || "public") === "public") codes[k] = snap.codes[k];
  }
  return { ...snap, codes };
}

// The same quantities on a newer snapshot, matched by uid, then through the supersede chain
export function toLatest(oldSnap, newSnap, ids) {
  const oldNodes = byId(oldSnap), byUid = new Map(newSnap.nodes.map((n) => [n.uid, n.id]));
  const succ = newSnap.succession || {};
  const out = { ids: [], renamed: [], superseded: [], removed: [] };
  for (const id of ids) {
    const uid = oldNodes.get(id).uid;
    if (byUid.has(uid)) {
      const now = byUid.get(uid);
      out.ids.push(now);
      if (now !== id) out.renamed.push([id, now]);
      continue;
    }
    const seen = new Set([uid]), todo = [uid];
    let found = null;
    while (todo.length && !found) {
      for (const u of succ[todo.shift()] || []) {
        if (byUid.has(u)) { found = byUid.get(u); break; }
        if (!seen.has(u)) { seen.add(u); todo.push(u); }
      }
    }
    if (found) { out.ids.push(found); out.superseded.push([id, found]); } else out.removed.push(id);
  }
  out.ids = [...new Set(out.ids)];
  return out;
}
