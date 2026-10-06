// Pure logic for the /s short-link store: DOM-free and fetch-free so
// node:test exercises it directly. The Worker (index.js) supplies KV and the
// request; nothing here fabricates a payload, and minting is the ONLY write
// surface the site Worker has.
//
// Policy, stated where it is enforced:
//   - a short link names an ENVELOPE (or a bare lineage record, normalized on
//     read like everywhere else); nothing else is storable
//   - payload cap 64 KB as sent; member cap 64 lineages
//   - minting is public but rate-limited per IP per day; a minted payload is
//     PUBLIC by construction (anyone with the code can read it)
//   - codes are 9 chars of an unambiguous base58 alphabet, collision-checked
//   - a member citing evidence outside the public registry (private-members.js)
//     is refused unless the request opts in with ?publish_private=1; the
//     stored bytes are exactly the bytes sent, so nothing marks the opt-in
//     but the KV metadata

import { privateReasons, memberLabel } from "../../../docs/assets/private-members.js";

const CODE_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz";
const CODE_LEN = 9;
const CODE_RE = new RegExp(`^[${CODE_ALPHABET}]{${CODE_LEN}}$`);
const MAX_PAYLOAD_BYTES = 64 * 1024;
const MAX_MEMBERS = 64;
const MINTS_PER_DAY = 20;

function randomCode(randomValues) {
  // randomValues: a Uint8Array(CODE_LEN) already filled by crypto (injected
  // so tests are deterministic). Modulo bias over 58 symbols from 256 values
  // is acceptable for an unguessability handle (not a key).
  let out = "";
  for (let i = 0; i < CODE_LEN; i++) out += CODE_ALPHABET[randomValues[i] % CODE_ALPHABET.length];
  return out;
}

function parseCode(segment) {
  const c = String(segment == null ? "" : segment).trim();
  return CODE_RE.test(c) ? c : null;
}

// Validate a mint body: a bare lineage record or a v1 envelope. Returns
// {ok: true, envelope} with the payload normalized to envelope form,
// or {ok: false, error}. Mirrors the page's normalizeEnvelope contract: a
// bare record becomes a one-element envelope; both-keys or unknown v rejects.
function validateMintBody(text) {
  if (typeof text !== "string" || !text.length) return { ok: false, error: "empty body" };
  if (text.length > MAX_PAYLOAD_BYTES) return { ok: false, error: "payload exceeds 64 KB" };
  let payload;
  try {
    payload = JSON.parse(text);
  } catch (e) {
    return { ok: false, error: "not JSON" };
  }
  if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
    return { ok: false, error: "not an object" };
  }
  let envelope;
  if (Array.isArray(payload.lineages)) {
    if (payload.v !== 1) return { ok: false, error: "unknown envelope version" };
    if (payload.lineage) return { ok: false, error: "both envelope and record keys" };
    if (!payload.lineages.length) return { ok: false, error: "empty envelope" };
    if (payload.lineages.length > MAX_MEMBERS) return { ok: false, error: "too many lineages" };
    envelope = payload;
  } else if (payload.lineage && typeof payload.lineage === "object") {
    envelope = { v: 1, lineages: [payload] };
  } else {
    return { ok: false, error: "neither an envelope nor a lineage record" };
  }
  for (const m of envelope.lineages) {
    if (!m || typeof m !== "object" || !m.lineage || typeof m.lineage !== "object") {
      return { ok: false, error: "a member carries no lineage" };
    }
  }
  return { ok: true, envelope };
}

// The refusal for an envelope whose members cite evidence outside the public
// registry, or null when none does. Throws when the registry lacks its tables.
function mintRefusal(envelope, registry) {
  const m = envelope.lineages.length;
  const lines = [], lineages = [];
  envelope.lineages.forEach((member, i) => {
    const fields = [...new Set(privateReasons(member, registry).map((r) => r.field))];
    if (!fields.length) return;
    lines.push(`Lineage ${i + 1} of ${m} (${fields.join(", ")})`);
    lineages.push(i + 1);
  });
  if (!lines.length) return null;
  return {
    error: `Not minted: a short link is public, and these lineages cite evidence that is not in the public registry: ${lines.join("; ")}. To publish them anyway, repeat the request with the query parameter publish_private=1.`,
    lineages,
  };
}

// The reader's label per member citing such evidence (the playground's words).
const memberLabels = (envelope, registry) =>
  envelope.lineages.map((member, i) => memberLabel(i + 1, privateReasons(member, registry))).filter(Boolean);

const esc = (s) =>
  String(s == null ? "" : s).replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]
  );

// The crawlable shell for a stored short link. Everything shown comes from
// the stored envelope; a missing doc title gets the generic form. `labels`
// (memberLabels) join the description; `noindex` keeps the shell out of search.
function shortlinkHTML(envelope, code, origin, { labels = [], noindex = false } = {}) {
  const n = envelope.lineages.length;
  const doc = envelope.doc || {};
  const title = doc.title ? String(doc.title) : `A shared set of lineages`;
  const src = doc.source ? `, source ${doc.source}` : "";
  const desc = [`${n} lineage${n === 1 ? "" : "s"}${src}, shared on the openmaterials playground.`, ...labels].join(" ");
  const target = `${origin}/play/#s=${code}`;
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${esc(title)}</title>${noindex ? '\n<meta name="robots" content="noindex">' : ""}
<meta property="og:type" content="website">
<meta property="og:site_name" content="openmaterials.ai">
<meta property="og:title" content="${esc(title)}">
<meta property="og:description" content="${esc(desc)}">
<meta name="twitter:card" content="summary">
<link rel="canonical" href="${esc(origin)}/s/${code}">
<meta http-equiv="refresh" content="0;url=${esc(target)}">
</head>
<body>
<p>${esc(title)}: ${esc(desc)}</p>
<p><a href="${esc(target)}">Open the datasheets</a></p>
<script>location.replace(${JSON.stringify(target)});</script>
</body>
</html>
`;
}

function shortlinkNotFoundHTML(code, origin) {
  return `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>No shared set</title></head>
<body>
<p>No shared set lives at the code <code>${esc(code)}</code>. Short links are
minted from the playground; this one may have been mistyped.</p>
<p><a href="${esc(origin)}/play/">Open the playground</a></p>
</body>
</html>
`;
}

export {
  CODE_ALPHABET, CODE_LEN, CODE_RE, MAX_PAYLOAD_BYTES, MAX_MEMBERS, MINTS_PER_DAY,
  randomCode, parseCode, validateMintBody, mintRefusal, memberLabels, shortlinkHTML, shortlinkNotFoundHTML,
};
