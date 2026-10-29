# Current Physlib bridge

This Lean 4.35 package pins Physlib `9b583cb6ef6e9cc537c4d4b786b508de1abbcf42`. It is the map's only Lean package.

- `OMAIPhyslibDimensions.lean`: generated native seven-base ISQ encodings for
  every dimension-bearing catalog field, including promoted parameters. Opaque
  dimensions are omitted. These are declarations, not theorems; they do not establish unit
  conversions, model adequacy, formula equality, or numerical-code correctness.
- `OMAIPhyslibSemantics.lean`: scalar and isotropic thermoelectric formulas and
  harmonic closed-form consistency, under the documented model, normalization,
  frequency, and operating-point assumptions.
- `OMAIPhyslibHarmonicEnsemble.lean`: the full Nat-spectrum oscillator ensemble,
  partition and energy sums, finiteness and integrability, and identification of
  the OMAI F/U/S/C formulas. Fixed-spectrum derivatives and the sinh form of heat
  capacity are proved on the positive-temperature domain.
- `OMAIPhyslibHarmonicSums.lean`: four finite uniform-q molar contractions of the
  proved single-mode quantities, with exactly `3*N_atoms` branches. These are
  normalized sums, not a construction of a joint product ensemble.
- `OMAIPhyslibHarmonicProduct.lean`: the heterogeneous full-Nat joint ensemble,
  partition factorization, actual F/U/S/C, and the four molar endpoints. Its
  rectangular occupation reindexing preserves the measure and Hamiltonian.
- `OMAIPhyslibHarmonicDensity.lean` and `OMAIPhyslibJointDensity.lean`: volumetric
  heat capacity with positive primitive-cell volume, its molar relation, and
  the same formula from the actual joint ensemble. Exact real unit lemmas do
  not certify floating-point conversion code.
- `OMAIPhyslibStaticEnsemble.lean` and `OMAIPhyslibResponseUnits.lean`: an actual
  signed static-energy singleton, F/U shifts and S/Cv invariance, with cell/molar
  derivative scalings and non-unit normalization controls.
- `OMAIPhyslibResponseCalculus.lean` and `OMAIPhyslibHarmonicVolume.lean`: local
  C2 response calculus and its identification with a volume-dependent actual
  static-plus-harmonic ensemble. Cp is an enthalpy derivative, not the desired
  response formula by definition.
- `OMAIPhyslibResponseWitness.lean` and `OMAIPhyslibHarmonicResponse.lean`: an
  explicit heterogeneous nonzero-expansion example, a separate zero-response
  control, and the catalog Cp identity and inequality. These cover one operator
  and its output, not the numerical QHA producer or its input producers.
- `OMAIPhyslibModeGruneisen.lean`: derivative-defined mode Gruneisen
  parameters, actual per-mode canonical heat capacities and their weighted mean
  Gamma on the static-plus-harmonic volume family. The fixed-volume relation
  `(dP/dT)_V = Gamma*C_V_vol` is a supporting result, and the per-mode heat
  capacity is proved to decrease strictly with frequency at fixed positive
  temperature. Gamma uses no expansion, bulk modulus, branch or free energy.
- `OMAIPhyslibThermalGruneisen.lean`: the catalog endpoint `alpha*K/C_vol` and
  the theorem that, on a local stable constant-pressure branch, Gamma at the
  branch volume equals it with the volumetric expansion, isothermal
  bulk modulus `V_m*F_VV` and volumetric heat capacity `sum(c)/(N_q*v)` of the
  same model. This covers the identity operator and its
  output, not the opaque weighted-contraction operator, mode-Gruneisen producers
  or phonopy's thermal-Gruneisen quotient.
- `OMAIPhyslibGruneisenWitness.lean`: exact examples with heat-capacity
  arguments `hbar*omega/(kB*T) = 1, 2, 3` and mode parameters 1, 2, 3, where
  Gamma lies strictly between 1 and the arithmetic mean 2; a positive-expansion
  branch; a negative-rate branch with negative Gamma and expansion; and a zero
  control. The branches hold for every positive molar scale and q count, the
  zero control for every positive molar scale with one q point.
