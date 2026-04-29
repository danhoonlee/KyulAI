"""Train a GointMLP-inspired DD deep sequence classifier."""

from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from torch.utils.data import DataLoader, Subset

from .deep_sequence import (
    DDGointSequenceClassifier,
    DDSequenceDataset,
    choose_device,
    combined_loss,
    load_sequence_samples,
    predict_from_logits,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _splitter(cv_mode: str, splits: int, random_state: int):
    if cv_mode == "sample":
        return StratifiedKFold(n_splits=splits, shuffle=True, random_state=random_state)
    if cv_mode == "grouped":
        return StratifiedGroupKFold(n_splits=splits, shuffle=True, random_state=random_state)
    raise ValueError(f"Unknown cv mode: {cv_mode}")


def _class_weights(labels: np.ndarray, device: torch.device) -> torch.Tensor:
    counts = np.bincount(labels, minlength=3).astype(np.float32)
    weights = counts.sum() / np.maximum(counts, 1.0)
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32, device=device)


def _run_epoch(model, loader, optimizer, device, class_weights, train: bool) -> tuple[float, list[int], list[int]]:
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    y_true: list[int] = []
    y_pred: list[int] = []
    for batch in loader:
        x = batch["x"].to(device)
        labels = batch["label"].to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)
        class_logits, ordinal_logits = model(x)
        loss = combined_loss(class_logits, ordinal_logits, labels, class_weights=class_weights)
        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=3.0)
            optimizer.step()
        pred = predict_from_logits(class_logits)
        total_loss += float(loss.detach().cpu()) * labels.numel()
        total_n += labels.numel()
        y_true.extend(labels.detach().cpu().numpy().tolist())
        y_pred.extend(pred.detach().cpu().numpy().tolist())
    return total_loss / max(1, total_n), y_true, y_pred


