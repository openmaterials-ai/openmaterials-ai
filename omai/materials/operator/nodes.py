r"""Operator nodes for the materials domain (grown from AtomisticSkills).

Node table:

  Node                                   quantity tag             dimension                indices
  -------------------------------------  -----------------------  -----------------------  -------
  Diffusivity                            diffusivity              DIFFUSIVITY              ()
  ActivationEnergy                       activation_energy        ENERGY                   ()
  ElectricalConductivity[carrier=ionic]  electrical_conductivity  ELECTRICAL_CONDUCTIVITY  ()
  ConfigurationalEnergy                  configurational_energy   ENERGY                   ()
  CarrierDensity                         carrier_density          NUMBER_DENSITY           ()
  MigrationBarrier                       migration_barrier        ENERGY                   ()
  MigrationPrefactor[method=harmonic_tst]  migration_prefactor    FREQUENCY                ()

MigrationPrefactor[method=harmonic_tst] (2026-11-15) is the prefactor nu* that
pairs with MigrationBarrier in one hop's rate nu* exp(-E_m / k_B T): the
Vineyard ratio of the normal-mode frequencies at the minimum and at the saddle,
in the classical high-temperature limit. The method label keeps it apart from a
prefactor fitted to measured rates, which is not this quantity.

CarrierDensity arrives from the physics review (2026-07-10, second supersede):
the L^-3 mobile-carrier number density n_c that makes the Nernst-Einstein ionic
conductivity executable (sigma = n_c z^2 e^2 D / (k_B T)). NEW dimension
NUMBER_DENSITY (0,-3,0,0,0,0,0) = 1/m^3, a pure inverse-volume. In the Diffusion
tier alongside Diffusivity and the ionic conductivity it feeds.

ElectricalConductivity[carrier=ionic] and ConfigurationalEnergy arrive from the
config-thermo scan (AtomisticSkills arXiv 2605.24002: pymatgen-analysis-diffusion
and smol).

The electric-current axis in the diffusion slice. ElectricalConductivity carries
the fresh ELECTRICAL_CONDUCTIVITY dimension (M=-1,L=-3,T=3,Theta=0,N=0,I=2,J=0),
the map's first I=+2 node and the first electric-current-axis node in the
diffusion slice (the materials-side Voltage at I=-1 already opened the axis, so
it is NOT the first current-axis node overall). It is EMPHATICALLY NOT the
thermal-transport ThermalConductivity (1,1,-3,-1,0,0,0): different L and T signs,
an I axis instead of a Theta axis, a distinct quantity that shares only the
English word "conductivity". The Nernst-Einstein ionic conductivity and the
already-mapped Diffusivity differ only by the number-density x z^2 e^2 / (k_B T)
conversion factor, so they are companions on the same axis.

The carrier label. The node is ElectricalConductivity[carrier=ionic]: the
carrier label (a new registered LABEL_KEY, collision-free against order,
bte_solver, transport_model, channel, wrt) keeps the ionic conductivity distinct
from the electronic sibling (carrier=electronic) that will join the same
ElectricalConductivity family from amset. Same tag and dimension, distinct nodes
only by the carrier label. Served scalar here (the skills report the scalar
extrapolated sigma_RT); the rank-2 tensor generalization sigma_{alpha,beta}
(conductivity_components) is a representation-layer packing, noted but not the
node's index signature.

ConfigurationalEnergy is a lattice-model (cluster-expansion) energy: plain ENERGY
(1,2,-2,0,0,0,0), the same exponent vector as TotalEnergy and FormationEnergy but
a DISTINCT quantity kept apart by the configurational_energy tag. It is the
energy smol's ClusterExpansion predicts for a configuration on a FIXED lattice
and FIXED cell (relax_cell=False), reference-shifted by the training set (total or
formation energy), NOT a relaxed-structure DFT/MLIP TotalEnergy and NOT a
per-atom FormationEnergy. The basis is a per-instance caveat (extensive per
supercell, per primitive cell with normalized=True, or per atom as the GCMC skill
reports), as is the ECI reference convention; both ride in the description and
instance conditions, not the dimension. The cluster-expansion checkpoint that
predicts it is a Potential-representation analog (an MLIP-checkpoint sibling),
recorded on the producing edge, not minted as a node here.
"""
from __future__ import annotations

from omai.operator.dimensions import (
    DIFFUSIVITY,
    ELECTRICAL_CONDUCTIVITY,
    ENERGY,
    FREQUENCY,
    NUMBER_DENSITY,
)
from omai.operator.space import Field, ObservableSpace, Space

