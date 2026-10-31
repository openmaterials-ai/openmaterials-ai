// The openmaterials site Worker. The static site (docs/) is served as edge
// assets untouched; this script runs only for the routes named in
// wrangler.jsonc run_worker_first:
//
//   GET /healthz        liveness + the published map/lineage version
//   GET /l/<64-hex>     canonical permalink: resolve a lineage id against the
//                       committed projection, serve OG metadata, redirect to
//                       the playground datasheet. A 404 or 400 otherwise.
//
// The Worker holds no state and no secrets. On openmaterials.ai it reads the
// data files from the Pages origin, which every browser reads and which
// updates on each push; its bundled assets update only on deploy and serve
// as the fallback (and as the data on workers.dev and in wrangler dev). So
// the resolver and the badges follow the site once Pages publishes; a change
// to a data file's shape still needs a Worker deploy.

import {
  parsePrefix, resolvePrefix, permalinkHTML, notFoundHTML, ambiguousHTML,
  parseLPath, entriesBySource, entrySourceRef,
  sourceListingHTML, sourceEmptyHTML, sourceMismatchHTML,
} from "./resolve.js";
import {
  MINTS_PER_DAY, randomCode, parseCode, validateMintBody, mintRefusal, memberLabels,
  shortlinkHTML, shortlinkNotFoundHTML,
} from "./shortlinks.js";
import { badgeSVG, statBadgeSVG, BADGE_PATH_RE, STAT_BADGE_PATH_RE } from "./badge.js";
import { CARD_VERSION, parseMPath, shareMeta, shellHTML, oembedJSON, errorHTML } from "./shareroute.js";
import { PREFIX, decode, encode, resolveSnapshot, withPublicCodes } from "../../../docs/assets/share.js";

// Origins allowed to mint (the read side is public by design). localhost
// covers wrangler dev and the docs http.server used by tests.
const MINT_ORIGINS = [
  "https://openmaterials.ai",
  "https://openmaterials-site.giuseppe-barbalinardo.workers.dev",
];
const isMintOrigin = (o) =>
  !!o && (MINT_ORIGINS.includes(o) || /^http:\/\/localhost(:\d+)?$/.test(o));

const corsHeaders = (origin) => ({
  "access-control-allow-origin": origin,
  "access-control-allow-methods": "POST, OPTIONS",
  "access-control-allow-headers": "content-type",
});

async function asset(env, request, path, read, ttl = 60) {
  const url = new URL(request.url);
  url.pathname = path;
  url.search = "";
  if (url.hostname === "openmaterials.ai") {
    try {
      const live = await fetch(url, { cf: { cacheTtl: ttl }, signal: AbortSignal.timeout(3000) });
      if (live.ok) return await read(live);
      console.warn(`live ${path}: ${live.status}; using the bundled copy`);
    } catch (e) {
      console.warn(`live ${path}: ${e}; using the bundled copy`);
    }
  }
  const res = await env.ASSETS.fetch(new Request(url, { method: "GET" }));
  if (!res.ok) throw new Error(`asset ${path}: ${res.status}`);
  return read(res);
}
const assetJSON = (env, request, path) => asset(env, request, path, (r) => r.json());
const assetText = (env, request, path) => asset(env, request, path, (r) => r.text());

const html = (body, status, headers = {}) =>
  new Response(body, {
    status,
    headers: { "content-type": "text/html; charset=utf-8", ...headers },
  });

