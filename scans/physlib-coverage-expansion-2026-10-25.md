# Harmonic proofs and Physlib navigation

Reviewed 2026-10-25. This OMAI-only expansion follows [PR #170](https://github.com/openmaterials-ai/openmaterials-ai/pull/170), merged as `01658f82dff364c5f8667680b71d0262f3ad7782`. Physlib remains pinned to `8ddcc004043c5b537e4225fa763121c176b62a4a` on Lean 4.35.0. Both remote heads were checked before integration. The historical Lean 4.31 package and its scientific evidence are unchanged.

## Coverage

| Measure | Merged #170 | This expansion |
|---|---:|---:|
| Catalog quantities / operators | 129 / 127 | 129 / 127 |
| Mapping groups | 16 | 18 |
| Compiled groups | 3 | 13 |
| Source-only groups | 13 | 5 |
| Quantities with any reviewed reference | 21 / 129 | 23 / 129 |
| Operators with any reviewed reference | 10 / 127 | 12 / 127 |
| Formula-output quantities covered by compiled results | 3 / 129 | 12 / 129 |
| Standalone quantity interpretations | 0 | 1 (Temperature) |
| Operators covered by compiled results | 3 / 127 | 12 / 127 |
| Distinct referenced upstream declarations / modules | 27 / 9 | 27 / 9 |

The original report counted four quantities associated with compiled groups, including an input lattice conductivity. The output-only baseline above is three. Inputs are still visible as references but no longer inflate formula-output proof counts. The 27 declarations are a reviewed reference set, not a denominator for all of Physlib. ISQ dimension coverage remains separate: 126 of 131 fields across 124 of 129 quantities.

## New results

**Single-mode harmonic thermodynamics.** The bridge constructs a canonical ensemble on all nonnegative integers with counting measure and the actual upstream oscillator spectrum. It evaluates the partition and energy-weighted sums, proves Boltzmann finiteness and normalized energy integrability, and identifies the upstream F/U/S/C quantities with OMAI's formulas. Fixed-spectrum derivatives establish dF/dT=-S and dU/dT=C. Heat capacity is transferred from the proved mean-energy equality on the open positive-temperature domain; no differentiation under an infinite sum is assumed.

**Four molar contractions.** The proved single-mode quantities are summed over a finite grid with N_q q points and exactly 3*N_atoms branches, using N_A/N_q normalization. These results identify OMAI's molar F/U/S/C formulas as normalized sums of actual Physlib quantities. They do not construct a joint product ensemble or prove a product-partition theorem. The basis is a mole of primitive cells, not atoms.

**Temperature and pressure.** Nonnegative absolute-temperature values round-trip through Physlib Temperature. Positive-temperature beta and unit-scaling results retain the exact upstream kB convention. In three dimensions, the explicit sign conversion from tensile-positive Cauchy stress to OMAI's compressive-positive stress makes trace(sigma)/3 equal the given inviscid pressure at each spacetime point. No static-flow or equilibrium premise is required. Stress is an input association, not a verified DFT producer.

The three new modules contain **39 authored theorems**. The complete compiled-environment audit covers **205 theorem declarations and 369 total declarations**, including generated helpers and the existing dimension witnesses. Only `propext`, `Classical.choice` and `Quot.sound` are permitted. The audit rejects missing reviewed formula contracts before building.

## Scientific limits

All harmonic modes require positive angular frequency and positive temperature, exact upstream hbar/kB, and a fixed spectrum. Zero-point energy contributes to F and U, not an additive term in S or C. Stored linear THz requires `omega_SI = 2*pi*10^12*nu_THz`. An unmodified Gamma mesh containing zero acoustic modes does not satisfy the molar proof's premises.

The proofs do not establish phonon/eigenmode production, spectral completeness of a quantum Hamiltonian, nonuniform q weighting, a zero-mode prescription, per-atom molar conversion, numerical convergence, or finite-precision correctness. Temperature is a representation result; the pressure result is restricted to the stated inviscid law.

## Map, package and website

The map and bridge inventory support navigation in both directions: OMAI quantity/operator to Physlib declaration, and exact upstream declaration/module to every reviewed OMAI binding. Reverse lookup preserves conditions and evidence; it is not a theorem about inverse functions. The scientific graph, UIDs, formulas, inputs, outputs and lineage rules are unchanged.

Python exposes `formula_bindings_for_physlib(declaration=..., module=...)` and `physlib_declaration_index()`. Both use installed package resources. Added coverage fields are optional for retained schema-v1 payloads; all supplied counts are checked. New proof subjects distinguish formula outputs, standalone interpretations and input associations.

Website inventory, map panels, README, specification HTML and PDF are updated together from the same records. The deployed website at review time still contains merged #170; this expansion requires its own publication.

## Review and validation

Principal software, HPC and mathematics agent reviewers shared findings and checked one another's scope. These are agent reviews, not external human certification. The mathematics review independently compiled all three modules and probed 52 authored theorem/definition/instance names. It found no blocking defect.

The software review found that an unknown parameterized map ID could silently select its bare quantity and display the wrong evidence. Exact unknown IDs now produce a missing-target panel, with a regression against the actual map handler. A separate compatibility review preserved reading of older schema-v1 coverage records. A deletion test checks that a missing molar formula contract fails the audit.

The full offline Python suite passed: **2,629 passed, 102 skipped, 1 live API acceptance test deselected**. Focused review regressions passed **24 tests**, with 4 optional compiler-environment checks skipped. Separately, the compiled source audit checked all 27 upstream names and their defining modules. The fresh installed wheel, **18 JavaScript navigation tests**, pinned Lean build and transitive axiom audit passed. No simulation or paid compute was run.

The new navigation has not been visually verified in a browser. Its actual handlers and rendering logic are tested; the earlier merged website was separately checked live. Browser verification of one revision is not evidence for another.

## Next proof targets

1. Construct the finite product ensemble and connect its partition function and extensive quantities to the normalized sums already proved.
2. Formalize the input-frequency unit map and a scientifically justified zero-acoustic-mode treatment.
3. Review derivative-based thermodynamic identities and response functions against the exact upstream hypotheses before promoting more records.
4. Keep transport, QHA, CALPHAD and empirical-model gaps explicit where matching concepts do not supply a formula proof.

[Proof sources and reproduction instructions](https://github.com/openmaterials-ai/openmaterials-ai/tree/feat/physlib-coverage-expansion/lean/bridge), [mapping records](https://github.com/openmaterials-ai/openmaterials-ai/blob/feat/physlib-coverage-expansion/omai/data/formula_bindings.json), and [build evidence](https://github.com/openmaterials-ai/openmaterials-ai/blob/feat/physlib-coverage-expansion/lean/bridge/build-evidence.json) give the assumptions and checked source hashes. OMAI owns formulas, MCG operations, and mapengine computation. This expansion changes neither downstream repository and opens no Physlib PR.
