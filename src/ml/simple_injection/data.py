"""Data loading utilities for the Simple Injection Moldex3D task."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

DEFAULT_DATA_DIR = Path("data/datasets/Simple_Injection")
DEFAULT_DOE_DIR = DEFAULT_DATA_DIR / "DOE"
DEFAULT_RESULT_DIR = DEFAULT_DATA_DIR / "Result"
DEFAULT_FILLING_PRESSURE_DIR = DEFAULT_DATA_DIR / "Filling_Pressure"
DEFAULT_VALIDATION_SET_DIR = DEFAULT_DATA_DIR / "Validation_Set"
DEFAULT_TRAINING_DIR = DEFAULT_DATA_DIR / "Training"
DEFAULT_TRAINING_1_DIR = DEFAULT_DATA_DIR / "Training_1"
DEFAULT_TRAINING_2_DIR = DEFAULT_DATA_DIR / "Training_2"

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


def _supplemental_csvs(doe_dir: Path, kind: str) -> list[Path]:
    return sorted(doe_dir.glob(f"supplemental_*_{kind}_doe.csv"))


def load_geometry_doe(
    doe_dir: str | Path = DEFAULT_DOE_DIR,
    include_supplemental: bool = False,
) -> dict[str, dict[str, float | str]]:
    doe_path = Path(doe_dir)
    rows = _read_dict_csv(doe_path / "geometry_doe_30.csv")
    if include_supplemental:
        for path in _supplemental_csvs(doe_path, "geometry"):
            rows.extend(_read_dict_csv(path))
    geometry: dict[str, dict[str, float | str]] = {}
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


def load_process_doe(
    doe_dir: str | Path = DEFAULT_DOE_DIR,
    include_supplemental: bool = False,
) -> dict[str, dict[str, float | str]]:
    doe_path = Path(doe_dir)
    rows = _read_dict_csv(doe_path / "process_doe_10.csv")
    if include_supplemental:
        for path in _supplemental_csvs(doe_path, "process"):
            rows.extend(_read_dict_csv(path))
    process: dict[str, dict[str, float | str]] = {}
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


def load_training_doe_ids(
    training_dir: str | Path = DEFAULT_TRAINING_DIR,
) -> tuple[set[str], set[str]]:
    """Return geometry/process DOE ids that have normalized training results."""
    root = Path(training_dir)
    geometry_ids: set[str] = set()
    process_ids: set[str] = set()
    for result_kind in ("Filling_Pressure", "Sprue_Pressure"):
        result_root = root / result_kind
        if not result_root.exists():
            continue
        for geometry_dir in sorted(path for path in result_root.iterdir() if path.is_dir()):
            if not re.fullmatch(r"G\d{2}", geometry_dir.name, re.IGNORECASE):
                continue
            geometry_ids.add(geometry_dir.name.upper())
            for process_dir in sorted(path for path in geometry_dir.iterdir() if path.is_dir()):
                if re.fullmatch(r"P\d{2}", process_dir.name, re.IGNORECASE):
                    process_ids.add(process_dir.name.upper())
    return geometry_ids, process_ids


def _to_float(value: str) -> float | None:
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


RUN_RE = re.compile(r"(G\d{2})_(P\d{2})")
FILLING_PRESSURE_RE = re.compile(r"(G\d{2})_(P\d{2})_Filling_Pressure\.csv$", re.IGNORECASE)
SINGLE_SPRUE_PRESSURE_RE = re.compile(r"(G\d{2})_(P\d{2})_.*Sprue.*Pressure.*\.csv$", re.IGNORECASE)
SUPPLEMENTAL_CASE_MATRIX = "supplemental_v02_v03_case_matrix_60.csv"


def load_result_curves(result_dir: str | Path = DEFAULT_RESULT_DIR) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for path in sorted(Path(result_dir).rglob("*.csv")):
        name = path.name.upper()
        if "SPRUE" not in name or "PRESSURE" not in name:
            continue
        single_case_match = SINGLE_SPRUE_PRESSURE_RE.search(path.name)
        if single_case_match:
            curve = _read_first_xy_curve(path)
            if curve is not None:
                curves[f"{single_case_match.group(1)}_{single_case_match.group(2)}"] = curve
            continue
        with path.open(newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        header_idx = next(
            (i for i, row in enumerate(rows) if any(cell.strip() == "Time (sec)" for cell in row)),
            None,
        )
        if header_idx is None:
            raise ValueError(f"Could not find XYPlot header row in {path}")

        header = rows[header_idx]
        found_in_header = False
        for col in range(0, len(header) - 1, 2):
            match = RUN_RE.search(header[col + 1])
            if not match:
                continue
            found_in_header = True
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
        if not found_in_header:
            match = RUN_RE.search(path.name) or RUN_RE.search(path.as_posix())
            curve = _read_first_xy_curve(path) if match else None
            if curve is not None and match is not None:
                curves[f"{match.group(1)}_{match.group(2)}"] = curve
    return curves


def load_training_2_result_curves(data_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    """Load one-case sprue pressure CSV files from the Training_2 extension set."""
    root = Path(data_dir) / "Training_2"
    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    if not root.exists():
        return curves

    for path in sorted(root.rglob("*.csv")):
        name = path.name.upper()
        if "SPRUE" not in name or "PRESSURE" not in name:
            continue
        match = RUN_RE.search(path.name)
        if not match:
            match = RUN_RE.search(path.as_posix())
        if not match:
            continue
        curve = _read_first_xy_curve(path)
        if curve is None:
            continue
        curves[f"{match.group(1)}_{match.group(2)}"] = curve
    return curves


def _read_first_xy_curve(path: Path) -> tuple[np.ndarray, np.ndarray] | None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    header_idx = next(
        (i for i, row in enumerate(rows) if any(cell.strip() == "Time (sec)" for cell in row)),
        None,
    )
    if header_idx is None:
        return None
    header = rows[header_idx]
    time_col = next((idx for idx, cell in enumerate(header) if cell.strip() == "Time (sec)"), 0)
    value_col = time_col + 1
    times = []
    pressures = []
    for row in rows[header_idx + 1 :]:
        if value_col >= len(row):
            continue
        t = _to_float(row[time_col])
        p = _to_float(row[value_col])
        if t is None or p is None:
            continue
        times.append(t)
        pressures.append(p)
    if not times:
        return None
    order = np.argsort(times)
    return np.asarray(times, dtype=float)[order], np.asarray(pressures, dtype=float)[order]


def _supplemental_case_rows(data_dir: str | Path) -> list[dict[str, str]]:
    path = Path(data_dir) / "DOE" / SUPPLEMENTAL_CASE_MATRIX
    if not path.exists():
        return []
    return _read_dict_csv(path)


def _validation_set_case_map(data_dir: str | Path) -> dict[Path, str]:
    """Map Validation_Set raw folders to supplemental DOE sample ids.

    Example:
    Validation_Set/V02/v02FAM_G01/P01 -> G31_P11
    """
    data_path = Path(data_dir)
    root = data_path / "Validation_Set"
    if not root.exists():
        return {}
    rows = _supplemental_case_rows(data_path)
    if not rows:
        return {}

    rows_by_family: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        rows_by_family.setdefault(row["family"], []).append(row)

    family_index: dict[str, dict[str, list[str]]] = {}
    for family, family_rows in rows_by_family.items():
        family_key = family.split("_", 1)[0].upper()
        geometry_ids = sorted({row["geometry_id"] for row in family_rows})
        process_ids = sorted({row["process_id"] for row in family_rows})
        family_index[family_key] = {
            "geometry_ids": geometry_ids,
            "process_ids": process_ids,
        }

    case_map: dict[Path, str] = {}
    for family_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        family_key = family_dir.name.upper()
        if family_key not in family_index:
            continue
        geometry_ids = family_index[family_key]["geometry_ids"]
        process_ids = family_index[family_key]["process_ids"]
        for geometry_dir in sorted(path for path in family_dir.iterdir() if path.is_dir()):
            geometry_match = re.search(r"G(\d+)", geometry_dir.name, re.IGNORECASE)
            if not geometry_match:
                continue
            geometry_idx = int(geometry_match.group(1)) - 1
            if geometry_idx < 0 or geometry_idx >= len(geometry_ids):
                continue
            geometry_id = geometry_ids[geometry_idx]
            for process_dir in sorted(path for path in geometry_dir.iterdir() if path.is_dir()):
                process_match = re.search(r"P(\d+)", process_dir.name, re.IGNORECASE)
                if not process_match:
                    continue
                process_idx = int(process_match.group(1)) - 1
                if process_idx < 0 or process_idx >= len(process_ids):
                    continue
                process_id = process_ids[process_idx]
                case_map[process_dir] = f"{geometry_id}_{process_id}"
    return case_map


def load_validation_set_result_curves(data_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    curves: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for process_dir, sample_id in _validation_set_case_map(data_dir).items():
        path = process_dir / "Packing-Sprue Pressure.csv"
        if not path.exists():
            continue
        curve = _read_first_xy_curve(path)
        if curve is not None:
            curves[sample_id] = curve
    return curves


def _parse_filling_pressure_csv(path: Path, sample_id: str, source_file: str) -> dict[str, object] | None:
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = [row for row in csv.reader(f) if any(cell.strip() for cell in row)]

    stats: dict[str, float | str] = {}
    bins: list[dict[str, float | int]] = []
    in_distribution = False
    for row in rows:
        first = row[0].strip()
        if first == "[Distribution]":
            in_distribution = True
            continue
        if not in_distribution and len(row) == 1 and "=" in first:
            key, value = [item.strip() for item in first.split("=", 1)]
            number = _to_float(value)
            stats[key.lower()] = number if number is not None else value
            continue
        if in_distribution and first.isdigit() and len(row) >= 6:
            bins.append(
                {
                    "group": int(first),
                    "from_MPa": float(row[1]),
                    "to_MPa": float(row[2]),
                    "center_MPa": float(row[3]),
                    "count": int(float(row[4])),
                    "volume_ratio_pct": float(row[5]),
                }
            )

    if not bins:
        return None
    return {
        "sample_id": sample_id,
        "source_file": source_file,
        "stats": {
            "min_MPa": float(stats.get("min", 0.0)),
            "max_MPa": float(stats.get("max", 0.0)),
            "avg_MPa": float(stats.get("avg", 0.0)),
            "sd_MPa": float(stats.get("sd", 0.0)),
        },
        "group_count": len(bins),
        "total_count": sum(int(bin_row["count"]) for bin_row in bins),
        "total_volume_ratio_pct": sum(float(bin_row["volume_ratio_pct"]) for bin_row in bins),
        "bins": bins,
        "note": (
            "Moldex3D histogram export; spatial mesh coordinates are not included, "
            "so this is a distribution summary rather than a contour field."
        ),
    }


def load_filling_pressure_distribution(
    filling_dir: str | Path = DEFAULT_FILLING_PRESSURE_DIR,
) -> dict[str, dict[str, object]]:
    """Load Moldex3D filling pressure histogram exports.

    Moldex3D's CSV export is a summary distribution, not a mesh-point field. It
    preserves global statistics and binned volume ratios but not spatial values.
    """
    distributions: dict[str, dict[str, object]] = {}
    root = Path(filling_dir)
    if not root.exists():
        return distributions

    for path in sorted(root.rglob("*.csv")):
        match = FILLING_PRESSURE_RE.search(path.name)
        if not match:
            continue
        sample_id = f"{match.group(1)}_{match.group(2)}"
        relative_path = path.relative_to(root)
        existing = distributions.get(sample_id)
        if existing is not None:
            existing_path = Path(str(existing["source_file"]))
            if len(relative_path.parts) <= len(existing_path.parts):
                continue
        parsed = _parse_filling_pressure_csv(path, sample_id, relative_path.as_posix())
        if parsed is not None:
            distributions[sample_id] = parsed
    return distributions


def load_validation_set_filling_pressure_distribution(data_dir: str | Path = DEFAULT_DATA_DIR) -> dict[str, dict[str, object]]:
    distributions: dict[str, dict[str, object]] = {}
    data_path = Path(data_dir)
    for process_dir, sample_id in _validation_set_case_map(data_path).items():
        candidates = [process_dir / "Filling_Pressure.csv"]
        candidates.extend(sorted(process_dir.glob("*Filling Pressure.csv")))
        candidates.extend(sorted(process_dir.glob("*_Filling_Pressure.csv")))
        path = next((candidate for candidate in candidates if candidate.exists()), None)
        if path is None:
            continue
        parsed = _parse_filling_pressure_csv(path, sample_id, path.relative_to(data_path).as_posix())
        if parsed is not None:
            distributions[sample_id] = parsed
    return distributions


def load_filling_pressure_training_arrays(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    group_count: int = 10,
) -> tuple[list[SimpleInjectionRecord], np.ndarray, np.ndarray, list[str], list[str], list[str]]:
    data_path = Path(data_dir)
    geometry = load_geometry_doe(data_path / "DOE", include_supplemental=True)
    process = load_process_doe(data_path / "DOE", include_supplemental=True)
    training_filling = data_path / "Training" / "Filling_Pressure"
    training_1_filling = data_path / "Training_1" / "Filling_Pressure"
    training_2_root = data_path / "Training_2"

    filling = load_filling_pressure_distribution(training_filling)
    if not filling:
        filling = load_filling_pressure_distribution(training_1_filling)
    if not filling:
        filling = load_filling_pressure_distribution(data_path / "Filling_Pressure")
    if not filling:
        filling = load_filling_pressure_distribution(data_path / "Filling")

    training_2_filling = {}
    if not training_filling.exists():
        training_2_filling = load_filling_pressure_distribution(training_2_root)
        filling.update(training_2_filling)
    if not training_filling.exists() and not training_2_filling:
        filling.update(load_validation_set_filling_pressure_distribution(data_path))

    records: list[SimpleInjectionRecord] = []
    targets = []
    target_columns = [
        "min_MPa",
        "max_MPa",
        "avg_MPa",
        "sd_MPa",
    ] + [f"group_{idx:02d}_volume_ratio_pct" for idx in range(1, group_count + 1)]

    for sample_id, summary in sorted(filling.items()):
        geometry_id, process_id = sample_id.split("_")
        if geometry_id not in geometry or process_id not in process:
            continue
        bins = sorted(
            cast(list[dict[str, object]], summary["bins"]),
            key=lambda row: int(cast(Any, row["group"])),
        )
        if len(bins) != group_count:
            continue
        features = _with_derived_features({**geometry[geometry_id], **process[process_id]})
        records.append(
            SimpleInjectionRecord(
                geometry_id=geometry_id,
                process_id=process_id,
                gate_type=str(features["gate_type"]),
                features=features,
                time=np.asarray([0.0, 1.0]),
                pressure=np.asarray([0.0, 1.0]),
            )
        )
        stats = cast(dict[str, object], summary["stats"])
        targets.append(
            [
                float(cast(Any, stats["min_MPa"])),
                float(cast(Any, stats["max_MPa"])),
                float(cast(Any, stats["avg_MPa"])),
                float(cast(Any, stats["sd_MPa"])),
                *[float(cast(Any, row["volume_ratio_pct"])) for row in bins],
            ]
        )

    if not records:
        raise ValueError(f"No filling pressure distribution CSV files found under {data_dir}")
    x, feature_columns, gate_types = make_feature_matrix(records)
    return records, x, np.asarray(targets, dtype=float), target_columns, feature_columns, gate_types


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
    geometry = load_geometry_doe(doe_dir or data_path / "DOE", include_supplemental=doe_dir is None)
    process = load_process_doe(doe_dir or data_path / "DOE", include_supplemental=doe_dir is None)
    if result_dir is not None:
        curves = load_result_curves(result_dir)
    else:
        training_sprue = data_path / "Training" / "Sprue_Pressure"
        training_1_sprue = data_path / "Training_1" / "Sprue_Pressure"
        curves = load_result_curves(training_sprue)
        if not curves:
            curves = load_result_curves(training_1_sprue)
        if not curves:
            curves = load_result_curves(data_path / "Result")
        training_2_curves = {}
        if not training_sprue.exists():
            training_2_curves = load_training_2_result_curves(data_path)
            curves.update(training_2_curves)
        if not training_sprue.exists() and not training_2_curves:
            curves.update(load_validation_set_result_curves(data_path))

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