// Crawlers skip a stored set that cites evidence outside the public registry.
const NOINDEX = { "x-robots-tag": "noindex" };

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === "/healthz") {
      try {
        const v = await assetJSON(env, request, "/data/version.json");
        return Response.json({ ok: true, version: v.version || null });
      } catch (e) {
        return Response.json({ ok: false }, { status: 500 });
      }
    }

    // /badge/<hash>.svg: the version badge for any pinned map version, a
    // pure function of the path (the badge asserts the embedder's pin; it
    // does not certify the hash exists). /badge.svg itself is the static
    // asset for the CURRENT version, written at map_data time.
    if (url.pathname.startsWith("/badge/")) {
      // /badge/stat/<name>.svg: a live statistic of the published map,
      // computed from the same data files every page reads. Short cache:
      // the numbers move with deploys, not with wall clock.
      const sm = url.pathname.match(STAT_BADGE_PATH_RE);
      if (sm) {
        try {
          const name = sm[1];
          let count, label = name;
          if (name === "lean") {
            // the operators with a Lean theorem out of all operators, as omai.map_layers.lean_badge counts them
            const f = (await assetJSON(env, request, "/data/map_layers.json")).counts.formulas;
            label = "Lean theorems";
            count = `${f.local + f.physlib}/${Object.values(f).reduce((a, b) => a + b, 0)} operators`;
          } else if (name === "nodes") {
            const graph = await assetJSON(env, request, "/data/graph.json");
            count = (graph.nodes || []).length;
          } else if (name === "operators") {
            // the home page count: one row per operator
            const roadmap = await assetJSON(env, request, "/data/lean_roadmap.json");
            count = (roadmap.rows || []).length;
          } else if (name === "codes") {
            const codes = await assetJSON(env, request, "/data/codes.json");
            count = Object.keys(codes).length;
          } else {
            const insts = await assetJSON(env, request, "/data/instances.json");
            count = (Array.isArray(insts) ? insts : insts.instances || []).length;
          }
          return new Response(statBadgeSVG(label, count), {
            headers: {
              "content-type": "image/svg+xml; charset=utf-8",
              "cache-control": "public, max-age=300",
              "access-control-allow-origin": "*",
            },
          });
        } catch (e) {
          return new Response("stat unavailable", { status: 503 });
        }
      }
      const m = url.pathname.match(BADGE_PATH_RE);
      if (!m) {
        return new Response("a version badge is /badge/<8-64 hex>.svg", { status: 400 });
      }
      return new Response(badgeSVG(m[1]), {
        headers: {
          "content-type": "image/svg+xml; charset=utf-8",
          "cache-control": "public, max-age=31536000, immutable",
          "access-control-allow-origin": "*",
        },
      });
    }

    if (url.pathname.startsWith("/l/")) {
      const parsed = parseLPath(decodeURIComponent(url.pathname.slice(3)));
      if (!parsed) {
        return html("<!doctype html><p>Malformed id: a permalink is /l/&lt;sha256 or 8+ hex prefix&gt;, /l/&lt;scheme:ref&gt;, or /l/&lt;scheme:ref&gt;/&lt;hash&gt;.</p>", 400);
      }
      let instances;
      try {
        instances = await assetJSON(env, request, "/data/instances.json");
      } catch (e) {
        return html("<!doctype html><p>The instance projection is unavailable.</p>", 503);
      }
      if (parsed.ref && !parsed.hash) {
        const family = entriesBySource(instances, parsed.ref);
        return family.length
          ? html(sourceListingHTML(parsed.ref, family, url.origin), 200)
          : html(sourceEmptyHTML(parsed.ref, url.origin), 404);
      }
      const r = resolvePrefix(instances, parsed.hash);
      if (r.ok) {
        if (parsed.ref && entrySourceRef(r.entry) !== parsed.ref) {
          return html(sourceMismatchHTML(parsed.ref, r.entry, url.origin), 409);
        }
        return html(permalinkHTML(r.entry, url.origin), 200);
      }
      if (r.ambiguous) return html(ambiguousHTML(parsed.hash, r.ambiguous, url.origin), 300);
      return html(notFoundHTML(parsed.hash, url.origin), 404);
    }

    if (url.pathname === "/s" || url.pathname.startsWith("/s/")) {
      return handleShortlink(request, env, url);
    }

    if (url.pathname.startsWith("/m/")) return handleShare(request, env, url);
    if (url.pathname === "/oembed") return handleOembed(request, env, url);

    // Everything else is the static site, exactly as GitHub Pages serves it.
    return env.ASSETS.fetch(request);
  },
};

