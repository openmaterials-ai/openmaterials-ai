# Changelog

Changes to the `openmaterials-ai` package, its record format and the ids it
mints, for consumers. Versioning follows README.md ("Versioning"): before 1.0
an identity change takes the minor version, and this file lists every re-keyed
id.

## Unreleased

- `meskal`: the release's `license_source` and the code's credits say the
  source repository is not public, and the credits `url` is null; they cited
  a repository and a page that are not public. The licence read at v1.1.0
  (BSD-3-Clause) is unchanged. No id changes.
- The `mescal` representation is removed (`docs/data/codes.json` and
  `registry.json` lose the key; `index/codes/mescal.json` is deleted): MESCAL
  is MESKAL's former name and `meskal` maps the same two nodes. `mescal` is an
  alias of `meskal`, so `release_check` resolves an `execution.registry` row
  naming it against MESKAL's releases (a null-version row with a digest is now
  reported), and `private_reasons` gives
  `{field: "execution.registry", kind: "code"}` (public before). The three
  MESCAL values keep their ids. Removed API:
  `omai.thermal_transport.representation.mescal` and the `MESCAL_*` names;
  this takes the minor version.
- `omai.cure_kinetics.evaluate`: `cure_conversion` evaluates
  kamal_cure_conversion as its own integral (Gauss-Legendre in
  s = ln(alpha / (1 - alpha)) and a Newton root, no time step; other rate laws
  refused) and `glass_transition_temperature` evaluates
  dibenedetto_glass_transition. They are registered as the representation
  `openmaterials-ai` on CureConversion and GlassTransitionTemperature (33
  representations). `omai.render.canonical_params` returns the bytes whose
  sha256 a record's `kinetics_params_sha256` and `tg_params_sha256` carry,
  and drops keys whose value is None. A record whose `execution.registry` row
  names `openmaterials-ai` now resolves to a representation: `private_reasons`
  gives `[]` for it (a code reason before) and `release_check` reports
  "version not registered" (before: "not a representation") until a release
  entry lists that version. The map, its operators and every id are
  unchanged; a new public name and a representation take the minor version.
