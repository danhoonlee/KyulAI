"""Training script for DD laminate classifiers.

Trains both:
1. Image classifier (ResNet18) on force-displacement graph images
2. Angle predictor (MLP) on (theta1, theta2, case) -> type mapping
"""

import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold
from torch.utils.data import DataLoader, Dataset

from .classifier import DDAnglePredictor, DDImageClassifier, DDPtPredictor, get_image_transforms
from .data import DDSample, load_dd_dataset


class DDImageDataset(Dataset):
    """PyTorch Dataset for DD laminate graph images."""

    def __init__(self, samples: list[DDSample], transform=None):
        self.samples = [s for s in samples if s.image_path_p1 is not None]
        self.transform = transform

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        sample = self.samples[idx]
        image_path = sample.image_path_p1
        if image_path is None:
            raise ValueError("DDImageDataset samples must have an image_path_p1")
        img = Image.open(image_path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        label = sample.label - 1  # 0-indexed for CrossEntropyLoss
        return img, label, sample.test_id


class DDAngleDataset(Dataset):
    """PyTorch Dataset for angle-based prediction."""

    def __init__(self, samples: list[DDSample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        s = self.samples[idx]
        features = torch.tensor(
            [s.theta1, s.theta2, 0.0 if s.case == "Case3" else 1.0],
            dtype=torch.float32,
        )
        label = s.label - 1
        return features, label


def train_image_classifier(
    data_dir: str = "data/datasets/DD",
    epochs: int = 30,
    batch_size: int = 16,
    lr: float = 1e-3,
    output_dir: str = "models/dd_laminate",
    device: str | None = None,
) -> dict:
    """Train the image classifier with stratified k-fold cross-validation."""
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    dataset = load_dd_dataset(data_dir)
    print(dataset.summary())
    print(f"\nDevice: {device}")

    samples = [s for s in dataset.samples if s.image_path_p1 is not None]
    labels = np.array([s.label for s in samples])

    # Stratified 5-fold CV
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_results = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(samples, labels)):
        print(f"\n{'=' * 50}")
        print(f"Fold {fold + 1}/5")
        print(f"{'=' * 50}")

        train_samples = [samples[i] for i in train_idx]
        val_samples = [samples[i] for i in val_idx]

        train_dataset = DDImageDataset(train_samples, get_image_transforms(training=True))
        val_dataset = DDImageDataset(val_samples, get_image_transforms(training=False))

        # Class weights for imbalanced data
        train_labels = [s.label for s in train_samples]
        class_counts = np.bincount(train_labels, minlength=4)[1:]  # skip 0
        class_weights = 1.0 / (class_counts + 1e-6)
        class_weights = class_weights / class_weights.sum() * len(class_weights)
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_dataset, batch_size=batch_size)

        model = DDImageClassifier(pretrained=True).to(device)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, model.parameters()), lr=lr)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=10, gamma=0.5)

        best_val_acc = 0.0
        for epoch in range(epochs):
            # Train
            model.train()
            train_loss = 0.0
            train_correct = 0
            train_total = 0
            for imgs, labels_batch, _ in train_loader:
                imgs, labels_batch = imgs.to(device), labels_batch.to(device)
                optimizer.zero_grad()
                outputs = model(imgs)
                loss = criterion(outputs, labels_batch)
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
                train_correct += (outputs.argmax(1) == labels_batch).sum().item()
                train_total += labels_batch.size(0)
            scheduler.step()

            # Validate
            model.eval()
            val_correct = 0
            val_total = 0
            all_preds = []
            all_labels = []
            with torch.no_grad():
                for imgs, labels_batch, _ in val_loader:
                    imgs, labels_batch = imgs.to(device), labels_batch.to(device)
                    outputs = model(imgs)
                    preds = outputs.argmax(1)
                    val_correct += (preds == labels_batch).sum().item()
                    val_total += labels_batch.size(0)
                    all_preds.extend(preds.cpu().numpy())
                    all_labels.extend(labels_batch.cpu().numpy())

            val_acc = val_correct / val_total
            if (epoch + 1) % 5 == 0 or epoch == 0:
                print(
                    f"  Epoch {epoch + 1:>3d}/{epochs}: "
                    f"train_loss={train_loss / len(train_loader):.4f} "
                    f"train_acc={train_correct / train_total:.3f} "
                    f"val_acc={val_acc:.3f}"
                )

            if val_acc > best_val_acc:
                best_val_acc = val_acc

        print(f"\n  Best val accuracy: {best_val_acc:.3f}")
        print(f"  Confusion matrix:\n{confusion_matrix(all_labels, all_preds)}")
        print(
            classification_report(
                all_labels,
                all_preds,
                target_names=["Type 1", "Type 2", "Type 3"],
            )
        )
        fold_results.append(best_val_acc)

    mean_acc = np.mean(fold_results)
    print(f"\n{'=' * 50}")
    print(f"Mean CV accuracy: {mean_acc:.3f} (+/- {np.std(fold_results):.3f})")

    # Train final model on all data
    print("\nTraining final model on all data...")
    full_dataset = DDImageDataset(samples, get_image_transforms(training=True))
    full_loader = DataLoader(full_dataset, batch_size=batch_size, shuffle=True)

    all_labels_list = [s.label for s in samples]
    class_counts = np.bincount(all_labels_list, minlength=4)[1:]
    class_weights = 1.0 / (class_counts + 1e-6)
    class_weights = class_weights / class_weights.sum() * len(class_weights)
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)

    final_model = DDImageClassifier(pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimizer = torch.optim.Adam(filter(lambda p: p.requires_grad, final_model.parameters()), lr=lr)

    for _epoch in range(epochs):
        final_model.train()
        for imgs, labels_batch, _ in full_loader:
            imgs, labels_batch = imgs.to(device), labels_batch.to(device)
            optimizer.zero_grad()
            loss = criterion(final_model(imgs), labels_batch)
            loss.backward()
            optimizer.step()

    # Save model
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    model_path = out_path / "image_classifier.pt"
    torch.save(final_model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

    return {"cv_accuracy": mean_acc, "fold_results": fold_results}


def train_angle_predictor(
    data_dir: str = "data/datasets/DD",
    epochs: int = 200,
    batch_size: int = 32,
    lr: float = 1e-3,
    output_dir: str = "models/dd_laminate",
    device: str | None = None,
) -> dict:
    """Train the angle-based type predictor."""
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    dataset = load_dd_dataset(data_dir)
    samples = dataset.samples

    labels = np.array([s.label for s in samples])
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_results = []

    for fold, (train_idx, val_idx) in enumerate(skf.split(samples, labels)):
        print(f"\nFold {fold + 1}/5")

        train_ds = DDAngleDataset([samples[i] for i in train_idx])
        val_ds = DDAngleDataset([samples[i] for i in val_idx])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size)

        train_labels = [samples[i].label for i in train_idx]
        class_counts = np.bincount(train_labels, minlength=4)[1:]
        class_weights = 1.0 / (class_counts + 1e-6)
        class_weights = class_weights / class_weights.sum() * len(class_weights)
        weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)

        model = DDAnglePredictor(hidden_dim=128).to(device)
        criterion = nn.CrossEntropyLoss(weight=weight_tensor)
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)

        best_val_acc = 0.0
        for _epoch in range(epochs):
            model.train()
            for features, labels_batch in train_loader:
                features, labels_batch = features.to(device), labels_batch.to(device)
                optimizer.zero_grad()
                loss = criterion(model(features), labels_batch)
                loss.backward()
                optimizer.step()

            model.eval()
            val_correct = 0
            val_total = 0
            with torch.no_grad():
                for features, labels_batch in val_loader:
                    features, labels_batch = features.to(device), labels_batch.to(device)
                    preds = model(features).argmax(1)
                    val_correct += (preds == labels_batch).sum().item()
                    val_total += labels_batch.size(0)

            val_acc = val_correct / val_total
            if val_acc > best_val_acc:
                best_val_acc = val_acc

        print(f"  Best val accuracy: {best_val_acc:.3f}")
        fold_results.append(best_val_acc)

    mean_acc = np.mean(fold_results)
    print(f"\nAngle predictor mean CV accuracy: {mean_acc:.3f} (+/- {np.std(fold_results):.3f})")

    # Train final model on all data
    full_ds = DDAngleDataset(samples)
    full_loader = DataLoader(full_ds, batch_size=batch_size, shuffle=True)

    all_labels_list = [s.label for s in samples]
    class_counts = np.bincount(all_labels_list, minlength=4)[1:]
    class_weights = 1.0 / (class_counts + 1e-6)
    class_weights = class_weights / class_weights.sum() * len(class_weights)
    weight_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device)

    final_model = DDAnglePredictor(hidden_dim=128).to(device)
    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

    for _epoch in range(epochs):
        final_model.train()
        for features, labels_batch in full_loader:
            features, labels_batch = features.to(device), labels_batch.to(device)
            optimizer.zero_grad()
            loss = criterion(final_model(features), labels_batch)
            loss.backward()
            optimizer.step()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    model_path = out_path / "angle_predictor.pt"
    torch.save(final_model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

    return {"cv_accuracy": mean_acc, "fold_results": fold_results}


class DDPtDataset(Dataset):
    """PyTorch Dataset for Pt regression."""

    def __init__(self, samples: list[DDSample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int):
        s = self.samples[idx]
        features = torch.tensor(
            [s.theta1, s.theta2, 0.0 if s.case == "Case3" else 1.0],
            dtype=torch.float32,
        )
        pt = torch.tensor(s.pt, dtype=torch.float32)
        return features, pt


def train_pt_predictor(
    data_dir: str = "data/datasets/DD",
    epochs: int = 300,
    batch_size: int = 32,
    lr: float = 1e-3,
    output_dir: str = "models/dd_laminate",
    device: str | None = None,
) -> dict:
    """Train the Pt (transition load) regression model."""
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    dataset = load_dd_dataset(data_dir)
    samples = dataset.samples

    # Compute normalization stats
    pts = np.array([s.pt for s in samples])
    pt_mean, pt_std = pts.mean(), pts.std()
    print(f"Pt stats: mean={pt_mean:.0f}, std={pt_std:.0f}")

    from sklearn.model_selection import KFold

    kf = KFold(n_splits=5, shuffle=True, random_state=42)
    fold_results = []

    for fold, (train_idx, val_idx) in enumerate(kf.split(samples)):
        print(f"\nFold {fold + 1}/5")

        train_ds = DDPtDataset([samples[i] for i in train_idx])
        val_ds = DDPtDataset([samples[i] for i in val_idx])

        train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True)
        val_loader = DataLoader(val_ds, batch_size=batch_size)

        model = DDPtPredictor(hidden_dim=128).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=lr)
        scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.5)

        best_val_mae = float("inf")
        for _epoch in range(epochs):
            model.train()
            for features, pt_batch in train_loader:
                features, pt_batch = features.to(device), pt_batch.to(device)
                # Normalize target
                pt_norm = (pt_batch - pt_mean) / pt_std
                optimizer.zero_grad()
                loss = criterion(model(features), pt_norm)
                loss.backward()
                optimizer.step()
            scheduler.step()

            model.eval()
            val_errors: list[float] = []
            with torch.no_grad():
                for features, pt_batch in val_loader:
                    features, pt_batch = features.to(device), pt_batch.to(device)
                    preds = model(features) * pt_std + pt_mean
                    val_errors.extend(
                        float(err) for err in torch.abs(preds - pt_batch).cpu().numpy()
                    )

            val_mae = float(np.mean(val_errors))
            if val_mae < best_val_mae:
                best_val_mae = val_mae

        rel_error = best_val_mae / pt_mean * 100
        print(f"  Best val MAE: {best_val_mae:.0f} ({rel_error:.1f}%)")
        fold_results.append(best_val_mae)

    mean_mae = np.mean(fold_results)
    print(f"\nPt predictor mean CV MAE: {mean_mae:.0f} ({mean_mae / pt_mean * 100:.1f}%)")

    # Train final model
    full_ds = DDPtDataset(samples)
    full_loader = DataLoader(full_ds, batch_size=batch_size, shuffle=True)

    final_model = DDPtPredictor(hidden_dim=128).to(device)
    optimizer = torch.optim.Adam(final_model.parameters(), lr=lr)

    for _epoch in range(epochs):
        final_model.train()
        for features, pt_batch in full_loader:
            features, pt_batch = features.to(device), pt_batch.to(device)
            pt_norm = (pt_batch - pt_mean) / pt_std
            optimizer.zero_grad()
            loss = criterion(final_model(features), pt_norm)
            loss.backward()
            optimizer.step()

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    model_path = out_path / "pt_predictor.pt"
    torch.save(
        {
            "model_state_dict": final_model.state_dict(),
            "pt_mean": float(pt_mean),
            "pt_std": float(pt_std),
        },
        model_path,
    )
    print(f"Model saved to {model_path}")

    return {"cv_mae": mean_mae, "fold_results": fold_results}


