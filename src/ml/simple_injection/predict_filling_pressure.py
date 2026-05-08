"""Predict Simple Injection filling pressure histogram summaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import numpy as np

from .data import DEFAULT_DATA_DIR, build_record_from_inputs, load_geometry_doe, load_process_doe


def _load_inputs_from_ids(data_dir: str | Path, geometry_id: str, process_id: str) -> tuple[dict, dict]:
    doe_dir = Path(data_dir) / "DOE"
    geometry = load_geometry_doe(doe_dir)[geometry_id]
    process = load_process_doe(doe_dir)[process_id]
    return {"geometry_id": geometry_id, **geometry}, {"process_id": process_id, **process}


def _summary_from_prediction(sample_id: str, target_columns: list[str], values: np.ndarray) -> dict:
    values = np.clip(np.asarray(values, dtype=float), 0.0, None)
    stats = dict(zip(target_columns[:4], values[:4]))
    ratios = values[4:]
    ratios = ratios / max(float(np.sum(ratios)), 1e-9) * 100.0
    max_pressure = max(float(stats.get("max_MPa", 0.0)), 1e-9)
    bins = []
    step = max_pressure / max(len(ratios), 1)
    for index, ratio in enumerate(ratios, start=1):
        start = step * (index - 1)
        end = step * index
        bins.append(
            {
                "group": index,
                "from_MPa": float(start),
                "to_MPa": float(end),
                "center_MPa": float((start + end) / 2.0),
                "count": 0,
                "volume_ratio_pct": float(ratio),
            }
        )
    return {
        "sample_id": sample_id,
        "source_file": "predicted_filling_pressure_surrogate",
        "stats": {key: float(value) for key, value in stats.items()},
        "group_count": len(bins),
        "total_count": 0,
        "total_volume_ratio_pct": float(np.sum(ratios)),
        "bins": bins,
        "note": "Predicted filling pressure histogram summary; spatial mesh coordinates are not included.",
    }


def predict_filling_pressure(model_path: str | Path, geometry: dict, process: dict) -> dict:
    bundle = joblib.load(model_path)
    x, _ = build_record_from_inputs(geometry, process, gate_types=bundle["gate_types"])
    pred = bundle["model"].predict(x)[0]
    sample_id = f"{geometry.get('geometry_id', 'manual')}_{process.get('process_id', 'manual')}"
    return _summary_from_prediction(sample_id, bundle["target_columns"], pred)


def _geometry_from_args(args) -> dict:
    return {
        "geometry_id": "manual",
        "L_mm": args.L_mm,
        "W_mm": args.W_mm,
        "t_mm": args.t_mm,
        "D_mm": args.D_mm,
        "R_mm": args.R_mm if args.R_mm is not None else args.D_mm / 2.0,
        "gate_type": args.gate_type,
        "gate_size_width_mm": args.gate_size_width_mm,
        "gate_size_height_mm": args.gate_size_height_mm,
    }


def _process_from_args(args) -> dict:
    return {
        "process_id": "manual",
        "melt_temp_C": args.melt_temp_C,
        "mold_temp_C": args.mold_temp_C,
        "injection_time_s": args.injection_time_s,
        "packing_pressure_MPa": args.packing_pressure_MPa,
        "packing_time_s": args.packing_time_s,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict Simple Injection filling pressure histogram")
    parser.add_argument("--model", default="models/simple_injection_filling_pressure_v1/filling_pressure_surrogate.joblib")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--geometry-id")
    parser.add_argument("--process-id")
    parser.add_argument("--L-mm", dest="L_mm", type=float)
    parser.add_argument("--W-mm", dest="W_mm", type=float)
    parser.add_argument("--t-mm", dest="t_mm", type=float)
    parser.add_argument("--D-mm", dest="D_mm", type=float)
    parser.add_argument("--R-mm", dest="R_mm", type=float)
    parser.add_argument("--gate-type", default="edge_gate")
    parser.add_argument("--gate-size-width-mm", type=float, default=10.0)
    parser.add_argument("--gate-size-height-mm", type=float, default=1.5)
    parser.add_argument("--melt-temp-C", type=float)
    parser.add_argument("--mold-temp-C", type=float)
    parser.add_argument("--injection-time-s", type=float)
    parser.add_argument("--packing-pressure-MPa", type=float)
    parser.add_argument("--packing-time-s", type=float)
    args = parser.parse_args()

    if args.geometry_id and args.process_id:
        geometry, process = _load_inputs_from_ids(args.data_dir, args.geometry_id, args.process_id)
    else:
        required = [
            "L_mm",
            "W_mm",
            "t_mm",
            "D_mm",
            "melt_temp_C",
            "mold_temp_C",
            "injection_time_s",
            "packing_pressure_MPa",
            "packing_time_s",
        ]
        missing = [name for name in required if getattr(args, name) is None]
        if missing:
            raise SystemExit(
                "Provide --geometry-id and --process-id, or provide manual feature values. "
                f"Missing: {', '.join(missing)}"
            )
        geometry = _geometry_from_args(args)
        process = _process_from_args(args)

    print(json.dumps(predict_filling_pressure(args.model, geometry, process), indent=2))


if __name__ == "__main__":
    main()
