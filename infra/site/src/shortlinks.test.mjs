// node --test infra/site/src/shortlinks.test.mjs
// The short-link store's pure logic (mint validation, code discipline, the
// crawlable shell), then the Worker's /s routes against an in-memory KV.
import test from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import {
  CODE_ALPHABET, CODE_LEN, MAX_MEMBERS,
  randomCode, parseCode, validateMintBody, mintRefusal, shortlinkHTML, shortlinkNotFoundHTML,
} from "./shortlinks.js";
import worker from "./index.js";

const record = (name) => ({ id: "a".repeat(64), lineage: { node: "ThermalConductivity", material: name } });

test("codes: unambiguous alphabet, fixed length, strict parse", () => {
  assert.ok(!/[0OIl]/.test(CODE_ALPHABET), "ambiguous glyphs excluded");
  const bytes = new Uint8Array(CODE_LEN).map((_, i) => i * 37);
  const code = randomCode(bytes);
  assert.strictEqual(code.length, CODE_LEN);
  assert.strictEqual(parseCode(code), code);
  assert.strictEqual(parseCode(code.slice(1)), null);
  assert.strictEqual(parseCode(code + "!"), null);
  assert.strictEqual(parseCode(""), null);
});

test("mint: a bare record normalizes to a one-element envelope", () => {
  const v = validateMintBody(JSON.stringify(record("Si")));
  assert.ok(v.ok);
  assert.strictEqual(v.envelope.v, 1);
  assert.strictEqual(v.envelope.lineages.length, 1);
});

test("mint: a v1 envelope passes, the malformed shapes are refused", () => {
  const good = { v: 1, doc: { title: "T" }, lineages: [record("Si"), record("Ge")] };
  assert.ok(validateMintBody(JSON.stringify(good)).ok);
  for (const [bad, why] of [
    ["", "empty"],
    ["not json", "not JSON"],
    ["[1,2]", "array"],
    [JSON.stringify({ v: 2, lineages: [record("Si")] }), "unknown v"],
    [JSON.stringify({ v: 1, lineages: [] }), "empty envelope"],
    [JSON.stringify({ v: 1, lineages: [record("Si")], lineage: {} }), "both keys"],
    [JSON.stringify({ hello: "world" }), "neither"],
    [JSON.stringify({ v: 1, lineages: [{ id: "x" }] }), "member without lineage"],
    [JSON.stringify({ v: 1, lineages: Array.from({ length: MAX_MEMBERS + 1 }, () => record("Si")) }), "too many"],
  ]) {
    assert.strictEqual(validateMintBody(bad).ok, false, why);
  }
});

test("mint: the 64 KB cap holds", () => {
  const fat = { v: 1, lineages: [{ ...record("Si"), pad: "x".repeat(70 * 1024) }] };
  assert.strictEqual(validateMintBody(JSON.stringify(fat)).ok, false);
});

test("the shell carries the stored metadata and redirects into #s=", () => {
  const env = { v: 1, doc: { title: "CNT paper", source: "paper:cnt-2021-barbalinardo" }, lineages: [record("SWCNT"), record("SWCNT")] };
  const page = shortlinkHTML(env, "Abc123XYZ", "https://openmaterials.ai");
  assert.ok(page.includes('og:title" content="CNT paper"'));
  assert.ok(page.includes("2 lineages"));
  assert.ok(page.includes("paper:cnt-2021-barbalinardo"));
  assert.ok(page.includes("/play/#s=Abc123XYZ"));
  const anon = shortlinkHTML({ v: 1, lineages: [record("Si")] }, "Abc123XYZ", "https://openmaterials.ai");
  assert.ok(anon.includes("A shared set of lineages"), "no fabricated title");
  assert.ok(anon.includes("1 lineage,") || anon.includes("1 lineage"), "singular count");
});

test("the empty state names the code and fabricates nothing", () => {
  const page = shortlinkNotFoundHTML("Abc123XYZ", "https://openmaterials.ai");
  assert.ok(page.includes("Abc123XYZ"));
  assert.ok(!page.includes("og:title"));
});

test("escaping: hostile doc fields cannot break out of the shell", () => {
  const env = { v: 1, doc: { title: '<script>alert(1)</script>"' }, lineages: [record("Si")] };
  const page = shortlinkHTML(env, "Abc123XYZ", "https://openmaterials.ai");
  assert.ok(!page.includes("<script>alert"));
  assert.ok(page.includes("&lt;script&gt;"));
});

// ---- records citing evidence outside the public registry ------------------
// The pure refusal over every shared predicate vector, then the Worker itself
// (index.js) against an in-memory KV: refusal, the query-parameter opt-in, the
// stored bytes, the read headers, and the 503 when no registry is readable.

const read = (rel) => JSON.parse(readFileSync(new URL(rel, import.meta.url), "utf8"));
const vectors = read("../../../omai/vectors/private.json");
const registry = read("../../../docs/data/registry.json");