DIFFUSIVITY_STATE = ObservableSpace(
    name="Diffusivity",
    fields=(Field("D", DIFFUSIVITY, indices=()),),
    description=(
        "Self-diffusion coefficient D from the Einstein relation "
        "MSD(t) = 2 d D t in the linear regime. Produced from "
        "MeanSquaredDisplacement; per temperature."
    ),
    tier="Diffusion",
)

ACTIVATION_ENERGY = ObservableSpace(
    name="ActivationEnergy",
    fields=(Field("E_a", ENERGY, indices=()),),
    description=(
        "Arrhenius activation energy E_a from D(T) = D0 exp(-E_a/k_B T), "
        "obtained by a weighted fit over diffusivities at several temperatures."
    ),
    tier="Diffusion",
)

MIGRATION_BARRIER = ObservableSpace(
    name="MigrationBarrier",
    fields=(Field("E_m", ENERGY, indices=()),),
    tier="Diffusion",
    description=(
        "Migration barrier E_m of one defect or ion hop in a solid: the energy "
        "from the initial minimum to the saddle point along the hop's path, the "
        "activation energy of its transition-state-theory rate nu* exp(-E_m / "
        "k_B T). ENERGY. The species and charge state, the path and direction, "
        "the site (bulk, grain boundary, surface, contact) and the source "
        "(nudged elastic band, fit to measured rates, calibrated model) ride in "
        "instance conditions. For diffusion by this one mechanism at fixed "
        "defect density it equals the diffusivity's ActivationEnergy; a "
        "formation term or a second mechanism makes them differ. Molecular "
        "reaction barriers are ReactionBarrier. The prefactor of the same rate, "
        "in classical harmonic transition-state theory, is "
        "MigrationPrefactor[method=harmonic_tst]; an (E_m, nu*) pair of one hop "
        "shares its conditions."
    ),
)

MIGRATION_PREFACTOR = ObservableSpace(
    name="MigrationPrefactor[method=harmonic_tst]",
    fields=(Field("nu_star", FREQUENCY, indices=()),),
    labels={"method": "harmonic_tst"},
    tier="Diffusion",
    description=(
        "Prefactor nu* of the rate nu* exp(-E_m / k_B T) of one defect or ion "
        "hop in a solid, in classical harmonic transition-state theory at fixed "
        "cell (Vineyard, J. Phys. Chem. Solids 3, 121 (1957)): nu* = prod_{i=1..n} "
        "nu_i(min) / prod_{j=1..n-1} nu_j(saddle), the ratio of the cyclic "
        "normal-mode frequencies at the initial minimum and at the first-order "
        "saddle, the saddle's one imaginary mode excluded. FREQUENCY, linear THz "
        "canonical. With every atom displaced, bulk or slab, the three rigid "
        "translations are projected out and n = 3N - 3. A value from a listed "
        "subset of M atoms displaced with the rest held, none projected, n = 3M, "
        "approximates the full ratio, and its saddle order is checked only within "
        "that subspace. It is the classical high-temperature limit, valid for "
        "k_B T >> h nu_i over the modes that change between the minimum and the "
        "saddle; zero-point and Wigner corrections are excluded. Tunnelling "
        "dominates below the crossover temperature h |nu_imag| / (2 pi k_B), so "
        "being above it is necessary, not sufficient. It is per single path, so "
        "it excludes the count z of equivalent paths. In the Wert-Zener split "
        "nu* = nu exp(S_m / k_B), nu is one mode at the minimum along the hop and "
        "S_m = k_B sum_j ln(nu_j(min) / nu_j(saddle)) over the other n - 1 modes; "
        "the split is not unique, and nu* includes the entropy factor. "
        "MigrationBarrier E_m is its pair, and the two share the hop's "
        "conditions. Required conditions: the hop (species and charge state, "
        "path, direction, site), the potential, the cell, the displaced atom set "
        "and M, the masses, the finite-difference step, the imaginary-mode floor "
        "and the residual force of both frames; the error bound of ln nu* when "
        "the eigenvalue noise is known. A prefactor fitted to measured rates is "
        "not this node: it absorbs the path count, anharmonicity, recrossing and "
        "the error of its own barrier. Distinct from the diffusivity prefactor "
        "D_0 = z a^2 f nu* / (2 d), which also carries the jump length, the "
        "correlation factor and, for thermal defects, the formation entropy."
    ),
)

