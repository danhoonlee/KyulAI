from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import numpy as np
import torch

import scripts.dd_response_pt_consistent_deep_train as deep_training
import scripts.dd_response_uq_oof_deep as deep_uq
from src.ml.dd_laminate.response_deep import DDResponseGointSurrogate
from src.ml.dd_laminate.train_cases_2_3_4_classical import DDRecord


def _checkpoint(path: Path, *, input_dim: int = 4, seq_len: int = 8) -> None:
    config = {
        "input_dim": input_dim,
        "seq_len": seq_len,
        "hidden_dim": 4,
        "num_branches": 1,
        "dropout": 0.0,
        "scalar_dim": 6,
    }
    model = DDResponseGointSurrogate(**config)
    torch.save({"model_config": config, "model_state_dict": model.state_dict()}, path)


def test_train_model_can_disable_full_development_warm_start(tmp_path: Path, monkeypatch) -> None:
    checkpoint = tmp_path / "architecture.pt"
    _checkpoint(checkpoint)

    def fail_if_called(*_args, **_kwargs) -> None:
        raise AssertionError("warm_start must not run for strict OOF training")

    monkeypatch.setattr(deep_training, "warm_start", fail_if_called)
    args = Namespace(
        device_torch=torch.device("cpu"),
        batch_size=3,
        num_workers=0,
        goint_epochs=1,
        hybrid_epochs=1,
        goint_lr=1e-3,
        hybrid_lr=1e-3,
        weight_decay=0.0,
        ordinal_weight=0.1,
        scalar_weight=0.1,
        p1_weight=0.1,
        curve_weight=0.1,
    )
    features = np.zeros((3, 4), dtype=float)
    labels = np.asarray([1, 2, 3])
    scalars = np.zeros((3, 6), dtype=float)
    curves = np.zeros((3, 8), dtype=float)

    _, metadata = deep_training.train_model(
        mode="goint",
        baseline_path=checkpoint,
        x_norm=features,
        y_class=labels,
        y_scalars_norm=scalars,
        y_curves=curves,
        scalar_mean=np.zeros(6),
        scalar_std=np.ones(6),
        teacher_bundle=None,
        x_raw=features,
        locked_records=[],
        feature_set="theta_physics_geometry_v1",
        feature_mean=np.zeros(4),
        feature_std=np.ones(4),
        args=args,
        warm_start_weights=False,
    )

    assert metadata["warm_start_weights"] is False


def test_preflight_rejects_group_leakage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(deep_uq, "ROOT", tmp_path)
    architecture = tmp_path / "architecture.pt"
    _checkpoint(architecture)
    records = [
        DDRecord("Case2", "1", 30.0, -30.0, 100.0, 1, tmp_path / "1.csv"),
        DDRecord("Case2", "2", 30.0, -30.0, 110.0, 1, tmp_path / "2.csv"),
    ]
    config = {
        "selection_protocol": {"rows": 1, "grouped_folds": 1},
        "fixed_benchmark": {"rows": 1},
        "modes": ["goint"],
        "architectures": {"goint": "architecture.pt"},
    }

    try:
        deep_uq._validate_preflight(
            config=config,
            records=records,
            development_idx=np.asarray([0]),
            benchmark_idx=np.asarray([1]),
            development_groups=np.asarray(["Case2|30|-30"]),
            features=np.zeros((2, 4)),
            curves=np.zeros((2, 8)),
        )
    except ValueError as exc:
        assert "group leakage" in str(exc)
    else:
        raise AssertionError("preflight accepted a leaked design group")
