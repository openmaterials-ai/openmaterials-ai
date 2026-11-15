r"""Operators (edges) of the molecular domain.

Seven edges, all implicit (is_executable_in_sympy_override=False). The first
four are each an opaque applied function of its inputs with the molecular
method recorded as a scheme,
exactly like the electronic-transport, thermochemistry, and quasi-harmonic edges.

  compute_homo_lumo_gap        : (Structure, Potential) -> HOMOLUMOGap
  compute_reaction_barrier     : (TotalEnergy, Structure) -> ReactionBarrier[construction=neb_mep]
  compute_bond_dissociation    : (TotalEnergy, Structure) -> BondDissociationEnergy
  compute_molecular_frequencies: (Structure, Potential) -> MolecularFrequency
  rrho_ideal_gas_heat_capacity : (MolecularFrequency, Temperature) -> IdealGasMolarHeatCapacityP
  rrho_ideal_gas_heat_capacity[approximation=qrrho]
                                : (MolecularFrequency, Temperature)
                                  -> IdealGasMolarHeatCapacityP[approximation=qrrho]
  compute_infrared_intensities : (Structure, Potential, MolecularFrequency) -> InfraredIntensity
  compute_molecular_reaction_enthalpy: (TotalEnergy, MolecularFrequency,
                                 Temperature) -> MolecularReactionEnthalpy

rrho_ideal_gas_heat_capacity is a closed form (2026-11-15), dimensionally
proven, but not sympy-executable: its external constant and mode count are
properties of the molecule. The other two are opaque.

Connectivity. The four nodes plus four edges form ONE weakly connected component
through the pre-existing Structure / TotalEnergy / Potential source nodes:
compute_homo_lumo_gap and compute_molecular_frequencies consume Structure +
Potential (a molecular SCF / Hessian runs a structure under a chosen
functional/basis, the Potential-provenance analog); compute_reaction_barrier and
compute_bond_dissociation both consume TotalEnergy + Structure (a barrier and a
BDE are total-energy differences over molecular configurations). All inputs are
pre-existing store nodes, so the additions touch the store and are weakly
connected; every edge shares Structure.

Symbols. The output field symbols (E_{gap}^{mol}, E_{barrier}, E_{BDE}, and the
indexed nu_mol) are new and collision-checked; the input arguments \mathcal{S}
(Structure), V (Potential), E_{tot} (TotalEnergy) are existing registered symbols
reused as opaque-function arguments. The opaque solver functions (\Delta_{HL},
\Delta_{NEB}, \Delta_{BDE}, \nu^{H}) are applied functions, invisible to the
free-symbol check, so they need no vocabulary entries.
"""
from __future__ import annotations

import sympy as sp

from omai.operator.operator import Operator
from omai.molecular.operator.nodes import (
    BOND_DISSOCIATION_ENERGY,
    HOMO_LUMO_GAP,
    IDEAL_GAS_MOLAR_HEAT_CAPACITY_P,
    IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO,
    INFRARED_INTENSITY,
    MOLECULAR_FREQUENCY,
    MOLECULAR_REACTION_ENTHALPY,
    REACTION_BARRIER,
)
from omai.dft_ground_state.operator.nodes import TOTAL_ENERGY
from omai.materials.operator.shared_primitives import STRUCTURE
from omai.thermal_transport.operator.nodes import POTENTIAL, TEMPERATURE_STATE


# ---------------------------------------------------------------------------
# Symbols used by the formulas below.
# ---------------------------------------------------------------------------

