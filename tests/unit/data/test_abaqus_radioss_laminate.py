from pathlib import Path

import pytest

from scripts.generate_radioss_angle_batch import case2_angles, model_with_case2_angles
from src.data.converters.abaqus_radioss_laminate import (
    ConversionError,
    parse_abaqus_laminate,
    render_radioss_decks,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_001 = PROJECT_ROOT / "data" / "inp" / "Test_001 (1).inp"


def test_parses_test_001_without_losing_layup_or_orthotropy() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)

    assert len(model.nodes) == 6561
    assert len(model.elements) == 6400
    assert len(model.part_element_set) == 6400
    assert len(model.plies) == 16
    assert model.total_thickness == pytest.approx(0.12)
    assert [ply.angle_degrees for ply in model.plies[:4]] == [65.0, -65.0, 19.0, -19.0]
    assert model.material.e1 == pytest.approx(2.15e7)
    assert model.material.e2 == pytest.approx(1.23e6)
    assert model.material.e3 == pytest.approx(1.23e6)
    assert model.material.g12 == pytest.approx(571000.0)
    assert model.material.g13 == pytest.approx(571000.0)
    assert model.material.g23 == pytest.approx(571000.0)
    assert set(model.assembly_node_sets) == {"set-1", "set-2", "set-3", "set-4", "set-5"}
    assert model.nonlinear_geometry is True
    assert model.static_step.initial_increment == pytest.approx(0.001)
    assert model.static_step.time_period == pytest.approx(1.0)
    assert model.static_step.minimum_increment == pytest.approx(1e-14)
    assert model.static_step.maximum_increment == pytest.approx(0.001)
    assert model.static_step.maximum_increments == 100000


def test_renders_composite_radioss_cards_and_smooth_displacement() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(model, run_name="Test_001", run_time=1e-3)

    assert "/MAT/COMPSH/1" in decks.starter
    assert (
        f"{2.15e7:>20.12g}{1.23e6:>20.12g}{0.329:>20.12g}{0:>10}{1.23e6:>30.12g}" in decks.starter
    )
    assert "/PROP/SH_SANDW/1" in decks.starter
    assert "/PROP/TYPE19/" not in decks.starter
    assert "        12         4" in decks.starter
    assert "/SHELL/1" in decks.starter
    assert "/IMPDISP/1" in decks.starter
    assert "-0.15" in decks.starter
    assert decks.starter.count("/GRNOD/NODE/") > 5
    assert "lbf*s^2/in" not in decks.starter
    assert "175.126835246" in decks.starter
    assert f"{12:>10}{4:>10}{0:>10}{1:>10}{0:>40}" in decks.starter
    assert f"{2026:>10}{0:>10}" in decks.starter
    assert f"{48:>10}{1:>10}{0.12:>20}{0.833333333333:>20}" in decks.starter
    assert f"{65:>20}{0.0025:>20}{0:>20}{1:>10}{'':>10}{0:>20}" in decks.starter
    assert "/ANIM/SHELL/TENS/STRESS/ALL" in decks.engine
    assert "/ANIM/SHELL/TENS/STRAIN/ALL" in decks.engine
    assert "/ANIM/VECT/FINT" in decks.engine
    assert "/TH/NODE/1" in decks.starter
    assert f"{'REACX':>10}{'DX':>10}" in decks.starter
    assert "/IMPL/" not in decks.engine
    assert decks.manifest["node_count"] == 6561
    assert decks.manifest["shell_count"] == 6400
    assert decks.manifest["ply_count"] == 16
    assert decks.manifest["radioss_integration_layer_count"] == 48
    assert decks.manifest["conversion_profile"] == "kyulai_laminate_s4r_composite_v4"
    assert decks.manifest["thickness_integration_mapping"] == (
        "equal-thickness SH_SANDW sublayers per Abaqus ply integration point"
    )


