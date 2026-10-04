"""MESKAL adapter specs for the thermal-transport DAG (representation meskal).

MESKAL (Mesoscopic Scattering Kernel for Anharmonic Lattices, tag v1.1.0) is a
JAX library for differentiable lattice thermal transport: force constants from
a potential by nested automatic differentiation, three-phonon linewidths, the
BTE in the relaxation-time approximation and with the full collision matrix,
QHGK for amorphous solids, and an open-system Green's-function route. Importing
meskal enables float64. The facts below are read from the v1.1.0 sources; its
stages are validated against goldens that kALDo produced
(examples/generate_reference_goldens.py), whose array conventions it keeps.

  operator Space                                  MESKAL function
  ----------------------------------------------  -----------------------------------------
  Potential                                       potentials.nep, potentials.tersoff
  ForceConstants[order=3]                         fc_supercell.supercell_fc3
  DynamicalMatrix                                 harmonic.dynamical_matrix
  Frequency                                       harmonic.frequencies
  GroupVelocity                                   harmonic.velocities
  HeatCapacity                                    thermal.heat_capacity
  IsotopeAbundances                               isotope.mass_variance
  Linewidth[channel=anharmonic_3ph]               scattering.gamma_from_fc3
  Linewidth[channel=isotope]                      isotope.gamma_isotope
  Linewidth[channel=boundary]                     2 * isotope.gamma_boundary
  MeanFreeDisplacement[bte_solver=rta]            collision_matvec.mean_free_paths_matrix_free
  MeanFreeDisplacement[bte_solver=direct_inverse] collision_matvec.mean_free_paths_matrix_free
  ThermalConductivity[bte_solver=rta]             kappa.kappa_from_fc, runners.bulk_kappa
  ThermalConductivity[bte_solver=direct_inverse]  collision.kappa_full_from_fc, kappa_full_matrix_free
  ThermalConductivity[transport_model=qhgk]       qhgk.qhgk_kappa
  ModalDiffusivity                                qhgk.qhgk_diffusivity
  PhononTransmission                              green.transmission.caroli_transmission
  ThermalConductance[transport_model=landauer]    green.conductance.landauer_conductance

Conventions this module pins down:

  * gamma is the FWHM in rad/ps, the rate 1/tau: kALDo's bandwidth, twice the
    imaginary self-energy (green/self_energy.py states it). The isotope and
    boundary rates share the convention and add to it; the mean free path is
    velocity / gamma, the map's v / (2 Gamma).
  * Not mapped: supercell_fc2 returns FC2 already mass-weighted in (rad/ps)^2,
    not ForceConstants[order=2] in eV/A^2; rescaled_eigenvectors are divided
    by sqrt(mass), not the unit Eigenvectors; scattering.phase_space is
    population weighted, not the kinematic PhaseSpace3Phonon.
"""

from __future__ import annotations

from omai.representation.adapter import OperatorRepresentationSpec, SpaceRepresentationSpec
from omai.thermal_transport.operator.edges import (
    compute_anharmonic_linewidth,
    compute_force_constants_3,
    solve_bte_direct,
)
from omai.thermal_transport.operator.nodes import (
    ANHARMONIC_LINEWIDTH,
    BOUNDARY_LINEWIDTH,
    DYNAMICAL_MATRIX,
    FORCE_CONSTANTS_3,
    FREQUENCY_STATE,
    GROUP_VELOCITY,
    HEAT_CAPACITY,
    ISOTOPE_ABUNDANCES,
    ISOTOPIC_LINEWIDTH,
    MEAN_FREE_DISPLACEMENT_DIRECT,
    MEAN_FREE_DISPLACEMENT_RTA,
    MODAL_DIFFUSIVITY,
    PHONON_TRANSMISSION,
    POTENTIAL,
    THERMAL_CONDUCTANCE_LANDAUER,
    THERMAL_CONDUCTIVITY_DIRECT,
    THERMAL_CONDUCTIVITY_QHGK,
    THERMAL_CONDUCTIVITY_RTA,
)