- `omai.composites.evaluate`: `nan_kappa_random` and `nan_kappa_aligned`
  (the aligned node's declared value, al33) evaluate the Nan edges at a
  composite record's conditions (`NAN_KEYS`), with the interface as a
  per-direction series film (the 2004 form). The Kapitza radius is km / G,
  derived; a `kapitza_radius_nm` that disagrees with it is refused.
  `aligned_tensor_components` also returns al11, which is not a node value.
  The representation `openmaterials-ai` now also covers the two Nan nodes
  (still 33 representations). The map, its operators and every id are
  unchanged.

## 0.3.1

Every consumer pins `openmaterials-ai==0.3.1`.

- `meskal` is a private code: its release file carries `"visibility":
  "private"`, since its source has no public repository, and `registry.json`
  (shipped as `omai/data/registry.json`), `docs/data/codes.json` and
  `index/codes/meskal.json` carry the same key. A record whose
  `execution.registry` names it gives
  `{field: "execution.registry", kind: "code"}`: a MESKAL record with no
  other private evidence, public under 0.3.0, is now private. The site reads
  the live registry; a consumer with a bundled 0.3.0 registry disagrees with
  it until it takes 0.3.1. No id changes.
- `render_interface_conductance` documents `lead_length_nm` as side A's length
  (the first material of `interface_name`); values and ids are unchanged.

## 0.3.0

Every consumer pins `openmaterials-ai==0.3.0`. A consumer that runs the
private-evidence predicate (`omai.evidence.private_reasons`, or the
`private-members.js` it vendors) gives it a registry with the `code` and
`model_labels` tables: the `registry.json` this release ships and publishes
has both, a 0.2.0 copy has neither, so a bundled registry is updated with the
predicate. A record made against a private overlay carries `lineage_version`
and `overlay_version`: `record_light` and `record_simulation` fill them from
the overlay in `roots`, and the validators refuse such a record without them.

0.2.0 deferred overlays, retraction and the composite and cure renderers to
0.2.1. A new renderer or schema field takes the minor version (README.md,
"Versioning"), so they ship as 0.3.0.

### Breaking

- `omai.evidence.private_reasons` raises ValueError, and `private-members.js`
  throws, on a registry without the `code` and `model_labels` tables.
- Both predicates check the code that ran: an `execution.registry` row whose
  `id` is no representation or alias in the registry's `code` table, or whose
  code row has a `visibility` other than `"public"`, gives
  `{field: "execution.registry", kind: "code"}`, and a non-list
  `execution.registry` gives one. A record 0.2.0 reported as public can now
  report private. The release is never checked, and a row whose `version` is
  a key of `model_labels` names a model and gives no code reason.
- The packaged external-solve request `omai/tools/kaldo-direct-bte-si.json`
  pins the new graph version, so its `request_id` moves from `f54665faafd9`
  to `9c65fd692c45`. A request minted against graph `5a967e980890` fails as a
  stale map version.
- `lineage_version` (`version` in docs/data/version.json) moves from
  `9d1d27635859` to `61a981c02604`, and the graph version from
  `5a967e980890` to `baf99346621b`; `format_rules_version` stays
  `227566bf55a0`.

### Re-keyed ids

None. Every id in `omai/vectors/*.json` (lineage, record, render, model,
configuration, release and private-evidence cases), every committed instance
id and every configuration and model uid is unchanged from 0.2.0. The map log
gains records 274-289 (six `add_node` and `add_edge`, ten `edit_meta`) and
supersedes nothing, so no node or edge uid moves. Only the packaged request's
`request_id` moves, with the graph version (see Breaking).

### Added

- Private overlays (`omai.overlays`): a directory laid out like `docs/data/`
  plus `overlay.json` (`{namespace, base_graph_version}`), `map.json` (an
  add-only contribution of `add_node` and `add_edge`) and `registry.json` (the
  vocabulary it adds). `omai.overlays.load(roots)` checks each overlay listed
  in `roots` after the public root and raises `OverlayError` on public uids,
  public node names held for another uid, vocabulary collisions, a reused
  namespace, unnamespaced names, uncredited codes, covered nodes the map does
  not hold, symlinks, and one (code, version) naming two commits.
  `overlay_version(root)` is the sha256 over the base and every non-hidden
  file but `overlay.json`, computed, never stored. The lineage validators and
  writers, `release_check` (new `roots` parameter) and `unregistered_for`
  load the overlays in their `roots`; `ns:Name` nodes resolve, and a record is
  made against one overlay at most. Overlay code releases live at
  `releases/<ns>/<code>.json`. A published node keeps its overlay name in
  `Space.names` and in an optional `names` list on its graph.json node.
  GOVERNANCE.md states the overlay rules. Vector: `overlay.json`, a synthetic
  overlay's files and its `overlay_version`.
- `omai.gates.VOCABULARY` and a `vocabulary` parameter on
  `validate_contribution` (default the public tables).
- Retraction: a model or configuration record may carry
  `retracted: {date, reason}` (a real `YYYY-MM-DD` date, a non-blank reason).
  A retracted uid still resolves, so no record citing it breaks, and it is
  never served as current. `registry.json` lists retracted uids and aliases
  under `retracted` (`{kind: {uid: {date, reason}}}`, present only when a
  record is retracted; none is). `validate_light` reports citations of
  retracted uids under `retracted_citations` (`[{field, uid, reason}]`) and
  never refuses them. `record_configuration` refuses new provenance for a
  retracted cell, and the duplicate matcher skips it. `configurations.json`
  carries the field.
- Renderers in `omai.render`: `render_composite_kappa`,
  `render_interface_conductance` (keyword `potential` required),
  `render_cure_conversion` and `render_glass_transition`. Each requires every
  input its conditions hold and raises KeyError when one is missing or the
  method has no map node (aemd and neg_gk for the interface; any rate law but
  Kamal-Sourour for `CureConversion`); the cure renderers raise ValueError for
  a conversion outside [0, 1]. Each coerces its own number types, so an id
  never depends on how a producer typed 1200 or 1200.0, drops a zero spread,
  writes 4 significant figures in the detail, and cites rate-law and
  DiBenedetto parameters by sha256, never by value. `render.json` gains five
  vectors (15).
- Map: `InterfaceConductance[transport_model=nemd]` (Molecular dynamics tier,
  W/(m^2 K)) with its two-reservoir NEMD edge and a gpumd representation row;
  the Cure kinetics tier with `CureConversion` and
  `GlassTransitionTemperature`, produced by the Kamal-Sourour edge and the
  DiBenedetto edge in the Pascault-Williams form.
- Code visibility: a release file may carry
  `"visibility": "public" | "private"` (absent: public); `check_releases`
  refuses any other value. Every committed release file is public.
- `registry.json` gains `model_labels`, `{release_label: uid}` from the model
  records (`nep89_20250409`); the `model` table is unchanged.
- The wheel ships `omai/data/private-members.js`,
  `docs/assets/private-members.js` byte for byte, read with
  `importlib.resources.files("omai")`.
- `omai/vectors/private.json`: ten code cases (42 in all) and two refused
  registries (`code_missing`, `model_labels_missing`); its fixture registry
  gains `code` and `model_labels`.

### Changed

- The map: 129 nodes, 127 operators, 18 tiers, store head `baf99346621b`
  (289 records). Ten node and edge descriptions move to plain terms as
  `edit_meta` records.
- Wording: plain terms in docstrings, comments, test names and the document;
  no behavior changes.
- `omai.evidence.code_releases(roots)` appends each root's aliases and
  releases in root order (0.2.0 kept the first root holding a
  representation), so an overlay may add a release of a public code. Hidden
  files (a path component starting with ".") are not records or releases.
- README.md: number types in lineage identity (1200 and 1200.0 are
  different lineages). docs/openmaterials.tex describes what ships and states
  this map version.

## 0.2.0

Every consumer that validates records pins `openmaterials-ai==0.2.0` before
any producer emits the new record fields: a 0.1.3 `validate_light` accepts a
0.2.0 record carrying `unregistered` and ignores it (only the 0.1.3 schema
refuses it).

### Breaking

- The closed record schema gains three top-level fields, all outside identity:
  `unregistered` (`[{kind, uid}]`, `kind` `configuration` or `model`, `uid`
  the bare uid), `lineage_version` and `overlay_version` (64 lowercase hex).
  They join `FORMAT_DESCRIPTOR.record_fields`. A 0.1.3 validator
  (`omai.schema.validate_record`) refuses a record carrying any of them. A
  record carrying them has the id of the same lineage without them.
- A cited uid that no registry holds must be listed in `unregistered`;
  `validate_light`, `record_light` and `record_simulation` refuse an unlisted
  one. The citations checked are the configuration pin
  (`material.configuration`, compared without a `sha256:` prefix) and the
  model citation keys `conditions.potential_sha256`,
  `conditions.base_potential_sha256` and `conditions.calibration_sha256`
  (bound under `SetVoltage`, checked wherever it appears). The calibration key
  is fixed by ruling: that calibration is never registered, so a record citing
  it always lists it. A listed uid that later resolves is checked as registered,
  never an error. 0.1.3 refused a configuration pin with no committed record
  and did not check model citations.
- A model citation is the bare uid, 64 lowercase hex, no `sha256:` prefix;
  any other value (a prefix, uppercase, null, "unknown") is refused by the
  lineage validators and by the schema, which now declares the three citation
  keys in `lineage.conditions` (the map stays open otherwise).
- Every 64-hex field refuses a trailing newline: the Python validators use a
  full match, and each 64-hex pattern in the schema ends `(?!\n)$`, since
  Python's `$` matches before a final newline. 0.1.3's Python validators and
  schema accepted `<hex>\n`, which an ECMAScript schema validator refuses.
- `omai.render.render_kappa` raises TypeError when kappa is None (0.1.x
  printed "None"), and its detail text no longer reproduces the bytes 0.1.x
  served (see Changed).
- The packaged external-solve request `omai/tools/kaldo-direct-bte-si.json`
  pins the new graph version, so its `request_id` moves from `1b97039653fe`
  to `f54665faafd9`. A request minted against graph `9802d9e854c9` fails as a
  stale map version.
- `omai/vectors/records.json` goes from 34 to 35 vectors. The new
  `omai:safe_light_with_unregistered_and_versions` carries the three new
  fields and has the id of `mcg:safe_light`; a 0.1.3 schema refuses it.
- `format_rules_version` moves from `1c56768ac39a` to `227566bf55a0`, and
  `lineage_version` (`version` in docs/data/version.json) from `f69b18c18fb7`
  to `9d1d27635859`; the graph version moves from `9802d9e854c9` to
  `5a967e980890`.

### Re-keyed ids

No lineage id and no vector id changes. These map and record ids changed since
0.1.3:

| id | 0.1.3 | 0.2.0 | former id |
|---|---|---|---|
| configuration Si, diamond primitive cell (mp-149) | `55bf22ca8186` | `7b5e77b1062f` | kept under `canonical.aliases` |
| node `PhononDOS` | `9b0af04f9828` | `e14b6cdd007c` | kept as a node alias |
| node `PhaseSpace3Phonon` | `41a47eada8fe` | `ec483cecbdbf` | kept as a node alias |
| edge `compute_dos` | `5030641f5cd4` | `c42288d9daf6` | no alias |
| edge `fourier_to_dos` | `325b66602b58` | `d6b71066f0ce` | no alias |
| edge `compute_phase_space_3phonon` | `d045e62468c7` | `cff24024635e` | no alias |

- The configuration moved because `canonical_uid` now writes signed zero as
  `0.0`. A lattice residue near 1e-16 had a machine-dependent sign, so the
  committed cell hashed to `55bf22ca` where it was minted and to `7b5e77b1`
  on Linux x86-64. `omai.evidence.resolve`, the lineage validators and
  `omai.configurations.load` accept the former uid, so lineages pinning it
  keep their ids. A configuration uid minted elsewhere moves the same way
  when its canonical JSON held a `-0.0`; Si is the only configuration the
  commons holds.
- `PhononDOS` (from frequency) and `PhaseSpace3Phonon` (from dimensionless)
  now have dimension 1/frequency, the dimension of their delta sums;
  dimension is part of node identity. A `lineage.node_uid` pin of the former
  uid still validates. The three edges hash their endpoint uids, so they
  re-minted with their output nodes; their formulas are unchanged. The map log
  records each change as a `supersede`.

### Added

- The evidence registry: `omai/data/registry.json` in the wheel, published as
  `docs/data/registry.json`, with the tables `citation_keys`, `configuration`
  and `model` (each uid and alias mapped to its record) and `code` (every
  representation's aliases and releases). `omai.evidence.resolve(kind, uid,
  roots=None)` reads it.
- Model records (kind `model`, docs/data/models/), uid by
  `omai.evidence.model_uid`: the sha256 of the one evaluated file, or of the
  sorted digest manifest of several. Registered: NEP89 (`nep89_20250409`,
  `75168ece02e8`) and Si.tersoff (`52a93e905968`), each with licence
  `NOASSERTION` and the source searched. `omai.evidence.model_citations`
  reports what a lineage cites.
- Authored code releases (docs/data/releases/<representation>.json,
  `{aliases, releases}`): gpumd 3.9.5, kaldo 2.2.1, lammps 2025.7.22.4.0 and
  2025.7.22.5.0, meskal 1.1.0, phono3py 4.4.0, qe qe-7.5 (alias
  `quantum-espresso`), qe-d3q q-e-7.5. `omai.evidence.code_releases` reads
  them. The release check, `omai.lineages.release_check(execution,
  codes=None)`, reports the `execution.registry` rows that resolve to no
  registered release; `validate_light` returns them as
  `unresolved_registry_rows`. Nothing refuses them.
- `omai.evidence.private_reasons(record, registry=None)`: why a record cites
  evidence that is not public, `[{field, kind}]`. `docs/assets/private-members.js`
  is the same predicate for the site; `omai/vectors/private.json` holds the
  cases both agree on.
- `omai.lineages.unregistered_for(lineage, roots=None)`: the `unregistered`
  list a producer declares.
- `roots` on `validate_light`, `record_light` and `record_simulation`: where
  cited uids resolve, by default `docs/data/` in a source tree and the
  registry the wheel ships in an installed package. The two writers also take
  `unregistered`, `lineage_version` and `overlay_version`.
- Installed wheel: configuration pins resolve through the registry the wheel
  ships. 0.1.3 looked for docs/data/configurations/, which an installed
  package lacks, and refused every configuration pin, the committed Si uid
  included. CI builds the wheel, installs it outside the checkout and runs
  tests/installed_wheel.py.
- Vectors: `configurations.json` (the Si structure, its canonical JSON and
  uid; Python only, since it needs spglib), `models.json` (one-file,
  two-file and `training_state` fixtures), `releases.json` (release-check
  cases), `private.json` (private-evidence cases).
- The analog device metrology domain (`omai.analog_device_metrology`), with
  the nodes `ConductanceState`, `ConductanceWindow`,
  `ConductanceDriftExponent`, `StateCoefficientOfVariation`,
  `DotProductError`, `SchottkyBarrierHeight[band_carrier=electron]`,
  `WorkFunction`, `ElectronAffinity`, `ProgrammingPulseEnergy`, `SetVoltage`
  and `RetentionTime`, and ten edges. `MigrationBarrier` joins the materials
  domain.
- Representations: meskal (MESKAL 1.1.0, eighteen thermal-transport nodes),
  qe-d3q (D3Q and thermal2), and an ev.x `BulkModulus` row on qe.
- `canonical_uid` canonicalizes a partially occupied cell, naming such a site
  by its species and occupancies to 5 decimals (0.1.3 raised on it).

### Changed

- `omai.render`: the source detail names the "graph version" (`graph_version`
  in version.json, still passed as `map_version`); kappa and its error are
  written to 4 significant figures in plain decimal, ties rounded half up; a
  run without a spread writes no "+/-" term where 0.1.x printed "+/- None".
  Only the detail text changes: `value`, `uncertainty` and every id stay.
  `render.json` follows the new text and gains two vectors (10).
- `config_dir` on the validators and writers is deprecated, without a
  warning; pass `roots`. It now adds a directory of configuration records to
  the roots, where 0.1.3 replaced the lookup directory with it.
- `omai.badge.map_stats()["operators"]` counts the rows of
  docs/data/lean_roadmap.json, the home page count, instead of the distinct
  edge operators in graph.json.
- Package metadata: `License-Expression: Apache-2.0 AND CC-BY-4.0`. The code
  and the conformance vectors (omai/vectors/) are Apache-2.0; the registry the
  wheel ships under omai/data/ is map data, CC BY 4.0 (LICENSE-DATA, NOTICE).

### Deferred to 0.2.1

- Private overlays and their GOVERNANCE.md text. 0.2.0 validates
  `overlay_version` but nothing computes it yet.
- Retraction of model and configuration records.
- The composite and cure renderers.
