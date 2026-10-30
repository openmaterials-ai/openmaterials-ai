// The share-link logic against the committed latest snapshot.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  encode, decode, parseShare, resolveSnapshot, title, codesOf, chainOf, codesCovering, relatedCodes,
  nextSteps, describe, toLatest, shareURL,
} from "../../../docs/assets/share.js";

const V = new URL("../../../docs/data/v/", import.meta.url);
const index = JSON.parse(readFileSync(new URL("index.json", V)));
const snap = JSON.parse(readFileSync(new URL(`${index.latest}.json`, V)));
const N = snap.nodes.length;
const id = (s) => snap.nodes.find((n) => n.id === s).id;

test("every code round-trips through its selection", () => {
  for (const [key, c] of Object.entries(snap.codes)) {
    const hex = encode(snap, c.nodes);
    assert.match(hex, /^(?:[0-9a-f]{2})+$/);
    assert.ok(!hex.endsWith("00"));
    const d = decode(snap, hex);
    assert.ok(d.ok, key);
    assert.deepEqual(new Set(d.ids), new Set(c.nodes));
    assert.ok(codesOf(snap, d.ids).includes(key), key);
  }
  assert.equal(encode(snap, [snap.nodes[0].id]), "80");
});

test("malformed or out-of-range selections are refused", () => {
  const bytes = (N >> 3) + 1, over = new Uint8Array(bytes);
  over[N >> 3] = 0x80 >> (N & 7);
  const overHex = Array.from(over, (x) => x.toString(16).padStart(2, "0")).join("");
  for (const bad of ["", "0", "00", "8000", "ABC", "abc", "zz", overHex]) assert.equal(decode(snap, bad).ok, false, bad);
  assert.throws(() => encode(snap, []));
});

test("paths and fragments parse; prefixes resolve", () => {
  assert.deepEqual(parseShare("/m/1db368b8ece9/80"), { snapshot: "1db368b8ece9", selection: "80" });
  assert.deepEqual(parseShare("#1db368b8ece9/80"), { snapshot: "1db368b8ece9", selection: "80" });
  for (const bad of ["/m/1db3/80", "/m/1DB368B8ECE9/80", "/m/1db368b8ece9", "/x/1db368b8ece9/80"]) assert.equal(parseShare(bad), null, bad);
  assert.deepEqual(resolveSnapshot(index, index.latest.slice(0, 12)), { ok: true, hash: index.latest });
  assert.deepEqual(resolveSnapshot(index, "ffffffffffff"), { ok: false, reason: "unknown" });
  assert.deepEqual(resolveSnapshot({ snapshots: ["aaaaaaaa1", "aaaaaaaa2"] }, "aaaaaaaa"), { ok: false, reason: "ambiguous" });
  assert.equal(shareURL(index.latest, "80"), `https://openmaterials.ai/m/${index.latest.slice(0, 12)}/80`);
});

test("titles name a code, a quantity, a chain, or the tiers", () => {
  assert.equal(title(snap, snap.codes.kaldo.nodes), "kALDo");
  assert.equal(title(snap, snap.codes.mace.nodes), `${snap.codes.fairchem.name} and ${snap.codes.mace.name}`);
  const t = snap.nodes.find((n) => n.id === "Temperature");
  assert.equal(title(snap, ["Temperature"]), t.name);
  const chain = ["Potential", "ForceConstants[order=2]"].map(id);
  assert.deepEqual(chainOf(snap, chain), chain);
  assert.equal(title(snap, chain), `${snap.nodes[0].name} to ${snap.nodes.find((n) => n.id === chain[1]).name}`);
  assert.match(title(snap, ["Temperature", "Potential"]), /^2 quantities in Sources$/);
  assert.match(title(snap, snap.nodes.map((n) => n.id)), new RegExp(`^${N} quantities across \\d+ tiers$`));
});

test("codes, related codes, next steps and the description", () => {
  const k = snap.codes.kaldo.nodes;
  const cov = codesCovering(snap, k);
  assert.deepEqual(cov[0], { key: "kaldo", name: "kALDo", count: k.length });
  const rel = relatedCodes(snap, k, ["kaldo"]);
  assert.equal(rel[0].key, "phono3py");
  assert.ok(rel.every((r) => r.key !== "kaldo" && r.score > 0 && r.score <= 1));
  const steps = nextSteps(snap, ["ForceConstants[order=2]"]);
  assert.ok(steps.some((s) => s.id === "Potential" && s.via === "input"));
  assert.ok(steps.every((s) => s.id !== "ForceConstants[order=2]"));
  assert.match(describe(snap, k), new RegExp(`^${k.length} quantities in \\d+ tiers? of the OpenMaterials map, computed by \\d+ codes?: .+ and ${k.length - 3} more\\.$`));
});

test("an older snapshot maps forward by uid and through supersedes", () => {
  const dos = snap.nodes.find((n) => n.uid.startsWith("e14b6cdd007c"));
  const old = structuredClone(snap);
  const oldUid = Object.keys(snap.succession).find((u) => u.startsWith("9b0af04f9828"));
  old.nodes.find((n) => n.id === dos.id).uid = oldUid;
  old.nodes.find((n) => n.id === "Temperature").id = "OldTemperature";
  old.nodes.find((n) => n.id === "Potential").uid = "0".repeat(64);
  const m = toLatest(old, snap, [dos.id, "OldTemperature", "Potential"]);
  assert.deepEqual(m.superseded, [[dos.id, dos.id]]);
  assert.deepEqual(m.renamed, [["OldTemperature", "Temperature"]]);
  assert.deepEqual(m.removed, ["Potential"]);
  assert.deepEqual(m.ids, [dos.id, "Temperature"]);
});