// The short-link store: the one write surface. POST /s mints (rate-limited,
// validated, public-by-construction); GET /s/<code> serves the crawlable
// shell; GET /s/<code>/raw serves the stored bytes with open CORS (a minted
// payload is public data; the code is the only handle). A set citing evidence
// outside the public registry mints only with ?publish_private=1 and is then
// stored with metadata private: true. A set that is private by its metadata or
// by the registry as read now is served no-store and noindex.
async function handleShortlink(request, env, url) {
  const origin = request.headers.get("origin");
  // /s/ too: the domain route for the exact /s misses once ?publish_private=1 is added
  const mint = url.pathname === "/s" || url.pathname === "/s/";

  if (request.method === "OPTIONS" && mint) {
    return isMintOrigin(origin)
      ? new Response(null, { status: 204, headers: corsHeaders(origin) })
      : new Response(null, { status: 403 });
  }

  if (request.method === "POST" && mint) {
    if (!isMintOrigin(origin)) {
      return Response.json({ error: "origin not allowed to mint" }, { status: 403 });
    }
    const ip = request.headers.get("cf-connecting-ip") || "unknown";
    const day = new Date().toISOString().slice(0, 10);
    const rlKey = `rl:${day}:${ip}`;
    const used = parseInt((await env.SHORTLINKS.get(rlKey)) || "0", 10);
    if (used >= MINTS_PER_DAY) {
      return Response.json({ error: "daily mint limit reached" },
        { status: 429, headers: corsHeaders(origin) });
    }
    const body = await request.text();
    const v = validateMintBody(body);
    if (!v.ok) {
      return Response.json({ error: v.error }, { status: 400, headers: corsHeaders(origin) });
    }
    // live registry first, the bundled copy as fallback; neither readable, or
    // one the predicate refuses (citation_keys not its bound table): mint nothing
    let refusal;
    try {
      refusal = mintRefusal(v.envelope, await assetJSON(env, request, "/data/registry.json"));
    } catch (e) {
      return Response.json({ error: "The public registry could not be read, so nothing was minted. Try again later." },
        { status: 503, headers: corsHeaders(origin) });
    }
    if (refusal && url.searchParams.get("publish_private") !== "1") {
      return Response.json(refusal, { status: 400, headers: corsHeaders(origin) });
    }
    let code = null;
    for (let attempt = 0; attempt < 5 && !code; attempt++) {
      const bytes = new Uint8Array(9);
      crypto.getRandomValues(bytes);
      const candidate = randomCode(bytes);
      if (!(await env.SHORTLINKS.get(`s:${candidate}`))) code = candidate;
    }
    if (!code) return Response.json({ error: "could not allocate a code" },
      { status: 503, headers: corsHeaders(origin) });
    await env.SHORTLINKS.put(`s:${code}`, body, { metadata: {
      created: new Date().toISOString(), members: v.envelope.lineages.length, private: !!refusal } });
    await env.SHORTLINKS.put(rlKey, String(used + 1), { expirationTtl: 172800 });
    return Response.json({ code, url: `${url.origin}/s/${code}` },
      { status: 201, headers: corsHeaders(origin) });
  }

  if (request.method === "GET") {
    const raw = url.pathname.endsWith("/raw");
    const seg = url.pathname.slice(3).replace(/\/raw$/, "").replace(/\/$/, "");
    const code = parseCode(seg);
    if (!code) return html("<!doctype html><p>Malformed short code.</p>", 400);
    const { value: stored, metadata } = await env.SHORTLINKS.getWithMetadata(`s:${code}`);
    if (stored == null) {
      return raw
        ? Response.json({ error: "not found" },
            { status: 404, headers: { "access-control-allow-origin": "*" } })
        : html(shortlinkNotFoundHTML(code, url.origin), 404);
    }
    // private by the metadata, or by the registry as read now (sets stored
    // before this rule carry no flag); a registry or value that cannot be read
    // counts as private
    const v = validateMintBody(stored);
    let labels = null;
    if (v.ok) {
      try { labels = memberLabels(v.envelope, await assetJSON(env, request, "/data/registry.json")); } catch (e) {}
    }
    const isPrivate = metadata?.private === true || !labels || labels.length > 0;
    if (raw) {
      return new Response(stored, {
        headers: {
          "content-type": "application/json",
          "access-control-allow-origin": "*",
          "cache-control": isPrivate ? "no-store" : "public, max-age=31536000, immutable",
          ...(isPrivate ? NOINDEX : {}),
        },
      });
    }
    if (!labels) {
      labels = metadata?.private === true ? ["Some lineages cite evidence that is not in the public registry; their values cannot be checked against the commons."] : [];
    }
    return html(shortlinkHTML(v.envelope || { lineages: [] }, code, url.origin, { labels, noindex: isPrivate }), 200,
      isPrivate ? NOINDEX : {});
  }

  return new Response("method not allowed", { status: 405 });
}

