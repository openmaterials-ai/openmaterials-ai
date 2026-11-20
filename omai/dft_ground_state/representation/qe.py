"""Quantum ESPRESSO adapter specs for the DFT ground-state domain.

pw.x is the engine that grounds this domain: one SCF run produces the total
energy, the per-atom forces (tprnfor=.true., automatic in relax runs), and the
cell stress (tstress=.true.). The mapped artifacts, anchored to the vendored
q-e/ tree via the scan catalog `scans/qe-phonon.json` (QE 7.5):

  operator Space   QE artifact                                        program
  ---------------  -------------------------------------------------  -------
  Structure        input cards CELL_PARAMETERS / ATOMIC_POSITIONS /   pw.x
                   ATOMIC_SPECIES (or ibrav + celldm)
  TotalEnergy      stdout '!    total energy = ... Ry';               pw.x
                   XML total_energy (Hartree, etot/e2)
  Forces           stdout 'Forces acting on atoms' block (Ry/au);     pw.x
                   XML forces (Hartree/bohr, forces/e2)
  Stress           stdout 'total   stress' block (Ry/bohr**3 and      pw.x
                   kbar side by side); XML stress (Hartree/bohr^3)
  CubicLatticeParameter
                   vc-relax stdout 'Begin final coordinates' block    pw.x
                   (cell volume, CELL_PARAMETERS); XML atomic_structure
                   cell vectors (bohr)

Convention traps this module pins down:

  * stdout is Rydberg atomic units; the data-file-schema.xml divides every
    energy-bearing quantity by e2 = 2, i.e. stores Hartree atomic units
    (etot/e2 at PW/src/pw_restart_new.f90:728, forces/e2 at
    Modules/qexsd_init.f90:1366, stress/e2 at Modules/qexsd_init.f90:1394).
  * 'Ry/au' in the forces header means Ry/bohr.
  * The stress SIGN is the pressure convention (positive diagonal =
    compressive), verified from the vendored source, not assumed; see
    QE_STRESS.notes for the file:line derivation.
  * With smearing, the printed '!' energy is the smeared free-energy variant
    (F = E - TS_smear), flagged in the output near the '!' line.
  * The alat printed with the relaxed cell is the INPUT celldm(1), not the
    relaxed lattice constant; see QE_CUBIC_LATTICE_PARAMETER.notes.
"""

from __future__ import annotations

from omai.representation.adapter import (
    OperatorRepresentationSpec,
    SpaceRepresentationSpec,
)
from omai.dft_ground_state.operator.edges import (
    relax_cubic_lattice_parameter,
    solve_ground_state,
)
from omai.dft_ground_state.operator.nodes import (
    CUBIC_LATTICE_PARAMETER,
    FORCES,
    STRESS,
    STRUCTURE,
    TOTAL_ENERGY,
)


QE_STRUCTURE = SpaceRepresentationSpec(
    space=STRUCTURE,
    representation_name="qe",
    code_api={
        "structure": "pw.x input cards CELL_PARAMETERS / ATOMIC_POSITIONS / ATOMIC_SPECIES",
    },
    notes=(
        "The crystal structure a pw.x run consumes: the cell either as an "
        "explicit CELL_PARAMETERS card (ibrav=0) or as a Bravais lattice "
        "index ibrav with celldm parameters; species and masses in "
        "ATOMIC_SPECIES; positions in ATOMIC_POSITIONS (alat, bohr, angstrom, "
        "or crystal units, declared on the card). The two cell routes are "
        "equivalent inputs to the same Structure; ibrav != 0 additionally "
        "fixes QE's canonical orientation of the primitive vectors, which "
        "matters when comparing Cartesian tensors (forces, stress) against "
        "another code's frame. Opaque at the operator layer: an artifact, "
        "not a numeric unit."
    ),
)


