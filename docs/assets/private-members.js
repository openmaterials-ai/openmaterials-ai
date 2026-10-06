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
// `registry` is data/registry.json; one lacking its tables throws, so a caller
// that cannot read it refuses rather than passing everything.

const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const KINDS = ["configuration", "model"];

export function privateReasons(member, registry) {
  if (!isObj(registry) || !["citation_keys", "configuration", "model"].every((t) => isObj(registry[t]))) {
    throw new Error("registry lacks citation_keys, configuration or model");
  }
  if (!isObj(member)) return [];
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
