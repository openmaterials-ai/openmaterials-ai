"""Per-code adapter specs for the composites (effective-medium) domain.

Each submodule holds the SpaceRepresentationSpec instances for one code,
constructed against the shared operator DAG in `omai.composites.operator` so
cross-code agreement is checked at the operator level (per Principle 7).

The composite effective-medium formulas (Nan-EMT, with the Hasselman-Johnson
spherical-limit cross-check) live in the operator layer itself: the map's own
closed-form edges are the reference. No external code representation is
registered for them; the library's own evaluators are, as the representation
openmaterials-ai. Committed composite evidence keeps its provenance in each
instance's source ref.

  * `gpumd`: InterfaceConductance[transport_model=nemd] from direct
    two-reservoir NEMD.
  * `openmaterials_ai`: the two Nan nodes, random orientation and the aligned
    al33, through omai.composites.evaluate.
"""