for (const c of vectors.cases) {
  test(`mint refusal agrees with the predicate: ${c.name}`, () => {
    const r = mintRefusal({ v: 1, lineages: [record("Si"), c.member] }, vectors.registry);
    if (!c.reasons.length) return assert.strictEqual(r, null);
    assert.deepStrictEqual(r.lineages, [2]);
    for (const { field } of c.reasons) assert.ok(r.error.includes(field), field);
    assert.ok(r.error.includes("Lineage 2 of 2") && r.error.includes("publish_private=1"));
  });
}

const UNREG = [{ kind: "model", uid: "2".repeat(64) }];
const marked = (name) => ({ ...record(name), unregistered: UNREG });

function memoryKV() {
  const m = new Map();
  return {
    m,
    get: async (k) => (m.has(k) ? m.get(k).value : null),
    getWithMetadata: async (k) => m.get(k) ?? { value: null, metadata: null },
    put: async (k, value, opts = {}) => void m.set(k, { value, metadata: opts.metadata ?? null }),
  };
}
const siteEnv = (reg = registry) => ({
  SHORTLINKS: memoryKV(),
  ASSETS: { fetch: async () => (reg ? Response.json(reg) : new Response("missing", { status: 404 })) },
});
const HOST = "https://openmaterials-site.example.workers.dev";
const mint = (env, body, query = "", host = HOST) =>
  worker.fetch(new Request(`${host}/s${query}`, {
    method: "POST", headers: { origin: "http://localhost:8971" }, body,
  }), env);
const get = (env, path) => worker.fetch(new Request(`${HOST}${path}`), env);

test("worker: a set citing unregistered evidence is refused, naming lineage n of m", async () => {
  const env = siteEnv();
  const res = await mint(env, JSON.stringify({ v: 1, lineages: [record("Si"), marked("Ge"), record("C")] }));
  assert.strictEqual(res.status, 400);
  const body = await res.json();
  assert.match(body.error, /Lineage 2 of 3 \(unregistered\)/);
  assert.ok(body.error.includes("publish_private=1"));
  assert.deepStrictEqual(body.lineages, [2]);
  assert.strictEqual(env.SHORTLINKS.m.size, 0, "nothing stored, no mint counted");
});

test("worker: the flag in the body, in doc, or with another value is ignored", async () => {
  const env = siteEnv();
  for (const [payload, query] of [
    [{ v: 1, publish_private: true, lineages: [marked("Si")] }, ""],
    [{ v: 1, doc: { publish_private: true }, lineages: [marked("Si")] }, ""],
    [{ ...marked("Si"), publish_private: true }, ""],
    [{ v: 1, lineages: [marked("Si")] }, "?publish_private=true"],
    [{ v: 1, lineages: [marked("Si")] }, "?publish_private=yes"],
  ]) {
    const res = await mint(env, JSON.stringify(payload), query);
    assert.strictEqual(res.status, 400, JSON.stringify(payload) + query);
    assert.match((await res.json()).error, /Lineage 1 of 1/);
  }
});

test("worker: with ?publish_private=1 the set is stored as sent, private, no-store and noindex", async () => {
  const env = siteEnv();
  const sent = JSON.stringify({ v: 1, lineages: [record("Si"), marked("Ge")] }, null, 2);
  const res = await mint(env, sent, "?publish_private=1");
  assert.strictEqual(res.status, 201);
  const { code } = await res.json();
  const stored = env.SHORTLINKS.m.get(`s:${code}`);
  assert.strictEqual(stored.value, sent, "stored bytes are the bytes sent");
  assert.strictEqual(stored.metadata.private, true);
  const raw = await get(env, `/s/${code}/raw`);
  assert.strictEqual(raw.headers.get("cache-control"), "no-store");
  assert.strictEqual(raw.headers.get("x-robots-tag"), "noindex");
  assert.strictEqual(await raw.text(), sent);
  const shell = await get(env, `/s/${code}`);
  assert.strictEqual(shell.headers.get("x-robots-tag"), "noindex");
  const page = await shell.text();
  assert.ok(page.includes('<meta name="robots" content="noindex">'));
  assert.ok(page.includes("Lineage 2 cites a model that is not in the public registry; its values cannot be checked against the commons."));
  assert.ok(!page.includes("Lineage 1 cites"));
});

test("worker: a public set and a bare record mint as before, immutable and indexable", async () => {
  const env = siteEnv();
  for (const sent of [JSON.stringify({ v: 1, lineages: [record("Si")] }), JSON.stringify(record("Ge"))]) {
    const res = await mint(env, sent);
    assert.strictEqual(res.status, 201);
    const { code } = await res.json();
    assert.strictEqual(env.SHORTLINKS.m.get(`s:${code}`).value, sent);
    assert.strictEqual(env.SHORTLINKS.m.get(`s:${code}`).metadata.private, false);
    const raw = await get(env, `/s/${code}/raw`);
    assert.match(raw.headers.get("cache-control"), /immutable/);
    assert.strictEqual(raw.headers.get("x-robots-tag"), null);
    const page = await (await get(env, `/s/${code}`)).text();
    assert.ok(page.includes("1 lineage, shared") && !page.includes("noindex"));
  }
});

