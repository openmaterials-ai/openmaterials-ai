// The data source of the Worker's routes: the Pages origin on openmaterials.ai,
// the bundled assets everywhere else and whenever the origin fails.
import { test } from "node:test";
import assert from "node:assert/strict";
import worker from "./index.js";

const env = { ASSETS: { fetch: async () => Response.json({ version: "bundled" }) } };
const healthz = async (host) => (await (await worker.fetch(new Request(`https://${host}/healthz`), env)).json()).version;

test("openmaterials.ai reads the live origin", async () => {
  globalThis.fetch = async () => Response.json({ version: "live" });
  assert.equal(await healthz("openmaterials.ai"), "live");
});

test("other hosts read the bundled assets", async () => {
  globalThis.fetch = async () => Response.json({ version: "live" });
  assert.equal(await healthz("openmaterials-site.example.workers.dev"), "bundled");
});

test("a failing or non-ok origin falls back to the bundled assets", async () => {
  globalThis.fetch = async () => { throw new Error("down"); };
  assert.equal(await healthz("openmaterials.ai"), "bundled");
  globalThis.fetch = async () => new Response("not found", { status: 404 });
  assert.equal(await healthz("openmaterials.ai"), "bundled");
});

// The domain routes /s exactly, which misses once a query is added, so the playground mints at /s/ (routed as /s/*).
test("minting answers at /s and /s/, with or without the publish_private query", async () => {
  for (const path of ["/s", "/s/", "/s?publish_private=1", "/s/?publish_private=1"]) {
    const post = await worker.fetch(new Request(`https://openmaterials.ai${path}`, { method: "POST", headers: { origin: "https://evil.example" }, body: "{}" }), env);
    assert.equal(post.status, 403, path);
    assert.equal((await post.json()).error, "origin not allowed to mint", path);
    const pre = await worker.fetch(new Request(`https://openmaterials.ai${path}`, { method: "OPTIONS", headers: { origin: "https://evil.example" } }), env);
    assert.equal(pre.status, 403, path);
  }
});

// The Lean badge reads the map's own counts (docs/data/map_layers.json), as the static file does.
test("the Lean badge counts the formulas with a Lean theorem", async () => {
  const { readFileSync } = await import("node:fs");
  const { statBadgeSVG } = await import("./badge.js");
  const layers = JSON.parse(readFileSync(new URL("../../../docs/data/map_layers.json", import.meta.url), "utf8"));
  const f = layers.counts.formulas, total = Object.values(f).reduce((a, b) => a + b, 0);
  const e = { ASSETS: { fetch: async (req) => (new URL(req.url).pathname === "/data/map_layers.json" ? Response.json(layers) : new Response("", { status: 404 })) } };
  const res = await worker.fetch(new Request("https://openmaterials-site.example.workers.dev/badge/stat/lean.svg"), e);
  assert.equal(res.status, 200);
  assert.equal(await res.text(), statBadgeSVG("lean theorems", `${f.local + f.physlib}/${total} formulas`));
});
