// The tiered submap of a share-link snapshot (docs/data/v/<hash>.json): quantities in tier columns,
// named, with the data flow between them. A line-for-line port of omai/submap.py (layout, _edge_path,
// svg) that reads the names and symbol runs the snapshot already carries; tests/test_submap_js.py
// checks that both draw the same SVG, byte for byte, for every code. The landing page, the map and
// the site Worker's share card import it.

const BOX_W = 184, BOX_H = 48, ROW_GAP = 14;
const COL_W = 208, COL_GAP = 60, HEAD_H = 30, PAD = 12;

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#x27;");
// Python's format(x, ".0f"): round half to even
function f0(x) {
  const r = Math.round(x);
  return String(Math.abs(x % 1) === 0.5 && r % 2 !== 0 ? r - 1 : r);
}
// Python's default ordering of strings and of tuples of them
const cmp = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
const cmpPair = (a, b) => cmp(a[0], b[0]) || cmp(a[1], b[1]);

function truncate(s, n) {
  const cs = Array.from(s);
  return cs.length <= n ? s : cs.slice(0, n - 1).join("").trimEnd() + "…";
}

export function layout(snap, ids) {
  const nodes = new Map(snap.nodes.map((n) => [n.id, n]));
  const links = snap.links.filter(([s, t]) => nodes.has(s) && nodes.has(t)).map(([s, t]) => [s, t]);
  const drawn = new Set(ids.filter((i) => nodes.has(i)));
  let ctx = new Set();
  if (drawn.size < 4) {  // the inputs the selected quantities need, and their outputs when there are few
    const ins = new Set(links.filter(([s, t]) => drawn.has(t) && !drawn.has(s)).map(([s]) => s));
    const outs = new Set(links.filter(([s, t]) => drawn.has(s) && !drawn.has(t)).map(([, t]) => t));
    ctx = new Set([...ins, ...(outs.size <= 6 ? outs : [])]);
  }
  const shown = new Set([...drawn, ...ctx]);
  const edges = links.filter(([s, t]) => shown.has(s) && shown.has(t));
  const order = new Map(snap.tiers.map((t, i) => [t.name, t.order ?? i]));
  const tierOf = (i) => nodes.get(i).tier || "Other";
  const rank = (n) => (order.has(n) ? order.get(n) : 1e6);
  const tiers = [...new Set([...shown].map(tierOf))].sort((a, b) => rank(a) - rank(b) || cmp(a, b));
  // longest path from a source, by relaxation over sorted ids; a cycle stops after shown.size rounds
  const orderIds = [...shown].sort(cmp);
  const depth = new Map(orderIds.map((i) => [i, 0]));
  const sortedEdges = [...edges].sort(cmpPair);
  for (let r = 0; r < orderIds.length; r++) {
    let changed = false;
    for (const [s, t] of sortedEdges) {
      if (s !== t && depth.get(t) < depth.get(s) + 1 && depth.get(s) + 1 <= orderIds.length) {
        depth.set(t, depth.get(s) + 1);
        changed = true;
      }
    }
    if (!changed) break;
  }
  const columns = new Map(tiers.map((t) => [t, [...shown].filter((i) => tierOf(i) === t)
    .sort((a, b) => depth.get(a) - depth.get(b) || cmp(a, b))]));
  const pos = new Map();
  tiers.forEach((t, ci) => {
    const x = PAD + ci * (COL_W + COL_GAP) + (COL_W - BOX_W) / 2;
    columns.get(t).forEach((i, ri) => pos.set(i, { x, y: PAD + HEAD_H + ri * (BOX_H + ROW_GAP), col: ci, row: ri }));
  });
  let width = PAD * 2 + tiers.length * COL_W + Math.max(0, tiers.length - 1) * COL_GAP;
  // a loop within a column bows right to x0 + 0.75 * bow; in the last column that can pass the right edge
  for (const [s, t] of edges) {
    if (pos.get(s).col === pos.get(t).col) width = Math.max(width, Math.ceil(pos.get(s).x + BOX_W + 0.75 * bow(pos.get(s), pos.get(t)) + 2));
  }
  const tallest = Math.max(0, ...[...columns.values()].map((c) => c.length));
  const height = PAD * 2 + HEAD_H + tallest * (BOX_H + ROW_GAP) - ROW_GAP;
  return { tiers, columns, pos, edges, ctx, nodes, width, height: Math.max(height, 80) };
}

const bow = (a, b) => 28 + 6 * Math.abs(b.row - a.row);

