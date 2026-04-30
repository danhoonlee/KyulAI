"""GointMLP-inspired response surrogate for DD laminates."""

from __future__ import annotations

import torch
import torch.nn as nn


class ResponseBranch(nn.Module):
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


class DDResponseGointSurrogate(nn.Module):
    """JointMLP-style multi-task model for Type, scalar response, and curve."""

    def __init__(
        self,
        input_dim: int,
        seq_len: int,
        hidden_dim: int = 48,
        num_branches: int = 8,
        dropout: float = 0.14,
    ):
        super().__init__()
        self.branches = nn.ModuleList([ResponseBranch(input_dim, hidden_dim, dropout) for _ in range(num_branches)])
        joined_dim = hidden_dim * num_branches
        self.shared = nn.Sequential(
            nn.LayerNorm(joined_dim),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Linear(joined_dim, 3)
        self.ordinal = nn.Linear(joined_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim * 2),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim * 4),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, seq_len),
            nn.Softplus(),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        joined = torch.cat([branch(x) for branch in self.branches], dim=-1)
        shared = self.shared(joined)
        return (
            self.classifier(shared),
            self.ordinal(shared),
            self.scalar_head(shared),
            self.curve_head(shared),
        )


def predict_from_logits(class_logits: torch.Tensor) -> torch.Tensor:
    return torch.argmax(class_logits, dim=1)


def ordinal_targets(labels: torch.Tensor) -> torch.Tensor:
    return torch.stack([(labels > 0).float(), (labels > 1).float()], dim=1)


__all__ = [
    "DDResponseGointSurrogate",
    "ordinal_targets",
    "predict_from_logits",
]
