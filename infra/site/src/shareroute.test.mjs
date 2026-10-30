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
  assert.match(body, new RegExp(`<meta property="og:image" content="https://openmaterials.ai/m/${H}/${kaldo}.png">`));
  assert.ok(!body.split("<style>")[0].includes('name="robots"'), "a code's own selection may be indexed");
  const one = await (await get(`/m/${H}/${encode(snap, ["Temperature"])}`)).text();
  assert.match(one.split("<style>")[0], /<meta name="robots" content="noindex">/);
  assert.match(body, /application\/json\+oembed/);
  assert.ok(!body.includes("<!--share-meta-->"));
});

test("a longer prefix gets the canonical 12-character link", async () => {
  const body = await (await get(`/m/${index.latest}/${kaldo}`)).text();
  assert.match(body, new RegExp(`<link rel="canonical" href="https://openmaterials.ai/m/${H}/${kaldo}">`));
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
  assert.match(j.html, new RegExp(`src="https://openmaterials.ai/m/${H}/${kaldo}\\?embed=1"`));
  assert.equal(j.thumbnail_width, 1200);
  assert.equal((await get(`/oembed?url=${encodeURIComponent("https://example.com/m/" + H + "/80")}`)).status, 404);
  assert.equal((await get(`/oembed?url=${u}&format=xml`)).status, 501);
});

test("past the render limit, or when a render fails, the site card stands in", async () => {
  const limited = { ...env, CARD_LIMITER: { limit: async () => ({ success: false }) } };
  // The example host, as in every other test here: on the openmaterials.ai
  // host the Worker refreshes data from the live site first, so a bundled
  // snapshot newer than the deployed one would 404 against production state.
  const r = await worker.fetch(new Request(`https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}.png`), limited);
  assert.equal(r.status, 302);
  assert.match(r.headers.get("location"), /\/assets\/og\.png$/);
  // under node the WASM bundle cannot load, so the render fails and falls back the same way
  const r2 = await worker.fetch(new Request(`https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}.png`), env);
  assert.equal(r2.status, 302);
  assert.equal((await worker.fetch(new Request(`https://openmaterials-site.example.workers.dev/m/${H}/8000.png`), env)).status, 400);
});

test("a code the live registry no longer lists drops out of the shell", async () => {
  const reg = JSON.parse(readFileSync(new URL("data/registry.json", DOCS)));
  delete reg.code.kaldo;
  const e = { ASSETS: { fetch: async (req) => (new URL(req.url).pathname === "/data/registry.json" ? Response.json(reg) : env.ASSETS.fetch(req)) } };
  const body = await (await worker.fetch(new Request(`https://openmaterials-site.example.workers.dev/m/${H}/${kaldo}`), e)).text();
  assert.ok(!body.includes("<title>kALDo"), "kALDo is no longer named");
});
