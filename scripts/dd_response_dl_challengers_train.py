"""Evaluate Laminate Forecast deep-learning challengers against GointMLP."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.decomposition import PCA
from sklearn.metrics import f1_score
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader, Subset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.dd_response_physics_xai_train import make_response_targets
from src.ml.dd_laminate.laminate_physics import _case_stack
from src.ml.dd_laminate.response_deep import ordinal_targets, predict_from_logits
from src.ml.dd_laminate.response_feature_sets import (
    SUPPORTED_RESPONSE_FEATURE_SETS,
    response_feature_matrix,
)
from src.ml.dd_laminate.train_cases_2_3_4_classical import CURVE_GRID_LEN, load_records
from src.ml.dd_laminate.train_cases_2_3_4_goint import (
    class_weights,
    normalize,
    response_metric_row,
)

METRIC_KEYS = (
    "accuracy",
    "macro_f1",
    "pt_mae",
    "max_displacement_mae",
    "max_force_mae",
    "curve_norm_rmse",
    "curve_force_rmse",
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class PlainMLPResponse(nn.Module):
    def __init__(self, input_dim: int, seq_len: int, hidden_dim: int, dropout: float):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
        )
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.encoder(x)
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Dropout(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.net(x)


class ResidualMLPResponse(nn.Module):
    def __init__(self, input_dim: int, seq_len: int, hidden_dim: int, depth: int, dropout: float):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.GELU()
        )
        self.blocks = nn.Sequential(*[ResidualBlock(hidden_dim, dropout) for _ in range(depth)])
        self.norm = nn.LayerNorm(hidden_dim)
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.norm(self.blocks(self.input(x)))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class GatedBlock(nn.Module):
    def __init__(self, hidden_dim: int, dropout: float):
        super().__init__()
        self.norm = nn.LayerNorm(hidden_dim)
        self.value = nn.Linear(hidden_dim, hidden_dim)
        self.gate = nn.Linear(hidden_dim, hidden_dim)
        self.dropout = nn.Dropout(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.norm(x)
        return x + self.dropout(torch.tanh(self.value(z)) * torch.sigmoid(self.gate(z)))


class GatedMLPResponse(nn.Module):
    def __init__(self, input_dim: int, seq_len: int, hidden_dim: int, depth: int, dropout: float):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.SiLU()
        )
        self.blocks = nn.Sequential(*[GatedBlock(hidden_dim, dropout) for _ in range(depth)])
        self.norm = nn.LayerNorm(hidden_dim)
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.norm(self.blocks(self.input(x)))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class PhysicsGuidedMLPResponse(nn.Module):
    """Gated response surrogate with soft physics penalties applied in training."""

    physics_guided = True

    def __init__(self, input_dim: int, seq_len: int, hidden_dim: int, depth: int, dropout: float):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.SiLU()
        )
        self.blocks = nn.Sequential(*[GatedBlock(hidden_dim, dropout) for _ in range(depth)])
        self.norm = nn.LayerNorm(hidden_dim)
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.norm(self.blocks(self.input(x)))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class DeepONetResponse(nn.Module):
    """DeepONet-style response model: branch features times learned grid basis."""

    def __init__(
        self, input_dim: int, seq_len: int, hidden_dim: int, basis_dim: int, dropout: float
    ):
        super().__init__()
        self.branch = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualBlock(hidden_dim, dropout),
            ResidualBlock(hidden_dim, dropout),
            nn.LayerNorm(hidden_dim),
        )
        self.coeff = nn.Linear(hidden_dim, basis_dim)
        self.trunk = nn.Sequential(
            nn.Linear(1, hidden_dim // 2),
            nn.GELU(),
            nn.Linear(hidden_dim // 2, basis_dim),
        )
        self.curve_bias = nn.Parameter(torch.zeros(seq_len))
        grid = torch.linspace(0.0, 1.0, seq_len).view(seq_len, 1)
        self.register_buffer("grid", grid)
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.branch(x)
        coeff = self.coeff(z)
        basis = self.trunk(self.grid)
        curve = F.softplus(torch.einsum("bd,td->bt", coeff, basis) + self.curve_bias)
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), curve


class PCACurveMLPResponse(nn.Module):
    """Curve-focused MLP that predicts coefficients for a fixed PCA/POD basis."""

    pca_curve_head = True

    def __init__(
        self,
        input_dim: int,
        hidden_dim: int,
        depth: int,
        dropout: float,
        curve_mean: np.ndarray,
        curve_basis: np.ndarray,
    ):
        super().__init__()
        self.input = nn.Sequential(
            nn.Linear(input_dim, hidden_dim), nn.LayerNorm(hidden_dim), nn.SiLU()
        )
        self.blocks = nn.Sequential(*[GatedBlock(hidden_dim, dropout) for _ in range(depth)])
        self.norm = nn.LayerNorm(hidden_dim)
        n_components = int(curve_basis.shape[0])
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_coeff_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.SiLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, n_components),
        )
        self.curve_mean: torch.Tensor
        self.curve_basis: torch.Tensor
        self.register_buffer("curve_mean", torch.tensor(curve_mean, dtype=torch.float32))
        self.register_buffer("curve_basis", torch.tensor(curve_basis, dtype=torch.float32))

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        z = self.norm(self.blocks(self.input(x)))
        coeff = self.curve_coeff_head(z)
        curve = torch.einsum("bc,ct->bt", coeff, self.curve_basis) + self.curve_mean
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), curve


class StackResponseDataset(torch.utils.data.Dataset):
    def __init__(
        self,
        x: np.ndarray,
        stack_features: np.ndarray,
        y_class: np.ndarray,
        y_scalars_norm: np.ndarray,
        y_curve: np.ndarray,
    ):
        self.x = torch.tensor(x, dtype=torch.float32)
        self.stack = torch.tensor(stack_features, dtype=torch.float32)
        self.y_class = torch.tensor(y_class - 1, dtype=torch.long)
        self.y_scalars_norm = torch.tensor(y_scalars_norm, dtype=torch.float32)
        self.y_curve = torch.tensor(y_curve, dtype=torch.float32)

    def __len__(self) -> int:
        return len(self.y_class)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        return {
            "x": self.x[idx],
            "stack": self.stack[idx],
            "label": self.y_class[idx],
            "scalars": self.y_scalars_norm[idx],
            "curve": self.y_curve[idx],
        }


def build_stack_features(records) -> np.ndarray:
    rows: list[np.ndarray] = []
    case_index = {"Case2": 0.0, "Case3": 0.5, "Case4": 1.0}
    for record in records:
        stack = np.asarray(
            _case_stack(record.case, float(record.theta1), float(record.theta2)), dtype=float
        )
        z = np.linspace(-1.0, 1.0, len(stack), dtype=float)
        theta_rad = np.deg2rad(stack)
        case_value = np.full_like(stack, case_index.get(record.case, 0.0), dtype=float)
        theta1_flag = np.isclose(np.abs(stack), abs(float(record.theta1))).astype(float)
        theta2_flag = np.isclose(np.abs(stack), abs(float(record.theta2))).astype(float)
        rows.append(
            np.stack(
                [
                    stack / 90.0,
                    np.sin(theta_rad),
                    np.cos(theta_rad),
                    np.sin(2.0 * theta_rad),
                    np.cos(2.0 * theta_rad),
                    np.sign(stack),
                    z,
                    case_value,
                    theta1_flag,
                    theta2_flag,
                ],
                axis=1,
            )
        )
    return np.asarray(rows, dtype=float)


class LSTMStackResponse(nn.Module):
    def __init__(
        self, input_dim: int, stack_dim: int, seq_len: int, hidden_dim: int, dropout: float
    ):
        super().__init__()
        seq_hidden = max(32, hidden_dim // 2)
        self.stack_encoder = nn.LSTM(
            input_size=stack_dim,
            hidden_size=seq_hidden,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True,
        )
        self.global_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        joined_dim = hidden_dim + seq_hidden * 4
        self.fuse = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if stack is None:
            raise ValueError("LSTMStackResponse requires stack features.")
        seq_out, _ = self.stack_encoder(stack)
        seq_pool = torch.cat([seq_out.mean(dim=1), seq_out.amax(dim=1)], dim=-1)
        z = self.fuse(torch.cat([self.global_encoder(x), seq_pool], dim=-1))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class GRUStackResponse(nn.Module):
    def __init__(
        self, input_dim: int, stack_dim: int, seq_len: int, hidden_dim: int, dropout: float
    ):
        super().__init__()
        seq_hidden = max(32, hidden_dim // 2)
        self.stack_encoder = nn.GRU(
            input_size=stack_dim,
            hidden_size=seq_hidden,
            num_layers=2,
            batch_first=True,
            dropout=dropout,
            bidirectional=True,
        )
        self.global_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        joined_dim = hidden_dim + seq_hidden * 4
        self.fuse = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if stack is None:
            raise ValueError("GRUStackResponse requires stack features.")
        seq_out, _ = self.stack_encoder(stack)
        seq_pool = torch.cat([seq_out.mean(dim=1), seq_out.amax(dim=1)], dim=-1)
        z = self.fuse(torch.cat([self.global_encoder(x), seq_pool], dim=-1))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class GraphConvLayer(nn.Module):
    def __init__(self, input_dim: int, output_dim: int):
        super().__init__()
        self.linear = nn.Linear(input_dim, output_dim)

    def forward(self, nodes: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        mixed = torch.einsum("ij,bjf->bif", adjacency, nodes)
        return F.gelu(self.linear(mixed))


class StackGraphResponse(nn.Module):
    def __init__(
        self, input_dim: int, stack_dim: int, seq_len: int, hidden_dim: int, dropout: float
    ):
        super().__init__()
        graph_hidden = max(48, hidden_dim // 2)
        adjacency = torch.eye(16)
        for idx in range(15):
            adjacency[idx, idx + 1] = 1.0
            adjacency[idx + 1, idx] = 1.0
        degree = adjacency.sum(dim=1, keepdim=True).clamp_min(1.0)
        self.register_buffer("adjacency", adjacency / degree)
        self.gcn1 = GraphConvLayer(stack_dim, graph_hidden)
        self.gcn2 = GraphConvLayer(graph_hidden, graph_hidden)
        self.global_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        joined_dim = hidden_dim + graph_hidden * 2
        self.fuse = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualBlock(hidden_dim, dropout),
        )
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if stack is None:
            raise ValueError("StackGraphResponse requires stack features.")
        nodes = self.gcn2(self.gcn1(stack, self.adjacency), self.adjacency)
        graph_pool = torch.cat([nodes.mean(dim=1), nodes.amax(dim=1)], dim=-1)
        z = self.fuse(torch.cat([self.global_encoder(x), graph_pool], dim=-1))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


class GraphAttentionLayer(nn.Module):
    def __init__(self, input_dim: int, output_dim: int, dropout: float):
        super().__init__()
        self.query = nn.Linear(input_dim, output_dim)
        self.key = nn.Linear(input_dim, output_dim)
        self.value = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        self.scale = output_dim**-0.5

    def forward(self, nodes: torch.Tensor, adjacency_mask: torch.Tensor) -> torch.Tensor:
        q = self.query(nodes)
        k = self.key(nodes)
        v = self.value(nodes)
        score = torch.einsum("bid,bjd->bij", q, k) * self.scale
        score = score.masked_fill(~adjacency_mask, -1e9)
        attn = self.dropout(torch.softmax(score, dim=-1))
        return F.gelu(torch.einsum("bij,bjd->bid", attn, v))


class StackGATResponse(nn.Module):
    def __init__(
        self, input_dim: int, stack_dim: int, seq_len: int, hidden_dim: int, dropout: float
    ):
        super().__init__()
        graph_hidden = max(48, hidden_dim // 2)
        adjacency = torch.eye(16, dtype=torch.bool)
        for idx in range(15):
            adjacency[idx, idx + 1] = True
            adjacency[idx + 1, idx] = True
        self.register_buffer("adjacency_mask", adjacency)
        self.attn1 = GraphAttentionLayer(stack_dim, graph_hidden, dropout)
        self.attn2 = GraphAttentionLayer(graph_hidden, graph_hidden, dropout)
        self.global_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )
        joined_dim = hidden_dim + graph_hidden * 2
        self.fuse = nn.Sequential(
            nn.Linear(joined_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            ResidualBlock(hidden_dim, dropout),
        )
        self.classifier = nn.Linear(hidden_dim, 3)
        self.ordinal = nn.Linear(hidden_dim, 2)
        self.scalar_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, 3),
        )
        self.curve_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, seq_len),
            nn.Softplus(),
        )

    def forward(
        self, x: torch.Tensor, stack: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        if stack is None:
            raise ValueError("StackGATResponse requires stack features.")
        nodes = self.attn2(self.attn1(stack, self.adjacency_mask), self.adjacency_mask)
        graph_pool = torch.cat([nodes.mean(dim=1), nodes.amax(dim=1)], dim=-1)
        z = self.fuse(torch.cat([self.global_encoder(x), graph_pool], dim=-1))
        return self.classifier(z), self.ordinal(z), self.scalar_head(z), self.curve_head(z)


def candidate_factories(
    args: argparse.Namespace, stack_dim: int
) -> dict[str, Callable[[int, int], nn.Module]]:
    return {
        "plain_mlp": lambda input_dim, seq_len: PlainMLPResponse(
            input_dim, seq_len, args.hidden_dim, args.dropout
        ),
        "residual_mlp": lambda input_dim, seq_len: ResidualMLPResponse(
            input_dim, seq_len, args.hidden_dim, args.depth, args.dropout
        ),
        "gated_mlp": lambda input_dim, seq_len: GatedMLPResponse(
            input_dim,
            seq_len,
            max(64, args.hidden_dim - 32),
            args.depth + 1,
            max(0.05, args.dropout - 0.02),
        ),
        "physics_guided_mlp": lambda input_dim, seq_len: PhysicsGuidedMLPResponse(
            input_dim,
            seq_len,
            max(64, args.hidden_dim - 32),
            args.depth + 1,
            max(0.05, args.dropout - 0.02),
        ),
        "deeponet_response": lambda input_dim, seq_len: DeepONetResponse(
            input_dim, seq_len, args.hidden_dim, args.basis_dim, args.dropout
        ),
        "pca_curve_mlp": lambda input_dim, seq_len: GatedMLPResponse(
            input_dim,
            seq_len,
            max(64, args.hidden_dim - 32),
            args.depth + 1,
            max(0.05, args.dropout - 0.02),
        ),
        "stack_lstm": lambda input_dim, seq_len: LSTMStackResponse(
            input_dim, stack_dim, seq_len, args.hidden_dim, args.dropout
        ),
        "stack_gru": lambda input_dim, seq_len: GRUStackResponse(
            input_dim, stack_dim, seq_len, args.hidden_dim, args.dropout
        ),
        "stack_gnn": lambda input_dim, seq_len: StackGraphResponse(
            input_dim, stack_dim, seq_len, args.hidden_dim, args.dropout
        ),
        "stack_gat": lambda input_dim, seq_len: StackGATResponse(
            input_dim, stack_dim, seq_len, args.hidden_dim, args.dropout
        ),
    }


def soft_physics_loss(pred_curve: torch.Tensor) -> torch.Tensor:
    start_loss = pred_curve[:, 0].square().mean()
    peak_loss = (pred_curve.amax(dim=1) - 1.0).square().mean()
    monotonic_loss = F.relu(pred_curve[:, :-1] - pred_curve[:, 1:]).mean()
    curvature = pred_curve[:, 2:] - 2.0 * pred_curve[:, 1:-1] + pred_curve[:, :-2]
    curvature_loss = curvature.square().mean()
    return 0.15 * start_loss + 0.10 * peak_loss + 0.10 * monotonic_loss + 0.03 * curvature_loss


def pt_consistency_loss(
    pred_curve: torch.Tensor,
    scalars_norm: torch.Tensor,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
) -> torch.Tensor:
    mean = torch.as_tensor(scalar_mean, dtype=pred_curve.dtype, device=pred_curve.device)
    std = torch.as_tensor(scalar_std, dtype=pred_curve.dtype, device=pred_curve.device)
    scalars = torch.expm1(scalars_norm * std + mean)
    pt_norm = (scalars[:, 0] / scalars[:, 2].clamp_min(1e-6)).clamp(0.0, 1.5)
    distances = (pred_curve - pt_norm[:, None]).abs()
    soft_min = -torch.logsumexp(-distances / 0.025, dim=1) * 0.025
    range_low = pred_curve.amin(dim=1)
    range_high = pred_curve.amax(dim=1)
    outside_low = F.relu(range_low - pt_norm)
    outside_high = F.relu(pt_norm - range_high)
    return soft_min.mean() + 0.5 * (outside_low.square().mean() + outside_high.square().mean())


def run_epoch(
    model, loader, optimizer, weights, device: torch.device, train: bool, args
) -> dict[str, Any]:
    model.train(mode=train)
    y_true: list[int] = []
    y_pred: list[int] = []
    scalar_pred: list[np.ndarray] = []
    scalar_true: list[np.ndarray] = []
    curve_pred: list[np.ndarray] = []
    curve_true: list[np.ndarray] = []
    total_loss = 0.0
    total_n = 0
    with torch.set_grad_enabled(train):
        for batch in loader:
            x = batch["x"].to(device)
            stack = batch["stack"].to(device)
            labels = batch["label"].to(device)
            scalars = batch["scalars"].to(device)
            curve = batch["curve"].to(device)
            if train:
                optimizer.zero_grad(set_to_none=True)
            class_logits, ordinal_logits, pred_scalars, pred_curve = model(x, stack)
            class_loss = F.cross_entropy(class_logits, labels, weight=weights)
            ordinal_loss = F.binary_cross_entropy_with_logits(
                ordinal_logits, ordinal_targets(labels)
            )
            scalar_loss = F.smooth_l1_loss(pred_scalars, scalars)
            curve_loss = F.smooth_l1_loss(pred_curve, curve)
            loss = (
                class_loss
                + args.ordinal_weight * ordinal_loss
                + args.scalar_weight * scalar_loss
                + args.curve_weight * curve_loss
            )
            if getattr(model, "physics_guided", False):
                loss = loss + args.physics_weight * soft_physics_loss(pred_curve)
            if args.pt_consistency_weight > 0:
                loss = loss + args.pt_consistency_weight * pt_consistency_loss(
                    pred_curve, scalars, args.scalar_mean, args.scalar_std
                )
            if train:
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                optimizer.step()
            pred = predict_from_logits(class_logits)
            total_loss += float(loss.detach().cpu()) * labels.numel()
            total_n += labels.numel()
            y_true.extend(labels.detach().cpu().numpy().tolist())
            y_pred.extend(pred.detach().cpu().numpy().tolist())
            scalar_pred.append(pred_scalars.detach().cpu().numpy())
            scalar_true.append(scalars.detach().cpu().numpy())
            curve_pred.append(pred_curve.detach().cpu().numpy())
            curve_true.append(curve.detach().cpu().numpy())
    return {
        "loss": total_loss / max(1, total_n),
        "y_true": np.asarray(y_true, dtype=int),
        "y_pred": np.asarray(y_pred, dtype=int),
        "scalar_pred_norm": np.concatenate(scalar_pred, axis=0),
        "scalar_true_norm": np.concatenate(scalar_true, axis=0),
        "curve_pred": np.concatenate(curve_pred, axis=0),
        "curve_true": np.concatenate(curve_true, axis=0),
    }


def load_reference_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing", "path": str(path)}
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics", data)
    metrics["status"] = "reference"
    metrics["path"] = str(path)
    return metrics


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def state_dict_cpu(model: nn.Module) -> dict[str, torch.Tensor]:
    return {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}


def parameter_count(model: nn.Module) -> int:
    return sum(param.numel() for param in model.parameters())


def train_candidate(
    name: str,
    factory: Callable[[int, int], nn.Module],
    x_norm: np.ndarray,
    stack_features: np.ndarray,
    y_class: np.ndarray,
    y_scalars_norm: np.ndarray,
    y_curve: np.ndarray,
    groups: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], nn.Module]:
    args.scalar_mean = scalar_mean
    args.scalar_std = scalar_std
    dataset = StackResponseDataset(x_norm, stack_features, y_class, y_scalars_norm, y_curve)
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows: list[dict[str, Any]] = []
    fit_seconds_total = 0.0
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        set_seed(args.seed + fold * 100)
        train_loader = DataLoader(
            Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True
        )
        val_loader = DataLoader(
            Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False
        )
        model = factory(x_norm.shape[1], y_curve.shape[1]).to(args.device_torch)
        weights = class_weights(y_class[train_idx] - 1, args.device_torch)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=args.lr, weight_decay=args.weight_decay
        )
        best_state = None
        best_score = -1.0
        best_epoch = 0
        stale = 0
        started = time.perf_counter()
        for epoch in range(1, args.epochs + 1):
            run_epoch(
                model, train_loader, optimizer, weights, args.device_torch, train=True, args=args
            )
            out = run_epoch(
                model, val_loader, optimizer, weights, args.device_torch, train=False, args=args
            )
            score = f1_score(out["y_true"], out["y_pred"], average="macro", zero_division=0)
            if score > best_score:
                best_score = score
                best_epoch = epoch
                best_state = state_dict_cpu(model)
                stale = 0
            else:
                stale += 1
            if stale >= args.patience:
                break
        fit_seconds = time.perf_counter() - started
        fit_seconds_total += fit_seconds
        if best_state is not None:
            model.load_state_dict(best_state)
        out = run_epoch(
            model, val_loader, optimizer, weights, args.device_torch, train=False, args=args
        )
        row = response_metric_row(out, scalar_mean, scalar_std)
        row["fold"] = fold
        row["best_epoch"] = best_epoch
        row["fit_seconds"] = fit_seconds
        fold_rows.append(row)
        print(
            f"  {name} fold {fold}: f1={row['macro_f1']:.4f}, pt_mae={row['pt_mae']:.2f}, curve_rmse={row['curve_norm_rmse']:.5f}, epoch={best_epoch}",
            flush=True,
        )

    set_seed(args.seed)
    final_model = factory(x_norm.shape[1], y_curve.shape[1]).to(args.device_torch)
    final_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(
        final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    started = time.perf_counter()
    for _ in range(args.final_epochs):
        run_epoch(
            final_model, final_loader, optimizer, weights, args.device_torch, train=True, args=args
        )
    final_fit_seconds = time.perf_counter() - started
    predict_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
    started = time.perf_counter()
    run_epoch(
        final_model, predict_loader, optimizer, weights, args.device_torch, train=False, args=args
    )
    inference_seconds_per_sample = (time.perf_counter() - started) / max(1, len(dataset))

    summary: dict[str, Any] = {
        "status": "trained",
        "fold_metrics": fold_rows,
        "fit_seconds_total": fit_seconds_total,
        "final_fit_seconds": final_fit_seconds,
        "inference_seconds_per_sample": inference_seconds_per_sample,
        "parameter_count": parameter_count(final_model),
    }
    for key in METRIC_KEYS:
        values = [row[key] for row in fold_rows]
        summary[f"cv_{key}_mean"] = float(np.mean(values))
        summary[f"cv_{key}_std"] = float(np.std(values))
    return summary, final_model


def make_pca_curve_model(
    input_dim: int,
    y_curve_train: np.ndarray,
    args: argparse.Namespace,
) -> tuple[PCACurveMLPResponse, PCA]:
    pca = PCA(
        n_components=min(args.pca_components, y_curve_train.shape[0], y_curve_train.shape[1]),
        random_state=args.seed,
    )
    pca.fit(y_curve_train)
    model = PCACurveMLPResponse(
        input_dim=input_dim,
        hidden_dim=max(64, args.hidden_dim - 32),
        depth=args.depth + 1,
        dropout=max(0.05, args.dropout - 0.02),
        curve_mean=np.asarray(pca.mean_, dtype=np.float32),
        curve_basis=np.asarray(pca.components_, dtype=np.float32),
    ).to(args.device_torch)
    return model, pca


def train_pca_curve_candidate(
    x_norm: np.ndarray,
    stack_features: np.ndarray,
    y_class: np.ndarray,
    y_scalars_norm: np.ndarray,
    y_curve: np.ndarray,
    groups: np.ndarray,
    scalar_mean: np.ndarray,
    scalar_std: np.ndarray,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], nn.Module]:
    args.scalar_mean = scalar_mean
    args.scalar_std = scalar_std
    dataset = StackResponseDataset(x_norm, stack_features, y_class, y_scalars_norm, y_curve)
    splitter = GroupKFold(n_splits=args.splits)
    fold_rows: list[dict[str, Any]] = []
    fit_seconds_total = 0.0
    for fold, (train_idx, val_idx) in enumerate(splitter.split(x_norm, y_class, groups), start=1):
        set_seed(args.seed + fold * 100)
        train_loader = DataLoader(
            Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True
        )
        val_loader = DataLoader(
            Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False
        )
        model, pca = make_pca_curve_model(x_norm.shape[1], y_curve[train_idx], args)
        weights = class_weights(y_class[train_idx] - 1, args.device_torch)
        optimizer = torch.optim.AdamW(
            model.parameters(), lr=args.lr, weight_decay=args.weight_decay
        )
        best_state = None
        best_score = float("inf")
        best_epoch = 0
        stale = 0
        started = time.perf_counter()
        for epoch in range(1, args.epochs + 1):
            run_epoch(
                model, train_loader, optimizer, weights, args.device_torch, train=True, args=args
            )
            out = run_epoch(
                model, val_loader, optimizer, weights, args.device_torch, train=False, args=args
            )
            row = response_metric_row(out, scalar_mean, scalar_std)
            score = (
                row["curve_norm_rmse"] + 0.0002 * (row["pt_mae"] / 100.0) - 0.002 * row["macro_f1"]
            )
            if score < best_score:
                best_score = score
                best_epoch = epoch
                best_state = state_dict_cpu(model)
                stale = 0
            else:
                stale += 1
            if stale >= args.patience:
                break
        fit_seconds = time.perf_counter() - started
        fit_seconds_total += fit_seconds
        if best_state is not None:
            model.load_state_dict(best_state)
        out = run_epoch(
            model, val_loader, optimizer, weights, args.device_torch, train=False, args=args
        )
        row = response_metric_row(out, scalar_mean, scalar_std)
        row["fold"] = fold
        row["best_epoch"] = best_epoch
        row["fit_seconds"] = fit_seconds
        row["pca_components"] = int(pca.n_components_)
        fold_rows.append(row)
        print(
            f"  pca_curve_mlp fold {fold}: f1={row['macro_f1']:.4f}, pt_mae={row['pt_mae']:.2f}, curve_rmse={row['curve_norm_rmse']:.5f}, epoch={best_epoch}",
            flush=True,
        )

    set_seed(args.seed)
    final_model, pca = make_pca_curve_model(x_norm.shape[1], y_curve, args)
    final_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    weights = class_weights(y_class - 1, args.device_torch)
    optimizer = torch.optim.AdamW(
        final_model.parameters(), lr=args.lr, weight_decay=args.weight_decay
    )
    started = time.perf_counter()
    for _ in range(args.final_epochs):
        run_epoch(
            final_model, final_loader, optimizer, weights, args.device_torch, train=True, args=args
        )
    final_fit_seconds = time.perf_counter() - started
    predict_loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=False)
    started = time.perf_counter()
    run_epoch(
        final_model, predict_loader, optimizer, weights, args.device_torch, train=False, args=args
    )
    inference_seconds_per_sample = (time.perf_counter() - started) / max(1, len(dataset))

    summary: dict[str, Any] = {
        "status": "trained",
        "fold_metrics": fold_rows,
        "fit_seconds_total": fit_seconds_total,
        "final_fit_seconds": final_fit_seconds,
        "inference_seconds_per_sample": inference_seconds_per_sample,
        "parameter_count": parameter_count(final_model),
        "pca_components": int(pca.n_components_),
    }
    for key in METRIC_KEYS:
        values = [row[key] for row in fold_rows]
        summary[f"cv_{key}_mean"] = float(np.mean(values))
        summary[f"cv_{key}_std"] = float(np.std(values))
    return summary, final_model


def write_reports(report_dir: Path, output_dir: Path, payload: dict[str, Any]) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "model_comparison.json").write_text(
        json.dumps(json_safe(payload), indent=2), encoding="utf-8"
    )
    tree = payload["reference_models"]["response_surrogate_physics_v2"]
    goint = payload["reference_models"]["response_goint_physics_nn_v2"]
    trained = {
        name: row for name, row in payload["candidates"].items() if row.get("status") == "trained"
    }
    best_name = (
        min(
            trained,
            key=lambda key: (
                float(trained[key].get("cv_pt_mae_mean", float("inf"))),
                float(trained[key].get("cv_curve_norm_rmse_mean", float("inf"))),
                -float(trained[key].get("cv_macro_f1_mean", 0.0)),
            ),
        )
        if trained
        else None
    )
    recommendation = "No DL challenger was trained."
    if best_name:
        best = trained[best_name]
        if float(best["cv_pt_mae_mean"]) < float(
            goint.get("cv_pt_mae_mean", float("inf"))
        ) and float(best["cv_curve_norm_rmse_mean"]) < float(
            goint.get("cv_curve_norm_rmse_mean", float("inf"))
        ):
            recommendation = f"`{best_name}` beats the current GointMLP reference on Pt and normalized curve RMSE, but should remain research-only until API compatibility and the tree reference comparison are reviewed."
        else:
            recommendation = f"`{best_name}` is the best DL challenger in this run, but it does not clearly beat `response_goint_physics_nn_v2` across the main response metrics."

    lines = [
        "# DD Laminate Response DL Challengers v1",
        "",
        f"- Dataset: `{payload['dataset']}`",
        f"- Feature set: `{payload['feature_set']}`",
        f"- Samples: {payload['n_samples']}",
        f"- Validation: GroupKFold by theta pair, {payload['splits']} folds",
        f"- Curve target: direct {payload['seq_len']}-point normalized force curve head",
        f"- Output artifacts: `{output_dir}`",
        "",
        "## Fair Comparison Contract",
        "",
        "All trained DL challengers keep the same comparison surface as `response_goint_physics_nn_v2`:",
        "",
        "- Input features are fixed to `theta_physics_nn_v2` unless explicitly overridden.",
        "- Scalar targets are fixed to log-normalized `pt`, `max_displacement`, and `max_force`.",
        "- Curve targets are fixed to the direct normalized response curve head, not the Tree/PCA surrogate.",
        "- Loss terms keep the same class, ordinal, scalar, and curve weighting contract as the GointMLP trainer.",
        "- `physics_guided_mlp` keeps the same targets but adds soft output-shape penalties for curve start, peak normalization, monotonicity, and smoothness.",
        "- `deeponet_response` uses a DeepONet-style branch/trunk factorization to generate the response curve as a learned function on the displacement grid.",
        "- `pca_curve_mlp` fits a train-fold-only PCA/POD curve basis and predicts basis coefficients before reconstructing the full curve.",
        "- Stack LSTM/GRU/GNN/GAT candidates add only deterministic 16-ply stack features derived from the same theta/case input.",
        "- The intended variable is the neural architecture replacing the GointMLP-style branch mixer.",
        "",
        "## Reference Models",
        "",
        "| Model | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| response_surrogate_physics_v2 | {tree.get('cv_accuracy_mean', 0):.4f} | {tree.get('cv_macro_f1_mean', 0):.4f} | {tree.get('cv_pt_mae_mean', 0):.2f} | {tree.get('cv_max_force_mae_mean', 0):.2f} | {tree.get('cv_curve_norm_rmse_mean', 0):.5f} | {tree.get('cv_curve_force_rmse_mean', 0):.2f} |",
        f"| response_goint_physics_nn_v2 | {goint.get('cv_accuracy_mean', 0):.4f} | {goint.get('cv_macro_f1_mean', 0):.4f} | {goint.get('cv_pt_mae_mean', 0):.2f} | {goint.get('cv_max_force_mae_mean', 0):.2f} | {goint.get('cv_curve_norm_rmse_mean', 0):.5f} | {goint.get('cv_curve_force_rmse_mean', 0):.2f} |",
        "",
        "## Challenger Results",
        "",
        "| Candidate | Status | Type Acc | Macro F1 | Pt MAE | Max Force MAE | Curve Norm RMSE | Curve Force RMSE | Train s | Infer ms/sample | Params | Size MB |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, row in payload["candidates"].items():
        if row.get("status") != "trained":
            lines.append(
                f"| {name} | {row.get('status', 'not trained')}: {row.get('reason', '')} |  |  |  |  |  |  |  |  |  |  |"
            )
            continue
        infer_ms = float(row.get("inference_seconds_per_sample", 0.0)) * 1000.0
        lines.append(
            f"| {name} | trained | {row['cv_accuracy_mean']:.4f} | {row['cv_macro_f1_mean']:.4f} | "
            f"{row['cv_pt_mae_mean']:.2f} | {row['cv_max_force_mae_mean']:.2f} | {row['cv_curve_norm_rmse_mean']:.5f} | "
            f"{row['cv_curve_force_rmse_mean']:.2f} | {row.get('final_fit_seconds', 0.0):.2f} | {infer_ms:.4f} | "
            f"{int(row.get('parameter_count', 0))} | {row.get('artifact_size_mb', 0.0):.3f} |"
        )
    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            recommendation,
            "",
            "No backend model key or UI/API default was changed in this pass.",
        ]
    )
    (report_dir / "model_comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict[str, Any]:
    set_seed(args.seed)
    args.device_torch = torch.device(args.device)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    report_dir = Path(args.report_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    records = load_records(data_dir)
    x, feature_names = response_feature_matrix(records, args.feature_set)
    x_norm, feature_mean, feature_std = normalize(x, x)
    stack_features = build_stack_features(records)
    y_class = np.asarray([record.label for record in records], dtype=int)
    y_scalars, y_curve, grid = make_response_targets(records, args.seq_len)
    y_scalars_log = np.log1p(y_scalars)
    y_scalars_norm, scalar_mean, scalar_std = normalize(y_scalars_log, y_scalars_log)
    groups = np.asarray([f"{record.theta1}:{record.theta2}" for record in records])
    selected = set(args.candidates.split(",")) if args.candidates else None
    candidates: dict[str, Any] = {}
    for name, factory in candidate_factories(args, stack_features.shape[2]).items():
        if selected is not None and name not in selected:
            candidates[name] = {"status": "skipped", "reason": "not selected"}
            continue
        print(f"training {name}...", flush=True)
        try:
            if name == "pca_curve_mlp":
                row, model = train_pca_curve_candidate(
                    x_norm,
                    stack_features,
                    y_class,
                    y_scalars_norm,
                    y_curve,
                    groups,
                    scalar_mean,
                    scalar_std,
                    args,
                )
            else:
                row, model = train_candidate(
                    name,
                    factory,
                    x_norm,
                    stack_features,
                    y_class,
                    y_scalars_norm,
                    y_curve,
                    groups,
                    scalar_mean,
                    scalar_std,
                    args,
                )
            artifact_path = output_dir / f"{name}.pt"
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "model_type": name,
                    "model_config": {
                        "input_dim": int(x_norm.shape[1]),
                        "seq_len": int(y_curve.shape[1]),
                        "hidden_dim": int(args.hidden_dim),
                        "depth": int(args.depth),
                        "dropout": float(args.dropout),
                        "physics_weight": float(args.physics_weight),
                        "basis_dim": int(args.basis_dim),
                        "pca_components": int(row.get("pca_components", 0)),
                    },
                    "feature_builder": args.feature_set,
                    "feature_columns": feature_names,
                    "stack_feature_columns": [
                        "angle_norm",
                        "sin",
                        "cos",
                        "sin2",
                        "cos2",
                        "sign",
                        "z",
                        "case_index",
                        "is_theta1",
                        "is_theta2",
                    ],
                    "feature_mean": feature_mean,
                    "feature_std": feature_std,
                    "scalar_columns": ["pt", "max_displacement", "max_force"],
                    "scalar_log_mean": scalar_mean,
                    "scalar_log_std": scalar_std,
                    "grid": grid,
                    "metrics": {key: value for key, value in row.items() if key != "fold_metrics"},
                    "fold_metrics": row["fold_metrics"],
                    "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
                },
                artifact_path,
            )
            row["artifact_path"] = str(artifact_path)
            row["artifact_size_mb"] = float(artifact_path.stat().st_size / (1024 * 1024))
            candidates[name] = row
            print(
                f"done {name}: f1={row['cv_macro_f1_mean']:.4f}, pt_mae={row['cv_pt_mae_mean']:.2f}, curve_rmse={row['cv_curve_norm_rmse_mean']:.5f}",
                flush=True,
            )
        except Exception as exc:
            candidates[name] = {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
            print(f"failed {name}: {exc}", flush=True)
    payload = {
        "dataset": str(data_dir),
        "feature_set": args.feature_set,
        "n_samples": len(records),
        "seq_len": int(args.seq_len),
        "splits": int(args.splits),
        "loss_weights": {
            "ordinal_weight": float(args.ordinal_weight),
            "scalar_weight": float(args.scalar_weight),
            "curve_weight": float(args.curve_weight),
        },
        "pt_consistency_weight": float(args.pt_consistency_weight),
        "physics_guided_loss": {
            "physics_weight": float(args.physics_weight),
            "terms": [
                "curve_start_zero",
                "curve_peak_one",
                "monotonic_descent_penalty",
                "curvature_smoothness",
            ],
        },
        "feature_columns": feature_names,
        "stack_feature_columns": [
            "angle_norm",
            "sin",
            "cos",
            "sin2",
            "cos2",
            "sign",
            "z",
            "case_index",
            "is_theta1",
            "is_theta2",
        ],
        "reference_models": {
            "response_surrogate_physics_v2": load_reference_metrics(
                Path(args.baseline_tree_metrics)
            ),
            "response_goint_physics_nn_v2": load_reference_metrics(
                Path(args.baseline_goint_metrics)
            ),
        },
        "candidates": candidates,
    }
    write_reports(report_dir, output_dir, payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train DD response DL challengers without Curve CSV changes."
    )
    parser.add_argument("--data-dir", default="data/datasets/DD_cases_2_3_4_curated_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_response_dl_challengers_v1")
    parser.add_argument("--report-dir", default="reports/dd_response_dl_challengers_v1")
    parser.add_argument(
        "--baseline-tree-metrics",
        default="models/dd_laminate_response_physics_xai_v2/response_surrogate_metrics.json",
    )
    parser.add_argument(
        "--baseline-goint-metrics",
        default="models/dd_laminate_response_goint_physics_nn_v2/response_goint_metrics.json",
    )
    parser.add_argument(
        "--feature-set",
        choices=SUPPORTED_RESPONSE_FEATURE_SETS,
        default="theta_physics_nn_v2",
    )
    parser.add_argument("--seq-len", type=int, default=CURVE_GRID_LEN)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=90)
    parser.add_argument("--final-epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=128)
    parser.add_argument("--basis-dim", type=int, default=32)
    parser.add_argument("--pca-components", type=int, default=18)
    parser.add_argument("--depth", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--ordinal-weight", type=float, default=0.25)
    parser.add_argument("--scalar-weight", type=float, default=0.45)
    parser.add_argument("--curve-weight", type=float, default=0.25)
    parser.add_argument("--physics-weight", type=float, default=0.20)
    parser.add_argument("--pt-consistency-weight", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    parser.add_argument(
        "--candidates", default="", help="Comma-separated subset, e.g. plain_mlp,residual_mlp"
    )
    args = parser.parse_args()
    payload = run(args)
    print(json.dumps(json_safe(payload), indent=2))


if __name__ == "__main__":
    main()
