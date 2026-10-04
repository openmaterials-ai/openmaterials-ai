"""Analog-device-metrology operator DAG: re-exports the domain's NODES and EDGES.

Importing this package registers the domain's formula-symbol vocabulary and its
symbol-dimension bindings as side effects (mirroring the electronic-transport /
thermodynamic-identities / mechanics / thermochemistry packages), so validate_dag
and the dimensional gate see this domain's symbols. Here the side effect is
load-bearing for the five closed-form edges: their field-symbol dimension
bindings must be live before the dimensional gate runs so the formulas are
proven, not skipped.
"""
# ruff: noqa: F401  (dimensions_registry / vocabulary are imported for their
# import-time registration side effects; they are intentionally unused names.)
from omai.analog_device_metrology.operator import dimensions_registry, vocabulary
from omai.analog_device_metrology.operator.edges import EDGES
from omai.analog_device_metrology.operator.nodes import NODES

__all__ = ["NODES", "EDGES"]