# Output field symbols (new, registered in this domain's vocabulary).
_E_gap_mol = sp.Symbol(r"E_{gap}^{mol}")
_E_barrier = sp.Symbol(r"E_{barrier}")
_E_BDE = sp.Symbol(r"E_{BDE}")
_nu_mol = sp.IndexedBase("nu_mol")     # MolecularFrequency (indexed by mode m)
_m = sp.Symbol("m", integer=True)      # molecular normal-mode index
# Input arguments (existing registered symbols).
_S_struct = sp.Symbol(r"\mathcal{S}")  # Structure
_V_pot = sp.Symbol("V")                # Potential
_E_tot = sp.Symbol("E_{tot}")          # TotalEnergy
# Opaque solver functions (applied functions, not free symbols).
_gap_fn = sp.Function(r"\Delta_{HL}")
_neb_fn = sp.Function(r"\Delta_{NEB}")
_bde_fn = sp.Function(r"\Delta_{BDE}")
_hess_fn = sp.Function(r"\nu^{H}")     # mass-weighted-Hessian normal modes
_ir_fn = sp.Function(r"I^{IR}")        # dipole-derivative band intensity
_dh_fn = sp.Function(r"\Delta_{r}H")   # stoichiometric RRHO enthalpy sum
# Gas-phase thermochemistry symbols.
_cp_mol = sp.Symbol("cp_mol")          # IdealGasMolarHeatCapacityP
_ir_int = sp.IndexedBase("ir_int")     # InfraredIntensity (indexed by mode m)
_dh_r = sp.Symbol("dh_r")              # MolecularReactionEnthalpy
_nu_set = sp.Symbol("nu_mol")          # the mode set as one opaque argument
_T = sp.Symbol("T")
_kB = sp.Symbol("k_B")
_hbar = sp.Symbol(r"\hbar")
_N_A = sp.Symbol("N_A")
_c_ext = sp.Symbol("c_{ext}")          # 5/2 (atom), 7/2 (linear) or 4 (nonlinear)
_N_m = sp.Symbol("N_{m}", positive=True, integer=True)  # internal mode count
_x_m = 2 * sp.pi * _hbar * _nu_mol[_m] / (_kB * _T)
_nu_0 = sp.Symbol("nu_{0}", positive=True)  # quasi-RRHO rotor cutoff
_c_m = _x_m ** 2 * sp.exp(_x_m) / (sp.exp(_x_m) - 1) ** 2  # mode Cv over R
_w_m = 1 / (1 + (_nu_0 / _nu_mol[_m]) ** 4)  # Grimme damping, T-independent


# ---------------------------------------------------------------------------
# Operators.
# ---------------------------------------------------------------------------

compute_homo_lumo_gap = Operator(
    name="compute_homo_lumo_gap",
    inputs=(STRUCTURE, POTENTIAL),
    outputs=(HOMO_LUMO_GAP,),
    schemes={"method": "scf_orbital_gap"},
    formula=sp.Eq(_E_gap_mol, _gap_fn(_S_struct, _V_pot)),
    is_executable_in_sympy_override=False,
    description=(
        "Molecular HOMO-LUMO gap E_gap = Delta_HL[Structure, Potential]: the "
        "eV difference of the two discrete frontier KS molecular orbitals of a "
        "converged SCF, ORCA's homo_lumo_gap_eV (parse_orca_output.py:86-93). "
        "Delta_HL is opaque over the molecular Structure and the chosen "
        "functional / basis (the Potential-provenance analog, the def2-SVP "
        "default and the wB97M-V hyphenated-functional hack ride the scheme). "
        "The scheme records the scf_orbital_gap method. A COUSIN of the periodic "
        "band-gap producer, never equated (a molecule has no bands). Implicit (a "
        "molecular SCF, an opaque quantum-chemistry solve), so not "
        "sympy-executable."
    ),
)

compute_reaction_barrier = Operator(
    name="compute_reaction_barrier",
    inputs=(TOTAL_ENERGY, STRUCTURE),
    outputs=(REACTION_BARRIER,),
    schemes={"method": "ci_neb"},
    formula=sp.Eq(_E_barrier, _neb_fn(_E_tot, _S_struct)),
    is_executable_in_sympy_override=False,
    description=(
        "Reaction barrier E_barrier = Delta_NEB[E_tot, Structure] for the "
        "neb_mep construction: the peak-minus-reactant energy along the "
        "climbing-image nudged-elastic-band minimum-energy path, chem-neb-barrier "
        "via ase.mep NEBTools.get_barrier()[0] (calculate_barrier.py:126-127), "
        "results['barrier_eV']. Delta_NEB is opaque over the per-image "
        "TotalEnergy family (the E along the band) and the Structure endpoints; "
        "eV, MLIP. The scheme records the ci_neb method (idpp interpolation, 7 "
        "images, the MLIP checkpoint the discretization). This is the ONE "
        "construction minted this slice; the sella static-TS "
        "(construction=static_ts_mlip) and ORCA static-TS "
        "(construction=static_ts_dft) routes join the SAME reaction_barrier "
        "family later, distinct nodes only by the construction label, no re-mint. "
        "Distinct from the Arrhenius-slope ActivationEnergy. Implicit (a NEB "
        "path optimization), so not sympy-executable."
    ),
)