ELECTRICAL_CONDUCTIVITY_IONIC = ObservableSpace(
    name="ElectricalConductivity[carrier=ionic]",
    fields=(Field("sigma", ELECTRICAL_CONDUCTIVITY, indices=()),),
    labels={"carrier": "ionic"},
    description=(
        "Ionic electrical conductivity sigma from the Nernst-Einstein "
        "relation on the tracer diffusivity: sigma = (n/V) z^2 e^2 D / (k_B T), "
        "with the number density n/V, the squared ionic charge z^2 (oxidation "
        "state, else valence-electron count), the electron charge e, over the "
        "thermal energy k_B T. It assumes a HAVEN RATIO OF 1 (the tracer, not "
        "the collective charge, diffusivity drives it; the charge-diffusivity "
        "conductivity is a separate quantity). Dimension ELECTRICAL_CONDUCTIVITY "
        "(M=-1,L=-3,T=3,Theta=0,N=0,I=2,J=0), the S/m of siemens per metre; "
        "served here as the scalar extrapolated sigma_RT (300 K), with the "
        "rank-2 tensor sigma_{alpha,beta} generalization (conductivity "
        "components) a representation-layer packing. The map's first I=+2 node "
        "and the first electric-current-axis node in the diffusion slice (NOT "
        "the first current-axis node overall: Voltage at I=-1 precedes it), and "
        "EMPHATICALLY NOT ThermalConductivity (they share only the word "
        "'conductivity'). The carrier=ionic label keeps it distinct from the "
        "electronic sibling that will join the same ElectricalConductivity "
        "family from amset. A companion of Diffusivity (differing only by the "
        "conversion factor)."
    ),
    tier="Diffusion",
)

CARRIER_DENSITY = ObservableSpace(
    name="CarrierDensity",
    fields=(Field("n_c", NUMBER_DENSITY, indices=()),),
    description=(
        "Mobile-carrier number density n_c: the count of mobile charge "
        "carriers (the diffusing ionic species) per unit volume, the L^-3 "
        "quantity n/V that the Nernst-Einstein conductivity multiplies. NEW "
        "dimension NUMBER_DENSITY (0,-3,0,0,0,0,0) = 1/m^3, a pure "
        "inverse-volume (the count is dimensionless). It is the input the "
        "physics review found the map needed to make the Nernst-Einstein "
        "ionic conductivity EXECUTABLE: sigma = n_c z^2 e^2 D / (k_B T), with "
        "n_c now a first-class node rather than a Structure-derived opaque "
        "factor. Counted as (mobile species per cell) / (cell volume), so it "
        "rides the same Structure the diffusivity does; which species count as "
        "mobile is an opaque selector recorded on the producing edge, not in "
        "this scalar node. Served in per_m3 (canonical) or per_cm3 (1e6 "
        "factor). In the Diffusion tier alongside Diffusivity and the ionic "
        "conductivity it feeds."
    ),
    tier="Diffusion",
)

CONFIGURATIONAL_ENERGY = ObservableSpace(
    name="ConfigurationalEnergy",
    fields=(Field("E_cfg", ENERGY, indices=()),),
    description=(
        "Lattice-model energy of a configuration predicted by a cluster "
        "expansion: E = dot(coefs, correlations), the configurational-"
        "energetics analog of an MLIP potential energy on a structure. On a "
        "FIXED lattice and FIXED cell (relax_cell=False), reference-shifted by "
        "the training set (a total or a formation energy), so NOT a "
        "relaxed-structure DFT/MLIP TotalEnergy and NOT a per-atom "
        "FormationEnergy despite sharing the plain ENERGY dimension "
        "(1,2,-2,0,0,0,0); kept a distinct node by the configurational_energy "
        "quantity tag. BASIS is a per-instance caveat: extensive per supercell "
        "(processor.compute_property / predict default), per primitive cell "
        "(predict normalized=True, CV-RMSE in eV/prim), or per atom (eV/atom, "
        "what the grand-canonical-MC skill divides to report); which basis and "
        "which ECI training-energy reference an instance uses ride in the "
        "conditions, not the dimension. The cluster-expansion checkpoint that "
        "predicts it is a Potential-representation analog (the smol representation records "
        "it as an MLIP-checkpoint sibling), not minted as a node here."
    ),
    tier="Diffusion",
)

NODES: tuple[Space, ...] = (
    DIFFUSIVITY_STATE,
    ACTIVATION_ENERGY,
    MIGRATION_BARRIER,
    MIGRATION_PREFACTOR,
    ELECTRICAL_CONDUCTIVITY_IONIC,
    CONFIGURATIONAL_ENERGY,
    CARRIER_DENSITY,
)