- `OMAIPhyslibGibbsBranch.lean`: a two-parameter equilibrium family V(T,p) of a C2 Helmholtz surface, built by the C1 implicit-function theorem from any stable stationary point. On any open volume interval inside the domain where F(T,.) is strictly convex, a stationary point of F(T,V)+pV is its unique minimizer, by strict monotonicity of F_V and the mean value theorem; every sufficiently narrow window around the selected volume is such an interval. The envelope relations (dG/dT)_p = F_T and (dG/dp)_T = V and the compressibility (dV/dp)_T = -1/F_VV follow.
- `OMAIPhyslibQHA.lean`: the five quasiharmonic producers. G(T,p) is the minimum of F(T,V)+pV over a volume window; C_P = -T (d2G/dT2)_p, alpha_V = (dV/dT)_p/V with V = (dG/dp)_T, and K_T = V (d2F/dV2)_T at the volume (dG/dp)_T, the mirror of the Phonopy EOS B0; the Gamma contraction is the heat-capacity-weighted mean of supplied mode parameters. The producers read G for V, alpha_V and C_P, and the curvature F_VV at the volume dG/dp for K_T. On the static-plus-harmonic family, and on any window across which F+pV is convex, the theorems give (dG/dT)_p = -(N_A/N_q) times the Physlib ensemble entropy, (dG/dp)_T = V, C_P equal to the actual enthalpy derivative, to C_V + T V alpha_V^2 K_T and to C_V + T (dV/dT)_p (dS/dV)_T with (dS/dV)_T = -F_TV = alpha_V K_T, alpha_V = -F_TV/(V F_VV), and K_T = -V/(dV/dp)_T. The Gamma contraction is the existing weighted mean, so its theorem is a corollary of the thermal Gruneisen identity with alpha_V and K_T read off G. The closure check that the producers avoid expansion, bulk, cp, branch and Gamma is syntactic; for K_T and the contraction it shows only a different spelling.
- `OMAIPhyslibQHAWitness.lean`: exact windows on the signed-rate families with positive and negative expansion, C_P strictly above C_V and contracted Gamma in (1, 2) or below 0, and a constant-frequency control with zero expansion, C_P = C_V and zero Gamma.
- `OMAIElasticity.lean`: local linear-elasticity theorems over Mathlib, with no Physlib physics counterpart. Any stiffness tensor with the first minor symmetry that stores positive energy for every nonzero symmetric strain has positive Voigt bulk and shear moduli, which bounds the catalog's Poisson ratio in `(-1, 1/2)`. Isotropic tensors give the Lame values and are stable exactly when both moduli are positive. In a cubic crystal the trace of the stress depends only on the trace of the strain, with modulus `K`, and the shape-relaxed energy curvature `V0*E''(V0)` equals `K`.
- `OMAICompositeConductivity.lean`: local effective-medium theorems over Mathlib. Both closed-form branches of the spheroid depolarization factor equal one integral, so `L33` lies in (0, 1), decreases strictly with the aspect ratio, joins continuously at the sphere and tends to the needle and disk limits. For every shape the random Nan conductivity exceeds the matrix value exactly when `2 b11 + b33 > 0`. For spheres the Nan formulas reduce to Maxwell-Garnett with the Kapitza-corrected filler conductivity, and the Hasselman-Johnson formula is the same at `d = 2 a_rad` (the catalog's `d` is a diameter); it exceeds the matrix conductivity exactly above the critical radius `(k_m/G) k/(k - k_m)`. The aligned axial conductivity decreases strictly with `L33` and lies strictly between the series and parallel mixtures.
- `OMAICureKinetics.lean`: local cure-kinetics theorems over Mathlib. The Kamal-Sourour cure time increases strictly with conversion and its derivative is the reciprocal rate; near every interior cure time one inverse solves the rate law on a neighbourhood. The DiBenedetto relation, in kelvin, maps `[0, 1]` one to one onto `[T_g0, T_ginf]` and lies strictly below the linear interpolation for `0 < lambda < 1`.
- `OMAIPhyslibLatticeDynamics.lean`: second-order force constants on the sites of a Physlib `Crystal`, which supplies the site and translation bookkeeping; the lattice-dynamics content is OMAI-local. With equal mixed partials, translation invariance and finite range, the index-permutation symmetry `Phi_ij(-R) = Phi_ji(R)` follows, the catalog dynamical matrix (cell-vector phase `e^{+i q.R}`) is Hermitian at every wavevector, and with the acoustic sum rule the Gamma-point matrix has at least three independent zero modes. `DispersionRelation` is the catalog eigen-equation.
- `OMAIPhyslibPhononDispersion.lean`: on a finite Born-von Karman supercell whose harmonic energy is never negative, a Bloch-wave argument makes the dynamical matrix positive semidefinite at every character of the translations. Folding the crystal force constants into the supercell, `Phi_BvK(R) = sum_L Phi(R + L)`, gives the catalog `D(q)` exactly at every commensurate wavevector, so a stable supercell has `omega^2 >= 0` there. Incommensurate wavevectors, the normal case of a BTE mesh, are not covered.
- `OMAIPhyslibGroupVelocity.lean`: the Hellmann-Feynman theorem for a differentiable Hermitian matrix path, with the eigenvalue's differentiability derived, and the exact q-derivative of the catalog dynamical matrix. On a differentiable eigenvector path, away from Gamma, with `omega^2 > 0`, the catalog velocity `e^dagger (dD/dq) e / (2 omega)` is real and equals `d omega/dq`.
- `OMAIPhyslibLatticeWitness.lean`: the monatomic chain on Physlib's `ofUnitCell Z Unit`, with the textbook `omega^2 = (2K/M)(1 - cos(q a))` and catalog velocity `a sqrt(K/M) cos(q a / 2)` on `0 < q a < pi`, and stable Einstein springs on `ofUnitCell (ZMod 3) Unit`.
- `OMAIPhyslibRTAConductivity.lean`: the relaxation-time conductivity with the actual Physlib canonical mode heat capacities at `T > 0` and positive half-widths `Gamma = Im Sigma` is symmetric and positive semidefinite, and positive definite exactly when the group velocities span space.
- `OMAIPhyslibKappaContraction.lean` (Mathlib only, not bound): the linearized-BTE conductivity is positive semidefinite when the collision matrix is, but the catalog's collision matrix is defective. A three-mode linearized BTE with one process `1 + 2 <-> 3`, Casimir boundary scattering and Bose-Einstein weights has a negative modal contribution, so its cumulative conductivity is not monotone in either binning, which refutes the catalog's cumulative-distribution semantics.
- `OMAIPhyslibParticipationRatio.lean` (Mathlib only): `1/N <= p <= 1` for a normalized mass-weighted mode, with `p = 1` exactly for uniform amplitudes and `p = 1/N` exactly for a single-atom mode.
- `OMAIDeviceMetrology.lean`: local theorems over Mathlib for the analog-device formulas. Every continuous reference-time-independent drift law is the catalog's power law; inverting two-dimensional T^(3/2) thermionic data with the catalog's T^2 law shifts the barrier by k_B T_eff/2 with T_eff between the two temperatures; symmetric two-site retention relaxes to one half with time constant tau/2; the ramp set voltage is the mean of a normalized Gumbel first-hop law, through Gamma'(1) = -gamma; the programming error exceeds c/sqrt(2 n_w); the pulse energy brackets a monotone switching pulse; the uniform-channel conductance bounds a series channel.
- `OMAIMaterialsTransport.lean`: local theorems over Mathlib for Arrhenius diffusion and Nernst-Einstein conduction. The weighted Arrhenius fit is the least-squares line and recovers E_a exactly on exact data; fitting sigma instead of sigma T returns E_a - k_B T_eff with T_eff inside the data's temperature range.
- `OMAIStabilityEnergies.lean`: local stability theorems over Mathlib. The interpreted hull distance of per-atom formation energies does not depend on the elemental references, nor on any affine-in-composition shift applied to every entry, and a supporting affine function certifies a zero distance. Adsorption and intercalation-voltage energy differences are unchanged by per-element energy offsets exactly when the cells balance atoms. The average intercalation voltage is the mean of the open-circuit voltage profile, kinks between plateaus included. Surface and grain-boundary energies of slabs with energies affine in thickness are thickness independent exactly when the bulk reference equals the slab slope. The catalog's reaction-energy formula is a recorded defect.
- `OMAICalphad.lean`: local CALPHAD equilibrium theorems over Mathlib for interpreted solver outputs, per mole of atoms. The binary equilibrium molar Gibbs energy is the convex envelope of the phase Gibbs curves; with phase Gibbs functions concave in temperature it is concave in temperature at fixed composition, so the equilibrium entropy and, for T >= 0, the enthalpy are nondecreasing through every transition; differentiable phase curves share the common tangent at a two-phase minimum; the phase fractions are the lever rule; a unary or congruent transition with positive entropy change has a unique transition temperature.
- `OMAIPhyslibContinuum.lean`: absolute-temperature round trips and beta unit
  scaling; signed three-dimensional inviscid stress and pressure contraction.
- `*-formula-contract.json`: separately reviewed OMAI endpoint identities and
  source hashes. All sixteen contracts are required by the audit. New proofs do
  not rewrite the historical six-formula contract.
- `build-evidence.json`: source and configuration hashes, pinned dependencies,
  and the transitive axiom audit from a build with warnings treated as errors.
  This is a reproducible local build record, not external certification.

Use the project environment (Python 3.11 or newer). From the repository root:

```sh
python3 -m omai.physlib_dimensions
python3 -m pytest tests/test_physlib_dimensions.py -q
bash lean/bridge/check.sh
python3 -m omai.formula_bindings --check --lean-package lean/bridge
PHYSLIB_BRIDGE_PACKAGE=lean/bridge python3 -m pytest tests/test_physlib_response_contract.py -q
```

Use `bash lean/bridge/check.sh --no-cache` when the matching cache is already
present. Set `PYTHON` to the environment interpreter if `python3` is older.
`check.sh` disables Mathlib's full-cache post-update hook and requests
only external imports reachable from the bridge. It builds only this library,
then audits imported kernel declarations owned by every bridge source module,
plus the existing bridge namespace. This includes private and generated helpers.
The audit requires every source module to be reachable with full private data;
its probe deliberately uses non-module imports for that visibility. It rejects
any transitive axiom outside `propext`, `Classical.choice`, `Quot.sound`
(in particular `sorryAx`). Expanded audit counts are not counts of new formulas.

The source-reference audit builds the mapped Physlib modules and checks each
fully qualified declaration name and defining module in Lean's compiled
environment. This validates references, not OMAI formula equivalence. It does
not add to the bridge's theorem or mapping counts. The read-only
`--physlib-path /path/to/pinned/physlib` option checks the pinned files and
declaration lines without compiling Lean.

The operator layer is unit-free. Canonical numeric frequency representations use
linear THz; the harmonic symbolic angular frequency requires
`omega_SI = 2*pi*10^12*nu_linear_THz`. Dimension equality does not prove that
factor. Harmonic molar results use moles of primitive cells, not CALPHAD's moles
of atoms. Every mode must have strictly positive frequency; an unmodified Gamma
grid with zero acoustic modes does not meet the premises. This package contains formulas and proofs; operations remain in MCG
and computation in mapengine.

The package audit checks each Lean endpoint definition named in the reviewed
contracts against its fully qualified name and actual defining module. A product
proof can refer to an unchanged endpoint in the earlier sum module. The audit
records these name/module pairs and hashes its validation scripts; these checks
establish provenance, not scientific interpretation.