// A share link: the snapshot (immutable, named by its hash) and the selection decoded against it.
// {ok: true, hash, snap, ids} or {ok: false, response}
async function loadShare(request, env, prefix, selection) {
  let index, snap;
  try {
    index = await assetJSON(env, request, "/data/v/index.json");
  } catch (e) {
    return { ok: false, response: html(errorHTML("The list of map snapshots is unavailable."), 503) };
  }
  const found = resolveSnapshot(index, prefix);
  if (!found.ok) {
    return { ok: false, response: html(errorHTML(found.reason === "ambiguous"
      ? `The prefix ${prefix} matches more than one snapshot. The link needs a longer prefix.` : `No map snapshot is named ${prefix}.`), 404) };
  }
  try {
    snap = await asset(env, request, `/data/v/${found.hash}.json`, (r) => r.json(), 86400);  // named by its hash: never changes
  } catch (e) {
    return { ok: false, response: html(errorHTML(`Snapshot ${found.hash.slice(0, PREFIX)} is unavailable.`), 503) };
  }
  const d = decode(snap, selection);
  if (!d.ok) return { ok: false, response: html(errorHTML(`The selection does not fit snapshot ${found.hash.slice(0, PREFIX)}: ${d.reason}.`), 400) };
  // a code made private after the snapshot was frozen drops out; an unreadable registry shows no codes
  let registry = null;
  try { registry = await assetJSON(env, request, "/data/registry.json"); } catch (e) { /* fail closed */ }
  return { ok: true, hash: found.hash, snap: withPublicCodes(snap, registry), ids: d.ids };
}

async function handleShare(request, env, url) {
  const ref = parseMPath(url.pathname);
  if (!ref) return html(errorHTML("A share link is /m/<snapshot>/<selection>, with 8 to 64 hex characters of the snapshot and the selection in lowercase hex."), 400);
  const s = await loadShare(request, env, ref.prefix, ref.selection);
  if (!s.ok) return s.response;
  if (ref.png) return sharePNG(request, env, s);
  let template;
  try {
    template = await assetText(env, request, "/share/index.html");
  } catch (e) {
    return html(errorHTML("The share page is unavailable."), 503);
  }
  return html(shellHTML(template, shareMeta(s.snap, s.hash, s.ids)), 200, { "cache-control": "public, max-age=3600" });
}

async function handleOembed(request, env, url) {
  const cors = { "access-control-allow-origin": "*" };
  if ((url.searchParams.get("format") || "json") !== "json") return new Response("only format=json", { status: 501, headers: cors });
  let target;
  try { target = new URL(url.searchParams.get("url") || ""); } catch (e) { target = null; }
  const ref = target && (target.host === url.host || target.hostname === "openmaterials.ai") ? parseMPath(target.pathname) : null;
  if (!ref || ref.png) return Response.json({ error: "not a share link of this site" }, { status: 404, headers: cors });
  const s = await loadShare(request, env, ref.prefix, ref.selection);
  if (!s.ok) return Response.json({ error: "share link not found" }, { status: 404, headers: cors });
  return Response.json(oembedJSON(shareMeta(s.snap, s.hash, s.ids), url.searchParams.get("maxwidth"), url.searchParams.get("maxheight")),
    { headers: { ...cors, "cache-control": "public, max-age=3600" } });
}

// The card is a pure function of snapshot, selection and renderer (CARD_VERSION), so it lives in the
// edge cache under that key: an eviction costs one render, and nothing accumulates in storage. New renders
// are rate-limited per IP (CARD_LIMITER); past the limit, or if a render fails, the site card stands in.
async function sharePNG(request, env, s) {
  const key = new Request(`https://cards.openmaterials.ai/v${CARD_VERSION}/${s.hash}/${encode(s.snap, s.ids)}.png`);
  const cache = globalThis.caches ? caches.default : null;
  const headers = { "content-type": "image/png", "cache-control": "public, max-age=86400", "access-control-allow-origin": "*" };
  const hit = cache && await cache.match(key);
  if (hit) return new Response(hit.body, { headers });
  const fallback = () => Response.redirect(new URL("/assets/og.png", request.url).href, 302);
  if (env.CARD_LIMITER) {
    const { success } = await env.CARD_LIMITER.limit({ key: request.headers.get("cf-connecting-ip") || "unknown" });
    if (!success) return fallback();
  }
  let png;
  try {
    const [{ cardSVG }, { renderPNG }, { PNG_ASSETS }] = await Promise.all([import("./card.js"), import("./png.js"), import("./pngassets.js")]);
    png = await renderPNG(cardSVG(s.snap, s.hash, s.ids), PNG_ASSETS);
  } catch (e) {
    console.warn(`card ${s.hash.slice(0, PREFIX)}: ${e}`);
    return fallback();
  }
  if (cache) await cache.put(key, new Response(png, { headers: { "content-type": "image/png", "cache-control": "public, max-age=31536000" } }));
  return new Response(png, { headers });
}
