#!/usr/bin/env python3
"""Extract summed nodal internal-force histories from Radioss animation files."""

from __future__ import annotations

import argparse
import csv
import glob
import re
import subprocess
from collections.abc import Iterable, Iterator
from pathlib import Path


def animation_number(path: str) -> int:
    match = re.search(r"A(\d+)$", path)
    if match is None:
        raise ValueError(f"animation filename has no numeric suffix: {path}")
    return int(match.group(1))


def parse_vtk_stream(
    lines: Iterable[str], selected_nodes: set[int]
) -> tuple[float, float, float, float]:
    iterator: Iterator[str] = iter(lines)
    point_count: int | None = None
    time: float | None = None
    node_ids: list[int] = []
    force: tuple[float, float, float] | None = None
    for line in iterator:
        stripped = line.strip()
        if stripped == "TIME 1 1 double":
            time = float(next(iterator).strip())
        elif stripped.startswith("POINT_DATA "):
            point_count = int(stripped.split()[1])
        elif stripped == "SCALARS NODE_ID int 1":
            if point_count is None:
                raise RuntimeError("POINT_DATA must precede NODE_ID")
            next(iterator)  # LOOKUP_TABLE default
            node_ids = [int(next(iterator).strip()) for _ in range(point_count)]
        elif stripped == "VECTORS Internal_Forces float":
            if point_count is None or len(node_ids) != point_count:
                raise RuntimeError("NODE_ID block missing before Internal_Forces")
            total_x = total_y = total_z = 0.0
            for node_id in node_ids:
                x, y, z = (float(value) for value in next(iterator).split())
                if node_id in selected_nodes:
                    total_x += x
                    total_y += y
                    total_z += z
            force = total_x, total_y, total_z
    if time is None:
        raise RuntimeError("TIME block missing")
    if force is None:
        raise RuntimeError("Internal_Forces block missing")
    return time, *force


def extract(
    animation: str, converter: str, selected_nodes: set[int]
) -> tuple[float, float, float, float]:
    process = subprocess.Popen(
        [converter, animation],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None
    try:
        result = parse_vtk_stream(process.stdout, selected_nodes)
    finally:
        process.stdout.close()
    assert process.stderr is not None
    stderr = process.stderr.read()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"converter failed for {animation}: {stderr}")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--converter", required=True)
    parser.add_argument("--animation-glob", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--node-range", type=int, nargs=3, metavar=("START", "STOP", "STEP"))
    selection.add_argument("--node-ids", type=int, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.node_range is not None:
        start, stop, step = args.node_range
        if step <= 0 or stop < start:
            parser.error("node range requires STOP >= START and STEP > 0")
        selected_nodes = set(range(start, stop + 1, step))
    else:
        selected_nodes = set(args.node_ids)
    animations = sorted(glob.glob(args.animation_glob), key=animation_number)
    if not animations:
        parser.error("no animation files matched")

    rows = []
    for animation in animations:
        time, force_x, force_y, force_z = extract(animation, args.converter, selected_nodes)
        rows.append((animation_number(animation), time, force_x, force_y, force_z))
        print(
            f"{Path(animation).name}: t={time:.8g}, "
            f"Fx={force_x:.8g}, Fy={force_y:.8g}, Fz={force_z:.8g}",
            flush=True,
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["animation", "time", "fint_x", "fint_y", "fint_z"])
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
