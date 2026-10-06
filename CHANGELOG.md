# Changelog

Changes to the `openmaterials-ai` package, its record format and the ids it
mints, for consumers. Versioning follows README.md ("Versioning"): before 1.0
an identity change takes the minor version, and this file lists every re-keyed
id.

## 0.2.0

Every consumer that validates records pins `openmaterials-ai==0.2.0` before
any producer emits the new record fields.

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
  `conditions.base_potential_sha256` and, for `SetVoltage`,
  `conditions.calibration_sha256`. The `SetVoltage` calibration key is fixed
  by ruling: that calibration is never registered, so a record citing it
  always lists it. A listed uid that later resolves is checked as registered,
  never an error. 0.1.3 refused a configuration pin with no committed record
  and did not check model citations.
- A model citation is the bare uid, 64 lowercase hex, no `sha256:` prefix;
  any other value is refused.
- `omai/vectors/records.json` goes from 34 to 35 vectors. The new
  `omai:safe_light_with_unregistered_and_versions` carries the three new
  fields and has the id of `mcg:safe_light`; a 0.1.3 schema refuses it.
- `format_rules_version` moves from `1c56768ac39a` to `227566bf55a0`, and
  `lineage_version` (`version` in docs/data/version.json) from `f69b18c18fb7`
  to `9d1d27635859`; the graph version moves from `9802d9e854c9` to
  `5a967e980890`.

### Re-keyed ids

No lineage id and no vector id changes. These ids changed since 0.1.3:

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
- `config_dir` on the validators and writers is deprecated; pass `roots`.

### Deferred to 0.2.1

- Private overlays and their GOVERNANCE.md text. 0.2.0 validates
  `overlay_version` but nothing computes it yet.
- Retraction of model and configuration records.
- The composite and cure renderers.
