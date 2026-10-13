"""The renderers moved from MCG produce the instances they always produced.

The field-by-field expectations here are the ones MCG's own render tests held
(mcg/tests/tools/openmaterials/), so a move that changed an output would fail
rather than quietly reshape evidence already committed to the map.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from omai.lineages import lineage_id
from omai.render import (
    KAPPA_NODE,
    Instance,
    Source,
    _sig4,
    kj_per_mol_to_ev,
    provenance,
    render_composite_kappa,
    render_cure_conversion,
    render_glass_transition,
    render_interface_conductance,
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


def test_render_kappa_detail_drops_the_error_for_an_absent_spread():
    # 0.1.x printed "+/- None"; no spread now writes no "+/-" term.
    for std in (0, None):
        detail = render_kappa(kappa(kappa_std_W_per_mK=std), run_ref="r").source.detail
        assert "(HNEMD, 137.5 W/(m K) at 300 K" in detail
        assert "+/-" not in detail
    assert "+/- 4.2 W/(m K)" in render_kappa(kappa(), run_ref="r").source.detail


def test_sig4_is_plain_decimal_with_ties_half_up():
    # The platform's bytes: 4 significant figures, trailing zeros dropped.
    cases = {12345.6: "12350", 16.34999: "16.35", 0.41234567: "0.4123",
             120.25: "120.3", 16.125: "16.13", 137.5: "137.5", 300.0: "300",
             97.93078199999998: "97.93", 0.0: "0", -1.23456: "-1.235",
             9999.5: "10000", 0.000123456: "0.0001235"}
    for x, text in cases.items():
        assert _sig4(x) == text, x


def test_render_kappa_detail_writes_4_significant_figures():
    inst = render_kappa(kappa(kappa_W_per_mK=12345.6, kappa_std_W_per_mK=120.25))
    assert "(HNEMD, 12350 +/- 120.3 W/(m K) at 300 K" in inst.source.detail
    # The fields keep full precision.
    assert (inst.value, inst.uncertainty) == (12345.6, 120.25)


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
                          "rendered against openmaterials graph version abc123.")


def test_provenance_stamps_the_map_version_and_slugs_the_ref():
    src = provenance("Run Ref XYZ", "Something from a", map_version="abc123")
    assert isinstance(src, Source)
    assert src.kind == "simulation"
    assert src.ref == "materialscodegraph-run-ref-xyz"
    assert src.detail == ("Something from a MaterialsCodeGraph run Run Ref XYZ; "
                          "rendered against openmaterials graph version abc123.")


def test_provenance_says_unknown_when_no_map_version_is_given():
    # An instance must state what it was rendered against; "unknown" says so
    # rather than implying a pin that was never made.
    assert "graph version unknown." in provenance("r", "x").detail


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



# The composite inputs are the commons reference formulation's (its committed
# instance pins 1.2452); the aligned pair, the interface numbers and the rate-law
# constants are synthetic. The DiBenedetto constants are Rosetti et al.,
# Materials 11, 1960 (2018) (see test_cure_kinetics_domain.py).
_REFERENCE = next((Path(__file__).resolve().parents[1] / "docs" / "data" / "instances").glob(
    "dgeba-epoxy-5-vol-gnp-reference-formulation-*.json"))


def composite(**over) -> dict:
    base = {"composite_name": "DGEBA epoxy + 5 vol% GNP (reference formulation)",
            "method": "nan_emt_interfacial_series",
            "kappa_random_W_per_mK": 1.2452, "kappa_aligned_11_W_per_mK": 2.5,
            "kappa_aligned_33_W_per_mK": 0.25, "matrix_kappa_W_per_mK": 0.2,
            "filler": {"kappa_11_W_per_mK": 1200, "kappa_33_W_per_mK": 6,
                       "d1_um": 5, "d3_um": 0.02},
            "volume_fraction": 0.05, "interface_conductance_MW_per_m2K": 25,
            "kapitza_radius_nm": 8.0}
    base.update(over)
    return base


def test_composite_kappa_renders_the_committed_reference_conditions():
    # The committed b13e25c6 is a hand-written commons record the platform
    # cannot mint (its value sits in the lineage), so the check is on the
    # conditions, not on that id.
    inst = render_composite_kappa(composite(), map_version=MAP_VERSION)
    committed = json.loads(_REFERENCE.read_text())["lineage"]
    assert (inst.variable, inst.material) == (committed["node"], committed["material"])
    assert list(inst.conditions) == list(committed["conditions"])
    assert inst.conditions == committed["conditions"]
    assert all(isinstance(v, float) for k, v in inst.conditions.items()
               if k != "orientation")
    assert "uncertainty" not in inst.to_json_dict()
    assert "(Nan EMT, random orientation, f=0.05, 1.245 W/(m K))" in inst.source.detail


def test_composite_kappa_id_does_not_depend_on_number_typing():
    as_float = composite(filler={"kappa_11_W_per_mK": 1200.0, "kappa_33_W_per_mK": 6.0,
                                 "d1_um": 5.0, "d3_um": 0.02},
                         interface_conductance_MW_per_m2K=25.0)
    assert _id(render_composite_kappa(as_float)) == _id(render_composite_kappa(composite()))


def test_composite_kappa_refuses_an_unmodeled_method_or_a_missing_filler():
    with pytest.raises(KeyError):
        render_composite_kappa(composite(method="maxwell_garnett"))
    with pytest.raises(KeyError):
        render_composite_kappa(composite(filler=None))
    for key in ("kappa_11_W_per_mK", "kappa_33_W_per_mK", "d1_um", "d3_um"):
        filler = {k: v for k, v in composite()["filler"].items() if k != key}
        with pytest.raises(KeyError):
            render_composite_kappa(composite(filler=filler))


_TBC_INPUTS = ("lead_length_nm", "nx", "ny", "delta_T_K", "strain_pct_b")


def tbc(**over) -> dict:
    base = {"interface_name": "Si/Ge", "method": "nemd", "temperature_K": 300.0,
            "tbc_MW_per_m2K": 312.3456, "tbc_std_MW_per_m2K": 12.34567,
            "lead_length_nm": 4.4, "nx": 4, "ny": 4, "delta_T_K": 30.0,
            "strain_pct_b": 4.2}
    base.update(over)
    return base


def test_interface_conductance_renders_the_nemd_node_in_mw():
    inst = render_interface_conductance(tbc(), potential="NEP89",
                                        map_version=MAP_VERSION)
    assert inst.variable == "InterfaceConductance[transport_model=nemd]"
    assert (inst.material, inst.value, inst.units, inst.uncertainty) == (
        "Si/Ge", 312.3456, "MW/(m^2 K)", 12.34567)
    assert inst.conditions == {"T": "300 K", "method": "nemd", "potential": "NEP89",
                               "lead_length_nm": 4.4, "nx": 4, "ny": 4,
                               "delta_T_K": 30.0, "strain_pct_b": 4.2}
    assert ("Interface conductance of Si/Ge (NEMD, 312.3 +/- 12.35 MW/(m^2 K) "
            "at 300 K) from a") in inst.source.detail


def test_interface_conductance_requires_the_potential_and_the_run_inputs():
    with pytest.raises(TypeError):
        render_interface_conductance(tbc())
    with pytest.raises(KeyError):
        render_interface_conductance(tbc(), potential="")
    for key in _TBC_INPUTS:
        with pytest.raises(KeyError, match=key):
            render_interface_conductance(tbc(**{key: None}), potential="NEP89")


def test_interface_conductance_drops_an_absent_spread():
    for std in (0.0, None):
        inst = render_interface_conductance(tbc(tbc_std_MW_per_m2K=std),
                                            potential="NEP89")
        assert "uncertainty" not in inst.to_json_dict()
        assert "+/-" not in inst.source.detail


def test_interface_conductance_refuses_methods_the_map_does_not_model():
    for method in ("aemd", "neg_gk"):
        with pytest.raises(KeyError):
            render_interface_conductance(tbc(method=method), potential="NEP89")


_KAMAL = {"a1_pref_per_s": 1.0e5, "e1_J_per_mol": 7.0e4, "a2_pref_per_s": 1.0e6,
          "e2_J_per_mol": 6.0e4, "m": 0.5, "n": 1.5}


def cure(kinetics=None, **over) -> dict:
    base = {"schedule_name": "synthetic resin hold",
            "method": "kamal_dibenedetto_isothermal",
            "cure_temperature_K": 433.15, "hold_time_s": 3600.0, "alpha_0": 0.0,
            "kinetics": {**_KAMAL, "l_order": None, "amax_per_K": None,
                         "bmax": None, **(kinetics or {})},
            "tg": {"tg0_K": 262.35, "tg_inf_K": 489.15, "lam": 27 / 53},
            "kinetics_source": "explicit parameters from spec",
            "final_conversion": 0.912345, "final_tg_K": 453.1636,
            "vitrification_time_s": 2710.55}
    base.update(over)
    return base


def _id(inst) -> str:
    return lineage_id({"node": inst.variable, "material": inst.material,
                       "conditions": inst.conditions})


def test_cure_conversion_renders_the_kamal_sourour_hold():
    inst = render_cure_conversion(cure(), map_version=MAP_VERSION)
    assert inst.variable == "CureConversion"
    assert (inst.material, inst.value, inst.units) == (
        "synthetic resin hold", 0.912345, "dimensionless")
    # None dropped, keys sorted, floats as a lineage rounds them.
    digest = hashlib.sha256(json.dumps(_KAMAL, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    assert inst.conditions == {"method": "kamal_sourour", "T": "433.15 K",
                               "hold_time": "3600 s", "alpha_0": 0.0,
                               "kinetics_params_sha256": digest}
    assert "uncertainty" not in inst.to_json_dict()
    assert ("(Kamal-Sourour, 0.9123; vitrification at 2711 s, past which it is an "
            "upper bound for constants fit before vitrification)") in inst.source.detail
    assert "vitrification" not in render_cure_conversion(
        cure(vitrification_time_s=None)).source.detail


def test_cure_conversion_reads_the_parameters_never_the_method_label():
    same = render_cure_conversion(cure(method="anything", kinetics_source="kb: x"))
    assert same.to_json_dict() == render_cure_conversion(cure()).to_json_dict()
    as_object = cure(kinetics=None)
    as_object["kinetics"] = SimpleNamespace(**as_object["kinetics"])
    assert render_cure_conversion(as_object).conditions == render_cure_conversion(cure()).conditions


def test_cure_conversion_refuses_other_rate_laws_and_missing_parameters():
    for other in ({"l_order": 1.2}, {"amax_per_K": 0.05, "bmax": 20.0}):
        with pytest.raises(KeyError):
            render_cure_conversion(cure(kinetics=other))
    with pytest.raises(KeyError):
        render_cure_conversion(cure(kinetics={"m": None}))
    for key in ("kinetics", "alpha_0", "cure_temperature_K", "hold_time_s"):
        missing = {**cure(), key: None}
        with pytest.raises(KeyError):
            render_cure_conversion(missing)


def test_the_parameter_hash_is_unrounded_typed_and_keyed():
    def digest(**kinetics):
        return render_cure_conversion(cure(kinetics=kinetics)).conditions[
            "kinetics_params_sha256"]
    # Constants below the lineage rounding still separate.
    assert digest(a1_pref_per_s=2e-7) != digest(a1_pref_per_s=2e-7 + 1e-8)
    assert digest(m=2) == digest(m=2.0)
    assert digest(source="kb: a citation") == digest()


def test_cure_parameters_enter_the_id():
    base = render_cure_conversion(cure())
    other = render_cure_conversion(cure(kinetics={"a1_pref_per_s": 2.0e5}))
    assert other.value == base.value and _id(other) != _id(base)
    tg = render_glass_transition(cure())
    tg_other = render_glass_transition(cure(tg={"tg0_K": 262.35, "tg_inf_K": 489.15,
                                                "lam": 0.6}))
    assert tg_other.value == tg.value and _id(tg_other) != _id(tg)


def test_a_conversion_out_of_range_is_refused_by_both_cure_renderers():
    for render in (render_cure_conversion, render_glass_transition):
        for x in (-0.01, 1.2, float("nan")):
            with pytest.raises(ValueError, match="outside"):
                render(cure(final_conversion=x))


def test_glass_transition_renders_dibenedetto_with_the_kinetics_named():
    inst = render_glass_transition(cure(), map_version=MAP_VERSION)
    assert inst.variable == "GlassTransitionTemperature"
    assert (inst.value, inst.units) == (453.1636, "K")
    conversion = render_cure_conversion(cure())
    assert set(inst.conditions) == {"method", "conversion", "tg_params_sha256",
                                    "kinetics_model", "kinetics_params_sha256"}
    assert inst.conditions["method"] == "dibenedetto_pascault_williams"
    assert inst.conditions["conversion"] == 0.912345
    assert inst.conditions["kinetics_model"] == "kamal_sourour"
    assert (inst.conditions["kinetics_params_sha256"]
            == conversion.conditions["kinetics_params_sha256"])
    assert "at degree of cure 0.9123 (DiBenedetto, 453.2 K) from a" in inst.source.detail
    # Any rate law may set the conversion; the conditions name it.
    for other, model in (({"l_order": 1.2}, "karkanas_partridge"),
                         ({"amax_per_K": 0.05, "bmax": 20.0}, "kamal_sourour_amax"),
                         ({"l_order": 1.2, "amax_per_K": 0.05, "bmax": 20.0},
                          "karkanas_partridge_amax")):
        assert render_glass_transition(cure(kinetics=other)).conditions[
            "kinetics_model"] == model
    with pytest.raises(KeyError):
        render_glass_transition(cure(tg=None))
