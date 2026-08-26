#!/usr/bin/env python3
"""Recover nodal reaction force from the impulse columns exported by th_to_csv."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


GLOBAL_COLUMN_COUNT = 23


def derivative(times: list[float], values: list[float]) -> list[float]:
    if len(times) < 3:
        raise ValueError("at least three time samples are required")
    result = [0.0] * len(times)
    dt0 = times[1] - times[0]
    dt1 = times[2] - times[1]
    if abs(dt0 - dt1) > 1e-12 * max(1.0, abs(dt0), abs(dt1)):
        raise ValueError("reaction extraction currently requires uniform time-history output")
    result[0] = (-3.0 * values[0] + 4.0 * values[1] - values[2]) / (2.0 * dt0)
    for index in range(1, len(times) - 1):
        result[index] = (values[index + 1] - values[index - 1]) / (
            times[index + 1] - times[index - 1]
        )
    result[-1] = (3.0 * values[-1] - 4.0 * values[-2] + values[-3]) / (2.0 * dt0)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.input.open(newline="") as stream:
        rows = list(csv.reader(stream))
    header, data_rows = rows[0], rows[1:]
    if (len(header) - GLOBAL_COLUMN_COUNT) % 2 != 0:
        raise ValueError("expected paired displacement and reaction-impulse node columns")
    displacement_columns = range(GLOBAL_COLUMN_COUNT, len(header), 2)
    impulse_columns = range(GLOBAL_COLUMN_COUNT + 1, len(header), 2)
    node_count = len(list(displacement_columns))
    times = [float(row[0]) for row in data_rows]
    displacement = [
        -sum(float(row[index]) for index in displacement_columns) / node_count
        for row in data_rows
    ]
    reaction_impulse = [
        -sum(float(row[index]) for index in impulse_columns) for row in data_rows
    ]
    reaction_force = derivative(times, reaction_impulse)
    with args.output.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["time", "imposed_displacement", "reaction_force", "reaction_impulse"])
        writer.writerows(zip(times, displacement, reaction_force, reaction_impulse))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
