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
  globalThis.fetch = async () => { throw new Error("must not fetch"); };
  assert.equal(await healthz("openmaterials-site.example.workers.dev"), "bundled");
});

test("a failing or non-ok origin falls back to the bundled assets", async () => {
  globalThis.fetch = async () => { throw new Error("down"); };
  assert.equal(await healthz("openmaterials.ai"), "bundled");
  globalThis.fetch = async () => new Response("not found", { status: 404 });
  assert.equal(await healthz("openmaterials.ai"), "bundled");
});