compute_bond_dissociation = Operator(
    name="compute_bond_dissociation",
    inputs=(TOTAL_ENERGY, STRUCTURE),
    outputs=(BOND_DISSOCIATION_ENERGY,),
    schemes={"method": "homolytic_fragment_difference"},
    formula=sp.Eq(_E_BDE, _bde_fn(_E_tot, _S_struct)),
    is_executable_in_sympy_override=False,
    description=(
        "Bond dissociation energy E_BDE = Delta_BDE[E_tot, Structure]: the "
        "relaxed fragment total-energy difference E(A.) + E(B.) - E(A-B) of "
        "homolytic cleavage, chem-bond-dissociation (calculate_bde.py:8, "
        "bde_eV:486; rdkit fragments the bond, the MLIP supplies the energies). "
        "Delta_BDE is opaque over the intact-molecule and fragment TotalEnergy "
        "values and the molecular Structure; eV native (kcal/mol the chemist's "
        "convention, the script's 23.0605 factor truncated). The scheme records "
        "the homolytic_fragment_difference method (heterolytic charged-fragment "
        "cleavage is the sibling method, an instance condition). A labeled "
        "sibling of the solid-state reaction-energy producer, on the per-molecule "
        "basis. Implicit (relaxed-fragment MLIP energy differences with open-shell "
        "radicals), so not sympy-executable."
    ),
)

compute_molecular_frequencies = Operator(
    name="compute_molecular_frequencies",
    inputs=(STRUCTURE, POTENTIAL),
    outputs=(MOLECULAR_FREQUENCY,),
    schemes={"method": "hessian_normal_modes"},
    formula=sp.Eq(_nu_mol[_m], _hess_fn(_S_struct, _V_pot)),
    is_executable_in_sympy_override=False,
    description=(
        "Molecular normal-mode frequencies nu_mol,m = nu^{H}[Structure, "
        "Potential]: the 3N eigenfrequencies of the mass-weighted Hessian of the "
        "molecular potential at a stationary structure, cm^-1 native; six of "
        "them (five for a linear molecule) belong to the rigid translations "
        "and rotations and vanish at a stationary point up to numerical "
        "noise, and the 3N-6 (or 3N-5) internal modes codes report are the "
        "subset left after projecting those out. nu^{H} is opaque over the "
        "molecular Structure and the chosen functional / basis (the "
        "Potential-provenance analog; the Hessian is the second derivative of "
        "that energy surface); the method scheme records the "
        "hessian_normal_modes construction. Imaginary modes serialize NEGATIVE "
        "(a negative Hessian eigenvalue), and n_imaginary (their count) is the "
        "saddle-order diagnostic (0 for a minimum, 1 for a transition state). "
        "Indexed by mode m (the registered `mode` kind), NOT the periodic "
        "phonon (q, nu) axis. Unblocks the RRHO molecular-thermochemistry "
        "bundle (the modes drive the partition function). Implicit (a Hessian "
        "diagonalization, an opaque quantum-chemistry / MLIP solve), so not "
        "sympy-executable."
    ),
)

rrho_ideal_gas_heat_capacity = Operator(
    name="rrho_ideal_gas_heat_capacity",
    inputs=(MOLECULAR_FREQUENCY, TEMPERATURE_STATE),
    outputs=(IDEAL_GAS_MOLAR_HEAT_CAPACITY_P,),
    schemes={"approximation": "harmonic"},
    formula=sp.Eq(
        _cp_mol,
        _N_A * _kB * (_c_ext + sp.Sum(_c_m, (_m, 1, _N_m))),
    ),
    is_executable_in_sympy_override=False,
    description=(
        "Ideal-gas heat capacity of one gas-phase species under the rigid-rotor "
        "harmonic-oscillator model: C_p = N_A k_B (c_ext + sum_m x_m^2 "
        "e^{x_m} / (e^{x_m} - 1)^2), x_m = 2 pi hbar nu_m / (k_B T) = h nu_m / "
        "(k_B T), summed over the N_m internal modes of MolecularFrequency "
        "(3N-6, 3N-5 for a linear molecule, none for an atom). The external "
        "constant c_ext is 3/2 for translation, plus 0, 1 or 3/2 for rotation, "
        "plus 1 for Cp - Cv: 5/2 for an atom, 7/2 for a linear molecule and 4 "
        "for a nonlinear one. The geometry is a condition of every value. The "
        "quasi-RRHO treatment is the sibling edge "
        "rrho_ideal_gas_heat_capacity[approximation=qrrho]. Imaginary modes are "
        "refused, not inverted: the model holds at a minimum. Not "
        "sympy-executable because c_ext and N_m are properties of the species, "
        "not of the inputs. omai.molecular.evaluate.cp_table evaluates it."
    ),
)