def train_one_fold(
    dataset: DDSequenceDataset,
    train_idx: np.ndarray,
    val_idx: np.ndarray,
    labels: np.ndarray,
    device: torch.device,
    args,
) -> tuple[dict, dict]:
    train_loader = DataLoader(
        Subset(dataset, train_idx.tolist()),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,
    )
    val_loader = DataLoader(
        Subset(dataset, val_idx.tolist()),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=0,
    )
    model = DDGointSequenceClassifier(
        input_size=8,
        hidden_size=args.hidden_size,
        gru_layers=args.gru_layers,
        branch_dim=args.branch_dim,
        num_branches=args.num_branches,
        dropout=args.dropout,
    ).to(device)
    class_weights = _class_weights(labels[train_idx], device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=12)

    best_state = None
    best_macro_f1 = -1.0
    best_epoch = 0
    patience_count = 0
    history = []

    for epoch in range(1, args.epochs + 1):
        train_loss, train_true, train_pred = _run_epoch(model, train_loader, optimizer, device, class_weights, train=True)
        val_loss, val_true, val_pred = _run_epoch(model, val_loader, optimizer, device, class_weights, train=False)
        val_macro_f1 = f1_score(val_true, val_pred, average="macro", zero_division=0)
        val_acc = accuracy_score(val_true, val_pred)
        scheduler.step(val_macro_f1)
        history.append({
            "epoch": epoch,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "val_accuracy": val_acc,
            "val_macro_f1": val_macro_f1,
        })
        if val_macro_f1 > best_macro_f1:
            best_macro_f1 = val_macro_f1
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            patience_count = 0
        else:
            patience_count += 1
        if patience_count >= args.patience:
            break

    if best_state is not None:
        model.load_state_dict(best_state)
    _, val_true, val_pred = _run_epoch(model, val_loader, optimizer, device, class_weights, train=False)
    metrics = {
        "best_epoch": best_epoch,
        "accuracy": accuracy_score(val_true, val_pred),
        "macro_f1": f1_score(val_true, val_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(val_true, val_pred, average="weighted", zero_division=0),
        "confusion_matrix": confusion_matrix(val_true, val_pred, labels=[0, 1, 2]).tolist(),
        "classification_report": classification_report(
            val_true,
            val_pred,
            labels=[0, 1, 2],
            target_names=["Type 1", "Type 2", "Type 3"],
            output_dict=True,
            zero_division=0,
        ),
    }
    return metrics, {"state_dict": model.state_dict(), "history": history}


def train_final_model(dataset: DDSequenceDataset, labels: np.ndarray, device: torch.device, args):
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = DDGointSequenceClassifier(
        input_size=8,
        hidden_size=args.hidden_size,
        gru_layers=args.gru_layers,
        branch_dim=args.branch_dim,
        num_branches=args.num_branches,
        dropout=args.dropout,
    ).to(device)
    class_weights = _class_weights(labels, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        _run_epoch(model, loader, optimizer, device, class_weights, train=True)
    return model


def summarize_results(fold_metrics: list[dict]) -> dict:
    all_cm = np.sum([np.array(m["confusion_matrix"]) for m in fold_metrics], axis=0)
    return {
        "fold_scores": fold_metrics,
        "mean_accuracy": float(np.mean([m["accuracy"] for m in fold_metrics])),
        "std_accuracy": float(np.std([m["accuracy"] for m in fold_metrics])),
        "mean_macro_f1": float(np.mean([m["macro_f1"] for m in fold_metrics])),
        "std_macro_f1": float(np.std([m["macro_f1"] for m in fold_metrics])),
        "mean_weighted_f1": float(np.mean([m["weighted_f1"] for m in fold_metrics])),
        "confusion_matrix": all_cm.tolist(),
    }


def load_classical_results(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def write_report(out_dir: Path, args, summary: dict, classical: dict | None) -> None:
    lines = [
        "# DD Goint Sequence Classifier Report",
        "",
        "This is a DD-specific, GointMLP-inspired deep learning model: GRU sequence encoder + JointMLP-style multi-branch head + auxiliary ordinal loss.",
        "",
        "## Input",
        "",
        "Each force-displacement CSV is resampled to a fixed sequence. Per timestep features are:",
        "",
        "`displacement_norm`, `load_norm`, `step_norm`, `theta1/90`, `theta2/90`, `pt/pt_scale`, `case_id`, `load/pt`",
        "",
        "## Deep Model Result",
        "",
        f"Validation mode: `{args.cv_mode}`; folds: {args.splits}",
        "",
        "| Model | Accuracy | Macro F1 | Weighted F1 |",
        "|---|---:|---:|---:|",
        f"| dd_goint_sequence | {summary['mean_accuracy']:.4f} ± {summary['std_accuracy']:.4f} | {summary['mean_macro_f1']:.4f} ± {summary['std_macro_f1']:.4f} | {summary['mean_weighted_f1']:.4f} |",
        "",
        "Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:",
        "",
        "```text",
        str(np.array(summary["confusion_matrix"])),
        "```",
    ]
    if classical:
        lines.extend([
            "",
            "## Comparison With Existing Models",
            "",
            "Primary table below is from the existing `models/dd_laminate_csv_meta_v1` combined metadata+curve feature run.",
            "",
            "| Model | Accuracy | Macro F1 | Weighted F1 |",
            "|---|---:|---:|---:|",
        ])
        for name, result in sorted(classical["cv_results"].items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True):
            lines.append(
                f"| {name} | {result['mean_accuracy']:.4f} ± {result['std_accuracy']:.4f} | "
                f"{result['mean_macro_f1']:.4f} ± {result['std_macro_f1']:.4f} | {result['mean_weighted_f1']:.4f} |"
            )
    (out_dir / "deep_sequence_report.md").write_text("\n".join(lines) + "\n")


def write_predictions(out_dir: Path, samples: list, labels_true: list[int], labels_pred: list[int]) -> None:
    with (out_dir / "oof_predictions.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["case", "test_id", "true_type", "predicted_type"])
        writer.writeheader()
        for sample, true_label, pred_label in zip(samples, labels_true, labels_pred):
            writer.writerow({
                "case": sample.case,
                "test_id": sample.test_id,
                "true_type": true_label + 1,
                "predicted_type": pred_label + 1,
            })


def main() -> None:
    parser = argparse.ArgumentParser(description="Train DD GointMLP-inspired sequence classifier")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_deep_sequence_v1")
    parser.add_argument("--seq-len", type=int, default=256)
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--cv-mode", choices=["sample", "grouped"], default="sample")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--final-epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-size", type=int, default=32)
    parser.add_argument("--gru-layers", type=int, default=2)
    parser.add_argument("--branch-dim", type=int, default=24)
    parser.add_argument("--num-branches", type=int, default=4)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--classical-metrics", default="models/dd_laminate_csv_meta_v1/curve_classifier_metrics.json")
    parser.add_argument("--device", choices=["auto", "cpu", "mps", "cuda"], default="cpu")
    args = parser.parse_args()

    set_seed(args.seed)
    if args.device == "auto":
        device = choose_device()
    else:
        device = torch.device(args.device)
    samples = load_sequence_samples(args.data_dir)
    dataset = DDSequenceDataset(samples, seq_len=args.seq_len)
    labels = np.array([s.label - 1 for s in samples], dtype=int)
    groups = np.array([s.test_id for s in samples])

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    splitter = _splitter(args.cv_mode, args.splits, args.seed)
    split_iter = splitter.split(np.zeros(len(labels)), labels, groups) if args.cv_mode == "grouped" else splitter.split(np.zeros(len(labels)), labels)

    fold_metrics = []
    all_true = []
    all_pred = []
    all_indices = []
    for fold, (train_idx, val_idx) in enumerate(split_iter, start=1):
        print(f"Starting fold {fold}/{args.splits} on {device}...", flush=True)
        metrics, artifact = train_one_fold(dataset, train_idx, val_idx, labels, device, args)
        fold_metrics.append(metrics)
        # Re-run selected fold artifact on validation to store predictions.
        model = DDGointSequenceClassifier(
            input_size=8,
            hidden_size=args.hidden_size,
            gru_layers=args.gru_layers,
            branch_dim=args.branch_dim,
            num_branches=args.num_branches,
            dropout=args.dropout,
        ).to(device)
        model.load_state_dict(artifact["state_dict"])
        loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False, num_workers=0)
        model.eval()
        with torch.no_grad():
            for batch in loader:
                logits, _ = model(batch["x"].to(device))
                pred = predict_from_logits(logits).cpu().numpy().tolist()
                true = batch["label"].numpy().tolist()
                all_true.extend(true)
                all_pred.extend(pred)
        all_indices.extend(val_idx.tolist())
        print(f"Fold {fold}: acc={metrics['accuracy']:.4f}, macro_f1={metrics['macro_f1']:.4f}, best_epoch={metrics['best_epoch']}")

    summary = summarize_results(fold_metrics)
    final_model = train_final_model(dataset, labels, device, args)
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "model_config": {
                "input_size": 8,
                "hidden_size": args.hidden_size,
                "gru_layers": args.gru_layers,
                "branch_dim": args.branch_dim,
                "num_branches": args.num_branches,
                "dropout": args.dropout,
                "seq_len": args.seq_len,
            },
            "pt_scale": dataset.pt_scale,
            "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
            "summary": summary,
        },
        out_dir / "dd_goint_sequence.pt",
    )

    (out_dir / "deep_sequence_metrics.json").write_text(json.dumps(summary, indent=2))
    ordered = sorted(zip(all_indices, all_true, all_pred), key=lambda item: item[0])
    write_predictions(out_dir, [samples[i] for i, _, _ in ordered], [t for _, t, _ in ordered], [p for _, _, p in ordered])
    classical = load_classical_results(Path(args.classical_metrics))
    write_report(out_dir, args, summary, classical)

    print(f"Saved model: {out_dir / 'dd_goint_sequence.pt'}")
    print(f"Saved report: {out_dir / 'deep_sequence_report.md'}")
    print(f"Mean {args.cv_mode} CV accuracy: {summary['mean_accuracy']:.4f}")
    print(f"Mean {args.cv_mode} CV macro F1: {summary['mean_macro_f1']:.4f}")
    print(np.array(summary["confusion_matrix"]))


if __name__ == "__main__":
    main()
