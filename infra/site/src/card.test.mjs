// The share card: its layout as SVG, and (when resvg is installed) the PNG it rasterizes to.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { cardSVG, fitSubmap, BOX, W, H } from "./card.js";

const DOCS = new URL("../../../docs/", import.meta.url);
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
  const assets = { wasm: readFileSync(RESVG), fonts: ["newsreader-latin.ttf", "jetbrains-mono-latin.ttf", "jetbrains-mono-greek.ttf", "DejaVuSans.ttf"].map(font) };
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
