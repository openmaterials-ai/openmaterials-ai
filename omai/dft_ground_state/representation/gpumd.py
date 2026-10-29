"""gpumd adapter specs for the held-out fit errors of a fitted potential.

GPUMD's `nep` executable (https://github.com/brucefan1983/GPUMD, read at v4.7:
src/main_nep/snes.cu, fitness.cu, dataset.cu, structure.cu) evaluates a trained
nep.txt on labelled structures. With `prediction 1` added to the nep.in used for
training it reads the nep.txt weights and writes, for the structures in
train.xyz, energy_train.out (predicted and reference energy per atom),
force_train.out (3 predicted and 3 reference force components per atom) and
virial_train.out (6 predicted and 6 reference virial components per atom).
Putting the held-out set in train.xyz therefore gives the held-out errors. Each
value is the raw RMSE over the predicted/reference pairs: the written energies
carry no offset removal.
"""

from __future__ import annotations

from omai.dft_ground_state.operator.nodes import (
    POTENTIAL_ENERGY_FIT_ERROR,
    POTENTIAL_FORCE_FIT_ERROR,
    POTENTIAL_VIRIAL_FIT_ERROR,
)
from omai.representation.adapter import SpaceRepresentationSpec

_ROUTES = (
    "Prediction route: the nep.in used for training with `prediction 1` "
    "added (v4.7 takes the type order and descriptor hyperparameters from "
    "nep.in, not from the nep.txt header), the trained nep.txt, and the "
    "held-out set as train.xyz. Training-run route, with the held-out set as "
    "test.xyz: energy_test.out, force_test.out and virial_test.out from the "
    "last 100-generation report hold the same RMSEs for that report's "
    "nep.txt, and so do loss.out columns 8-10 of the last row "
    "(RMSE-E/F/V-Test, energy without offset removal) when no test.xyz frame "
    "sets energy_weight. loss.out columns 5-7 are training-set errors "
    "(energy after removal of the mean per-atom offset) and are not this node."
)

GPUMD_POTENTIAL_ENERGY_FIT_ERROR = SpaceRepresentationSpec(
    space=POTENTIAL_ENERGY_FIT_ERROR,
    representation_name="gpumd",
    observable_units={"rmse_E": "ev_per_atom"},
    code_api={
        "rmse_E": "nep, prediction 1 added to the training nep.in, held-out set as train.xyz: energy_train.out, RMSE of column 1 (predicted) vs column 2 (reference), eV/atom",
    },
    notes=_ROUTES,
)

GPUMD_POTENTIAL_FORCE_FIT_ERROR = SpaceRepresentationSpec(
    space=POTENTIAL_FORCE_FIT_ERROR,
    representation_name="gpumd",
    observable_units={"rmse_F": "eV_per_A"},
    code_api={
        "rmse_F": "nep, prediction 1 added to the training nep.in, held-out set as train.xyz: force_train.out, RMSE over the 3 pairs (columns 1-3 predicted vs 4-6 reference) of every row, eV/A",
    },
    notes=_ROUTES,
)

GPUMD_POTENTIAL_VIRIAL_FIT_ERROR = SpaceRepresentationSpec(
    space=POTENTIAL_VIRIAL_FIT_ERROR,
    representation_name="gpumd",
    observable_units={"rmse_W": "ev_per_atom"},
    code_api={
        "rmse_W": "nep, prediction 1 added to the training nep.in, held-out set as train.xyz: virial_train.out, RMSE over the 6 pairs (columns 1-6 predicted vs 7-12 reference), skipping rows whose reference is -1e6 (structure without a virial or stress label), eV/atom",
    },
    notes=_ROUTES,
)
