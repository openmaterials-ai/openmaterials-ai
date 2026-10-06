// node --test infra/site/src/private-members.test.mjs
// The shared private-evidence predicate agrees with omai.evidence.private_reasons
// on every case in omai/vectors/private.json, and refuses an unreadable registry.
import test from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { privateReasons } from "../../../docs/assets/private-members.js";

const vectors = JSON.parse(readFileSync(new URL("../../../omai/vectors/private.json", import.meta.url), "utf8"));
const registry = JSON.parse(readFileSync(new URL("../../../docs/data/registry.json", import.meta.url), "utf8"));

for (const c of vectors.cases) {
  test(`vector ${c.name}`, () => {
    assert.deepStrictEqual(privateReasons(c.member, vectors.registry), c.reasons);
  });
}

for (const r of vectors.refused_registries) {
  test(`refused registry ${r.name}`, () => {
    assert.throws(() => privateReasons({ lineage: {} }, r.registry));
  });
}

test("a registry without its tables throws instead of passing everything", () => {
  for (const bad of [null, {}, { model: {}, configuration: {} }, { ...registry, citation_keys: [] }]) {
    assert.throws(() => privateReasons({ lineage: {} }, bad));
  }
});

test("the published registry still binds every citation key the vectors use", () => {
  for (const [node, keys] of Object.entries(vectors.registry.citation_keys)) {
    assert.deepStrictEqual(registry.citation_keys[node], keys, node);
  }
});