def review_classifications(
    data_dir: str = "data/datasets/DD",
    model_path: str = "models/dd_laminate/image_classifier.pt",
    device: str | None = None,
) -> list[dict]:
    """Use trained model to review all classifications and flag disagreements."""
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else "cpu"

    dataset = load_dd_dataset(data_dir)
    transform = get_image_transforms(training=False)

    model = DDImageClassifier(pretrained=False)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.to(device)
    model.eval()

    disagreements = []
    for sample in dataset.samples:
        if sample.image_path_p1 is None:
            continue

        img = Image.open(sample.image_path_p1).convert("RGB")
        img_tensor = transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            logits = model(img_tensor)
            probs = torch.softmax(logits, dim=1).squeeze()
            predicted = logits.argmax(1).item() + 1

        if predicted != sample.label:
            disagreements.append(
                {
                    "test_id": sample.test_id,
                    "case": sample.case,
                    "theta1": sample.theta1,
                    "theta2": sample.theta2,
                    "manual_label": sample.label,
                    "predicted_label": predicted,
                    "confidence": probs[predicted - 1].item(),
                    "probs": {f"type{i + 1}": probs[i].item() for i in range(3)},
                }
            )

    print(f"\nFound {len(disagreements)} disagreements out of {len(dataset)} samples")
    for d in sorted(disagreements, key=lambda x: -x["confidence"]):
        print(
            f"  {d['case']}/{d['test_id']}: "
            f"manual=Type {d['manual_label']}, "
            f"predicted=Type {d['predicted_label']} "
            f"(conf={d['confidence']:.2f})"
        )

    return disagreements


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DD laminate classifiers")
    parser.add_argument("--mode", choices=["image", "angle", "pt", "review", "all"], default="all")
    parser.add_argument("--data-dir", default="data/datasets/DD")
    parser.add_argument("--output-dir", default="models/dd_laminate")
    parser.add_argument("--epochs-image", type=int, default=30)
    parser.add_argument("--epochs-angle", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    if args.mode in ("image", "all"):
        print("=" * 60)
        print("Training Image Classifier")
        print("=" * 60)
        train_image_classifier(
            data_dir=args.data_dir,
            epochs=args.epochs_image,
            batch_size=args.batch_size,
            lr=args.lr,
            output_dir=args.output_dir,
        )

    if args.mode in ("angle", "all"):
        print("\n" + "=" * 60)
        print("Training Angle Predictor")
        print("=" * 60)
        train_angle_predictor(
            data_dir=args.data_dir,
            epochs=args.epochs_angle,
            batch_size=args.batch_size,
            lr=args.lr,
            output_dir=args.output_dir,
        )

    if args.mode in ("pt", "all"):
        print("\n" + "=" * 60)
        print("Training Pt Predictor")
        print("=" * 60)
        train_pt_predictor(
            data_dir=args.data_dir,
            epochs=300,
            batch_size=args.batch_size,
            lr=args.lr,
            output_dir=args.output_dir,
        )

    if args.mode in ("review", "all"):
        model_path = f"{args.output_dir}/image_classifier.pt"
        if Path(model_path).exists():
            print("\n" + "=" * 60)
            print("Reviewing Classifications")
            print("=" * 60)
            review_classifications(data_dir=args.data_dir, model_path=model_path)
