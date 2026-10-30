// The /m/ share routes and /oembed through the Worker, with the bundled assets as the only data.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import worker from "./index.js";
import { encode } from "../../../docs/assets/share.js";

const DOCS = new URL("../../../docs/", import.meta.url);
const env = { ASSETS: { fetch: async (req) => {
  const path = new URL(req.url).pathname;
  try { return new Response(readFileSync(new URL("." + path, DOCS))); } catch (e) { return new Response("not found", { status: 404 }); }
} } };
const index = JSON.parse(readFileSync(new URL("data/v/index.json", DOCS)));
const snap = JSON.parse(readFileSync(new URL(`data/v/${index.latest}.json`, DOCS)));
const H = index.latest.slice(0, 12);
const kaldo = encode(snap, snap.codes.kaldo.nodes);
const get = (path) => worker.fetch(new Request(`https://openmaterials-site.example.workers.dev${path}`), env);

test("a share page carries the card and oEmbed tags crawlers read", async () => {
  const r = await get(`/m/${H}/${kaldo}`);
  assert.equal(r.status, 200);
  const body = await r.text();
  assert.match(body, /<title>kALDo \| OpenMaterials<\/title>/);
  assert.match(body, /<meta name="twitter:card" content="summary_large_image">/);
  assert.match(body, new RegExp(`<meta property="og:image" content="https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}.png">`));
  assert.match(body, /application\/json\+oembed/);
  assert.ok(!body.includes("<!--share-meta-->"));
});

test("a longer prefix gets the canonical 12-character link", async () => {
  const body = await (await get(`/m/${index.latest}/${kaldo}`)).text();
  assert.match(body, new RegExp(`<link rel="canonical" href="https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}">`));
});

test("bad links are refused before anything is rendered", async () => {
  assert.equal((await get(`/m/zz/80`)).status, 400);
  assert.equal((await get(`/m/${H}/ABC`)).status, 400);
  assert.equal((await get(`/m/${H}/8000`)).status, 400);
  const n = snap.nodes.length, buf = new Uint8Array((n >> 3) + 1);
  buf[n >> 3] = 0x80 >> (n & 7);
  assert.equal((await get(`/m/${H}/${Array.from(buf, (x) => x.toString(16).padStart(2, "0")).join("")}`)).status, 400);
  const unknown = await get(`/m/ffffffffffff/80`);
  assert.equal(unknown.status, 404);
  assert.match(await unknown.text(), /ffffffffffff/);
});

test("oEmbed answers a rich iframe of the embed view", async () => {
  const u = encodeURIComponent(`https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}`);
  const r = await get(`/oembed?url=${u}&maxwidth=500`);
  assert.equal(r.status, 200);
  const j = await r.json();
  assert.equal(j.type, "rich");
  assert.equal(j.width, 500);
  assert.match(j.html, new RegExp(`src="https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}\\?embed=1"`));
  assert.equal(j.thumbnail_width, 1200);
  assert.equal((await get(`/oembed?url=${encodeURIComponent("https://example.com/m/" + H + "/80")}`)).status, 404);
  assert.equal((await get(`/oembed?url=${u}&format=xml`)).status, 501);
});

test("a stored card is served from KV; past the daily limit the site card stands in", async () => {
  const store = new Map();
  const kv = { get: async (k, type) => (store.has(k) ? store.get(k) : null), put: async (k, v) => { store.set(k, v); } };
  const e = { ...env, SHORTLINKS: kv };
  const key = `card:${index.latest}:${kaldo}`;
  store.set(key, new Uint8Array([137, 80, 78, 71]).buffer);
  const r = await worker.fetch(new Request(`https://openmaterials.ai/m/${H}/${kaldo}.png`), e);
  assert.equal(r.status, 200);
  assert.equal(r.headers.get("content-type"), "image/png");
  assert.match(r.headers.get("cache-control"), /immutable/);
  const { CARDS_PER_DAY } = await import("./shareroute.js");
  store.set(`rl:card:${new Date().toISOString().slice(0, 10)}:unknown`, String(CARDS_PER_DAY));
  const other = encode(snap, ["Temperature"]);
  const r2 = await worker.fetch(new Request(`https://openmaterials.ai/m/${H}/${other}.png`), e);
  assert.equal(r2.status, 302);
  assert.match(r2.headers.get("location"), /\/assets\/og\.png$/);
  assert.equal((await worker.fetch(new Request(`https://openmaterials.ai/m/${H}/8000.png`), e)).status, 400);
});
