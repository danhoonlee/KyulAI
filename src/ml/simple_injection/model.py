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


class SimpleInjectionDeepONetSurrogate(nn.Module):
    """DeepONet-style operator model for pressure as a function of DOE inputs and time."""

    def __init__(
        self,
        input_dim: int,
        latent_dim: int = 96,
        branch_hidden_dim: int = 96,
        trunk_hidden_dim: int = 96,
        dropout: float = 0.08,
        fourier_features: int = 8,
    ):
        super().__init__()
        self.fourier_features = fourier_features
        trunk_input_dim = 1 + fourier_features * 2
        self.branch = nn.Sequential(
            nn.Linear(input_dim, branch_hidden_dim),
            nn.LayerNorm(branch_hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(branch_hidden_dim, branch_hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(branch_hidden_dim, latent_dim),
        )
        self.trunk = nn.Sequential(
            nn.Linear(trunk_input_dim, trunk_hidden_dim),
            nn.LayerNorm(trunk_hidden_dim),
            nn.SiLU(),
            nn.Linear(trunk_hidden_dim, trunk_hidden_dim),
            nn.SiLU(),
            nn.Linear(trunk_hidden_dim, latent_dim),
        )
        self.curve_bias = nn.Parameter(torch.zeros(1))
        self.scalar_head = nn.Sequential(
            nn.Linear(latent_dim, branch_hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(branch_hidden_dim, 2),
        )

    def _encode_time(self, grid: torch.Tensor) -> torch.Tensor:
        t = grid.reshape(-1, 1)
        if self.fourier_features <= 0:
            return t
        freqs = torch.arange(1, self.fourier_features + 1, dtype=t.dtype, device=t.device).reshape(1, -1)
        angles = 2.0 * torch.pi * t * freqs
        return torch.cat([t, torch.sin(angles), torch.cos(angles)], dim=-1)

    def forward(self, x: torch.Tensor, grid: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        branch_latent = self.branch(x)
        trunk_latent = self.trunk(self._encode_time(grid))
        curve_raw = torch.einsum("bd,td->bt", branch_latent, trunk_latent)
        curve_raw = curve_raw / max(1.0, branch_latent.shape[-1] ** 0.5)
        curve = torch.nn.functional.softplus(curve_raw + self.curve_bias)
        return self.scalar_head(branch_latent), curve


class SimpleInjectionHistogramDeepONetRegressor(nn.Module):
    """DeepONet-style model for compact filling-pressure histogram summaries."""

    def __init__(
        self,
        input_dim: int,
        bins: int = 10,
        latent_dim: int = 80,
        branch_hidden_dim: int = 80,
        trunk_hidden_dim: int = 80,
        dropout: float = 0.08,
        fourier_features: int = 4,
    ):
        super().__init__()
        self.bins = bins
        self.fourier_features = fourier_features
        trunk_input_dim = 1 + fourier_features * 2
        self.branch = nn.Sequential(
            nn.Linear(input_dim, branch_hidden_dim),
            nn.LayerNorm(branch_hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(branch_hidden_dim, branch_hidden_dim),
            nn.SiLU(),
            nn.Linear(branch_hidden_dim, latent_dim),
        )
        self.trunk = nn.Sequential(
            nn.Linear(trunk_input_dim, trunk_hidden_dim),
            nn.LayerNorm(trunk_hidden_dim),
            nn.SiLU(),
            nn.Linear(trunk_hidden_dim, latent_dim),
        )
        self.stats_head = nn.Sequential(
            nn.Linear(latent_dim, branch_hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(branch_hidden_dim, 4),
        )
        self.ratio_bias = nn.Parameter(torch.zeros(1))

    def _encode_bin(self, grid: torch.Tensor) -> torch.Tensor:
        t = grid.reshape(-1, 1)
        if self.fourier_features <= 0:
            return t
        freqs = torch.arange(1, self.fourier_features + 1, dtype=t.dtype, device=t.device).reshape(1, -1)
        angles = 2.0 * torch.pi * t * freqs
        return torch.cat([t, torch.sin(angles), torch.cos(angles)], dim=-1)

    def forward(self, x: torch.Tensor, bin_grid: torch.Tensor) -> torch.Tensor:
        branch_latent = self.branch(x)
        trunk_latent = self.trunk(self._encode_bin(bin_grid))
        ratio_raw = torch.einsum("bd,td->bt", branch_latent, trunk_latent)
        ratio_raw = ratio_raw / max(1.0, branch_latent.shape[-1] ** 0.5)
        return torch.cat([self.stats_head(branch_latent), ratio_raw + self.ratio_bias], dim=1)


__all__ = [
    "SimpleInjectionDeepONetSurrogate",
    "SimpleInjectionGointRegressor",
    "SimpleInjectionGointSurrogate",
    "SimpleInjectionHistogramDeepONetRegressor",
]
