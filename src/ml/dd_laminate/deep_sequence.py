"""GointMLP-inspired deep sequence classifier for DD laminate curves.

The old GointMLP project used a GRU over sequences followed by a JointMLP head
and CORAL ordinal classification. This module adapts that idea to DD laminate
force-displacement curves without requiring pytorch-lightning, coral_pytorch, or
sparsemax.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset


@dataclass(frozen=True)
class DDSequenceSample:
    case: str
    test_id: str
    theta1: float
    theta2: float
    pt: float
    label: int
    csv_path: Path


def _row_value(row: dict[str, str], *keys: str) -> str:
    normalized = {key.lower().replace("_", ""): value for key, value in row.items()}
    for key in keys:
        if key in row:
            return row[key]
        compact = key.lower().replace("_", "")
        if compact in normalized:
            return normalized[compact]
    raise KeyError(f"Missing one of {keys}. Available columns: {list(row.keys())}")


def _curve_csv_path(case_dir: Path, test_id: str) -> Path:
    candidates = [
        case_dir / "csv_load" / f"force_disp_Test_{test_id}.csv",
        case_dir / "csv_load" / f"force_disp_{test_id}.csv",
    ]
    if test_id.startswith("Test_"):
        candidates.extend(
            [
                case_dir / "csv_load" / f"force_disp_{test_id}.csv",
                case_dir / "csv_load" / f"force_disp_{test_id.replace('Test_', '')}.csv",
            ]
        )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_sequence_samples(data_dir: str | Path, cases: Iterable[str] = ("Case3", "Case4")) -> list[DDSequenceSample]:
    data_path = Path(data_dir)
    samples: list[DDSequenceSample] = []
    for case in cases:
        case_dir = data_path / case
        with (case_dir / "transition_load.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                test_id = _row_value(row, "Test_ID", "test_id")
                samples.append(
                    DDSequenceSample(
                        case=case,
                        test_id=test_id,
                        theta1=float(_row_value(row, "Theta1", "theta1")),
                        theta2=float(_row_value(row, "Theta2", "theta2")),
                        pt=float(_row_value(row, "Pt", "pt")),
                        label=int(row["type"]),
                        csv_path=_curve_csv_path(case_dir, test_id),
                    )
                )
    return samples


def _read_curve(path: Path) -> tuple[np.ndarray, np.ndarray]:
    arr = np.loadtxt(path, delimiter=",")
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise ValueError(f"Expected two-column force-displacement CSV: {path}")
    return arr[:, 0].astype(float), arr[:, 1].astype(float)


def _resample_curve(x: np.ndarray, y: np.ndarray, seq_len: int) -> tuple[np.ndarray, np.ndarray]:
    if len(x) < 2:
        raise ValueError("Curve must have at least two points")
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]
    unique_x, unique_idx = np.unique(x_sorted, return_index=True)
    unique_y = y_sorted[unique_idx]
    if len(unique_x) < 2:
        t_old = np.linspace(0.0, 1.0, len(y_sorted))
        t_new = np.linspace(0.0, 1.0, seq_len)
        y_new = np.interp(t_new, t_old, y_sorted)
        return t_new, y_new
    x_new = np.linspace(float(unique_x[0]), float(unique_x[-1]), seq_len)
    y_new = np.interp(x_new, unique_x, unique_y)
    return x_new, y_new


class DDSequenceDataset(Dataset):
    """Fixed-length sequence dataset for DD force-displacement curves."""

    def __init__(
        self,
        samples: list[DDSequenceSample],
        seq_len: int = 256,
        pt_scale: float | None = None,
    ):
        self.samples = samples
        self.seq_len = seq_len
        self.pt_scale = pt_scale or max(max(s.pt for s in samples), 1.0)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        sample = self.samples[idx]
        x, y = _read_curve(sample.csv_path)
        x_resampled, y_resampled = _resample_curve(x, y, self.seq_len)

        x_min = float(np.min(x_resampled))
        x_span = max(1e-9, float(np.max(x_resampled) - x_min))
        y_span = max(1e-9, float(max(np.max(y_resampled), sample.pt)))

        displacement_norm = (x_resampled - x_min) / x_span
        load_norm = y_resampled / y_span
        step_norm = np.linspace(0.0, 1.0, self.seq_len)
        theta1 = np.full(self.seq_len, sample.theta1 / 90.0)
        theta2 = np.full(self.seq_len, sample.theta2 / 90.0)
        pt = np.full(self.seq_len, sample.pt / self.pt_scale)
        case_id_map = {"Case2": 0.0, "Case3": 0.5, "Case4": 1.0}
        case_id = np.full(self.seq_len, case_id_map.get(sample.case, 0.5))
        load_to_pt = y_resampled / max(1e-9, sample.pt)

        features = np.stack(
            [
                displacement_norm,
                load_norm,
                step_norm,
                theta1,
                theta2,
                pt,
                case_id,
                load_to_pt,
            ],
            axis=1,
        ).astype(np.float32)

        # Labels are stored as Type 1/2/3. Training uses 0/1/2.
        label = sample.label - 1
        return {
            "x": torch.tensor(features, dtype=torch.float32),
            "label": torch.tensor(label, dtype=torch.long),
            "case": sample.case,
            "test_id": sample.test_id,
        }


class JointMLPHead(nn.Module):
    """Small multi-branch MLP head inspired by the old JointMLP module."""

    def __init__(self, input_dim: int, branch_dim: int = 32, num_branches: int = 4, dropout: float = 0.15):
        super().__init__()
        self.branches = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(input_dim, branch_dim),
                    nn.LayerNorm(branch_dim),
                    nn.LeakyReLU(),
                    nn.Dropout(dropout),
                    nn.Linear(branch_dim, branch_dim),
                    nn.LeakyReLU(),
                )
                for _ in range(num_branches)
            ]
        )
        joined = branch_dim * num_branches
        self.classifier = nn.Sequential(
            nn.LayerNorm(joined),
            nn.Dropout(dropout),
            nn.Linear(joined, 3),
        )
        self.ordinal = nn.Sequential(
            nn.LayerNorm(joined),
            nn.Dropout(dropout),
            nn.Linear(joined, 2),
        )

    def forward(self, features: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        joined = torch.cat([branch(features) for branch in self.branches], dim=-1)
        return self.classifier(joined), self.ordinal(joined)


class DDGointSequenceClassifier(nn.Module):
    """GRU encoder + JointMLP-style head for DD curve Type classification."""

    def __init__(
        self,
        input_size: int = 8,
        hidden_size: int = 64,
        gru_layers: int = 2,
        branch_dim: int = 32,
        num_branches: int = 4,
        dropout: float = 0.15,
    ):
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=gru_layers,
            batch_first=True,
            dropout=dropout if gru_layers > 1 else 0.0,
            bidirectional=True,
        )
        self.head = JointMLPHead(
            input_dim=hidden_size * 4,
            branch_dim=branch_dim,
            num_branches=num_branches,
            dropout=dropout,
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        outputs, _ = self.gru(x)
        pooled_mean = outputs.mean(dim=1)
        pooled_max = outputs.max(dim=1).values
        pooled = torch.cat([pooled_mean, pooled_max], dim=-1)
        return self.head(pooled)


def ordinal_targets(labels: torch.Tensor, num_classes: int = 3) -> torch.Tensor:
    """Encode labels 0/1/2 as CORAL-style ordinal levels."""
    levels = []
    for threshold in range(num_classes - 1):
        levels.append((labels > threshold).float())
    return torch.stack(levels, dim=1)


def combined_loss(
    class_logits: torch.Tensor,
    ordinal_logits: torch.Tensor,
    labels: torch.Tensor,
    ordinal_weight: float = 0.35,
    class_weights: torch.Tensor | None = None,
) -> torch.Tensor:
    ce = nn.functional.cross_entropy(class_logits, labels, weight=class_weights)
    ordinal = nn.functional.binary_cross_entropy_with_logits(
        ordinal_logits,
        ordinal_targets(labels, num_classes=3).to(ordinal_logits.device),
    )
    return ce + ordinal_weight * ordinal


def predict_from_logits(class_logits: torch.Tensor) -> torch.Tensor:
    return class_logits.argmax(dim=1)


def choose_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")
