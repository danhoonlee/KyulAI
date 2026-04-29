"""Train a GointMLP-inspired theta-only deep classifier."""

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

from .theta_deep import DDThetaDataset, DDThetaGointClassifier, combined_loss, load_theta_samples, predict_from_logits


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def split_iter(cv_mode: str, splits: int, seed: int, x, y, groups):
    if cv_mode == "sample":
        yield from StratifiedKFold(n_splits=splits, shuffle=True, random_state=seed).split(x, y)
    elif cv_mode == "grouped":
        yield from StratifiedGroupKFold(n_splits=splits, shuffle=True, random_state=seed).split(x, y, groups)
    else:
        raise ValueError(cv_mode)


def class_weights(labels: np.ndarray, device: torch.device) -> torch.Tensor:
    counts = np.bincount(labels, minlength=3).astype(np.float32)
    weights = counts.sum() / np.maximum(counts, 1.0)
    weights = weights / weights.mean()
    return torch.tensor(weights, dtype=torch.float32, device=device)


def run_epoch(model, loader, optimizer, device, weights, train: bool):
    model.train(mode=train)
    total_loss = 0.0
    total_n = 0
    y_true, y_pred = [], []
    for batch in loader:
        x = batch["x"].to(device)
        labels = batch["label"].to(device)
        if train:
            optimizer.zero_grad(set_to_none=True)
        class_logits, ordinal_logits = model(x)
        loss = combined_loss(class_logits, ordinal_logits, labels, ordinal_weight=0.35, class_weights=weights)
        if train:
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            optimizer.step()
        pred = predict_from_logits(class_logits)
        total_loss += float(loss.detach().cpu()) * labels.numel()
        total_n += labels.numel()
        y_true.extend(labels.detach().cpu().numpy().tolist())
        y_pred.extend(pred.detach().cpu().numpy().tolist())
    return total_loss / max(1, total_n), y_true, y_pred


def make_model(args, device):
    return DDThetaGointClassifier(
        input_dim=2,
        hidden_dim=args.hidden_dim,
        num_branches=args.num_branches,
        dropout=args.dropout,
    ).to(device)


