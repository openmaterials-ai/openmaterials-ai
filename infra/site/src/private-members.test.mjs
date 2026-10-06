// node --test infra/site/src/private-members.test.mjs
// The shared private-evidence predicate agrees with omai.evidence.private_reasons
// on every case in omai/vectors/private.json, and refuses an unreadable registry.
import test from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { privateReasons, memberLabel } from "../../../docs/assets/private-members.js";

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

test("the published registry binds the table the vectors and this module bind", () => {
  assert.deepStrictEqual(registry.citation_keys, vectors.registry.citation_keys);
  assert.deepStrictEqual(privateReasons({ lineage: {} }, registry), []);
});

test("the label names each kind once, is empty without reasons, and never claims a status", () => {
  for (const c of vectors.cases) {
    const label = memberLabel(3, c.reasons);
    if (!c.reasons.length) { assert.strictEqual(label, "", c.name); continue; }
    assert.match(label, /^Lineage 3 cites .+ not in the public registry; its values cannot be checked against the commons\.$/, c.name);
    assert.doesNotMatch(label, /private|owner|author|verified/i, c.name);
  }
  assert.strictEqual(memberLabel(1, [{ field: "unregistered", kind: "configuration" }, { field: "unregistered", kind: "model" }, { field: "conditions.potential_sha256", kind: "model" }]),
    "Lineage 1 cites a configuration and a model that are not in the public registry; its values cannot be checked against the commons.");
  assert.strictEqual(memberLabel(2, [{ field: "overlay_version", kind: "node" }]),
    "Lineage 2 cites a map node that is not in the public registry; its values cannot be checked against the commons.");
});
