# The site Worker

The edge deployment of openmaterials.ai. Wrangler serves the repository's
`docs/` directory as static assets, byte-identical to the GitHub Pages
deployment, and the Worker script runs only for the routes a fragment-only
static site cannot express:

- `GET /healthz`: liveness plus the published map/lineage version, read from
  the same `data/version.json` every browser reads.
- `GET /l/<12 hex>`: the short link for a committed value. It resolves an
  id prefix (8 to 64 hex characters of the lineage id, the sha256 of the
  value's canonical lineage), so it needs the Worker. `/i/<id>/` is the
  canonical static page for the same value, built into `docs/` and served
  without the Worker. The Worker resolves the prefix against
  `data/instances.json` and serves a shell whose title, Open Graph metadata,
  and paragraph name the property, material, value, kind, and source exactly
  as `/i/<id>/` does, with its canonical link set to `/i/<id>/`, then
  redirects to the playground datasheet (`/play/#id=<id>`), the one
  renderer. A well-formed prefix that matches no committed value gets a 404
  naming it; a malformed one gets a 400 before any data is read.

- `POST /s` and `GET /s/<code>[/raw]`: the short-link store, the Worker's one
  write surface. Minting stores a lineage envelope (or a bare record, read as
  a one-element envelope) in the `SHORTLINKS` KV namespace, byte for byte as
  sent, and returns `<origin>/s/<code>`; the code is 9 unambiguous base58
  characters.
  Minting is origin-gated (the site plus localhost) and rate-limited per IP
  per day; payloads are capped at 64 KB and 64 lineages, and a stored payload
  is PUBLIC by construction (anyone with the code can read it). `GET
  /s/<code>` serves a crawlable shell built only from the stored envelope and
  redirects into `/play/#s=<code>`, where the playground fetches
  `/s/<code>/raw` (open CORS, immutable) and renders through the same
  dual-read path as a `#x=` link. Unknown codes 404 naming the code;
  malformed codes 400 before any read.

  A set with a member citing evidence outside the public registry (the
  predicate `docs/assets/private-members.js`, over `data/registry.json` read
  like the other data files) is refused with a 400 naming each member as
  "Lineage n of m" and its fields, unless the request carries the query
  parameter `publish_private=1` (a flag in the body or in `doc` is ignored).
  An accepted one is stored with KV metadata `private: true`. A set private by
  that flag or by the registry as read now (sets stored before the rule carry
  no flag), or whose registry cannot be read, has its `/raw` served
  `no-store` and its shell `noindex` (meta and `X-Robots-Tag`), with each such
  member's label in the description. When no registry is readable (live or
  bundled), nothing is minted and the answer is 503; the playground does not
  retry on the other origin after any JSON answer from a Worker.

Everything else falls through to the assets, so removing the Worker returns
the site to plain static hosting. The Worker holds no secrets and, outside
the explicitly public short-link store, no data of its own: the permalink
resolver reads the committed projection the site serves, from the Pages origin
with the bundled copy as the fallback.

On openmaterials.ai the Worker reads its data files (`data/version.json`,
`data/instances.json`, `data/lean_roadmap.json` and the rest) from the Pages
origin, so a data merge reaches it once Pages publishes, without a redeploy.
The bundled assets are the fallback, and the data on workers.dev and in
`wrangler dev`. A change to a data file's shape still needs a Worker deploy.

## Develop

```
cd infra/site
npx wrangler dev --port 8971 --local-upstream localhost
```

## Deploy

```
cd infra/site
npx wrangler deploy
```

Deploys to the `openmaterials-site` Worker on workers.dev. A change to the
private-evidence rule: merging publishes `docs/data/registry.json` and the
playground on Pages; deploy the Worker from the merge commit right after,
then run the probe on both origins. Until the Worker matches the live
registry, the domain Worker answers 503 and the playground stops there:

```
infra/site/probe.sh                       # openmaterials.ai
infra/site/probe.sh https://openmaterials-site.giuseppe-barbalinardo.workers.dev
```

The probe posts a set whose lineage 1 cites an unregistered model and exits
non-zero unless the answer is a 400 naming lineage 1. A refusing Worker
stores nothing; if an old Worker stores the probe, the failure names its key
and the revoke command.

Revoke a stored set (for example one published by mistake): delete its key
from `infra/site`, `npx wrangler kv key delete --binding SHORTLINKS --remote "s:<code>"`. The
`/raw` of a private set is `no-store`, so no cache holds it afterwards; a
public set's `/raw` is immutable and may persist in caches. Attaching the
production domain (openmaterials.ai) is a DNS decision made by the project
owner, not by this deploy; until then GitHub Pages remains the origin the
domain points at, and the two deployments serve identical bytes.

The Python suite pins the contract in `tests/test_site_worker.py` (the assets
directory, the exact `run_worker_first` list, the static fallthrough, the
no-credentials rule) and runs the resolver's node tests against the real
committed projection.
