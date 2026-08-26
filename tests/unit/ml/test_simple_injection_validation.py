from src.ml.simple_injection.validation import (
    has_blocking_issues,
    validate_simple_injection_inputs,
)


def _valid_inputs() -> dict[str, float | str]:
    return {
        "L_mm": 154.01,
        "W_mm": 97.42,
        "t_mm": 2.207,
        "D_mm": 17.61,
        "R_mm": 8.805,
        "gate_type": "edge_gate",
        "gate_size_width_mm": 10.0,
        "gate_size_height_mm": 1.5,
        "melt_temp_C": 226.1,
        "mold_temp_C": 61.7,
        "injection_time_s": 2.47,
        "packing_pressure_MPa": 69.0,
        "packing_time_s": 4.731,
    }


def test_current_training_gate_condition_is_supported() -> None:
    issues = validate_simple_injection_inputs(_valid_inputs())

    assert not [issue for issue in issues if issue["category"] == "gate"]
    assert not has_blocking_issues(issues)


def test_gate_variants_are_rejected_outside_the_training_doe() -> None:
    inputs = _valid_inputs()
    inputs.update(
        {
            "gate_type": "fan_gate",
            "gate_size_width_mm": 15.0,
            "gate_size_height_mm": 1.8,
        }
    )

    issues = validate_simple_injection_inputs(inputs)
    gate_errors = {
        issue["field"]
        for issue in issues
        if issue["category"] == "gate" and issue["severity"] == "error"
    }

    assert gate_errors == {
        "gate_type",
        "gate_size_width_mm",
        "gate_size_height_mm",
    }
    assert has_blocking_issues(issues)
