# Path owners

Which seats must agree before a change to each path merges. This table is the rule of part 3 of the working agreement between seats. The `owner-agreement` check reads it from `main`, so a pull request is checked against the table it started from.

A pull request that changes a path needs one line from every seat that owns it, in the pull request body or a comment:

    <Seat> agreed at <head commit>

The author's own seat posts its line too, after its fresh reviewer has passed the change. Only lines written by an owner, member or collaborator of the repository count. A line holds while the diff of that seat's paths against `main` is unchanged. A later push that leaves those paths alone keeps the line, and one that touches them needs a new line. Every row that matches a path applies, so where rows overlap, every listed seat agrees. A path that no row names belongs to the default owner. A change to this file needs the chief of staff and every seat named in a row it adds or removes.

In a pattern, `dir/` is everything under `dir`, `*` matches inside one path segment, `**` across segments, and any other pattern is one file. Owners are seat names, not GitHub accounts, because every seat acts as the same GitHub user.

The check matches paths, not content. A migration that writes `token_ledger`, `token_expirations` or a `stripe_` table also needs Revenue and legal: its author asks for the line.

The check posts the commit status `owner-agreement` on every pull request. The deploy step of `deploy-site.yml` runs it on every main commit it ships and refuses a commit whose pull request lacks a line. A line posted on the merged pull request afterwards still counts, so the deploy can then be run again.

A pure revert needs no line (part 5 of the working agreement): a change whose diff is exactly the inverse of one of the last 100 commits on `main`. The seat that reverts tells the owners. A partial revert, a revert with any other change in it, and the revert of a revert (which lands the first change again) need their lines.

Local merge gate, from a clone with `gh` signed in: `python3 .github/scripts/owner_agreement.py --pr <number>`. It exits 3 and names the missing seats, or 2 when the table cannot be read.

## Seats

Chief of staff, Platform, Engines, Map, Revenue and legal, Product and marketing, IT and security.

## Table

| Paths | Seats | What |
| --- | --- | --- |
| `OWNERS.md` | Chief of staff | This table, plus every seat named in a changed row |
| `.github/` | Map, IT and security | CI, the site deploy and the owner check. Any workflow can read every repository secret |
| `.github/scripts/owner_agreement.py`, `.github/scripts/test_owner_agreement.py`, `.github/workflows/owner-agreement.yml` | Platform, IT and security | The owner check |
| `infra/` | Map, IT and security | The site Worker and the learn proxy, deployed with the Cloudflare token |
| `README.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `PRODUCT.md`, `examples/README.md` | Map, Product and marketing | Public copy |
| `LICENSE`, `LICENSE-DATA`, `NOTICE`, `THIRD_PARTY_NOTICES`, `CITATION.cff` | Map, Revenue and legal | Licences, notices and citation |
| `SECURITY.md` | Map, IT and security | Security policy |
| `docs/index.html`, `docs/assets/site.css`, `omai/code_pages.py`, `omai/code_cards.py` | Map, Product and marketing | The site's hand-written copy and design, and the page generators whose templates carry visible wording |
| `infra/learn-proxy/wrangler.jsonc` | Map, IT and security, Revenue and legal | The learn proxy's daily spend cap |
| (any other path) | Map | Default owner |