MESKAL_POTENTIAL = SpaceRepresentationSpec(
    space=POTENTIAL,
    representation_name="meskal",
    code_api={"potential": "potentials.nep (nep_io.load_nep) | potentials.tersoff"},
    notes=(
        "Native JAX force models, energy(structure, ...) -> scalar in eV, "
        "admitted only if nested-AD FC3 matches finite differences. NEP: "
        "nep4 and nep4_zbl read from a trained nep.txt (the NEP89 foundation "
        "model among them), a clean-room implementation of Fan et al., Phys. "
        "Rev. B 104, 104309 (2021) and J. Chem. Phys. 157, 114801 (2022). "
        "Tersoff: C, Si, Ge with the parameters of Phys. Rev. B 39, 5566 "
        "(1989)."
    ),
)


MESKAL_FORCE_CONSTANTS_3 = SpaceRepresentationSpec(
    space=FORCE_CONSTANTS_3,
    representation_name="meskal",
    observable_units={"phi": "eV_per_A3"},
    code_api={"phi": "fc_supercell.supercell_fc3(potential, structure, supercell)"},
    notes=(
        "Unweighted FC3 in eV/A^3, shape (n_modes, n_rep, n_modes, n_rep, "
        "n_modes), cell-0 rows only, from two nested forward-mode JVPs of the "
        "reverse-mode energy gradient of the supercell. Each atom pair is "
        "split equally over its shortest periodic images, kALDo's folding."
    ),
)


MESKAL_DYNAMICAL_MATRIX = SpaceRepresentationSpec(
    space=DYNAMICAL_MATRIX,
    representation_name="meskal",
    code_api={"D": "harmonic.dynamical_matrix(fc2, list_of_replicas, cell_inv, q_point)"},
    notes=(
        "D(q) = sum_l fc2[i, a, l, j, b] exp(2 pi i R_l . cell_inv . q), from "
        "the mass-weighted FC2, eigenvalues omega^2 in (rad/ps)^2. No "
        "non-analytic correction, so it equals BareDynamicalMatrix."
    ),
)


MESKAL_FREQUENCY = SpaceRepresentationSpec(
    space=FREQUENCY_STATE,
    representation_name="meskal",
    observable_units={"omega": "linear_THz"},
    code_api={"omega": "harmonic.frequencies"},
    notes=(
        "harmonic.frequencies in linear THz, shape (n_q, n_modes); a "
        "negative eigenvalue returns a negative frequency."
    ),
)


MESKAL_GROUP_VELOCITY = SpaceRepresentationSpec(
    space=GROUP_VELOCITY,
    representation_name="meskal",
    observable_units={"v": "angstrom_linear_THz"},
    code_api={"v": "harmonic.velocities"},
    notes=(
        "harmonic.velocities in A*THz, shape (n_q, n_modes, 3): the diagonal "
        "Hellmann-Feynman flux Re <e|dD/dk|e> / (2 omega), dD/dk by "
        "forward-mode AD, not rotated within degenerate subspaces."
    ),
)


MESKAL_HEAT_CAPACITY = SpaceRepresentationSpec(
    space=HEAT_CAPACITY,
    representation_name="meskal",
    observable_units={"c": "J_per_K"},
    code_api={"c": "thermal.heat_capacity(frequency_thz, temperature)"},
    notes=(
        "Per-mode quantum heat capacity in J/K, kALDo's scale; classical=True "
        "returns k_B."
    ),
)


MESKAL_ISOTOPE_ABUNDANCES = SpaceRepresentationSpec(
    space=ISOTOPE_ABUNDANCES,
    representation_name="meskal",
    observable_units={"g": "dimensionless"},
    code_api={"g": "isotope.mass_variance(species_masses, isotope_table)"},
    notes=(
        "Tamura g = sum_x f_x ((m_x - m_bar) / m_bar)^2 per species from "
        "(mass, abundance) pairs; the per-site g is occupations @ g. No "
        "natural-abundance default: a species absent from the table is pure."
    ),
)


MESKAL_LINEWIDTH = SpaceRepresentationSpec(
    space=ANHARMONIC_LINEWIDTH,
    representation_name="meskal",
    observable_units={"Gamma": "angular_THz"},
    observable_normalizations={"Gamma": "linewidth_2x_imag_self_energy"},
    code_api={"Gamma": "scattering.gamma_from_fc3"},
    notes=(
        "Three-phonon linewidth in rad/ps, shape (n_k, n_modes): the FWHM, "
        "tau = 1/Gamma, kALDo's bandwidth with per-mode ratio 1 against its "
        "goldens. Acoustic modes at Gamma masked to zero."
    ),
)


