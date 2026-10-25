# Joint harmonic ensembles and volumetric heat capacity

This OMAI-only tranche builds on [PR #174](https://github.com/openmaterials-ai/openmaterials-ai/pull/174), reviewed at `8429812e6ede92cb35b9d2b19e96d88df2b55a47`. That PR is unmerged. Current main was fetched at `01658f82dff364c5f8667680b71d0262f3ad7782`; Physlib remained `8ddcc004043c5b537e4225fa763121c176b62a4a`, on Lean 4.35.0. The historical Lean 4.31 package is unchanged.

## Results

The new product model allows different positive frequencies at every mode. It uses all natural-number occupations, the unweighted sum of the upstream oscillator energies, and product counting measure. The empty-index identity has one zero-energy microstate and partition one; it is not a zero-frequency oscillator or an empty state space.

The proofs establish partition factorization, Boltzmann finiteness, normalized energy integrability, and the actual joint F/U/S/C quantities. Entropy follows from the statistical F=U−TS identity after its measure hypotheses are proved. Heat capacity follows by differentiating the finite closed-form energy sum on positive temperatures; no interchange with an infinite occupation sum is assumed. The rectangular-grid occupation map preserves both the measure and the exact Hamiltonian.

Applying N_A/N_q after evaluating the joint quantities recovers the four existing molar formulas. This closes their joint-model interpretation gap but adds **zero unique operators**. Vacuum, singleton and unequal-frequency two-mode checks are compiled.

The newly proved volumetric endpoint is exactly `sum(c)/(N_q*V_cell)`, with positive primitive-cell volume. One proof uses actual single-mode Physlib heat capacities; another uses the actual joint ensemble capacity. Both cover the same `contract_volumetric_heat_capacity` operator and `VolumetricHeatCapacity` output. The molar relation is `C_vol=C_mol/(N_A*V_cell)`. With SI inputs the density has units J/(m³ K); exact real lemmas cover the Å³ factor 10⁻³⁰ and linear-THz/angular-frequency interpretation, without claiming to verify floating-point adapters.

## Coverage relative to PR #174

| Measure | PR #174 | This tranche |
|---|---:|---:|
| Catalog quantities / operators | 129 / 127 | 129 / 127 |
| Mapping groups | 18 | 21 |
| Compiled groups | 13 | 16 |
| Source-only groups | 5 | 5 |
| Compiled operators | 12 / 127 | 13 / 127 |
| Compiled formula-output quantities | 12 / 129 | 13 / 129 |
| Standalone interpretations | 1 | 1 |
| Quantities with reviewed references | 23 / 129 | 24 / 129 |
| Upstream declarations / modules referenced | 27 / 9 | 32 / 9 |

The compiled operator count is **10.24%** of the current catalog. Associated inputs are not counted as proved producers. Two proofs of one endpoint increase evidence-group counts, not unique coverage. The upstream counts describe this reference set, not the whole Physlib library.

The tranche adds **45 authored theorems**: 34 product results, 10 density/unit results and one joint-density composition. The complete environment audit contains **273 theorem declarations and 460 total declarations**, including existing dimension witnesses and Lean-generated helpers. Only `propext`, `Classical.choice` and `Quot.sound` are allowed.

## Provenance and review

Each reviewed formula contract now has its fully qualified Lean endpoint name and actual defining module checked by the compiler. Product contracts retain the original endpoint definitions in the sum module. The audit requires all seven contracts, hashes its validation scripts, and records 13 unique validated endpoint-definition pairs. These checks establish name provenance and detect drift; they do not automate scientific interpretation.

Tests reject invented namespaces, wrong defining modules, unsafe probe input, missing contracts, missing or inconsistent name-audit records, and stale source hashes. A regression adds another compiled proof group for an existing endpoint and checks that unique coverage does not increase. Retained schema-v1 payloads remain readable.

AI-assisted mathematical and software reviews checked the proof sources and integration. Separate warnings-as-errors compilations of the product, density and joint-density modules also passed. These reviews and local checks are not external human certification.

## Validation

- Full offline Python suite: **2,666 passed, 103 skipped, 1 live API acceptance test deselected**.
- Focused integration suite with real compiler/source checks enabled: **66 passed**.
- **40 JavaScript tests passed**, including 18 bridge/map navigation tests.
- Fresh installed wheel: registry, record validation and bidirectional lookup passed outside the source checkout.
- Lean build with warnings-as-errors: **3,321 build targets checked**; full axiom audit and 13 endpoint-definition name/module checks passed.
- All **32 upstream source names and defining modules** passed the separate compiled reference audit.
- Specification HTML and PDF regenerated; package and website mapping data are identical.

These are local results, not remote CI or deployment claims. The new rendering and browser interaction remain visually unverified. Scientific catalog IDs, formulas and lineage data are preserved; no simulation, paid scientific compute, downstream repair or Physlib PR was performed.

## Remaining limits

The model still requires positive temperature and strictly positive frequencies, a fixed finite independent spectrum and uniform q weights. Gamma acoustic zero modes, imaginary modes, intermode coupling, nonuniform quadrature, phonon/geometry producers and thermodynamic limits remain outside scope. Volume must be interpreted as primitive-cell volume, not silently replaced with a supercell volume. Normalization acts on the resulting thermodynamic quantity, never on the Hamiltonian.

The next response-identity work requires a volume-dependent thermodynamic model, a common unit/basis convention, and a smooth stable constant-pressure branch. Neither matching quantity names nor defining a response as the desired quotient would establish the missing model bridge.

[Proof sources](https://github.com/openmaterials-ai/openmaterials-ai/tree/feat/physlib-joint-ensemble/lean/bridge) · [Mapping records](https://github.com/openmaterials-ai/openmaterials-ai/blob/feat/physlib-joint-ensemble/omai/data/formula_bindings.json) · [Build evidence](https://github.com/openmaterials-ai/openmaterials-ai/blob/feat/physlib-joint-ensemble/lean/bridge/build-evidence.json)