def train_one_fold(dataset, train_idx, val_idx, labels, args, device):
    train_loader = DataLoader(Subset(dataset, train_idx.tolist()), batch_size=args.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(Subset(dataset, val_idx.tolist()), batch_size=args.batch_size, shuffle=False, num_workers=0)
    model = make_model(args, device)
    weights = class_weights(labels[train_idx], device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.5, patience=10)
    best_state = None
    best_score = -1.0
    best_epoch = 0
    stale = 0
    for epoch in range(1, args.epochs + 1):
        run_epoch(model, train_loader, optimizer, device, weights, train=True)
        _, y_true, y_pred = run_epoch(model, val_loader, optimizer, device, weights, train=False)
        score = f1_score(y_true, y_pred, average="macro", zero_division=0)
        scheduler.step(score)
        if score > best_score:
            best_score = score
            best_epoch = epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
        if stale >= args.patience:
            break
    if best_state is not None:
        model.load_state_dict(best_state)
    _, y_true, y_pred = run_epoch(model, val_loader, optimizer, device, weights, train=False)
    return {
        "best_epoch": best_epoch,
        "accuracy": accuracy_score(y_true, y_pred),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist(),
        "classification_report": classification_report(y_true, y_pred, labels=[0, 1, 2], target_names=["Type 1", "Type 2", "Type 3"], output_dict=True, zero_division=0),
    }, model.state_dict()


def summarize(metrics):
    cm = np.sum([np.array(m["confusion_matrix"]) for m in metrics], axis=0)
    return {
        "fold_scores": metrics,
        "mean_accuracy": float(np.mean([m["accuracy"] for m in metrics])),
        "std_accuracy": float(np.std([m["accuracy"] for m in metrics])),
        "mean_macro_f1": float(np.mean([m["macro_f1"] for m in metrics])),
        "std_macro_f1": float(np.std([m["macro_f1"] for m in metrics])),
        "mean_weighted_f1": float(np.mean([m["weighted_f1"] for m in metrics])),
        "confusion_matrix": cm.tolist(),
    }


def train_final(dataset, labels, args, device):
    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True, num_workers=0)
    model = make_model(args, device)
    weights = class_weights(labels, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    for _ in range(args.final_epochs):
        run_epoch(model, loader, optimizer, device, weights, train=True)
    return model


def write_report(out, args, summary, classical_theta=None):
    lines = [
        "# DD Theta Goint Classifier Report",
        "",
        "This is a GointMLP-inspired theta-only deep model: multi-branch JointMLP-style head plus auxiliary ordinal loss.",
        "It uses only `theta1` and `theta2`, normalized by 90 degrees.",
        "",
        "## Deep Theta Result",
        "",
        f"Validation mode: `{args.cv_mode}`; folds: {args.splits}",
        "",
        "| Model | Accuracy | Macro F1 | Weighted F1 |",
        "|---|---:|---:|---:|",
        f"| theta_goint | {summary['mean_accuracy']:.4f} ± {summary['std_accuracy']:.4f} | {summary['mean_macro_f1']:.4f} ± {summary['std_macro_f1']:.4f} | {summary['mean_weighted_f1']:.4f} |",
        "",
        "Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:",
        "",
        "```text",
        str(np.array(summary["confusion_matrix"])),
        "```",
    ]
    if classical_theta:
        key = "primary_sample_cv_results" if args.cv_mode == "sample" else "secondary_grouped_cv_results"
        if key in classical_theta:
            lines.extend([
                "",
                "## Classical Theta-Only Comparison",
                "",
                "| Model | Accuracy | Macro F1 | Weighted F1 |",
                "|---|---:|---:|---:|",
            ])
            for name, r in sorted(classical_theta[key].items(), key=lambda item: item[1]["mean_macro_f1"], reverse=True):
                lines.append(f"| {name} | {r['mean_accuracy']:.4f} ± {r['std_accuracy']:.4f} | {r['mean_macro_f1']:.4f} ± {r['std_macro_f1']:.4f} | {r['mean_weighted_f1']:.4f} |")
    (out / "theta_goint_report.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Train theta-only GointMLP-inspired DD classifier")
    parser.add_argument("--data-dir", default="data/datasets/DD_curated_csv_v1")
    parser.add_argument("--output-dir", default="models/dd_laminate_theta_goint_v1")
    parser.add_argument("--cv-mode", choices=["sample", "grouped"], default="sample")
    parser.add_argument("--splits", type=int, default=5)
    parser.add_argument("--epochs", type=int, default=180)
    parser.add_argument("--final-epochs", type=int, default=90)
    parser.add_argument("--patience", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hidden-dim", type=int, default=32)
    parser.add_argument("--num-branches", type=int, default=8)
    parser.add_argument("--dropout", type=float, default=0.12)
    parser.add_argument("--lr", type=float, default=8e-4)
    parser.add_argument("--weight-decay", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--device", choices=["cpu", "mps", "cuda"], default="cpu")
    parser.add_argument("--classical-theta-metrics", default="models/dd_laminate_theta_v1/theta_classifier_metrics.json")
    args = parser.parse_args()
    set_seed(args.seed)
    device = torch.device(args.device)
    samples = load_theta_samples(args.data_dir)
    dataset = DDThetaDataset(samples)
    labels = np.array([s.label - 1 for s in samples], dtype=int)
    groups = np.array([s.test_id for s in samples])
    dummy = np.zeros(len(labels))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    metrics = []
    for fold, (train_idx, val_idx) in enumerate(split_iter(args.cv_mode, args.splits, args.seed, dummy, labels, groups), start=1):
        print(f"Starting fold {fold}/{args.splits}...")
        fold_metrics, _ = train_one_fold(dataset, train_idx, val_idx, labels, args, device)
        print(f"Fold {fold}: acc={fold_metrics['accuracy']:.4f}, macro_f1={fold_metrics['macro_f1']:.4f}, best_epoch={fold_metrics['best_epoch']}")
        metrics.append(fold_metrics)
    summary = summarize(metrics)
    final = train_final(dataset, labels, args, device)
    torch.save({
        "model_state_dict": final.state_dict(),
        "model_config": {
            "input_dim": 2,
            "hidden_dim": args.hidden_dim,
            "num_branches": args.num_branches,
            "dropout": args.dropout,
        },
        "label_names": {0: "Type 1", 1: "Type 2", 2: "Type 3"},
        "summary": summary,
    }, out / "theta_goint.pt")
    (out / "theta_goint_metrics.json").write_text(json.dumps(summary, indent=2))
    classical = None
    classical_path = Path(args.classical_theta_metrics)
    if classical_path.exists():
        classical = json.loads(classical_path.read_text())
    write_report(out, args, summary, classical)
    print(f"Saved model: {out / 'theta_goint.pt'}")
    print(f"Saved report: {out / 'theta_goint_report.md'}")
    print(f"Mean {args.cv_mode} CV accuracy: {summary['mean_accuracy']:.4f}")
    print(f"Mean {args.cv_mode} CV macro F1: {summary['mean_macro_f1']:.4f}")
    print(np.array(summary["confusion_matrix"]))


if __name__ == "__main__":
    main()
