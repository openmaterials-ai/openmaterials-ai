// The share card, 1200 x 630: the selection's title, its counts, and its submap scaled to fit. Pure:
// a string of SVG that png.js rasterizes with resvg. The submap is the same drawing as the page
// (docs/assets/submap.js), restyled with literal colors because resvg reads no CSS variables.

import { svg as submapSVG, CARD_STYLE } from "../../../docs/assets/submap.js";
import { PREFIX, counts, encode, title } from "../../../docs/assets/share.js";

export const W = 1200, H = 630;
export const BOX = { x: 48, y: 176, w: 1104, h: 384 };

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const clip = (s, n) => (Array.from(s).length <= n ? s : Array.from(s).slice(0, n - 1).join("").trimEnd() + "…");

// {svg, scale}: the submap fitted into BOX, enlarged at most twice so a small one still reads
export function fitSubmap(snap, ids) {
  const inner = submapSVG(snap, ids, { mapHref: "/map/" });
  const m = /viewBox="0 0 (\d+) (\d+)"/.exec(inner);
  const w = +m[1], h = +m[2];
  const scale = Math.min(BOX.w / w, BOX.h / h, 2);
  const dw = w * scale, dh = h * scale, x = BOX.x + (BOX.w - dw) / 2, y = BOX.y + (BOX.h - dh) / 2;
  const placed = inner.replace(/ width="\d+" height="\d+"/, ` x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${dw.toFixed(1)}" height="${dh.toFixed(1)}"`);
  return { svg: placed, scale, x, y, w: dw, h: dh };
}

export function cardSVG(snap, hash, ids) {
  const fit = fitSubmap(snap, ids);
  const named = title(snap, ids);
  const link = `openmaterials.ai/m/${hash.slice(0, PREFIX)}/${clip(encode(snap, ids), 20)}`;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">` +
    `<style>${CARD_STYLE}.k{font-family:'JetBrains Mono';font-size:18px;fill:#57524A;letter-spacing:.04em}` +
    `.t{font-family:Newsreader;font-size:46px;fill:#1C1A17}.c{font-family:Newsreader;font-size:24px;fill:#57524A}</style>` +
    `<rect width="${W}" height="${H}" fill="#F4F1EA"/>` +
    `<text class="k" x="48" y="58">OPENMATERIALS.AI · SHARED MAP SELECTION</text>` +
    `<text class="t" x="48" y="118">${esc(clip(named, 44))}</text>` +
    `<text class="c" x="48" y="156">${esc(counts(snap, ids))}</text>` +
    fit.svg +
    `<rect x="0" y="${H - 6}" width="${W}" height="6" fill="#4F46E5"/>` +
    `<text class="k" x="48" y="602">${esc(link)}</text>` +
    `<text class="k" x="1152" y="602" text-anchor="end">map ${esc(snap.map_version.slice(0, 8))}</text>` +
    `</svg>`;
}
