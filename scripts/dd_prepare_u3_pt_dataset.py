"""Prepare a DD u3 Pt-regression manifest.

The u3 raw folders contain force-displacement CSV files and Matplotlib plots.
The plot titles contain the new u3 transition load (Pt), while the older
Double-Double transition tables only provide reusable theta values.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path


CASE_FROM_FOLDER = {
    "2": "Case2",
    "3": "Case3",
    "4": "Case4",
}

TEST_ID_RE = re.compile(r"Test[_\s-]*(\d+)", re.IGNORECASE)
PT_RE = re.compile(
    r"\b(?:P[12IAIl]\s*:\s*)?P[tTlL]\s*=\s*([0-9Oo°]+(?:\.[0-9]+)?)",
    re.IGNORECASE,
)
TRANSITION_RE = re.compile(r"Transition\s+load\s*=\s*([0-9]+(?:\.[0-9]+)?)", re.IGNORECASE)


def test_id_from_name(name: str) -> str | None:
    match = TEST_ID_RE.search(name)
    if not match:
        return None
    return f"{int(match.group(1)):03d}"


def read_theta_tables(raw_double_double_root: Path) -> dict[tuple[str, str], tuple[float, float]]:
    theta: dict[tuple[str, str], tuple[float, float]] = {}
    for case_number, case_name in CASE_FROM_FOLDER.items():
        table = raw_double_double_root / case_number / "transition load P1.csv"
        if not table.exists():
            table = raw_double_double_root / case_number / "transition load.csv"
        if not table.exists():
            raise FileNotFoundError(f"Missing transition table for theta lookup: {table}")
        with table.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                test_id = test_id_from_name(str(row.get("Test_ID", "")))
                if test_id is None:
                    continue
                theta[(case_name, test_id)] = (
                    float(row.get("Theta1") or row.get("theta1")),
                    float(row.get("Theta2") or row.get("theta2")),
                )
    return theta


def read_ocr_rows(path: Path) -> dict[Path, dict[str, object]]:
    rows: dict[Path, dict[str, object]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid OCR JSON on line {line_number}: {line[:120]}") from exc
            image_path = Path(str(row["path"]))
            rows[image_path] = row
    return rows


def ocr_number(value: str) -> float:
    cleaned = value.replace("°", "8").replace("O", "0").replace("o", "0")
    parsed = float(cleaned)
    if "." not in cleaned and parsed > 50000:
        return parsed / 100.0
    return parsed


def parse_pt(lines: list[str], image_name: str) -> tuple[float | None, str | None]:
    text = " ".join(lines)
    if "_transition" in image_name:
        match = TRANSITION_RE.search(text)
        if match:
            return ocr_number(match.group(1)), "transition_plot_title"
    match = PT_RE.search(text)
    if match:
        return ocr_number(match.group(1)), "p1_plot_title"
    match = TRANSITION_RE.search(text)
    if match:
        return ocr_number(match.group(1)), "transition_plot_title"
    return None, None


def collect_plot_labels(raw_u3_root: Path, ocr_rows: dict[Path, dict[str, object]]) -> dict[tuple[str, str], dict[str, object]]:
    labels: dict[tuple[str, str], dict[str, object]] = {}
    conflicts: list[dict[str, object]] = []
    for plot_path in sorted(raw_u3_root.glob("*-*/plot/plot_Test_*.png")):
        test_id = test_id_from_name(plot_path.name)
        if test_id is None:
            continue
        folder = plot_path.parent.parent.name
        ocr = ocr_rows.get(plot_path.resolve()) or ocr_rows.get(plot_path)
        if ocr is None:
            continue
        pt, source = parse_pt([str(line) for line in ocr.get("lines", [])], plot_path.name)
        if pt is None or source is None:
            continue
        key = (folder, test_id)
        candidate = {
            "pt": pt,
            "pt_source": source,
            "plot_path": str(plot_path),
            "ocr_lines": " | ".join(str(line) for line in ocr.get("lines", [])),
        }
        previous = labels.get(key)
        if previous is None:
            labels[key] = candidate
            continue
        # Prefer the P1 title when both P1 and transition plots exist.
        if previous["pt_source"] != "p1_plot_title" and source == "p1_plot_title":
            labels[key] = candidate
        elif abs(float(previous["pt"]) - pt) > 1e-2:
            conflicts.append({"folder": folder, "test_id": test_id, "first": previous, "second": candidate})
    if conflicts:
        raise RuntimeError(f"Conflicting OCR Pt labels: {conflicts[:5]}")
    return labels


def prepare_dataset(raw_double_double_root: Path, raw_u3_root: Path, ocr_jsonl: Path, output_root: Path) -> dict[str, object]:
    if output_root.exists():
        raise FileExistsError(f"Output already exists: {output_root}")
    output_root.mkdir(parents=True)

    theta_lookup = read_theta_tables(raw_double_double_root)
    ocr_rows = read_ocr_rows(ocr_jsonl)
    labels = collect_plot_labels(raw_u3_root, ocr_rows)

    manifest_rows: list[dict[str, object]] = []
    missing_label: list[str] = []
    missing_theta: list[str] = []
    source_counts: Counter[str] = Counter()
    folder_counts: Counter[str] = Counter()
    case_counts: Counter[str] = Counter()

    for csv_path in sorted(raw_u3_root.glob("*-*/csv/force_disp_Test_*.csv")):
        folder = csv_path.parent.parent.name
        case_number = folder.split("-", 1)[0]
        case_name = CASE_FROM_FOLDER.get(case_number)
        test_id = test_id_from_name(csv_path.name)
        if case_name is None or test_id is None:
            continue
        label = labels.get((folder, test_id))
        if label is None:
            missing_label.append(str(csv_path))
            continue
        theta = theta_lookup.get((case_name, test_id))
        if theta is None:
            missing_theta.append(f"{case_name} Test_{test_id}")
            continue

        local_csv = output_root / case_name / folder / "csv_load" / csv_path.name
        local_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(csv_path, local_csv)

        row = {
            "case": case_name,
            "case_id": int(case_number),
            "u3_folder": folder,
            "u3_bucket": folder.split("-", 1)[1],
            "test_id": test_id,
            "theta1": theta[0],
            "theta2": theta[1],
            "Pt": float(label["pt"]),
            "pt_source": label["pt_source"],
            "raw_csv_path": str(csv_path),
            "curve_csv": str(local_csv),
            "plot_path": label["plot_path"],
        }
        manifest_rows.append(row)
        source_counts[str(label["pt_source"])] += 1
        folder_counts[folder] += 1
        case_counts[case_name] += 1

    manifest_path = output_root / "manifest.csv"
    fieldnames = [
        "case",
        "case_id",
        "u3_folder",
        "u3_bucket",
        "test_id",
        "theta1",
        "theta2",
        "Pt",
        "pt_source",
        "raw_csv_path",
        "curve_csv",
        "plot_path",
    ]
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest_rows)

    summary = {
        "raw_double_double_root": str(raw_double_double_root),
        "raw_u3_root": str(raw_u3_root),
        "output_root": str(output_root),
        "manifest": str(manifest_path),
        "records": len(manifest_rows),
        "case_counts": dict(sorted(case_counts.items())),
        "folder_counts": dict(sorted(folder_counts.items())),
        "pt_source_counts": dict(sorted(source_counts.items())),
        "missing_label_count": len(missing_label),
        "missing_theta_count": len(missing_theta),
        "missing_label_examples": missing_label[:20],
        "missing_theta_examples": missing_theta[:20],
    }
    (output_root / "dataset_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    missing_by_folder: dict[str, list[str]] = defaultdict(list)
    for path in missing_label:
        p = Path(path)
        missing_by_folder[p.parent.parent.name].append(p.name)
    with (output_root / "missing_labels.json").open("w", encoding="utf-8") as handle:
        json.dump({k: sorted(v) for k, v in sorted(missing_by_folder.items())}, handle, indent=2)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-double-double-root", default="/Users/danlee/KyulAI_codex/data/datasets/Double-Double")
    parser.add_argument("--raw-u3-root", default="/Users/danlee/KyulAI_codex/data/datasets/Double-Double/u3")
    parser.add_argument("--ocr-jsonl", required=True)
    parser.add_argument("--output-root", default="/Users/danlee/KyulAI_codex/data/datasets/DD_u3_pt_v1")
    args = parser.parse_args()

    summary = prepare_dataset(
        Path(args.raw_double_double_root),
        Path(args.raw_u3_root),
        Path(args.ocr_jsonl),
        Path(args.output_root),
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