QE_TOTAL_ENERGY = SpaceRepresentationSpec(
    space=TOTAL_ENERGY,
    representation_name="qe",
    observable_units={"E_tot": "ry"},
    code_api={
        "E_tot": "pw.x stdout '!    total energy = ... Ry'; XML total_energy element",
    },
    notes=(
        "The converged SCF total energy. The '!' marker prefixes the "
        "CONVERGED value (intermediate iterations print unmarked estimates); "
        "the format lives at q-e/PW/src/electrons.f90:1758 (9080 FORMAT, "
        "F17.8, Ry). The data-file-schema.xml stores total_energy divided by "
        "e2 = 2, i.e. Hartree atomic units (qexsd_init_total_energy call at "
        "q-e/PW/src/pw_restart_new.f90:728), a factor-2 trap when parsing "
        "XML instead of stdout. With smearing the printed quantity is the "
        "smeared free energy F = E - TS_smear, flagged in the output."
    ),
)


QE_FORCES = SpaceRepresentationSpec(
    space=FORCES,
    representation_name="qe",
    observable_units={"F": "Ry_per_bohr"},
    code_api={
        "F": "pw.x stdout 'Forces acting on atoms (cartesian axes, Ry/au):' block (tprnfor=.true.)",
    },
    notes=(
        "Per-atom Cartesian forces in Ry/bohr ('Ry/au' means Ry/bohr): "
        "header at q-e/PW/src/forces.f90:345, per-atom 'atom N type M "
        "force =' lines (3F14.8) at q-e/PW/src/forces.f90:527. Printed when "
        "tprnfor=.true. (automatic in relax / md calculations). The XML "
        "stores forces/e2, i.e. Hartree/bohr (q-e/Modules/qexsd_init.f90:"
        "1366). This block is exactly what finite-displacement drivers "
        "(phonopy for FC2, thirdorder.py for FC3) harvest from supercell "
        "runs."
    ),
)


QE_STRESS = SpaceRepresentationSpec(
    space=STRESS,
    representation_name="qe",
    observable_units={"sigma": "kbar"},
    code_api={
        "sigma": "pw.x stdout 'total   stress  (Ry/bohr**3) ... (kbar)  P=' block (tstress=.true.)",
    },
    notes=(
        "Cell stress printed in Ry/bohr^3 and kbar side by side, with the "
        "pressure P = trace/3 in kbar on the header line (9000 format at "
        "q-e/PW/src/stress.f90:264; P computed as (sigma(1,1)+sigma(2,2)+"
        "sigma(3,3))*ry_kbar/3 at q-e/PW/src/stress.f90:228). SIGN "
        "CONVENTION, verified from the vendored source rather than assumed: "
        "QE prints the PRESSURE convention, positive diagonal = compressive. "
        "The variable-cell force is fcell proportional to (stress - press*I) "
        "(q-e/Modules/cell_base.f90:1008-1013, subroutine cell_force), so "
        "equilibrium under a positive external pressure press requires "
        "stress = press*I with POSITIVE diagonal entries; a compressed cell "
        "therefore prints positive sigma and positive P. Equivalently "
        "sigma_QE = -(1/V) dE/d(strain), the negative of the tension-"
        "positive continuum-mechanics Cauchy convention. The XML stores "
        "stress/e2, Hartree atomic units (q-e/Modules/qexsd_init.f90:1394)."
    ),
)