function edgePath(a, b) {
  if (b.col > a.col) {
    const x0 = a.x + BOX_W, y0 = a.y + BOX_H / 2, x1 = b.x, y1 = b.y + BOX_H / 2;
    const dx = Math.max(24, (x1 - x0) * 0.5);
    return `M${f0(x0)} ${f0(y0)} C${f0(x0 + dx)} ${f0(y0)} ${f0(x1 - dx)} ${f0(y1)} ${f0(x1)} ${f0(y1)}`;
  }
  if (b.col === a.col) {
    const x0 = a.x + BOX_W, y0 = a.y + BOX_H / 2, x1 = b.x + BOX_W, y1 = b.y + BOX_H / 2;
    const w = bow(a, b);
    return `M${f0(x0)} ${f0(y0)} C${f0(x0 + w)} ${f0(y0)} ${f0(x1 + w)} ${f0(y1)} ${f0(x1)} ${f0(y1)}`;
  }
  const x0 = a.x + BOX_W / 2, y0 = a.y, x1 = b.x + BOX_W / 2, y1 = b.y;
  const top = Math.min(y0, y1) - 40;
  return `M${f0(x0)} ${f0(y0)} C${f0(x0)} ${f0(top)} ${f0(x1)} ${f0(top)} ${f0(x1)} ${f0(y1)}`;
}

function symbolSVG(runs) {
  if (!runs || !runs.length) return "";
  return runs.map(([t, lv]) => lv === "sub" ? `<tspan baseline-shift="sub" font-size="75%">${esc(t)}</tspan>`
    : lv === "sup" ? `<tspan baseline-shift="super" font-size="75%">${esc(t)}</tspan>` : esc(t)).join("");
}

// The submap; one no wider than fitUnder px scales to its container instead of scrolling.
export function svg(snap, ids, { mapHref = "../../map/", fitUnder = 0 } = {}) {
  const L = layout(snap, ids);
  const out = [
    `<svg class="submap-svg${L.width <= fitUnder ? " fit" : ""}" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${L.width} ${L.height}" ` +
    `width="${L.width}" height="${L.height}" role="group" aria-label="The quantities on the map, by tier, with the data flow between them">`,
    '<defs><marker id="sm-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">' +
    '<path d="M0 0 L10 5 L0 10 Z" class="sm-head"/></marker></defs>',
  ];
  L.tiers.forEach((t, ci) => {
    const x = PAD + ci * (COL_W + COL_GAP);
    out.push(`<rect class="sm-col" x="${x}" y="${PAD}" width="${COL_W}" height="${L.height - 2 * PAD}" rx="4"/>`);
    out.push(`<text class="sm-tier" x="${x + 12}" y="${PAD + 19}">${esc(t)}</text>`);
  });
  for (const [s, t] of L.edges) out.push(`<path class="sm-edge" d="${edgePath(L.pos.get(s), L.pos.get(t))}" marker-end="url(#sm-arrow)"/>`);
  for (const [i, p] of L.pos) {
    const n = L.nodes.get(i);
    const sym = symbolSVG(n.sym);
    const cls = "sm-node" + (L.ctx.has(i) ? " sm-ctx" : "") + (n.type === "hidden" ? " sm-hid" : "");
    out.push(`<a href="${mapHref}#node=${esc(i)}" class="${cls}"><title>${esc(n.name)}: ${esc(i)}</title>`);
    out.push(`<rect x="${f0(p.x)}" y="${f0(p.y)}" width="${BOX_W}" height="${BOX_H}" rx="6"/>`);
    if (sym) {
      out.push(`<text class="sm-name" x="${f0(p.x + 12)}" y="${f0(p.y + 20)}">${esc(truncate(n.name, 26))}</text>`);
      out.push(`<text class="sm-sym" x="${f0(p.x + 12)}" y="${f0(p.y + 38)}">${sym}</text>`);
    } else {
      out.push(`<text class="sm-name" x="${f0(p.x + 12)}" y="${f0(p.y + 29)}">${esc(truncate(n.name, 26))}</text>`);
    }
    out.push("</a>");
  }
  out.push("</svg>");
  return out.join("");
}

// The submap's classes in the light theme's literal colors, for renderers without CSS variables (resvg).
export const CARD_STYLE =
  ".sm-col{fill:#FBFAF6;stroke:#DDD7CB}" +
  ".sm-tier{font-family:'JetBrains Mono';font-size:11px;font-weight:500;letter-spacing:.06em;fill:#57524A}" +
  ".sm-edge{fill:none;stroke:#8E877B;stroke-width:1.4;opacity:.8}.sm-head{fill:#8E877B}" +
  ".sm-node rect{fill:#F4F1EA;stroke:#4F46E5;stroke-width:1.4}.sm-hid rect{stroke-dasharray:4 3}" +
  ".sm-ctx rect{stroke:#DDD7CB}.sm-ctx text{fill:#57524A}" +
  ".sm-name{font-family:Newsreader;font-size:13px;fill:#1C1A17}" +
  ".sm-sym{font-family:'JetBrains Mono';font-size:12px;fill:#4F46E5}";
