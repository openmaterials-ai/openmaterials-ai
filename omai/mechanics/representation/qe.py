"""Quantum ESPRESSO adapter specs for the mechanics domain.

One row. ev.x (PW/tools/ev.f90, built by `make pw` in QE 7.5) fits total
energies pw.x computed at several volumes to an equation of state and prints
the bulk modulus: the compute_bulk_modulus_eos route of BulkModulus.

  operator Space  QE artifact                                        program
  --------------  -------------------------------------------------  -------
  BulkModulus     <BULK_MODULUS_KBAR> (XML output; full precision)   ev.x

ElasticConstants has no QE row: the strain-stress fit is a code-agnostic step
the pymatgen representation already carries (ElasticTensor.from_independent_strains);
QE contributes the stresses through its Stress row.
"""

from __future__ import annotations

from omai.representation.adapter import (
    OperatorRepresentationSpec,
    SpaceRepresentationSpec,
)
from omai.mechanics.operator.edges import compute_bulk_modulus_eos
from omai.mechanics.operator.nodes import BULK_MODULUS


QE_BULK_MODULUS = SpaceRepresentationSpec(
    space=BULK_MODULUS,
    representation_name="qe",
    observable_units={"K": "kbar"},
    code_api={
        "K": "ev.x <BULK_MODULUS_KBAR> (XML output of the E(V) fit of pw.x energies), kbar",
    },
    notes=(
        "ev.x (q-e/PW/tools/ev.f90) reads lattice-parameter-or-volume and "
        "total-energy pairs from pw.x runs at several volumes and fits the "
        "equation of state chosen at its prompt (istat in ev.f90): 1 is "
        "third-order Birch-Murnaghan "
        "(V0, K0, K0'; the method=birch_murnaghan scheme), 2 adds K0'' "
        "(fourth order), 3 Keane, 4 Murnaghan. The text header labels types 1 "
        "and 2 'birch 1st order' and 'birch 3rd order', the XML 'Birch 1st "
        "order' and 'Birch 2nd order'. The header prints k0 in kbar (truncated "
        "to an integer) and in GPa whatever the input units; "
        "<BULK_MODULUS_KBAR> in the XML output carries full precision and is "
        "the value to read. The EOS and the volume set are run conditions a "
        "lineage must record."
    ),
)


QE_COMPUTE_BULK_MODULUS_EOS = OperatorRepresentationSpec(
    operator=compute_bulk_modulus_eos,
    representation_name="qe",
    scheme_overrides={"method": "birch_murnaghan", "n_points": "user_volume_set"},
    discretization_choices={
        "volume_scan_grid": "the pw.x runs supplied as input; no fixed count",
    },
    notes=(
        "ev.x is a fit over energies pw.x computed elsewhere. This spec is "
        "EOS type 1 at the ev.x prompt (istat=1), third-order "
        "Birch-Murnaghan (the canonical method); types 2, "
        "3 and 4 change what is computed and need a per-run spec. The volume "
        "set is whatever was computed, recorded on the lineage."
    ),
)