QE_CUBIC_LATTICE_PARAMETER = SpaceRepresentationSpec(
    space=CUBIC_LATTICE_PARAMETER,
    representation_name="qe",
    observable_units={"a_lat": "bohr"},
    code_api={
        "a_lat": "pw.x vc-relax stdout block 'Begin final coordinates' to 'End final coordinates' (CELL_PARAMETERS vectors, 'new unit-cell volume'); XML output/atomic_structure cell a1, a2, a3",
    },
    notes=(
        "From a converged pw.x run with calculation='vc-relax'. The final "
        "cell is printed between 'Begin final coordinates' and 'End final "
        "coordinates' (q-e/PW/src/output_tau.f90:89 and :163): the line "
        "'new unit-cell volume = V a.u.^3 ( V Ang^3 )' (:92-93, F12.5 and "
        "F11.5), the density, then the three cell vectors (3F14.9) under one "
        "of three headers chosen by the units of the input CELL_PARAMETERS "
        "card: 'CELL_PARAMETERS (alat= x)' with the vectors in units of alat "
        "(:102, and the default at :112), 'CELL_PARAMETERS (bohr)' (:105) or "
        "'CELL_PARAMETERS (angstrom)' (:108). A parser reads all three. The "
        "alat in the first header is the INPUT celldm(1): pw.x moves the "
        "cell by rescaling the vectors at fixed alat. The XML stores the same "
        "input alat as an attribute of atomic_structure and the cell vectors "
        "alat*at(:,i) in bohr (q-e/PW/src/pw_restart_new.f90:356-357). "
        "Reading that alat returns the starting lattice constant. Only with "
        "cell_dofree='ibrav' (and ibrav not 0) does pw.x print the relaxed "
        "celldm(1), at every step through remake_cell "
        "(q-e/PW/src/move_ions.f90:163, q-e/Modules/latgen.f90:755-756). For "
        "ibrav 1, 2 and 3 that number is a_lat in bohr, a cross-check. a_lat "
        "comes from the vectors: with "
        "V_cell the volume of the final simulation cell, N_cell its atom "
        "count and N_conv the atom count of the conventional cubic cell from "
        "a symmetry analysis of the final structure, a_lat = (V_cell N_conv / "
        "N_cell)^(1/3). For a primitive cell N_conv / N_cell is the lattice-"
        "point count 1, 2 or 4 of the P, I or F lattice, so it is not 4 in "
        "general. The vectors carry nine decimals, the volume line five, so "
        "the vectors are the more precise source. 1 bohr = 0.529177210903 A, "
        "the value pw.x 7.5 itself uses (q-e/Modules/constants.f90:38). "
        "Record a value only when three checks pass. (1) The relaxation "
        "converged. For cell_dynamics='bfgs' stdout prints 'bfgs converged "
        "in N scf cycles and M bfgs steps' (q-e/Modules/bfgs_module.f90:"
        "1114-1116) and never 'bfgs failed after' (:1109-1112). The final "
        "coordinates block alone is no evidence: after a failure bfgs also "
        "sets its converged flag (:388-394) and move_ions prints the block "
        "(q-e/PW/src/move_ions.f90:262). For the same reason the XML "
        "optimization flag (q-e/PW/src/pw_restart_new.f90:310-315) does not "
        "separate the two, while the exit status does: 3 when the optimizer "
        "failed, 0 otherwise (q-e/PW/src/run_pwscf.f90:343-351). Damped cell "
        "dynamics print their own convergence line. (2) The final structure "
        "is cubic, its space group 195 to 230 at a stated symmetry "
        "tolerance. (3) The final SCF agrees with the target. After "
        "convergence pw.x repeats the SCF with the G-vectors of the relaxed "
        "cell (q-e/PW/src/move_ions.f90:192-197). Its pressure P minus the "
        "target press is the Pulay stress of the fixed-basis relaxation, "
        "which a higher ecutwfc and ecutrho reduce, plus the residual the "
        "relaxation left, up to press_conv_thr. Record it, and refuse the "
        "value when it exceeds a stated tolerance."
    ),
)


# ---------------------------------------------------------------------------
# Operator-level spec (diagnostic: how pw.x performs the SCF solve)
# ---------------------------------------------------------------------------

