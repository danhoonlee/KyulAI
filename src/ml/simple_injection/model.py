"""GointMLP-inspired neural surrogate for Simple Injection pressure curves."""

from __future__ import annotations

import torch
import torch.nn as nn


class PressureBranch(nn.Module):
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


class SimpleInjectionGointSurrogate(nn.Module):
    """Multi-branch MLP that jointly predicts pressure scalars and curve shape."""

    def __init__(
        self,
        input_dim: int,
        seq_len: int,
        hidden_dim: int = 48,
        num_branches: int = 8,
        dropout: float = 0.12,
    ):
        super().__init__()
        self.branches = nn.ModuleList(
            [PressureBranch(input_dim, hidden_dim, dropout) for _ in range(num_branches)]
        )
        joined_dim = hidden_dim * num_branches
        self.shared = nn.Sequential(
            nn.LayerNorm(joined_dim),
            nn.Dropout(dropout),
        )
        self.scalar_head = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim * 2),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, 2),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim * 4),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 4, seq_len),
            nn.Softplus(),
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        joined = torch.cat([branch(x) for branch in self.branches], dim=-1)
        shared = self.shared(joined)
        return self.scalar_head(shared), self.curve_head(shared)


class SimpleInjectionGointRegressor(nn.Module):
    """Multi-branch MLP for compact tabular Moldex3D targets."""

    def __init__(
        self,
        input_dim: int,
        output_dim: int,
        hidden_dim: int = 48,
        num_branches: int = 8,
        dropout: float = 0.12,
    ):
        super().__init__()
        self.branches = nn.ModuleList(
            [PressureBranch(input_dim, hidden_dim, dropout) for _ in range(num_branches)]
        )
        joined_dim = hidden_dim * num_branches
        self.head = nn.Sequential(
            nn.LayerNorm(joined_dim),
            nn.Dropout(dropout),
            nn.Linear(joined_dim, hidden_dim * 3),
            nn.LeakyReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 3, hidden_dim),
            nn.LeakyReLU(),
            nn.Linear(hidden_dim, output_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        joined = torch.cat([branch(x) for branch in self.branches], dim=-1)
        return self.head(joined)


__all__ = ["SimpleInjectionGointRegressor", "SimpleInjectionGointSurrogate"]
