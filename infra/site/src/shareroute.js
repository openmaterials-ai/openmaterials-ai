// Pure logic for the /m/<snapshot>/<selection> share links and /oembed: DOM-free and fetch-free so
// node:test runs it against the committed snapshots. The Worker (index.js) supplies the data. The
// page itself is docs/share/index.html; this module only writes the meta tags crawlers read
// (X, LinkedIn and Slack do not run JavaScript) and the oEmbed answer.

import { PREFIX, SITE, codesOf, encode, describe, parseShare, title } from "../../../docs/assets/share.js";

// Bump when the card drawing changes, so cached cards of the old drawing are not served.
export const CARD_VERSION = 1;

const PATH_RE = /^\/m\/([^/]+)\/([^/]+?)(\.png)?$/;

// {prefix, selection, png} for /m/<prefix>/<hex>[.png], else null (the prefix is checked by parseShare)
export function parseMPath(pathname) {
  const m = PATH_RE.exec(pathname || "");
  if (!m) return null;
  const ref = parseShare(`/m/${m[1]}/${m[2]}`);
  return ref ? { prefix: ref.snapshot, selection: ref.selection, png: !!m[3] } : null;
}

// Canonical, og:url, the card and the embed always name openmaterials.ai, also when the staging copy serves the page.
export function shareMeta(snap, hash, ids) {
  const hex = encode(snap, ids);
  const url = `${SITE}/m/${hash.slice(0, PREFIX)}/${hex}`;
  return {
    title: `${title(snap, ids)} | OpenMaterials`,
    name: title(snap, ids),
    description: describe(snap, ids),
    url,
    image: `${url}.png`,
    embed: `${url}?embed=1`,
    index: codesOf(snap, ids).length > 0,  // only a code's own selection is worth a search result
  };
}

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export function shellHTML(template, meta) {
  const tags = [
    `<meta name="description" content="${esc(meta.description)}">`,
    `<link rel="canonical" href="${esc(meta.url)}">`,
    `<meta property="og:type" content="website">`,
    `<meta property="og:site_name" content="openmaterials.ai">`,
    `<meta property="og:title" content="${esc(meta.title)}">`,
    `<meta property="og:description" content="${esc(meta.description)}">`,
    `<meta property="og:url" content="${esc(meta.url)}">`,
    `<meta property="og:image" content="${esc(meta.image)}">`,
    `<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">`,
    `<meta property="og:image:alt" content="Submap of ${esc(meta.name)} on the OpenMaterials map, with the selected quantities in their tiers.">`,
    `<meta name="twitter:card" content="summary_large_image">`,
    ...(meta.index ? [] : [`<meta name="robots" content="noindex">`]),
    `<link rel="alternate" type="application/json+oembed" href="${esc(`${SITE}/oembed?url=${encodeURIComponent(meta.url)}&format=json`)}" title="${esc(meta.title)}">`,
  ].join("\n");
  return template.replace(/<title>[^<]*<\/title>/, () => `<title>${esc(meta.title)}</title>`).replace("<!--share-meta-->", () => tags);
}

export function oembedJSON(meta, maxwidth, maxheight) {
  const width = Math.min(Number(maxwidth) > 0 ? Number(maxwidth) : 760, 760);
  const height = Math.min(Number(maxheight) > 0 ? Number(maxheight) : 480, 480);
  return {
    version: "1.0",
    type: "rich",
    title: meta.title,
    provider_name: "OpenMaterials",
    provider_url: SITE,
    width,
    height,
    html: `<iframe src="${esc(meta.embed)}" title="${esc(meta.name)} on the OpenMaterials map" width="${width}" height="${height}" loading="lazy" style="border:1px solid #DDD7CB;border-radius:2px"></iframe>`,
    thumbnail_url: meta.image,
    thumbnail_width: 1200,
    thumbnail_height: 630,
  };
}

export const errorHTML = (message) =>
  `<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Share link | OpenMaterials</title>` +
  `<p>${esc(message)} <a href="/map/">Open the map</a> to make a new link.</p>`;