QE_SOLVE_GROUND_STATE = OperatorRepresentationSpec(
    operator=solve_ground_state,
    representation_name="qe",
    discretization_choices={
        "ecutwfc": "plane-wave kinetic-energy cutoff for wavefunctions, Ry (ecutrho for the density, default 4x)",
        "k_mesh": "Monkhorst-Pack K_POINTS automatic grid nk1 x nk2 x nk3, optionally shifted",
        "smearing": "occupations: fixed for insulators; smearing (gaussian / mp / mv / fd) with degauss for metals",
        "conv_thr": "SCF self-consistency threshold on the estimated energy error, Ry (electron_maxstep bounds iterations)",
        "pseudopotentials": "UPF files from pseudo_dir per ATOMIC_SPECIES; the XC functional is read from the UPFs unless input_dft overrides",
    },
    notes=(
        "pw.x realizes solve_ground_state as a plane-wave pseudopotential "
        "Kohn-Sham SCF loop. The Potential input's provenance for a QE run "
        "is exactly the pseudopotential set + XC functional + cutoffs "
        "(matching the thermal-domain QE_POTENTIAL note): two runs differing "
        "in any of these realize different Potentials, so instances must "
        "record them in the conditions. The k-mesh, smearing, and conv_thr "
        "are discretization choices of the solve itself: they change how "
        "accurately E_KS is minimized, not what E_KS is."
    ),
)


QE_RELAX_CUBIC_LATTICE_PARAMETER = OperatorRepresentationSpec(
    operator=relax_cubic_lattice_parameter,
    representation_name="qe",
    discretization_choices={
        "calculation": "vc-relax, the variable-cell relaxation. relax keeps the cell and scf moves nothing, so neither records a lattice parameter",
        "cell_dynamics": "bfgs (default for vc-relax, with ion_dynamics bfgs) or damped dynamics damp-pr / damp-w, whose convergence line differs",
        "cell_dofree": "cell degrees of freedom that move: all (default), ibrav (keeps the input Bravais lattice, no effect when ibrav=0), volume (only the scale changes, allowed only for ibrav=1) and others",
        "press": "target pressure, kbar (default 0)",
        "press_conv_thr": "convergence threshold on the pressure, kbar (default 0.5)",
        "forc_conv_thr": "force threshold of the ionic steps, Ry/bohr (default 1.0D-3)",
        "etot_conv_thr": "energy threshold between ionic steps, Ry (default 1.0D-4)",
        "ecutwfc": "wavefunction cutoff, Ry, with ecutrho for the density: fixed-basis relaxation leaves a Pulay stress that falls as they rise",
        "k_mesh": "Monkhorst-Pack K_POINTS grid, as for solve_ground_state",
        "smearing": "occupations and degauss, as for solve_ground_state",
    },
    notes=(
        "pw.x realizes relax_cubic_lattice_parameter as calculation="
        "'vc-relax': ionic and cell steps until energy, force and pressure "
        "meet their thresholds (defaults from q-e/PW/Doc/INPUT_PW.def at "
        "qe-7.5), then a final SCF with the G-vectors of the relaxed cell. "
        "pw.x symmetrizes forces and stress with the symmetry operations it "
        "found for the input structure and kept, so the relaxation keeps "
        "them, and the result is a stationary point within that symmetry, "
        "not a proof of stability. The kept set can be smaller than the "
        "space group: nosym and noinv remove operations, a "
        "starting_magnetization pattern lowers them, and fractional "
        "translations incommensurate with the FFT grid are dropped. Hence "
        "the check on the final structure. cell_dofree='volume' stops with "
        "an error unless ibrav=1 (q-e/Modules/cell_base.f90:753-755), and "
        "'ibrav' does nothing when ibrav=0 (q-e/Modules/latgen.f90:749-751). "
        "Instances record the Potential's provenance as for "
        "solve_ground_state, and in the conditions press, press_conv_thr, "
        "cell_dofree, cell_dynamics, nosym and noinv, ecutwfc, ecutrho, the "
        "k-mesh, the smearing and degauss, the final-SCF pressure and its "
        "tolerance, and the space group found with its symmetry tolerance."
    ),
)
