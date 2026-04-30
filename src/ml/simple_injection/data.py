"""Data loading utilities for the Simple Injection Moldex3D task."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


DEFAULT_DATA_DIR = Path("data/datasets/Simple_Injection")
DEFAULT_DOE_DIR = DEFAULT_DATA_DIR / "DOE"
DEFAULT_RESULT_DIR = DEFAULT_DATA_DIR / "Result"

BASE_FEATURE_COLUMNS = [
    "L_mm",
    "W_mm",
    "t_mm",
    "D_mm",
    "R_mm",
    "gate_size_width_mm",
    "gate_size_height_mm",
    "melt_temp_C",
    "mold_temp_C",
    "injection_time_s",
    "packing_pressure_MPa",
    "packing_time_s",
]

DERIVED_FEATURE_COLUMNS = [
    "area_mm2",
    "hole_area_mm2",
    "net_area_mm2",
    "volume_mm3",
    "aspect_ratio",
    "hole_diameter_ratio",
    "gate_area_mm2",
    "gate_to_thickness_ratio",
    "flow_length_to_thickness",
    "process_total_time_s",
]


@dataclass(frozen=True)
class SimpleInjectionRecord:
    geometry_id: str
    process_id: str
    gate_type: str
    features: dict[str, float | str]
    time: np.ndarray
    pressure: np.ndarray

    @property
    def sample_id(self) -> str:
        return f"{self.geometry_id}_{self.process_id}"


def _clean_key(key: str) -> str:
    key = key.strip().replace("\ufeff", "")
    return {
        "gate_size (Width)_mm": "gate_size_width_mm",
        "gate_size (Hieght)_mm": "gate_size_height_mm",
    }.get(key, key)


def _read_dict_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            cleaned = {_clean_key(k): (v or "").strip() for k, v in row.items() if k}
            if any(cleaned.values()):
                rows.append(cleaned)
        return rows


def load_geometry_doe(doe_dir: str | Path = DEFAULT_DOE_DIR) -> dict[str, dict[str, float | str]]:
    rows = _read_dict_csv(Path(doe_dir) / "geometry_doe_30.csv")
    geometry = {}
    for row in rows:
        geometry_id = row["geometry_id"]
        geometry[geometry_id] = {
            "L_mm": float(row["L_mm"]),
            "W_mm": float(row["W_mm"]),
            "t_mm": float(row["t_mm"]),
            "D_mm": float(row["D_mm"]),
            "R_mm": float(row["R_mm"]),
            "gate_type": row["gate_type"],
            "gate_size_width_mm": float(row["gate_size_width_mm"]),
            "gate_size_height_mm": float(row["gate_size_height_mm"]),
        }
    return geometry


def load_process_doe(doe_dir: str | Path = DEFAULT_DOE_DIR) -> dict[str, dict[str, float]]:
    rows = _read_dict_csv(Path(doe_dir) / "process_doe_10.csv")
    process = {}
    for row in rows:
        process_id = row["process_id"]
        process[process_id] = {
            "melt_temp_C": float(row["melt_temp_C"]),
            "mold_temp_C": float(row["mold_temp_C"]),
            "injection_time_s": float(row["injection_time_s"]),
            "packing_pressure_MPa": float(row["packing_pressure_MPa"]),
            "packing_time_s": float(row["packing_time_s"]),
        }
    return process


def _to_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


RUN_RE = re.compile(r"(G\d{2})_(P\d{2})")


def load_result_curves(result_dir: str | Path = DEFAULT_RESULT_DIR) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for path in sorted(Path(result_dir).glob("*SPRUE PRESSURE*.csv")):
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        header_idx = next(
            (i for i, row in enumerate(rows) if any(cell.strip() == "Time (sec)" for cell in row)),
            None,
        )
        if header_idx is None:
            raise ValueError(f"Could not find XYPlot header row in {path}")

        header = rows[header_idx]
        for col in range(0, len(header) - 1, 2):
            match = RUN_RE.search(header[col + 1])
            if not match:
                continue
            sample_id = f"{match.group(1)}_{match.group(2)}"
            times = []
            pressures = []
            for row in rows[header_idx + 1 :]:
                if col + 1 >= len(row):
                    continue
                t = _to_float(row[col])
                p = _to_float(row[col + 1])
                if t is None or p is None:
                    continue
                times.append(t)
                pressures.append(p)
            if not times:
                continue
            order = np.argsort(times)
            time = np.asarray(times, dtype=float)[order]
            pressure = np.asarray(pressures, dtype=float)[order]
            curves[sample_id] = (time, pressure)
    return curves


def _with_derived_features(features: dict[str, float | str]) -> dict[str, float | str]:
    out = dict(features)
    length = float(out["L_mm"])
    width = float(out["W_mm"])
    thickness = float(out["t_mm"])
    diameter = float(out["D_mm"])
    gate_width = float(out["gate_size_width_mm"])
    gate_height = float(out["gate_size_height_mm"])
    area = length * width
    hole_area = np.pi * (diameter / 2.0) ** 2
    net_area = max(area - hole_area, 1e-9)
    out.update(
        {
            "area_mm2": area,
            "hole_area_mm2": hole_area,
            "net_area_mm2": net_area,
            "volume_mm3": net_area * thickness,
            "aspect_ratio": length / max(width, 1e-9),
            "hole_diameter_ratio": diameter / max(min(length, width), 1e-9),
            "gate_area_mm2": gate_width * gate_height,
            "gate_to_thickness_ratio": gate_height / max(thickness, 1e-9),
            "flow_length_to_thickness": max(length, width) / max(thickness, 1e-9),
            "process_total_time_s": float(out["injection_time_s"]) + float(out["packing_time_s"]),
        }
    )
    return out


def load_records(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    doe_dir: str | Path | None = None,
    result_dir: str | Path | None = None,
) -> list[SimpleInjectionRecord]:
    data_path = Path(data_dir)
    geometry = load_geometry_doe(doe_dir or data_path / "DOE")
    process = load_process_doe(doe_dir or data_path / "DOE")
    curves = load_result_curves(result_dir or data_path / "Result")

    records = []
    for sample_id, (time, pressure) in sorted(curves.items()):
        geometry_id, process_id = sample_id.split("_")
        if geometry_id not in geometry or process_id not in process:
            continue
        features = _with_derived_features({**geometry[geometry_id], **process[process_id]})
        records.append(
            SimpleInjectionRecord(
                geometry_id=geometry_id,
                process_id=process_id,
                gate_type=str(features["gate_type"]),
                features=features,
                time=time,
                pressure=pressure,
            )
        )
    return records


def make_feature_matrix(
    records: list[SimpleInjectionRecord],
    gate_types: list[str] | None = None,
) -> tuple[np.ndarray, list[str], list[str]]:
    if gate_types is None:
        gate_types = sorted({record.gate_type for record in records})
    feature_columns = BASE_FEATURE_COLUMNS + [f"gate_type__{gate}" for gate in gate_types] + DERIVED_FEATURE_COLUMNS
    rows = []
    for record in records:
        row = [float(record.features[col]) for col in BASE_FEATURE_COLUMNS]
        row.extend(1.0 if record.gate_type == gate else 0.0 for gate in gate_types)
        row.extend(float(record.features[col]) for col in DERIVED_FEATURE_COLUMNS)
        rows.append(row)
    return np.asarray(rows, dtype=float), feature_columns, gate_types


def load_training_arrays(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    seq_len: int = 128,
    gate_types: list[str] | None = None,
) -> tuple[list[SimpleInjectionRecord], np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str], list[str]]:
    records = load_records(data_dir)
    if not records:
        raise ValueError(f"No sprue pressure result curves found under {data_dir}")
    x, feature_columns, gate_types = make_feature_matrix(records, gate_types=gate_types)
    grid = np.linspace(0.0, 1.0, seq_len)
    scalars = []
    curves = []
    for record in records:
        max_time = max(float(np.max(record.time)), 1e-9)
        max_pressure = max(float(np.max(record.pressure)), 1e-9)
        time_norm = np.clip(record.time / max_time, 0.0, 1.0)
        pressure_norm = np.interp(grid, time_norm, record.pressure) / max_pressure
        pressure_norm = np.clip(pressure_norm, 0.0, None)
        scalars.append([max_time, max_pressure])
        curves.append(pressure_norm)
    return records, x, np.asarray(scalars, dtype=float), np.asarray(curves, dtype=float), grid, feature_columns, gate_types


def build_record_from_inputs(
    geometry: dict[str, float | str],
    process: dict[str, float],
    gate_types: list[str],
) -> tuple[np.ndarray, list[str]]:
    geometry_id = str(geometry.get("geometry_id", "GXX"))
    process_id = str(process.get("process_id", "PXX"))
    features = _with_derived_features({**geometry, **process})
    record = SimpleInjectionRecord(
        geometry_id=geometry_id,
        process_id=process_id,
        gate_type=str(features["gate_type"]),
        features=features,
        time=np.asarray([0.0, 1.0]),
        pressure=np.asarray([0.0, 1.0]),
    )
    x, feature_columns, _ = make_feature_matrix([record], gate_types=gate_types)
    return x, feature_columns

