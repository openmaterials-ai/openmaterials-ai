"""D3Q and thermal2 adapter specs for the thermal-transport DAG (representation qe-d3q).

D3Q (https://github.com/anharmonic/d3q, tag q-e-7.5) is the anharmonic
plugin of Quantum ESPRESSO 7.5: d3q.x computes third-order dynamical
matrices by DFPT and the 2n+1 theorem, consuming the pw.x SCF and ph.x DFPT
outputs of the same QE build; the thermal2 tools Fourier transform them to
real space and solve the phonon Boltzmann transport equation. The facts
below are read from the thermal2 manual (https://anharmonic.github.io/thermal2)
and the q-e-7.5 sources.

  operator Space                                  D3Q artifact                          program
  ----------------------------------------------  ------------------------------------  ----------
  ForceConstants[order=2]                         mat2R (thermal2 format, not flfrc)    d3_q2r.x
  ForceConstants[order=3]                         mat3R (.asr, .sparse)                 d3_qq2rr.x
  Linewidth[channel=anharmonic_3ph]               $prefix_T$T_s$sigma.out ('lw imag')   d3_lw.x
  ThermalConductivity[bte_solver=rta]             $prefix.$grid_P_sma.out (sma)         d3_tk.x
  ThermalConductivity[bte_solver=direct_inverse]  $prefix.$grid_T$T_s$sigma.out (cgp)   d3_tk.x

Conventions this module pins down:

  * Rydberg atomic units throughout: mat2R in Ry/bohr^2, mat3R in Ry/bohr^3
    (the d3_sparse.x threshold is quoted in Ry/bohr^3), against the eV/A^2
    and eV/A^3 of kaldo and phono3py.
  * d3_lw.x writes the HWHM Gamma, the imaginary part of the bubble
    self-energy, in cm^-1: tau = 1/(2 Gamma_ang) = 1/(4 pi c Gamma), Gamma
    the cm^-1 value and Gamma_ang = 2 pi c Gamma. The canonical
    imag_self_energy normalization (phono3py's gamma); kaldo's bandwidth and
    ShengBTE's w_anharmonic carry twice it, 2 Gamma_ang in rad/ps.
  * With delta_approx='gauss', and always in cgp, the delta is
    f_gauss(x, s) = exp(-(x/s)^2) / (s sqrt(pi)) (thermal2/functions.f90):
    the standard deviation is s / sqrt(2), not s. The default 'tetra'
    (tetrahedra) and a bare calculation='lw' (mode 'full', a complex-frequency
    Lorentzian) do not use it.
  * The map carries no format label on ForceConstants[order=2], so
    thermal2's mat2R sits on the plain order=2 node with its format in notes.
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
    FORCE_CONSTANTS_2,
    FORCE_CONSTANTS_3,
    THERMAL_CONDUCTIVITY_DIRECT,
    THERMAL_CONDUCTIVITY_RTA,
)


QE_D3Q_FORCE_CONSTANTS_2 = SpaceRepresentationSpec(
    space=FORCE_CONSTANTS_2,
    representation_name="qe-d3q",
    observable_units={"phi": "Ry_per_bohr2"},
    code_api={"phi": "d3_q2r.x mat2R (thermal2 format, not flfrc; centered by default, nfar=2), Ry/bohr^2"},
    notes=(
        "Harmonic force constants as thermal2 reads them: d3_q2r.x Fourier "
        "transforms the ph.x dynamical matrices and writes mat2R, thermal2's "
        "own text format (write_fc2), not q2r.x's flfrc (d3q's "
        "tools/fc2mat2R.sh converts), in Ry/bohr^2. With the default nfar=2 "
        "the R set is centered: each value is split among equidistant "
        "Wigner-Seitz images (quter.f90), so per-element values equal q2r.x's "
        "only with nfar=0. The map has no format label on "
        "ForceConstants[order=2], so this row sits on the plain order=2 node "
        "and the format lives here. Same traps as the qe representation's flfrc: "
        "short-range only for polar solids, masses in Rydberg atomic mass "
        "units."
    ),
)


QE_D3Q_FORCE_CONSTANTS_3 = SpaceRepresentationSpec(
    space=FORCE_CONSTANTS_3,
    representation_name="qe-d3q",
    observable_units={"phi": "Ry_per_bohr3"},
    code_api={"phi": "d3_qq2rr.x mat3R (d3_asr3.x, d3_sparse.x refine it), Ry/bohr^3"},
    notes=(
        "Third-order force constants by DFPT and the 2n+1 theorem. d3q.x, "
        "built against Quantum ESPRESSO 7.5 (tag q-e-7.5), reads the pw.x "
        "SCF and ph.x DFPT outputs and writes third-order dynamical matrices "
        "at q triplets (fild3dyn, XML); d3_qq2rr.x Fourier transforms them "
        "to real space (mat3R, centered by default like mat2R: -f, default "
        "2), d3_asr3.x imposes the acoustic sum rule, d3_sparse.x drops "
        "elements below a threshold given in Ry/bohr^3. No supercell "
        "displacements. 1 Ry/bohr^3 = 91.82 eV/A^3 against the canonical "
        "eV/A^3 of kaldo and phono3py."
    ),
)


QE_D3Q_LINEWIDTH = SpaceRepresentationSpec(
    space=ANHARMONIC_LINEWIDTH,
    representation_name="qe-d3q",
    observable_units={"Gamma": "inverse_cm"},
    # Canonical imag_self_energy: thermal2 writes the HWHM, no factor of 2.
    code_api={"Gamma": "d3_lw.x calculation='lw imag' ($prefix_T$T_s$sigma.out), cm^-1"},
    notes=(
        "Three-phonon linewidth per mode, in cm^-1, along a q path or on a "
        "grid. The thermal2 manual defines it as the HWHM, the imaginary "
        "part of the bubble self-energy: tau = 1/(2 Gamma_ang) = "
        "1/(4 pi c Gamma), Gamma the cm^-1 value; phono3py's gamma. kaldo's "
        "bandwidth and ShengBTE's w_anharmonic are 2 Gamma_ang in rad/ps. One "
        "output file per (temperature, smearing) configuration. The linewidth "
        "block (3*nat columns, one per mode) is the anharmonic_3ph value only "
        "with isotopic_disorder and casimir_scattering at their .false. "
        "defaults; with either on it is the total, and the anharmonic part is "
        "lw - lw_iso - lw_cas (the next two blocks)."
    ),
)


QE_D3Q_THERMAL_CONDUCTIVITY_RTA = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTIVITY_RTA,
    representation_name="qe-d3q",
    observable_units={"kappa": "W_per_m_per_K"},
    code_api={"kappa": "d3_tk.x calculation='sma' ($prefix.$grid_P_sma.out, K_P), W/(m K)"},
    notes=(
        "Single-mode approximation (thermal2's name for the RTA) kappa "
        "tensor in W/(m K), one row per (temperature, smearing) "
        "configuration: K_P, the populations term, the same K_P rows d3_tk.x "
        "prints to stdout. _C.out (Wigner coherences) and _TOT.out "
        "(K_P + K_C) are not the RTA. With store_lw=.true. (default .false.) "
        "the per-channel HWHM in cm^-1 are written alongside (lw., lwiso., "
        "lwcas. files); the SMA uses twice their sum."
    ),
)


QE_D3Q_THERMAL_CONDUCTIVITY_DIRECT = SpaceRepresentationSpec(
    space=THERMAL_CONDUCTIVITY_DIRECT,
    representation_name="qe-d3q",
    observable_units={"kappa": "W_per_m_per_K"},
    code_api={"kappa": "d3_tk.x calculation='cgp' (alias 'exact'; last row of $prefix.$grid_T$T_s$sigma.out), W/(m K)"},
    notes=(
        "Exact solution of the linearized BTE by preconditioned conjugate "
        "gradient on the variational functional (Fugallo, Lazzeri, "
        "Paulatto, Mauri 2013): the canonical bte_solver=direct_inverse, "
        "the same fixed point as kaldo's inverse, phono3py's is_LBTE=True "
        "and ShengBTE's converged iteration, by a different algorithm. The "
        "per-configuration file appends one row per iteration (first column "
        "the iteration, -1 the SMA start); $prefix.$grid_SMA.out and "
        "$prefix.$grid_iter<N>.out are all-configuration summaries. It stops "
        "once, for every configuration, each diagonal component's relative "
        "change times RY_TO_WATTMM1KM1 (~8.5e8, check_conv_tk) is below "
        "thr_tk (default 1e-2, about 1.2e-11 relative; pass thr_tk = 8.5e8 x "
        "the wanted relative tolerance), or after niter_max (default 1000) "
        "iterations; only the former prints 'Convergence achieved', and a "
        "solve that exhausts niter_max is unconverged."
    ),
)


# ---------------------------------------------------------------------------
# Operator-level specs (diagnostic: how D3Q and thermal2 perform the steps)
# ---------------------------------------------------------------------------

QE_D3Q_COMPUTE_FORCE_CONSTANTS_3 = OperatorRepresentationSpec(
    operator=compute_force_constants_3,
    representation_name="qe-d3q",
    scheme_overrides={"symmetry_group": "qe_spacegroup"},
    discretization_choices={
        "method": "DFPT with the 2n+1 theorem (d3q.x) on a regular q triplet grid; no supercell displacements",
        "acoustic_sum_rule": "d3_asr3.x, iterative, applied to mat3R after d3_qq2rr.x",
    },
    notes=(
        "d3q.x symmetrizes the third-order matrices with QE's space-group "
        "machinery (d3matrix), not spglib: the qe_spacegroup scheme of the "
        "qe representation's FC2, one order up."
    ),
)


QE_D3Q_COMPUTE_LINEWIDTH = OperatorRepresentationSpec(
    operator=compute_anharmonic_linewidth,
    representation_name="qe-d3q",
    parameter_units={"broadening_sigma": "inverse_cm"},
    # f_gauss is kaldo's halfwidth form; holds for delta_approx='gauss' and cgp.
    scheme_overrides={"broadening_param": "halfwidth"},
    discretization_choices={
        "bz_summation": "full_grid",
        "delta_cutoff_sigmas": "infinity",
        "degeneracy_averaging": "on",
        "delta_approx": "tetra (default, s unused) or gauss; cgp always gauss",
    },
    notes=(
        "Sums the full inner grid with no Gaussian cutoff and averages "
        "degenerate modes (merge_degen). With delta_approx='gauss' (d3_lw.x "
        "'lw imag' or 'lw real', d3_tk.x 'sma') and always in cgp, the "
        "smearing s enters as f_gauss(x, s) = exp(-(x/s)^2) / (s sqrt(pi)), "
        "kaldo's halfwidth form: the standard deviation is s / sqrt(2), so a "
        "fixed stdev sigma elsewhere is s = sqrt(2) sigma. The default "
        "delta_approx='tetra' integrates by optimized tetrahedra; a bare "
        "calculation='lw' runs mode 'full', a complex-frequency Lorentzian of "
        "width s (linewidth.f90). delta_approx and the mode belong on the "
        "lineage."
    ),
)


QE_D3Q_SOLVE_BTE_DIRECT = OperatorRepresentationSpec(
    operator=solve_bte_direct,
    representation_name="qe-d3q",
    discretization_choices={
        "collision_matrix_assembly": "full_grid",
        "linear_solver": "preconditioned conjugate gradient on the variational functional (calculation='cgp'), matrix-free",
        "convergence_eps_default": "1e-2 (thr_tk, on the relative change times RY_TO_WATTMM1KM1 ~ 8.5e8)",
        "max_iterations_default": "1000",
    },
    notes=(
        "Fugallo, Lazzeri, Paulatto, Mauri 2013: the linearized BTE is "
        "solved exactly by minimizing a variational functional with a "
        "preconditioned conjugate gradient; the same fixed point as "
        "phono3py's pseudo-inverse and ShengBTE's iteration. Only the "
        "diagonal is stored (A_out, computed once and checkpointed by "
        "save_cg_step); each step applies the scattering-in part matrix-free "
        "on the full grid (inner grid = outer grid, no symmetry reduction)."
    ),
)