MESKAL_ISOTOPIC_LINEWIDTH = SpaceRepresentationSpec(
    space=ISOTOPIC_LINEWIDTH,
    representation_name="meskal",
    observable_units={"Gamma": "angular_THz"},
    observable_normalizations={"Gamma": "linewidth_2x_imag_self_energy"},
    code_api={"Gamma": "isotope.gamma_isotope"},
    notes=(
        "Tamura rate (pi/2) omega^2 sum g |<e|e'>|^2 delta(omega - omega') / "
        "n_k in rad/ps, shape (n_k, n_modes), with the three-phonon Gaussian "
        "delta; enters the BTE through extra_gamma beside gamma_from_fc3. "
        "Overlaps are per site; inputs are rescaled_eigenvectors renormalized "
        "per mode, equal to the unit eigenvectors only when all site masses "
        "are equal."
    ),
)


MESKAL_BOUNDARY_LINEWIDTH = SpaceRepresentationSpec(
    space=BOUNDARY_LINEWIDTH,
    representation_name="meskal",
    observable_units={"Gamma": "angular_THz"},
    observable_normalizations={"Gamma": "linewidth_2x_imag_self_energy"},
    code_api={"Gamma": "2 * isotope.gamma_boundary(velocity, length)"},
    notes=(
        "2 |v| / L in 1/ps (velocity in A*THz, L in A): MESKAL's documented "
        "finite-size linewidth, passed through extra_gamma (CHANGELOG 1.0.0), "
        "a 1/tau like gamma. In the map's convention it is Gamma = |v| / L, "
        "equal to compute_boundary_scattering at the same L; "
        "isotope.gamma_boundary alone returns |v| / L."
    ),
)


MESKAL_MEAN_FREE_DISPLACEMENT_RTA = SpaceRepresentationSpec(
    space=MEAN_FREE_DISPLACEMENT_RTA,
    representation_name="meskal",
    observable_units={"F": "angstrom"},
    code_api={"F": "collision_matvec.mean_free_paths_matrix_free(..., include_off_diagonal=False)"},
    notes=(
        "velocity / gamma per mode in A, shape (n_k * n_modes, 3), gamma "
        "including extra_gamma; zero on masked modes."
    ),
)


MESKAL_MEAN_FREE_DISPLACEMENT_DIRECT = SpaceRepresentationSpec(
    space=MEAN_FREE_DISPLACEMENT_DIRECT,
    representation_name="meskal",
    observable_units={"F": "angstrom"},
    code_api={"F": "collision_matvec.mean_free_paths_matrix_free"},
    notes=(
        "Solution of W F = v for the full collision operator W, in A, shape "
        "(n_k * n_modes, 3), returned with the relative residual of the "
        "BiCGSTAB solve."
    ),
)


MESKAL_THERMAL_CONDUCTIVITY_RTA = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTIVITY_RTA,
    representation_name="meskal",
    observable_units={"kappa": "W_per_m_per_K"},
    code_api={"kappa": "kappa.kappa_from_fc (runners.bulk_kappa: kappa_tensor_W_m_K)"},
    notes=(
        "RTA tensor (3, 3) in W/(m K), sum c v (v / gamma) / (V n_q), "
        "differentiable end to end; classical=True switches populations and "
        "heat capacities to equipartition. runners.bulk_kappa reads a staged "
        "FC2/FC3 bundle and returns the tensor and its mean diagonal on a "
        "Gamma-centered mesh, third_bandwidth 1.0 THz by default."
    ),
)


MESKAL_THERMAL_CONDUCTIVITY_DIRECT = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTIVITY_DIRECT,
    representation_name="meskal",
    observable_units={"kappa": "W_per_m_per_K"},
    code_api={"kappa": "collision.kappa_full_from_fc | collision_matvec.kappa_full_matrix_free"},
    notes=(
        "Full linearized BTE, tensor (3, 3) in W/(m K): kappa_full_from_fc "
        "builds the dense collision matrix and calls jnp.linalg.solve (kALDo's "
        "method='inverse', 251.920315 against its 251.920313 W/(m K) on the "
        "test system); kappa_full_matrix_free never materializes it and "
        "returns the residual. include_off_diagonal=False gives the exact RTA "
        "limit of the same solve. Takes the fixed third_bandwidth only, not "
        "the adaptive widths."
    ),
)


