// Why a lineage record cites evidence that is not in the public registry: the
// predicate the site Worker's short-link store and the playground share, so a
// refusal and a label name the same members and fields. A mirror of
// omai.evidence.private_reasons; omai/vectors/private.json holds the cases both
// must agree on. Fail closed on shape:
//   - `unregistered` present and not []: one reason per entry, kind the entry's
//     kind (configuration or model, else null); a non-list is one reason
//   - `overlay_version` present and not null: kind "node"
//   - lineage.material.configuration ("sha256:" stripped) not in the registry
//   - a registry citation key in lineage.conditions whose value is not a
//     registered model uid
//   - a member that is not an object: field "record"
// `registry` is data/registry.json. One lacking its tables, or whose
// citation_keys is not exactly BOUND (the keys omai.evidence.CITATION_KEYS
// binds, same nodes, same keys in order), throws, so a caller that cannot read
// it refuses rather than checking fewer keys. A stale copy (the one bundled into
// the Worker) over-refuses a uid registered after it was built; a key bound
// later makes the registry and this module disagree, which throws until both
// are redeployed. The Worker reads the live registry first and uses the bundled
// copy only when the live one is unreadable.

const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const KINDS = ["configuration", "model"];
const BOUND = { Potential: ["potential_sha256", "base_potential_sha256"], SetVoltage: ["calibration_sha256"] };
const bindsExactly = (table) =>
  isObj(table) &&
  Object.keys(table).length === Object.keys(BOUND).length &&
  Object.entries(BOUND).every(
    ([node, keys]) => has(table, node) && Array.isArray(table[node]) &&
      table[node].length === keys.length && keys.every((k, i) => table[node][i] === k),
  );

export function privateReasons(member, registry) {
  if (
    !isObj(registry) ||
    !["citation_keys", "configuration", "model"].every((t) => isObj(registry[t])) ||
    !bindsExactly(registry.citation_keys)
  ) {
    throw new Error("registry lacks configuration or model, or its citation_keys is not the bound table");
  }
  if (!isObj(member)) return [{ field: "record", kind: null }];
  const out = [];
  if (has(member, "unregistered")) {
    const listed = member.unregistered;
    if (!Array.isArray(listed)) out.push({ field: "unregistered", kind: null });
    for (const entry of Array.isArray(listed) ? listed : []) {
      const kind = isObj(entry) ? entry.kind : null;
      out.push({ field: "unregistered", kind: KINDS.includes(kind) ? kind : null });
    }
  }
  if (member.overlay_version != null) out.push({ field: "overlay_version", kind: "node" });
  const lineage = isObj(member.lineage ?? member.recipe) ? (member.lineage ?? member.recipe) : {};
  const material = lineage.material;
  if (isObj(material) && has(material, "configuration")) {
    let pin = material.configuration;
    if (typeof pin === "string" && pin.startsWith("sha256:")) pin = pin.slice("sha256:".length);
    if (!(typeof pin === "string" && has(registry.configuration, pin))) {
      out.push({ field: "material.configuration", kind: "configuration" });
    }
  }
  const conditions = isObj(lineage.conditions) ? lineage.conditions : {};
  for (const keys of Object.values(registry.citation_keys)) {
    for (const key of keys) {
      const uid = conditions[key];
      if (has(conditions, key) && !(typeof uid === "string" && has(registry.model, uid))) {
        out.push({ field: `conditions.${key}`, kind: "model" });
      }
    }
  }
  return out;
}

// The reader's label for lineage n (numbered from 1) given its reasons, "" when
// there are none: one wording for the playground and the Worker's shell.
const WORDS = { configuration: "a configuration", model: "a model", node: "a map node" };
export function memberLabel(n, reasons) {
  const kinds = [...new Set(reasons.map((r) => WORDS[r.kind] || "evidence"))];
  if (!kinds.length) return "";
  return `Lineage ${n} cites ${kinds.join(" and ")} that ${kinds.length > 1 ? "are" : "is"} not in the public registry; its values cannot be checked against the commons.`;
}
