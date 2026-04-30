"""GointMLP-inspired theta/case deep classifier for DD laminates."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset

from .deep_sequence import combined_loss, predict_from_logits


@dataclass(frozen=True)
class DDThetaSample:
    case: str
    test_id: str
    theta1: float
    theta2: float
    label: int


def load_theta_samples(data_dir: str | Path, cases: Iterable[str] = ("Case3", "Case4")) -> list[DDThetaSample]:
    data_path = Path(data_dir)
    samples: list[DDThetaSample] = []
    for case in cases:
        with (data_path / case / "transition_load.csv").open(newline="") as f:
            for row in csv.DictReader(f):
                samples.append(
                    DDThetaSample(
                        case=case,
                        test_id=row["Test_ID"],
                        theta1=float(row["Theta1"]),
                        theta2=float(row["Theta2"]),
                        label=int(row["type"]),
                    )
                )
    return samples


class DDThetaDataset(Dataset):
    def __init__(self, samples: list[DDThetaSample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        sample = self.samples[idx]
        features = np.array([
            sample.theta1 / 90.0,
            sample.theta2 / 90.0,
            1.0 if sample.case == "Case4" else 0.0,
        ], dtype=np.float32)
        return {
            "x": torch.tensor(features, dtype=torch.float32),
            "label": torch.tensor(sample.label - 1, dtype=torch.long),
            "case": sample.case,
            "test_id": sample.test_id,
        }


class ThetaBranch(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LeakyReLU(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DDThetaGointClassifier(nn.Module):
    """JointMLP-style theta/case classifier with ordinal auxiliary head."""

    def __init__(self, input_dim: int = 3, hidden_dim: int = 32, num_branches: int = 8, dropout: float = 0.12):
        super().__init__()
        self.branches = nn.ModuleList([ThetaBranch(input_dim, hidden_dim, dropout) for _ in range(num_branches)])
        joined_dim = hidden_dim * num_branches
        self.shared = nn.Sequential(
            nn.LayerNorm(joined_dim),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Linear(joined_dim, 3)
        self.ordinal = nn.Linear(joined_dim, 2)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        joined = torch.cat([branch(x) for branch in self.branches], dim=-1)
        shared = self.shared(joined)
        return self.classifier(shared), self.ordinal(shared)


__all__ = [
    "DDThetaSample",
    "DDThetaDataset",
    "DDThetaGointClassifier",
    "load_theta_samples",
    "combined_loss",
    "predict_from_logits",
]