MESKAL_THERMAL_CONDUCTIVITY_QHGK = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTIVITY_QHGK,
    representation_name="meskal",
    observable_units={"kappa": "W_per_m_per_K"},
    code_api={"kappa": "qhgk.qhgk_kappa (sum over axis 0)"},
    notes=(
        "Gamma-point QHGK of Isaeva et al., Nat. Commun. 10, 3853 (2019): "
        "per-mode (n_modes, 3, 3) in W/(m K), a resonant Lorentzian of FWHM "
        "2 (b_i + b_j) on the bandwidth b in rad/ps, no antiresonant term, "
        "the two-mode quantum heat capacity when a temperature is given."
    ),
)


MESKAL_MODAL_DIFFUSIVITY = SpaceRepresentationSpec(
    space=MODAL_DIFFUSIVITY,
    representation_name="meskal",
    observable_units={"D_mode": "mm2_per_s"},
    code_api={"D_mode": "qhgk.qhgk_diffusivity"},
    notes=(
        "Per-mode diffusivity in mm^2/s, shape (n_modes,): 1/3 of the "
        "Cartesian trace, A^2/ps divided by 100, kALDo's convention."
    ),
)


MESKAL_PHONON_TRANSMISSION = SpaceRepresentationSpec(
    space=PHONON_TRANSMISSION,
    representation_name="meskal",
    observable_units={"T_trans": "dimensionless"},
    code_api={"T_trans": "green.transmission.caroli_transmission(z, h_device, sigma_left, sigma_right)"},
    notes=(
        "Caroli T = Re Tr[Gamma_L G Gamma_R G^dagger] at z = omega^2 + i eta, "
        "lead self-energies from Sancho-Rubio decimation (lead_self_energy); "
        "an optional sigma_extra inserts BTE linewidths as the optical "
        "potential -i omega gamma."
    ),
)


MESKAL_THERMAL_CONDUCTANCE_LANDAUER = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTANCE_LANDAUER,
    representation_name="meskal",
    observable_units={"G": "nW_per_K"},
    code_api={"G": "green.conductance.landauer_conductance(nu_thz, transmission, temperatures_k)"},
    notes=(
        "Landauer G(T) in nW/K, trapezoid rule on the linear-THz grid; one "
        "value per temperature."
    ),
)


# ---------------------------------------------------------------------------
# Operator-level specs (diagnostic: how MESKAL performs the steps)
# ---------------------------------------------------------------------------

MESKAL_COMPUTE_FORCE_CONSTANTS_3 = OperatorRepresentationSpec(
    operator=compute_force_constants_3,
    representation_name="meskal",
    scheme_overrides={"symmetry_group": "C1"},
    discretization_choices={
        "method": "two nested forward-mode JVPs of the reverse-mode energy gradient of the supercell; no displacements",
        "replica_folding": "each atom pair split equally over its shortest periodic images",
    },
    notes="No symmetry reduction.",
)


MESKAL_COMPUTE_LINEWIDTH = OperatorRepresentationSpec(
    operator=compute_anharmonic_linewidth,
    representation_name="meskal",
    parameter_units={"broadening_sigma": "linear_THz"},
    scheme_overrides={"broadening_param": "halfwidth", "symmetry_group": "C1"},
    discretization_choices={
        "bz_summation": "full_grid",
        "delta_cutoff_sigmas": "2",
        "degeneracy_averaging": "off",
    },
    notes=(
        "Fixed third_bandwidth s in linear THz enters as "
        "exp(-(x/sigma)^2) / sqrt(pi sigma^2), sigma = 2 pi s, kALDo's "
        "halfwidth form, cut at 2 sigma; the decay channel carries "
        "0.5 (1 + n' + n''). A per-mode array from broadening.mode_broadening "
        "(rad/ps) switches to adaptive widths combined per triplet in "
        "quadrature."
    ),
)


MESKAL_SOLVE_BTE_DIRECT = OperatorRepresentationSpec(
    operator=solve_bte_direct,
    representation_name="meskal",
    scheme_overrides={"symmetry_group": "C1"},
    discretization_choices={
        "collision_matrix_assembly": "full_grid",
        "linear_solver": "jnp.linalg.solve (dense) or BiCGSTAB with a diagonal preconditioner (matrix-free)",
        "convergence_eps_default": "1e-10 (BiCGSTAB relative tolerance)",
        "max_iterations_default": "2000",
    },
    notes=(
        "Off-diagonal entries are scaled by omega' / omega as in kALDo's "
        "inverse solver; the matrix-free operator is nonsymmetric, hence "
        "BiCGSTAB."
    ),
)
