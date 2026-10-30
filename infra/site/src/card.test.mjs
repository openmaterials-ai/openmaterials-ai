// The share card: its layout as SVG, and (when resvg is installed) the PNG it rasterizes to.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { cardSVG, fitSubmap, BOX, W, H } from "./card.js";

const DOCS = new URL("../../../docs/", import.meta.url);
const FONTS = ["newsreader-latin.ttf", "jetbrains-mono-latin.ttf", "jetbrains-mono-greek.ttf", "DejaVuSans.ttf", "dejavu-math-subset.ttf"];
const index = JSON.parse(readFileSync(new URL("data/v/index.json", DOCS)));
const snap = JSON.parse(readFileSync(new URL(`data/v/${index.latest}.json`, DOCS)));
const ALL = snap.nodes.map((n) => n.id);
const CASES = { kaldo: snap.codes.kaldo.nodes, one: ["Temperature"], all: ALL };

test("the card is 1200 x 630 and names the selection", () => {
  const s = cardSVG(snap, index.latest, CASES.kaldo);
  assert.match(s, new RegExp(`^<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}"`));
  assert.ok(s.endsWith("</svg>"));
  assert.match(s, />kALDo</);
  assert.equal((s.match(/<svg/g) || []).length, (s.match(/<\/svg>/g) || []).length);
});

test("every submap fits its box, the widest scaled down", () => {
  for (const [k, ids] of Object.entries(CASES)) {
    const f = fitSubmap(snap, ids);
    assert.ok(f.x >= BOX.x - 0.01 && f.y >= BOX.y - 0.01 && f.x + f.w <= BOX.x + BOX.w + 0.01 && f.y + f.h <= BOX.y + BOX.h + 0.01, k);
    assert.ok(f.scale <= 2, k);
  }
  assert.ok(fitSubmap(snap, ALL).scale < 0.5);
});

const RESVG = new URL("../node_modules/@resvg/resvg-wasm/index_bg.wasm", import.meta.url);
test("the card rasterizes to a 1200 x 630 PNG", { skip: !existsSync(RESVG) && "npm ci in infra/site installs resvg" }, async () => {
  const { renderPNG } = await import("./png.js");
  const font = (f) => new Uint8Array(readFileSync(new URL(`../fonts/${f}`, import.meta.url)));
  const assets = { wasm: readFileSync(RESVG), fonts: FONTS.map(font) };
  for (const [k, ids] of Object.entries(CASES)) {
    const t0 = performance.now();
    const png = await renderPNG(cardSVG(snap, index.latest, ids), assets);
    const ms = performance.now() - t0;
    assert.deepEqual([...png.slice(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
    const dv = new DataView(png.buffer, png.byteOffset);
    assert.equal(dv.getUint32(16), 1200);
    assert.equal(dv.getUint32(20), 630);
    if (process.env.CARD_OUT) writeFileSync(`${process.env.CARD_OUT}/card-${k}.png`, png);
    console.log(`card ${k}: ${png.length} bytes in ${ms.toFixed(0)} ms`);
  }
});

// The code points a TrueType font maps (cmap formats 4 and 12), enough to check coverage.
function cmap(buf) {
  const v = new DataView(buf.buffer, buf.byteOffset, buf.byteLength), out = new Set();
  const n = v.getUint16(4);
  let cm = 0;
  for (let i = 0; i < n; i++) if (String.fromCharCode(...buf.slice(12 + 16 * i, 16 + 16 * i)) === "cmap") cm = v.getUint32(12 + 16 * i + 8);
  for (let i = 0; i < v.getUint16(cm + 2); i++) {
    const t = cm + v.getUint32(cm + 4 + 8 * i + 4), fmt = v.getUint16(t);
    if (fmt === 4) {
      const seg = v.getUint16(t + 6) / 2;
      for (let k = 0; k < seg; k++) {
        const end = v.getUint16(t + 14 + 2 * k), start = v.getUint16(t + 16 + 2 * seg + 2 * k);
        for (let c = start; c <= end && c !== 0xffff; c++) out.add(c);
      }
    } else if (fmt === 12) {
      for (let k = 0; k < v.getUint32(t + 12); k++) {
        const g = t + 16 + 12 * k;
        for (let c = v.getUint32(g); c <= v.getUint32(g + 4); c++) out.add(c);
      }
    }
  }
  return out;
}

test("the bundled fonts draw every character a card can show", () => {
  const have = new Set();
  for (const f of FONTS) for (const c of cmap(new Uint8Array(readFileSync(new URL(`../fonts/${f}`, import.meta.url))))) have.add(c);
  const need = new Set();
  for (const n of snap.nodes) for (const t of [n.name, n.tier, ...(n.sym || []).map((r) => r[0])]) for (const ch of t) need.add(ch.codePointAt(0));
  for (const c of Object.values(snap.codes)) for (const ch of c.name) need.add(ch.codePointAt(0));
  const missing = [...need].filter((c) => !have.has(c)).map((c) => String.fromCodePoint(c));
  assert.deepEqual(missing, []);
});
