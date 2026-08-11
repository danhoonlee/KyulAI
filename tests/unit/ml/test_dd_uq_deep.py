from __future__ import annotations

import json
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


def test_train_model_runs_fold_local_pretraining_before_fine_tuning(
    tmp_path: Path, monkeypatch
) -> None:
    checkpoint = tmp_path / "architecture.pt"
    _checkpoint(checkpoint)
    stages: list[str] = []

    def pretrain_epoch(*_args, **_kwargs) -> float:
        stages.append("pretrain")
        return 2.0

    def fine_tune_epoch(*_args, **_kwargs) -> float:
        stages.append("fine_tune")
        return 1.0

    monkeypatch.setattr(deep_training, "run_response_pretrain_epoch", pretrain_epoch)
    monkeypatch.setattr(deep_training, "run_goint_epoch", fine_tune_epoch)
    args = Namespace(
        device_torch=torch.device("cpu"),
        batch_size=3,
        num_workers=0,
        goint_epochs=1,
        hybrid_epochs=1,
        goint_lr=1e-3,
        hybrid_lr=1e-3,
        pretrain_goint_epochs=2,
        pretrain_hybrid_epochs=2,
        pretrain_goint_lr=2e-3,
        pretrain_hybrid_lr=2e-3,
        pretrain_ordinal_weight=0.2,
        pretrain_scalar_weight=0.3,
        pretrain_curve_weight=0.4,
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

    assert stages == ["pretrain", "pretrain", "fine_tune"]
    assert metadata["training_stages"][0] == {
        "stage": "fold_local_response_pretraining",
        "enabled": True,
        "epochs": 2,
        "learning_rate": 2e-3,
        "rows": 3,
        "uses_p1_targets": False,
        "uses_teacher_targets": False,
        "uses_synthetic_rows": False,
        "loss_first": 2.0,
        "loss_final": 2.0,
    }
    assert metadata["training_stages"][1]["stage"] == "pt_consistent_fine_tuning"


def test_hybrid_pretraining_excludes_teacher_and_synthetic_rows(
    tmp_path: Path, monkeypatch
) -> None:
    checkpoint = tmp_path / "architecture.pt"
    _checkpoint(checkpoint)
    observed: list[tuple[str, int, bool]] = []
    real_rows = 3
    synthetic_rows = 2
    teacher_real = deep_training.TeacherOutputs(
        probabilities=np.full((real_rows, 3), 1.0 / 3.0),
        scalars=np.zeros((real_rows, 6)),
        curves=np.zeros((real_rows, 8)),
    )
    teacher_synthetic = deep_training.TeacherOutputs(
        probabilities=np.full((synthetic_rows, 3), 1.0 / 3.0),
        scalars=np.zeros((synthetic_rows, 6)),
        curves=np.zeros((synthetic_rows, 8)),
    )
    synthetic_dataset = deep_training.PtConsistentDataset(
        np.zeros((synthetic_rows, 4)),
        np.asarray([1, 2]),
        np.zeros((synthetic_rows, 6)),
        np.zeros((synthetic_rows, 8)),
        teacher=teacher_synthetic,
    )

    monkeypatch.setattr(
        deep_training,
        "tree_teacher_predictions",
        lambda *_args, **_kwargs: teacher_real,
    )
    monkeypatch.setattr(
        deep_training,
        "normalized_teacher",
        lambda outputs, *_args, **_kwargs: outputs,
    )
    monkeypatch.setattr(
        deep_training,
        "synthetic_teacher_dataset",
        lambda **_kwargs: synthetic_dataset,
    )

    def pretrain_epoch(_model, loader, _optimizer, _args) -> float:
        dataset = loader.dataset
        observed.append(
            (
                "pretrain",
                len(dataset),
                dataset.teacher_probabilities is not None,
            )
        )
        return 2.0

    def hybrid_epoch(_model, loader, _optimizer, _args) -> float:
        dataset = loader.dataset
        observed.append(
            (
                "fine_tune",
                len(dataset),
                dataset.teacher_probabilities is not None,
            )
        )
        return 1.0

    monkeypatch.setattr(deep_training, "run_response_pretrain_epoch", pretrain_epoch)
    monkeypatch.setattr(deep_training, "run_hybrid_epoch", hybrid_epoch)
    args = Namespace(
        device_torch=torch.device("cpu"),
        batch_size=3,
        num_workers=0,
        goint_epochs=1,
        hybrid_epochs=1,
        goint_lr=1e-3,
        hybrid_lr=1e-3,
        pretrain_goint_epochs=1,
        pretrain_hybrid_epochs=1,
        pretrain_goint_lr=2e-3,
        pretrain_hybrid_lr=2e-3,
        pretrain_ordinal_weight=0.2,
        pretrain_scalar_weight=0.3,
        pretrain_curve_weight=0.4,
        weight_decay=0.0,
        ordinal_weight=0.1,
        scalar_weight=0.1,
        p1_weight=0.1,
        curve_weight=0.1,
    )
    features = np.zeros((real_rows, 4), dtype=float)
    labels = np.asarray([1, 2, 3])
    scalars = np.zeros((real_rows, 6), dtype=float)
    curves = np.zeros((real_rows, 8), dtype=float)

    _, metadata = deep_training.train_model(
        mode="hybrid",
        baseline_path=checkpoint,
        x_norm=features,
        y_class=labels,
        y_scalars_norm=scalars,
        y_curves=curves,
        scalar_mean=np.zeros(6),
        scalar_std=np.ones(6),
        teacher_bundle={"teacher": "fold-local"},
        x_raw=features,
        locked_records=[],
        feature_set="theta_physics_geometry_v1",
        feature_mean=np.zeros(4),
        feature_std=np.ones(4),
        args=args,
        warm_start_weights=False,
    )

    assert observed == [
        ("pretrain", real_rows, False),
        ("fine_tune", real_rows + synthetic_rows, True),
    ]
    assert metadata["training_stages"][0]["uses_teacher_targets"] is False
    assert metadata["training_stages"][0]["uses_synthetic_rows"] is False
    assert metadata["training_stages"][1]["uses_teacher_targets"] is True
    assert metadata["training_stages"][1]["synthetic_rows"] == synthetic_rows


def test_preflight_rejects_group_leakage(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(deep_uq, "ROOT", tmp_path)
    architecture = tmp_path / "architecture.pt"
    _checkpoint(architecture)
    records = [
        DDRecord("Case2", "1", 30.0, -30.0, 100.0, 1, tmp_path / "1.csv"),
        DDRecord("Case2", "2", 30.0, -30.0, 110.0, 1, tmp_path / "2.csv"),
    ]
    config = {
        "selection_protocol": {
            "rows": 1,
            "grouped_folds": 1,
            "forbid_fixed_benchmark_selection": True,
        },
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


def test_pretraining_is_explicitly_opt_in() -> None:
    root = Path(__file__).resolve().parents[3]
    v1 = json.loads(
        (root / "research/dd_aicomp2026/configs/20260811-uq-deep-geometry-case-v1.json").read_text()
    )
    v2 = json.loads(
        (root / "research/dd_aicomp2026/configs/20260811-uq-deep-fold-pretrain-v2.json").read_text()
    )

    v1_args = deep_uq._training_args(v1, torch.device("cpu"))
    v2_args = deep_uq._training_args(v2, torch.device("cpu"))

    assert v1_args.pretrain_goint_epochs == 0
    assert v1_args.pretrain_hybrid_epochs == 0
    assert v2_args.pretrain_goint_epochs == 45
    assert v2_args.pretrain_hybrid_epochs == 45


def test_preflight_rejects_teacher_targets_during_pretraining(tmp_path: Path) -> None:
    records = [
        DDRecord("Case2", "1", 30.0, -30.0, 100.0, 1, tmp_path / "1.csv"),
        DDRecord("Case2", "2", 40.0, -30.0, 110.0, 1, tmp_path / "2.csv"),
    ]
    config = {
        "selection_protocol": {
            "rows": 1,
            "grouped_folds": 1,
            "forbid_fixed_benchmark_selection": True,
        },
        "fixed_benchmark": {"rows": 1},
        "pretraining": {
            "enabled": True,
            "scope": "fold_fit_rows_only",
            "teacher_targets": True,
            "synthetic_rows": False,
            "goint_epochs": 1,
            "hybrid_epochs": 1,
        },
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
        assert "teacher targets" in str(exc)
    else:
        raise AssertionError("preflight accepted teacher targets during pretraining")