def test_renders_same_condition_nonlinear_implicit_step() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(
        model,
        run_name="Test_001",
        analysis_mode="implicit",
        output_interval=0.01,
    )

    assert "Linear Abaqus default static displacement ramp" in decks.starter
    assert "         1         4" in decks.starter
    assert f"{1:>10}{4:>10}{0:>10}{0:>10}{0:>40}" in decks.starter
    assert f"{0:>20.12g}{0:>20.12g}" in decks.starter
    assert f"{1:>20.12g}{1:>20.12g}" in decks.starter
    assert "/IMPL/NONLIN/2\n6 2 0.005 0 0" in decks.engine
    assert "/IMPL/SOLVER/2\n5 0 0 0" in decks.engine
    assert "/IMPL/DTINI\n0.001" in decks.engine
    assert "/IMPL/DT/STOP\n1e-14 0.001" in decks.engine
    assert "/IMPL/NCYCLE/STOP\n100000" in decks.engine
    assert "/TFILE\n0.001" in decks.engine
    assert decks.engine.startswith("/RUN/Test_001/1\n1\n")
    assert decks.manifest["analysis_mode"] == "implicit"
    assert decks.manifest["shell_formulation"] == 1
    assert decks.manifest["run_time"] == pytest.approx(1.0)
    assert decks.manifest["implicit_nonlinear_method"] == 2
    assert decks.manifest["implicit_stiffness_reform_interval"] == 6


def test_allows_implicit_stiffness_reform_interval_override() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(
        model,
        run_name="Test_001_la3",
        analysis_mode="implicit",
        implicit_stiffness_reform_interval=3,
    )

    assert "/IMPL/NONLIN/2\n3 2 0.005 0 0" in decks.engine
    assert decks.manifest["implicit_stiffness_reform_interval"] == 3


def test_allows_explicit_shell_formulation_benchmark_override() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(
        model,
        run_name="Test_001_qeph_diagnostic",
        analysis_mode="implicit",
        shell_formulation=24,
    )

    assert "        24         4" in decks.starter
    assert decks.manifest["shell_formulation"] == 24


def test_history_only_mode_keeps_tfile_and_omits_animation() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(
        model,
        run_name="Test_001_history_only",
        analysis_mode="implicit",
        animation_output=False,
    )

    assert "/TFILE\n0.001" in decks.engine
    assert "/ANIM/" not in decks.engine
    assert decks.manifest["animation_output_enabled"] is False


def test_case2_angle_replacement_preserves_everything_except_ply_angles() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    changed = model_with_case2_angles(model, 40.0, -51.0)

    assert case2_angles(40.0, -51.0, 16) == [40.0, -40.0, -51.0, 51.0] * 4
    assert [ply.angle_degrees for ply in changed.plies] == [40.0, -40.0, -51.0, 51.0] * 4
    assert [ply.thickness for ply in changed.plies] == [ply.thickness for ply in model.plies]
    assert changed.nodes == model.nodes
    assert changed.elements == model.elements
    assert changed.boundaries == model.boundaries


def test_q4_disables_unsupported_drilling_stiffness() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    decks = render_radioss_decks(
        model,
        run_name="Test_001_q4",
        analysis_mode="implicit",
        shell_formulation=1,
    )

    assert f"{1:>10}{4:>10}{0:>10}{0:>10}{0:>40}" in decks.starter


def test_scales_initial_nodal_z_for_diagnostic_sweep() -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    source_node = max(model.nodes, key=lambda node: abs(node.z))
    decks = render_radioss_decks(
        model,
        run_name="Test_001_half_imperfection",
        analysis_mode="implicit",
        initial_geometry_z_scale=0.5,
    )

    expected_node = (
        f"{source_node.node_id:>10}{source_node.x:>20.12g}{source_node.y:>20.12g}"
        f"{source_node.z * 0.5:>20.12g}"
    )
    assert expected_node in decks.starter
    assert decks.manifest["initial_geometry_z_scale"] == pytest.approx(0.5)
    assert decks.manifest["converted_max_abs_z"] == pytest.approx(
        decks.manifest["source_max_abs_z"] * 0.5
    )


@pytest.mark.parametrize("scale", [-1.0, float("inf"), float("nan")])
def test_rejects_invalid_initial_nodal_z_scale(scale: float) -> None:
    model = parse_abaqus_laminate(TEST_001.read_text(), title=TEST_001.stem)
    with pytest.raises(ConversionError, match="initial_geometry_z_scale"):
        render_radioss_decks(model, initial_geometry_z_scale=scale)


def test_rejects_unsupported_element_type() -> None:
    text = TEST_001.read_text().replace("*Element, type=S4R", "*Element, type=S8R", 1)
    with pytest.raises(ConversionError, match="only S4R"):
        parse_abaqus_laminate(text)


def test_rejects_transformed_instance() -> None:
    text = TEST_001.read_text().replace(
        "*Instance, name=Part-1-1, part=Part-1\n*End Instance",
        "*Instance, name=Part-1-1, part=Part-1\n1., 0., 0.\n*End Instance",
        1,
    )
    with pytest.raises(ConversionError, match="must be flattened"):
        parse_abaqus_laminate(text)