test("worker: a private bare record is refused as lineage 1 of 1, then minted with the parameter", async () => {
  const env = siteEnv();
  const sent = JSON.stringify(marked("Si"));
  const refused = await mint(env, sent);
  assert.strictEqual(refused.status, 400);
  assert.match((await refused.json()).error, /Lineage 1 of 1 \(unregistered\)/);
  const res = await mint(env, sent, "?publish_private=1");
  assert.strictEqual(res.status, 201);
  const { code } = await res.json();
  assert.strictEqual(env.SHORTLINKS.m.get(`s:${code}`).value, sent);
  const page = await (await get(env, `/s/${code}`)).text();
  assert.ok(page.includes("Lineage 1 cites a model"));
});

test("worker: no usable registry (live or bundled) mints nothing and answers 503", async () => {
  const realFetch = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error("pages down"); };
  try {
    for (const [env, host] of [
      [siteEnv(null), "https://openmaterials.ai"],
      [siteEnv(null), HOST],
      [siteEnv({ model: {}, configuration: {} }), HOST],
      // readable, but its citation_keys is not the predicate's bound table
      [siteEnv({ ...registry, citation_keys: {} }), HOST],
      [siteEnv({ ...registry, citation_keys: { ...registry.citation_keys, Extra: ["x_sha256"] } }), HOST],
    ]) {
      const res = await mint(env, JSON.stringify(record("Si")), "?publish_private=1", host);
      assert.strictEqual(res.status, 503);
      assert.strictEqual(env.SHORTLINKS.m.size, 0);
    }
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("worker: a private set's shell still serves, noindex and labelled, when the registry is unusable", async () => {
  const env = siteEnv();
  const { code } = await (await mint(env, JSON.stringify(marked("Si")), "?publish_private=1")).json();
  env.ASSETS.fetch = async () => Response.json({ ...registry, citation_keys: {} });
  const shell = await get(env, `/s/${code}`);
  assert.strictEqual(shell.status, 200);
  assert.strictEqual(shell.headers.get("x-robots-tag"), "noindex");
  assert.ok((await shell.text()).includes("Some lineages cite evidence that is not in the public registry"));
});

test("worker: the live registry is read first on openmaterials.ai", async () => {
  const realFetch = globalThis.fetch;
  // a uid registered after the bundled copy was built: live passes, bundled refuses
  const live = { ...registry, model: { ...registry.model, ["2".repeat(64)]: "models/x.json" } };
  globalThis.fetch = async () => Response.json(live);
  try {
    const body = JSON.stringify({ lineage: { node: "X", conditions: { potential_sha256: "2".repeat(64) } } });
    assert.strictEqual((await mint(siteEnv(), body, "", "https://openmaterials.ai")).status, 201);
    assert.strictEqual((await mint(siteEnv(), body)).status, 400);
  } finally {
    globalThis.fetch = realFetch;
  }
});

test("worker: a set stored before the rule, or unreadable, is served no-store and noindex", async () => {
  const env = siteEnv();
  const old = JSON.stringify({ v: 1, lineages: [marked("Si")] });
  const pub = JSON.stringify({ v: 1, lineages: [record("Si")] });
  await env.SHORTLINKS.put("s:AAAAAAAAA", old, { metadata: { created: "2026-10-01", members: 1 } });
  await env.SHORTLINKS.put("s:BBBBBBBBB", pub, { metadata: { created: "2026-10-01", members: 1 } });
  await env.SHORTLINKS.put("s:CCCCCCCCC", "{}", { metadata: null });
  const headers = async (path) => (await get(env, path)).headers;
  for (const path of ["/s/AAAAAAAAA/raw", "/s/AAAAAAAAA", "/s/CCCCCCCCC/raw", "/s/CCCCCCCCC"]) {
    assert.strictEqual((await headers(path)).get("x-robots-tag"), "noindex", path);
  }
  assert.strictEqual((await headers("/s/AAAAAAAAA/raw")).get("cache-control"), "no-store");
  assert.ok((await (await get(env, "/s/AAAAAAAAA")).text()).includes("Lineage 1 cites a model"));
  assert.match((await headers("/s/BBBBBBBBB/raw")).get("cache-control"), /immutable/);
  // the registry unusable: a public set is no longer served immutable or indexable
  env.ASSETS.fetch = async () => new Response("missing", { status: 404 });
  assert.strictEqual((await headers("/s/BBBBBBBBB/raw")).get("cache-control"), "no-store");
  assert.strictEqual((await headers("/s/BBBBBBBBB")).get("x-robots-tag"), "noindex");
});
