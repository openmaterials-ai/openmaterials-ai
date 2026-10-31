# Changelog

Changes to the `openmaterials-ai` package, its record format and the ids it
mints, for consumers. Versioning follows README.md ("Versioning"): before 1.0
an identity change takes the minor version, and this file lists every re-keyed
id.

## Unreleased

- The direct linearized BTE carries local Lean proofs (OMAILinearizedBTE, binding linearized-bte-conductivity), so the formula coverage moves from 83 to 85 of 133 operators and from 73 to 75 nodes. The catalog's Chaput collision matrix is symmetric for an even smearing kernel and a |V_3|^2 symmetric under exchange of its first two modes on momentum-conserving triples, and so is its weighting M = C^(1/2) Omega~ C^(1/2). Without the in-scattering kernel the linear system is solved exactly by the relaxation-time F = v/(2 Gamma). For a symmetric collision matrix the conductivity of any solution is symmetric, and positive semidefinite whenever Chaput's matrix is, which needs exact energy conservation and enters as a hypothesis (the identity that proves it is issue 221). solve_bte[bte_solver=direct_inverse] and contract_kappa[bte_solver=direct_inverse] are no longer recorded as gaps. The edge's missing |V_3|^2 input is issue 222. No id changes.
- An edge uid hashes its main formula, not its auxiliary formulas, yet a code that claims the operator implements both. tests/test_auxiliary_formula_pins.py pins a digest of the auxiliary formulas of each of the seven edges that carry them (tests/fixtures/auxiliary_formula_pins.json), so an auxiliary edit under an unchanged uid fails until the pin is regenerated and this file names the edge and the change (issue 217). No id changes.
- The phonon scattering channels carry local Lean proofs (OMAIPhononScattering, binding phonon-scattering-channels), so the formula coverage moves from 78 to 83 of 133 operators and from 68 to 73 nodes. The Tamura isotope linewidth is nonnegative and, for normalized eigenvectors, at most (pi/4) omega^2 g_max D(omega) with D the density of states smeared with the isotope kernel. The three-phonon linewidth is nonnegative for a |V_3|^2 symmetric under exchange of the two partner phonons, as the Maradudin-Fein form is, and an even smearing kernel that does not increase with the offset, which covers the catalog's Gaussian. For an arbitrary |V_3|^2 it is nonnegative when the kernel vanishes at signed offsets above omega_q nu, and a compiled example with an even but non-monotone kernel gives a negative linewidth. With the Casimir boundary linewidth |v|/(2L) in Matthiessen's sum the relaxation-time mean free displacement never exceeds the boundary length L, with equality exactly when the other channels vanish. sum_linewidths and solve_bte[bte_solver=rta] are no longer recorded as gaps. No id changes.
- The anharmonic and boundary linewidths follow the canonical convention Gamma = Im Sigma = 1/(2 tau) (issue 210). `compute_linewidth[channel=anharmonic_3ph]` moves from `d621418b9f5a` to `bed23822fc14` (records 369-370): its Brillouin-zone sum was divided by the atoms per cell instead of N_q, and its |V_3|^2 kernel carried no hbar^3, so the prefactor pi/(N hbar^2) was dimensionally open and, completed, gave the rate 1/tau. The corrected prefactor is pi/(2 N_q hbar^2) with |V_3|^2 = hbar^3 |V|^2 / (8 omega omega' omega''), an energy squared that now carries the Bloch phases and conjugations of the decay vertex. In angular units this equals phono3py's imaginary self-energy (Togo, Chaput and Tanaka, PRB 91, 094306 (2015)) and half of ShengBTE's rate 1/tau (Li, Carrete, Katcho and Mingo, Comput. Phys. Commun. 185, 1747 (2014)). `compute_boundary_scattering` moves from `6b7443f91473` to `1326da3355b5` (records 371-372): Gamma = |v|/L was the Casimir rate 1/tau, so the linewidth is |v|/(2L), which phono3py's |v|/(4 pi L) in linear THz equals in angular units. Two node descriptions state the convention by `edit_meta` (records 373-374). `solve_bte[bte_solver=direct_inverse]` keeps its id: its collision-matrix constant becomes pi/(N_q hbar^2), the constant of 2 Gamma, in an auxiliary formula, which is not identity. The ShengBTE, phono3py and kaldo boundary notes now state each code's quantity against the canonical linewidth. The graph version moves from `2933ca50010b` to `e7e0bfd4f7ca`, the lineage version from `ba4214ff67d6` to `1feeefc2b1d6` and the share snapshot from `97bc25ba71ed` to `7cfa947f3e9f`. The packaged kaldo request is re-minted (`236ecc1cf14d` to `4143d675438b`). No committed value changes, because each code's linewidth array was already normalized to the canonical convention. The re-keyed edge ids take the next minor package version. This entry does not publish a release.
- Three catalog statements are corrected. `compute_isotope_scattering` moves from `651498262f7d` to `7cf53f521738` by an `add_edge` plus a `supersede` record (records 363-364). The Tamura rate weighted the eigenvector overlap with a mass variance g_i whose atom index the inner overlap sum had already bound, and it summed over the Brillouin zone without 1/N_q, so it grew with the q-mesh. The corrected linewidth is Gamma_iso = (pi/4N_q) omega^2 sum_{q'nu'} delta(omega - omega') sum_b g_b |e_b(q nu)* . e_b(q' nu')|^2 with b the basis atom. Tamura's (pi/2N) prefactor (PRB 27, 858 (1983)) gives the rate 1/tau, and the canonical linewidth is Gamma = Im Sigma = 1/(2 tau), the convention under which the kaldo and ShengBTE isotopic arrays are scaled by 0.5. Four descriptions are corrected by `edit_meta` (records 365-368): the Linewidth[channel=isotope] node states the same linewidth, the QuantumKineticEnergy node and the sample_quantum_kinetic_energy edge give the centroid-virial prefactor as 1/(2P) with P the bead count, not 1/(2N), and the SeebeckCoefficient node names its downstream PowerFactor and ZT nodes instead of calling them deferred. The graph version moves from `d188748b014e` to `2933ca50010b`, the lineage version from `c458656768f1` to `ba4214ff67d6` and the share snapshot from `ac3fe0da9d81` to `97bc25ba71ed`. The packaged kaldo request is re-minted (`611488fd3f6a` to `236ecc1cf14d`). The re-keyed edge id takes the next minor package version. This entry does not publish a release.
- The physlib crosswalk (`docs/data/physlib_crosswalk.json`) is regenerated at the Lean bridge's pinned Physlib revision (issue 169, step 1). Entries are graded against the declarations the compiled bindings use: `exact` when the declaration is the node's quantity, `related` when a binding producing the node cites it or a formalization would specialize it. Units, dimensions, tuple projections, vacuum constants and classical ensembles standing in for quantum per-mode quantities no longer count, so the classical MicroHamiltonian free energy, entropy and internal energy leave the per-mode nodes, the pressure grade drops to related, and the electronic conductivity cites the record's sigma as exact. 47 of 136 nodes cite at least one declaration (11 exact, six of them on the thermoelectric record), every source line verified against the checkout, and a new `needs_upstream` section gives each of the other 89 a proposal for the upstream definition, naming the bridge module that formalizes it locally where one exists. `tests/test_physlib_crosswalk.py` checks the match-or-proposal completeness, the absence of em dashes and that the pinned revision is the bridge's. The share snapshot and code pages are re-minted because the snapshot freezes the crosswalk. No id changes.
- Two published value ids move: the PtSe2 bulk thermal conductivity of Donadio and collaborators (arXiv:2111.13395), cross-plane `4207b2ffedd2` to `4eaa9f67e155` and in-plane `457f936b93d9` to `adab238871da`. The `method` string of their lineage is reworded (the solver is unstated, so the value sits on the neutral node), and a value id is the hash of its lineage, so the ids follow. The old share stubs under `docs/i/` are pruned and the old ids no longer resolve. One `edit_meta` (record 362) rewords the total Linewidth: the linearized collision operator is a sum over independent mechanisms, so the channel rates add (Matthiessen's rule at the rate level). Graph version `d188748b014e`, lineage `c458656768f1`, snapshot `670a34927c09`.
- No em dashes remain in the hand-written files: 279 occurrences in 57 files, rewritten sentence by sentence with the meaning kept (a comma for a parenthetical, a colon for an explanation, a new sentence for an independent clause, `to` for ranges). Seven descriptions change by `edit_meta` (records 355-361): the quantities BareDynamicalMatrix, the total Linewidth, CumulativeKappa[wrt=mfp], Trajectory, HeatCurrentACF and VelocityAutocorrelation, and the NEMD `contract_kappa`. Two error messages of the representation layer are reworded with their tested words kept, and the table placeholder of one diagnostic script became `n/a`. Graph version `d5966372ca82`, lineage `9bcff4a03446`, snapshot `40bad5cf2755`. The six tests that ran node through `shutil.which` now go through `tests/node_runner.py`, so `OMAI_NODE` covers them. No id changes.
- Lean items 1 to 4 of issue 188. `dispersion_omega2_nonneg` reaches the contract definition `DispersionRelation` and is cited: a solution with a nonzero eigenvector of a positive semidefinite dynamical matrix has real `omega^2 >= 0`. `hellmann_feynman` and `catalogGroupVelocity_eq_deriv` take the eigen-equation and the normalization on a neighbourhood of the point only; `retention_symmetric_relaxation` assumes the rate equation for `t >= 0` only. `springs_fold_stable` and `springs_fold_three_stable` witness the folded-stability hypothesis of the commensurate-wavevector theorem on every finite ring and on `Z/3Z`. Eight simp or ring evaluations of the elasticity definitions and the one-line `tendsto_kapitzaCorrected` move from the cited declarations to the support sets, and the two binding statements keep the clauses the substantive theorems back. No id changes.
- The three catalog-defect formulas of issue 188 item 7 are corrected. `apply_nac_correction` moves from `37f84c36a536` to `b8fd10813fea` (records 346-347): the non-analytic term is the Gonze-Lee q -> 0 form, the wavevector components contracted with the Born charges and with `eps_inf`, the prefactor `4 pi q_e^2/(V_cell sqrt(M_i M_j))`, and the `(alpha, beta)` block of the atom pair the outer product of the contracted charges; the earlier form multiplied free components so that its q dependence cancelled. Its long-wavelength limit is now transcribed as `nonAnalytic` and bound by the static-dielectric binding, so the formula coverage moves from 77 to 78 of 133 operators. The linearized-BTE collision matrix, an auxiliary definition that is not part of the edge identity, is the symmetric weighting `M = C^(1/2) Omega~ C^(1/2)` of Chaput's symmetric collision matrix (diagonal `2 Gamma`, off-diagonal elements weighted by `2 sqrt(n''(n''+1))` of the third mode with `q + q' + q'' = G` and the three energy channels), whose relaxation-time limit is `F = v/(2 Gamma)` and whose conductivity is positive semidefinite whenever `Omega~` is; the earlier form was not symmetric and had the limit `F = hbar c v/(2 Gamma)`. The descriptions of `solve_bte[bte_solver=direct_inverse]` and of the two cumulative-conductivity operators say that a cumulative sum of signed modal terms is a distribution when the terms are nonnegative, and the BornCharges node names its index convention (`edit_meta`, records 348-354). The graph version moves from `2d7cf79f7e45` to `06b0bf80b839` and the lineage version from `80dba7fc47c8` to `98da97c6d855`; the packaged kaldo request is re-minted (`c5bbe38a4b46` to `742f235765ec`). The re-keyed id takes the next minor package version.
- Any selection on the map now has a share link. `omai.snapshots` freezes the data a share page reads into `docs/data/v/<sha256>.json`, written once and never rewritten. A snapshot holds the quantities with their names and symbols, the data flow, the public codes, the Lean and physlib status and the uid succession of the map log. `docs/data/v/index.json` names the latest snapshot. A link `https://openmaterials.ai/m/<snapshot prefix>/<selection>` carries the snapshot and a hex bitset over its quantities, so it renders the same page for as long as the snapshot is served. The map's Share button copies the link for whatever is lit, and shift-click picks quantities one by one. The page is `docs/share/index.html`. The site Worker serves it on `/m/` with per-link meta tags, renders a 1200 x 630 card once per link with resvg, stores the card in KV and answers oEmbed on `/oembed`. Code pages embed and share through the same link. `docs/assets/submap.js` draws the submap in the browser and the Worker, checked against `omai.submap` byte for byte. No id changes.
- Review follow-ups of the physlib coverage stack (issue 188, items 5, 6, 8, 10 and 11). Five descriptions are corrected by `edit_meta` (records 341-345): the Nan effective-medium terms are Nan's, not Bruggeman's; a filler lowers the composite conductivity below the crossover radius `a_c = a_K k/(k - k_m)` (Every, Tzou, Hasselman and Raj 1990), not below `a_K`; no bound is proved for the Nan formula outside its dilute range; the Kamal-Sourour conversion carries no proved bound. The paper's dimensional-gate paragraph is refreshed (133 edges, 59 ok, none violated, 74 skipped), the Physlib-cited results are described as citing declarations rather than anchored in README, the paper, llms.txt and the site pages, and the phonon-structure scan notes that a code's eigenvector basis need not lie on a differentiable path. The thermal-Gruneisen and response contract tests pin their own catalog rows and derive the node and operator totals from the live inventory, as does the tranche registry; the response test still pins the bytes of the map log and the version file. Their fixture compiles honour `OMAI_LEAN_PROBE_TIMEOUT`. The graph version moves from `c917b4073f36` to `2d7cf79f7e45` and the lineage version from `cb4f6b4d2adb` to `80dba7fc47c8`; the packaged kaldo request is re-minted (`b7673153f5d2` to `c5bbe38a4b46`). No id changes.
- `lean/bridge/audit.py` and `lean/bridge/verify_contracts.py` read `OMAI_LEAN_PROBE_TIMEOUT` (seconds, default 120) for their two compiler probes, which can exceed two minutes on a loaded host. The audit itself is unchanged. No id changes.
- Review follow-ups of the thermochemistry, atomistic and transport tranches (issue 192). Nine edges are re-minted, each by an `add_edge` plus a `supersede` record (records 308-325), and fifteen descriptions are corrected by `edit_meta` (records 326-340). `compute_reaction_energy` moves from `2f0b118bbe3e` to `2204ada808d0`: the signed formula-unit coefficient now multiplies the atoms of its formula unit, `sum_i c_i N^fu_i dH_f,i`, so 2 Li + 1/2 O2 -> Li2O gives -6.18 eV, not -2.06 eV. `compute_gruneisen` moves from `997206477b90` to `990caec662f7`: the Maradudin-Fein contraction with eigenvectors, masses, Bloch phases and positions replaces the two-index contraction that left three indices free. `compute_heat_current` moves from `c0093343fed4` to `02678de87aa0`: the per-atom virial term `sum_i sum_b W_iab v_ib` replaces the origin-dependent single-atom term. `fourier_to_dos` moves from `d6b71066f0ce` to `c142a31f3e5f`: the transform is normalized by `6/(pi Cv(0))` to the density of states per atom, three states on omega > 0. `compute_static_dielectric` moves from `ea3c7c5ef213` to `f658f73a7983`: Eigenvectors joins its inputs. `compute_electronic_conductivity` (`9fc03548d4ca` to `9b20bb39ed27`), `compute_seebeck` (`8514fb3e8586` to `f34ee134bfed`), `compute_electronic_thermal_conductivity` (`fe7f863a4325` to `b24757dc6349`) and `compute_carrier_mobility` (`c168368c90fa` to `8de71440c521`) change their method scheme from `bte_ibte` to `bte_mrta`, amset's momentum relaxation time approximation. The description records: the energy above the hull is zero on the whole lower hull; the intercalation voltage form holds for monovalent working ions; the surface and grain-boundary forms state their stoichiometric-slab and two-boundary conditions; MolarEnthalpy covers the equilibrium assemblage; the molecular frequencies are the 3N Hessian eigenvalues with the internal subset reported; the heat-current autocorrelation distinguishes linear from circular correlators; PhononDOS and the velocity autocorrelation state their normalization; the ReactionEnergy and HeatCurrent node descriptions follow their producers, and the ReactionEnergy node says that an rxn-network instance carries its dGf(T) temperature as a condition. The graph version moves from `02b3fc768e66` to `c917b4073f36` and the lineage version from `f5a7cb57594f` to `cb4f6b4d2adb`; the packaged kaldo external-solve request is re-minted (`1a88760844bd` to `b7673153f5d2`). Lean: the cited declaration `commonTangent_of_isLocalMin` becomes `commonTangent_of_isLocalExtr` (a public name in `formula_bindings.json`) and needs only a local extremum (its vanishing derivative), and where the equilibrium envelope follows the two-phase chord its tangent intercepts are the common-tangent intercepts (`chemicalPotentials_equilibriumGibbs_of_twoPhaseChord`); the enthalpy monotonicity needs nonnegative temperatures on the interior only; the hull distance reads only the competing set; the thickness statement is pairwise; the corrected reaction energy is transcribed (`catalogReactionEnergy`) and its reference independence is bound, so the formula coverage moves from 76 to 77 of 133 operators; the Wiedemann-Franz statement drops its unused `Sigma_0 != 0`; the VACF spectrum theorems carry the new normalization (integral 3 on omega > 0); the acoustic sum rules need only the first (second order) or second (third order) derivatives of the potential differentiable at the reference, and the elastic-constant symmetries and Voigt bounds need rotation invariance only on a neighbourhood of the reference cell; the St Venant-Kirchhoff energy of the Green-Lagrange strain is a compiled witness (`svkEnergy_elasticConstants_symmetries`, `svkEnergy_elasticConstants`, `svkEnergy_voigt_pos`) with the isotropic constants `(V0/V)(lam delta_ab delta_cd + mu (delta_ac delta_bd + delta_ad delta_bc))`. The re-keyed ids take the next minor package version (0.6.0). This entry does not publish a release.
- `docs/data/releases/openmaterials-ai.json` registers 0.5.0 (tag v0.5.0, commit 1aac5df), so `release_check` resolves an `execution.registry` row naming `openmaterials-ai` 0.5.0 against the live registry. The 0.5.0 wheel's bundled registry predates the tag and still reports it unregistered. No id changes.
- `docs/data/releases/openmaterials-ai.json` registers 0.5.1 (tag v0.5.1, commit 032fc32), the republished 0.5.0 code. No id changes.

## 0.5.1

The code of 0.5.0, republished. Every openmaterials-ai release file was removed from PyPI on 2026-10-29, and PyPI never accepts a removed filename again, so 0.5.0 cannot be uploaded a second time. Consumers pin `openmaterials-ai==0.5.1`. Against 0.5.0 only the version string changes: no code, record format, vector or id differs. No earlier version is on PyPI any more. Each keeps its git tag.

## 0.5.0

Every consumer pins `openmaterials-ai==0.5.0`. The minor version follows README "Versioning": public names are removed (`omai.lean_identities`, `omai.lean_units`, twelve `KALDO_*` specs, four names of `omai.physlean_export`, one `omai.thermal_transport.representation` module and one `CODE_CREDITS` key) and added (the external-solve snapshot API, `omai.formula_bindings`, `omai.physlib_dimensions`, the code-page generators), and the `ngspice` representation is added. The map moves from graph_version `baf99346621b` to `02b3fc768e66` and the lineage version from `61a981c02604` to `f5a7cb57594f` through append-only contributions: no node, edge or evidence uid is re-keyed. The packaged kaldo external-solve request is re-minted, so its `request_id` moves from `9c65fd692c45` to `1a88760844bd` (three steps, below); its `lineage_id` is unchanged.

- `omai.external_solve` receives a request as an immutable snapshot: `snapshot_request` checks shape and hashes without a map and returns an `ExternalSolveRequestSnapshot`, `validate_request_snapshot` authorizes it against the current store on every call, and `validate_request` accepts either form. Builders detach caller-owned lineage and execution values. Envelope version 1, request and lineage hashing and the executor's `ExternalSolveRequired` behavior are unchanged. docs/external-solve-snapshots.md describes the handoff. No id changes.
- `record_to_fragment` and `envelope_to_fragment` write gzip with a fixed header (MTIME 0, OS byte 255), so with a given zlib a record or envelope encodes to the same fragment on every clock and supported Python. The deflate body still depends on the zlib build (zlib-ng can differ). No id hashes a fragment, and fragments minted before decode as before. No id changes.
- `omai.code_pages`, `omai.code_cards` and `omai.refs_export` generate the per-code pages under docs/codes/ from the registry and the map. No id changes.
- The `kaldo` representation stops listing six interfaces absent from the kaldo 2.2.1 wheel (issue 180): Born charges on `atoms.info`, the Wigner conductivity with its populations and coherences split, and the two cumulative conductivities (against frequency and mean free path). `BornCharges`, `ThermalConductivity[transport_model=wigner]`, `ThermalConductivity[transport_model=wigner_populations]`, `ThermalConductivity[transport_model=wigner_coherences]`, `CumulativeKappa[wrt=omega]` and `CumulativeKappa[wrt=mfp]` keep their uids and lose kaldo coverage. Removed API: `KALDO_BORN_CHARGES`, `KALDO_PROVIDE_BORN_CHARGES`, `KALDO_THERMAL_CONDUCTIVITY_WIGNER`, `KALDO_THERMAL_CONDUCTIVITY_WIGNER_POPULATIONS`, `KALDO_THERMAL_CONDUCTIVITY_WIGNER_COHERENCES`, `KALDO_COMPUTE_KAPPA_WIGNER_POPULATIONS`, `KALDO_COMPUTE_KAPPA_WIGNER_COHERENCES`, `KALDO_COMBINE_KAPPA_WIGNER`, `KALDO_CUMULATIVE_KAPPA_OMEGA`, `KALDO_CUMULATIVE_KAPPA_MFP`, `KALDO_CONTRACT_CUMULATIVE_KAPPA_OMEGA` and `KALDO_CONTRACT_CUMULATIVE_KAPPA_MFP`.
- `omai.physlean_export` keeps `write_export` (without `index_out`) for `docs/data/lean.json`. `build_dimensions_export` moves to `omai.physlib_dimensions`. `build_export`, `DOMAINS` and the `build_graph_dict` re-export are removed (`omai.map_data` still has the last two).
- One private code representation is removed from the public commons: its thermal-transport representation module and re-exports, its credits, release file, `index/codes` entry and `codes.json` and registry key, and its three values on `PhononTransmission` and `ThermalConductance[transport_model=landauer]` with their share pages under `docs/i/`. The representation count moves from 34 to 33 and the value count from 93 to 90. Records 304 to 307 (`edit_meta`) drop the code name from the descriptions of `provide_transmission` and `compute_conductance[transport_model=landauer]` and state their symbols and units; both nodes and both edges stay, and no node or edge uid moves. The graph version moves from `2b27f48fbddb` to `02b3fc768e66`, and the unified lineage version from `45be98afae7c` to `f5a7cb57594f`. The packaged kaldo external-solve request pins the new graph version, so its `request_id` moves from `77ba6b7ef660` to `1a88760844bd`; its `lineage_id` is unchanged. A record whose `execution.registry` names the removed code now gives `{field: "execution.registry", kind: "code"}` as an unlisted code, the same reason as before.
- Removed API: one `omai.thermal_transport.representation` module, its `__all__` names and one `CODE_CREDITS` key. A record whose `execution.registry` names the removed code now also appears in `validate_light(...)["unresolved_registry_rows"]` (reason "not a representation"); under 0.4.0 that row resolved.
- One Lean package. The Lean 4.31 package in `lean/` (pinned to Physlib
  a74414af) is removed, with its generators `omai.lean_identities` and
  `omai.lean_units` and the `lean.yml` workflow. It held five-base node
  dimensions, 13 edge-dimension equalities and 18 theorems that restated
  closed-form formulas (from `Y = N/D` conclude `Y*D = N`), none of which
  certified anything about the physics. `lean/bridge` is the only package.
  Its generated `OMAIPhyslibDimensions.lean` keeps every dimension
  definition and drops the 133 `_exponents` theorems that restated them.
- `docs/data/lean.json` now lists each node's Physlib seven-base ISQ
  declarations from `lean/bridge` (`nodes[id].lean` and `nodes[id].fields`)
  with `physlib_rev` and `lean_toolchain`; the `edges` and `identities` keys
  are gone. 131 nodes have an entry, up from 102.
- `docs/data/lean_roadmap.json` rates formulas as `definition`, `hard` or
  `na`; `easy` and `trivial` merge into `definition`. `proven` now means a
  compiled formula bridge proves a statement about the operator. The Bose-
  Einstein occupation, Dirac delta and Heaviside step count as special
  functions, not code outputs. No id changes.
- `formula_bindings.json` gains the relation `local`: a compiled theorem
  about an OMAI formula that Physlib has no model for. A local binding
  cites no Physlib source, must be compiled and must state conditions and
  remaining obligations. Inventory rows covered only by local bindings have
  status `local` and keep their Physlib gap reason. `operators_compiled` and
  `nodes_compiled` keep their meaning (Physlib-anchored subjects only); new
  counters `operators_compiled_local`, `nodes_compiled_local`,
  `operators_proved`, `nodes_proved`, `operators_local` and `nodes_local`
  report the rest. Payloads without local bindings validate as before; a
  payload with local bindings must carry the new counters. A cited
  declaration may live in any bridge module the evidence source imports.
- New compiled bindings: the quasiharmonic producers (Gibbs energy, C_P, expansion, isothermal modulus, Gruneisen contraction), crystal lattice dynamics (dynamical matrix, dispersion, group velocity) and the relaxation-time conductivity, anchored to Physlib; local bindings for the elastic moduli, composite conductivity and depolarization factor, cure kinetics, the participation ratio, analog-device metrology, Arrhenius transport, the stability energy differences (hull distance, adsorption, intercalation voltage, surface and grain-boundary energies) and the CALPHAD equilibrium outputs (equilibrium Gibbs energy, enthalpy, entropy, chemical potentials, phase fractions, the unary or congruent transition temperature), and the derivatives of an atomistic or cell energy (Hellmann-Feynman force balance, force-constant sum rules and symmetry, central-difference error, cell-stress balance, hyperelastic elastic-constant symmetries and Voigt positivity, molecular normal modes at a minimum). The non-analytic correction, the linearized-BTE collision matrix, the cumulative conductivity of a linearized-BTE solution, the reaction energy (formula-unit coefficients applied to per-atom formation energies) and the mode Gruneisen formula (third-order force constants contracted over two indices with three left free) are recorded as catalog defects in their gap reasons. No id changes.
- Transport bindings: Physlib-anchored bindings for the Boltzmann electronic coefficients (conductivity, Seebeck coefficient and electronic thermal conductivity as Onsager moments of a nonnegative transport window; nonnegative kappa_e, a Physlib thermoelectric material, the Mahan-Sofo bound, the Sommerfeld Lorenz number) and for the phonon density of states and the Landauer conductance (sum rules on a Physlib crystal, the Physlib oscillator heat capacity as the Landauer weight, the conductance quantum); local bindings for the carrier mobility and the electronic density of states, the static dielectric tensor, the molecular-dynamics correlation estimators (velocity autocorrelation, mean squared displacement, heat-current autocorrelation, Green-Kubo conductivity) and the VACF spectrum. The molecular-dynamics heat-current formula is recorded as a catalog defect. No id changes.
- `docs/data/releases/openmaterials-ai.json` registers 0.4.0 (tag v0.4.0), so
  `release_check` resolves an `execution.registry` row naming
  `openmaterials-ai` 0.4.0 against the live registry. The 0.4.0 wheel's
  bundled registry predates the tag and still reports it unregistered. No id
  changes.
- The `ngspice` representation (the ngspice circuit simulator) maps
  `ConductanceState` and `DotProductError`, and
  `docs/data/releases/ngspice.json` registers ngspice-47 (version `47`), so
  a registry row naming `ngspice` 47 resolves. The representation count moves
  from 33 to 34. No node, edge or id changes.
- The map gains PotentialEnergyFitError, PotentialForceFitError and
  PotentialVirialFitError (dft_ground_state) and
  PotentialUncertaintyExceedance[method=committee_force_spread]
  (thermal_transport), each with one producing edge: records 290-295 and
  296-297, two contributions that supersede nothing, so no node or edge uid
  moves. The graph version moves from `baf99346621b` to `9476086d423e` and
  `lineage_version` from `61a981c02604` to `6f66f9c5e9c2`;
  `format_rules_version` stays `227566bf55a0`. The packaged external-solve
  request `omai/tools/kaldo-direct-bte-si.json` pins the new graph version,
  so its `request_id` moves from `9c65fd692c45` to `dd544ee37fd8`. A request
  minted against graph `baf99346621b` fails as a stale map version.
- The analog-device-metrology domain adds `ConductanceRelaxationTime`,
  `InterfaceTrapRelaxationTime` and benchmark-qualified
  `ClassificationAccuracy`. `subthreshold_conductance_tangent_time` evaluates
  the initial raw-conductance tangent under a single-mode subthreshold model.
  `evaluate_reservoir_classification` is an external response-family contract,
  not an executable classifier. Records 298-302 add the three nodes and two
  edges, and record 303 clarifies the `ClassificationAccuracy` description.
  No literature values or code coverage are added. Existing node, edge and
  evidence ids, record-format rules and private-evidence handling are
  unchanged. The graph version moves from `9476086d423e` to `2b27f48fbddb`,
  and the unified lineage version from `6f66f9c5e9c2` to `45be98afae7c`. The
  packaged kaldo external-solve fixture is re-minted against that graph,
  moving its `request_id` from `dd544ee37fd8` to `77ba6b7ef660`. Its
  scientific lineage and `lineage_id` are unchanged. Requests pinned to the
  former graph fail the existing stale-version gate.

## 0.4.0

Every consumer pins `openmaterials-ai==0.4.0`. No id changes: the map, its
operators and graph_version (baf99346) are unchanged.

- Release entries stay append-only: an entry's `license_source` text may
  now be corrected, while `version`, `tag`, `commit`, `released` and `spdx`
  never change.
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
  entry lists that version. A new public name and a representation take the
  minor version.
- `omai.composites.evaluate`: `nan_kappa_random` and `nan_kappa_aligned`
  (the aligned node's declared value, al33) evaluate the Nan edges at a
  composite record's conditions (`NAN_KEYS`), with the interface as a
  per-direction series film (the 2004 form). The Kapitza radius is km / G,
  derived; a `kapitza_radius_nm` that disagrees with it is refused.
  `aligned_tensor_components` also returns al11, which is not a node value.
  The representation `openmaterials-ai` now also covers the two Nan nodes
  (still 33 representations).

## 0.3.1

Every consumer pins `openmaterials-ai==0.3.1`.

- One code is marked private: its release file carries `"visibility":
  "private"`, since its source has no public repository, and `registry.json`
  (shipped as `omai/data/registry.json`) and `docs/data/codes.json` carry
  the same key. A record whose `execution.registry` names it gives
  `{field: "execution.registry", kind: "code"}`: such a record with no other
  private evidence, public under 0.3.0, is now private. The site reads
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
  2025.7.22.5.0, phono3py 4.4.0, qe qe-7.5 (alias
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
- Representations: qe-d3q (D3Q and thermal2) and an ev.x `BulkModulus` row
  on qe.
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