rrho_ideal_gas_heat_capacity_qrrho = Operator(
    name="rrho_ideal_gas_heat_capacity[approximation=qrrho]",
    inputs=(MOLECULAR_FREQUENCY, TEMPERATURE_STATE),
    outputs=(IDEAL_GAS_MOLAR_HEAT_CAPACITY_P_QRRHO,),
    schemes={"approximation": "qrrho"},
    formula=sp.Eq(
        _cp_mol,
        _N_A * _kB * (_c_ext + sp.Sum(
            _w_m * _c_m + (1 - _w_m) / 2, (_m, 1, _N_m))),
    ),
    is_executable_in_sympy_override=False,
    description=(
        "Quasi-RRHO ideal-gas heat capacity of one gas-phase species: C_p = "
        "N_A k_B (c_ext + sum_m [w_m c_m + (1 - w_m)/2]), c_m = x_m^2 e^{x_m} / "
        "(e^{x_m} - 1)^2 the harmonic mode term and w_m = 1/(1 + (nu0/nu_m)^4). "
        "It is the temperature derivative of the quasi-RRHO enthalpy H = w H_vib "
        "+ (1 - w) RT/2 of Li, Gomes, Sharada, Bell and Head-Gordon, J. Phys. "
        "Chem. C 119, 1840 (2015): w depends on nu_m and nu0 and does not depend "
        "on T, so each mode contributes w c_m + (1 - w)/2. The damping function "
        "is the one Grimme introduced for the entropy, Chem. Eur. J. 18, 9955 "
        "(2012). Soft torsions go to the free-rotor limit R/2, stiff modes keep "
        "their harmonic term. The rotor cutoff nu0 (cm^-1, 50 by default) is a "
        "condition of every value, as is the geometry: c_ext = 5/2 for an atom, "
        "7/2 for a linear molecule and 4 for a nonlinear one. Imaginary modes "
        "are refused, not inverted. Not sympy-executable for the reason of the "
        "harmonic edge. omai.molecular.evaluate.cp_table evaluates both."
    ),
)

compute_infrared_intensities = Operator(
    name="compute_infrared_intensities",
    inputs=(STRUCTURE, POTENTIAL, MOLECULAR_FREQUENCY),
    outputs=(INFRARED_INTENSITY,),
    schemes={"method": "dipole_derivative"},
    formula=sp.Eq(_ir_int[_m], _ir_fn(_S_struct, _V_pot, _nu_mol[_m])),
    is_executable_in_sympy_override=False,
    description=(
        "Infrared intensity of each normal mode ir_int,m = I^{IR}[Structure, "
        "Potential, nu_mol,m]: the integrated absorption of mode m, proportional "
        "to |d mu / d Q_m|^2, the squared derivative of the molecular dipole "
        "along the mass-weighted normal coordinate of the same Hessian that "
        "gives MolecularFrequency. That Hessian fixes the modes, so the edge "
        "reads MolecularFrequency and the index m aligns each intensity with "
        "its frequency. I^{IR} is opaque over the molecular Structure and "
        "the chosen method (the Potential-provenance analog). The scheme "
        "records the dipole_derivative construction (the harmonic double "
        "approximation). km/mol native. Implicit (a Hessian plus dipole "
        "derivatives from an electronic-structure method), so not "
        "sympy-executable."
    ),
)

compute_molecular_reaction_enthalpy = Operator(
    name="compute_molecular_reaction_enthalpy",
    inputs=(TOTAL_ENERGY, MOLECULAR_FREQUENCY, TEMPERATURE_STATE),
    outputs=(MOLECULAR_REACTION_ENTHALPY,),
    schemes={"method": "rrho_enthalpy_difference"},
    formula=sp.Eq(_dh_r, _dh_fn(_E_tot, _nu_set, _T)),
    is_executable_in_sympy_override=False,
    description=(
        "Reaction enthalpy of a balanced gas-phase reaction Delta_r H(T) = "
        "sum_i s_i H_i(T), s_i the signed stoichiometric coefficient (positive "
        "for a product) and H_i = N_A [E_tot,i + sum_m (h nu_m / 2 + h nu_m / "
        "(e^{x_m} - 1))] + c_H R T the RRHO molar enthalpy of species i: its "
        "electronic TotalEnergy, the zero-point and thermal energy of its "
        "MolecularFrequency modes, and the ideal-gas external term c_H = 4 "
        "(nonlinear), 7/2 (linear) or 5/2 (atom). Delta_r H is opaque over the per-species "
        "energies, mode sets and stoichiometry; the scheme records the "
        "rrho_enthalpy_difference construction. The reaction must balance in "
        "atoms and charge. Per mole of reaction as written, kJ/mol; the "
        "electronic Delta_r E = sum_i s_i N_A E_tot,i is a secondary. Implicit "
        "(a stoichiometric sum over species), so not sympy-executable."
    ),
)

EDGES: tuple[Operator, ...] = (
    compute_homo_lumo_gap,
    compute_reaction_barrier,
    compute_bond_dissociation,
    compute_molecular_frequencies,
    rrho_ideal_gas_heat_capacity,
    rrho_ideal_gas_heat_capacity_qrrho,
    compute_infrared_intensities,
    compute_molecular_reaction_enthalpy,
)
