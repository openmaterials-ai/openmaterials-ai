"""The renderers moved from MCG produce the instances they always produced.

The field-by-field expectations here are the ones MCG's own render tests held
(mcg/tests/tools/openmaterials/), so a move that changed an output would fail
rather than quietly reshape evidence already committed to the map.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from omai.render import (
    KAPPA_NODE,
    Instance,
    Source,
    kj_per_mol_to_ev,
    provenance,
    render_kappa,
    render_molar_cp,
    render_reaction_energy,
    slugify,
)

MAP_VERSION = "9802d9e854c915eb47d867575730a556ab7f4a565e392bf5b29da58338f08434"


def kappa(**over) -> dict:
    base = {"method": "hnemd", "material_name": "Si", "temperature_K": 300.0,
            "n_seeds": 4, "code": "GPUMD", "kappa_W_per_mK": 137.5,
            "kappa_std_W_per_mK": 4.2}
    base.update(over)
    return base


def test_render_kappa_full_instance_shape():
    inst = render_kappa(kappa(), run_ref="run-ref-xyz", potential="Si-NEP",
                        map_version=MAP_VERSION)
    assert inst.variable == "ThermalConductivity[transport_model=hnemd]"
    assert inst.material == "Si"
    assert inst.conditions == {"T": "300 K", "method": "hnemd", "n_seeds": 4,
                               "code": "GPUMD", "potential": "Si-NEP"}
    assert inst.value == 137.5
    assert inst.units == "W/(m K)"
    assert inst.uncertainty == 4.2
    assert inst.source.kind == "simulation"
    assert inst.source.ref == "materialscodegraph-run-ref-xyz"
    assert MAP_VERSION in inst.source.detail
    assert inst.source.detail.startswith("Bulk Si kappa (HNEMD, ")


def test_render_kappa_variable_follows_the_method():
    for method, node in KAPPA_NODE.items():
        inst = render_kappa(kappa(method=method), run_ref="r")
        assert inst.variable == node


def test_render_kappa_refuses_a_method_the_map_does_not_model():
    # Rerouting nemd onto another node would be a provenance lie.
    with pytest.raises(KeyError):
        render_kappa(kappa(method="nemd"), run_ref="r")


def test_render_kappa_uncertainty_is_none_when_std_is_absent_or_zero():
    assert render_kappa(kappa(kappa_std_W_per_mK=None),
                        run_ref="r").uncertainty is None
    assert render_kappa(kappa(kappa_std_W_per_mK=0),
                        run_ref="r").uncertainty is None


def test_render_kappa_omits_the_uncertainty_key_when_there_is_no_spread():
    # The served records carry no "uncertainty": null. A single-seed run
    # reports std 0, which is not a claim of exactness.
    d = render_kappa(kappa(kappa_std_W_per_mK=0), run_ref="r").to_json_dict()
    assert "uncertainty" not in d
    assert render_kappa(kappa(), run_ref="r").to_json_dict()["uncertainty"] == 4.2


def test_render_kappa_detail_prints_none_for_an_absent_spread():
    # The worker prints "+/- None", not "+/- 0", and the served bytes have it.
    detail = render_kappa(kappa(kappa_std_W_per_mK=0), run_ref="r").source.detail
    assert "+/- None W/(m K)" in detail
    assert "+/- 4.2 W/(m K)" in render_kappa(kappa(), run_ref="r").source.detail


def test_render_kappa_without_a_run_ref_is_the_served_platform_form():
    # What a public share page carries: no run identity anywhere.
    inst = render_kappa(kappa(), map_version=MAP_VERSION)
    assert inst.source.ref == "materialscodegraph"
    assert "MaterialsCodeGraph run;" in inst.source.detail
    assert "run-ref" not in inst.source.detail


def test_render_kappa_with_a_run_ref_keeps_the_commons_form():
    # Still available: the committed instances under docs/data/instances/ use
    # it (materialscodegraph-dgeba-cp300-gfn2 and friends).
    inst = render_kappa(kappa(), run_ref="dgeba-cp300-gfn2")
    assert inst.source.ref == "materialscodegraph-dgeba-cp300-gfn2"
    assert "MaterialsCodeGraph run dgeba-cp300-gfn2;" in inst.source.detail


def test_render_kappa_code_defaults_to_gpumd():
    result = kappa()
    del result["code"]
    assert render_kappa(result, run_ref="r").conditions["code"] == "GPUMD"


def test_render_kappa_formats_a_fractional_temperature_like_python_g():
    inst = render_kappa(kappa(temperature_K=301.5), run_ref="r")
    assert inst.conditions["T"] == "301.5 K"


def test_render_kappa_accepts_an_object_with_the_same_fields():
    # The MCG call sites pass a pydantic result object; attribute access must
    # work exactly as the dict does.
    @dataclass
    class KappaResult:
        method: str = "hnemd"
        material_name: str = "Si"
        temperature_K: float = 300.0
        n_seeds: int = 4
        code: str = "GPUMD"
        kappa_W_per_mK: float = 137.5
        kappa_std_W_per_mK: float | None = 4.2

    assert (render_kappa(KappaResult(), run_ref="r").to_json_dict()
            == render_kappa(kappa(), run_ref="r").to_json_dict())


def cp_result(**over) -> dict:
    base = {"molecule_name": "C21H24O4 (DGEBA)",
            "cp_temperatures_K": [200.0, 250.0, 300.0, 350.0],
            "cp_harmonic_J_per_molK": [301.2, 350.9, 397.7, 442.1],
            "n_imaginary": 0}
    base.update(over)
    return base


def test_render_molar_cp_picks_the_grid_temperature():
    inst = render_molar_cp(cp_result(), run_ref="dgeba-cp300-gfn2", at_K=300.0,
                           map_version=MAP_VERSION)
    assert inst.variable == "MolarHeatCapacity"
    assert inst.material == "C21H24O4 (DGEBA)"
    assert inst.value == 397.7
    assert inst.units == "J/(K mol)"
    assert inst.uncertainty is None
    assert inst.conditions == {"T": "300 K", "phase": "gas",
                               "approximation": "harmonic (RRHO)",
                               "model": "GFN2-xTB", "n_imaginary": 0}
    assert MAP_VERSION in inst.source.detail


def test_render_molar_cp_refuses_an_off_grid_temperature():
    # Interpolating silently would misstate what was computed.
    with pytest.raises(ValueError, match="not on the Cp grid"):
        render_molar_cp(cp_result(), run_ref="r", at_K=275.0)


def test_render_molar_cp_material_label_overrides_the_molecule_name():
    inst = render_molar_cp(cp_result(), run_ref="r", material_label="DGEBA")
    assert inst.material == "DGEBA"
    # The detail still names the molecule that was computed.
    assert "C21H24O4 (DGEBA)" in inst.source.detail


def reaction(**over) -> dict:
    base = {"reaction_name": "glycidyl phenyl ether + aniline -> "
                             "1-(phenylamino)-3-phenoxy-2-propanol",
            "dh298_kJ_per_mol": -106.3, "de_elec_kJ_per_mol": -98.4}
    base.update(over)
    return base


def test_render_reaction_energy_converts_to_ev_per_event():
    inst = render_reaction_energy(reaction(), run_ref="r",
                                  material="C9H10O2 (glycidyl phenyl ether)",
                                  map_version=MAP_VERSION)
    assert inst.variable == "ReactionEnergy"
    assert inst.units == "eV"
    # The commons conformance target pins this exact number.
    assert inst.value == -1.101722
    assert inst.conditions["dh298_kJ_per_mol"] == -106.3
    assert inst.conditions["de_elec_kJ_per_mol"] == -98.4
    assert inst.conditions["normalization"] == "per_reaction_event"
    assert inst.conditions["T"] == "298.15 K"


def test_render_reaction_energy_methylamine_matches_the_commons_target():
    inst = render_reaction_energy(
        reaction(reaction_name="glycidyl phenyl ether + methylamine -> "
                               "1-(methylamino)-3-phenoxy-2-propanol",
                 dh298_kJ_per_mol=-116.1),
        run_ref="r", material="C9H10O2 (glycidyl phenyl ether)")
    assert inst.value == -1.203292


def test_kj_per_mol_to_ev_is_the_codata_constant():
    assert kj_per_mol_to_ev(96.48533212331) == 1.0


def test_provenance_without_a_run_ref_names_no_run():
    src = provenance(what="Something from a", map_version="abc123")
    assert src.ref == "materialscodegraph"
    assert src.detail == ("Something from a MaterialsCodeGraph run; "
                          "rendered against openmaterials map version abc123.")


def test_provenance_stamps_the_map_version_and_slugs_the_ref():
    src = provenance("Run Ref XYZ", "Something from a", map_version="abc123")
    assert isinstance(src, Source)
    assert src.kind == "simulation"
    assert src.ref == "materialscodegraph-run-ref-xyz"
    assert src.detail == ("Something from a MaterialsCodeGraph run Run Ref XYZ; "
                          "rendered against openmaterials map version abc123.")


def test_provenance_says_unknown_when_no_map_version_is_given():
    # An instance must state what it was rendered against; "unknown" says so
    # rather than implying a pin that was never made.
    assert "map version unknown." in provenance("r", "x").detail


def test_instance_to_json_dict_omits_absent_optional_keys():
    inst = Instance(variable="Frequency", material="Si", conditions={},
                    units="THz", source=provenance("r", "x"))
    d = inst.to_json_dict()
    assert "value" not in d
    assert "artifact" not in d
    assert "uncertainty" not in d


def test_instance_filename_is_the_map_kebab_convention():
    inst = render_kappa(kappa(), run_ref="run-ref-xyz")
    assert inst.filename() == (
        "si-thermalconductivity-transport-model-hnemd-"
        "materialscodegraph-run-ref-xyz.json")


def test_slugify_collapses_non_alphanumeric_runs():
    assert slugify("C21H24O4 (DGEBA)") == "c21h24o4-dgeba"
    assert slugify("") == ""
