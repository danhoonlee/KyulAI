"""Predict DD Type from theta1/theta2/case with the theta Goint model."""

from __future__ import annotations

import argparse
from pathlib import Path

import torch

from .theta_deep import DDThetaGointClassifier, predict_from_logits
from .train_cases_2_3_4_classical import theta_feature_row, DDRecord


def predict(theta1: float, theta2: float, model_path: str | Path, case: str = "Case4", device: str = "cpu"):
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    cfg = checkpoint["model_config"]
    model = DDThetaGointClassifier(
        input_dim=cfg["input_dim"],
        hidden_dim=cfg["hidden_dim"],
        num_branches=cfg["num_branches"],
        dropout=cfg["dropout"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    if "feature_columns" in checkpoint:
        record = DDRecord(
            case=case,
            test_id="Estimated",
            theta1=theta1,
            theta2=theta2,
            pt=0.0,
            label=0,
            csv_path=Path(""),
        )
        x_raw = torch.tensor([theta_feature_row(record)], dtype=torch.float32)
        feature_mean = torch.tensor(checkpoint["feature_mean"], dtype=torch.float32)
        feature_std = torch.tensor(checkpoint["feature_std"], dtype=torch.float32)
        x = ((x_raw - feature_mean) / torch.clamp(feature_std, min=1e-9)).to(device)
    else:
        x = torch.tensor([[theta1 / 90.0, theta2 / 90.0, 1.0 if case == "Case4" else 0.0]], dtype=torch.float32, device=device)
    with torch.no_grad():
        logits, ordinal_logits = model(x)
        probs = torch.softmax(logits, dim=1).squeeze(0).cpu()
        ordinal = torch.sigmoid(ordinal_logits).squeeze(0).cpu()
        pred = int(predict_from_logits(logits).item()) + 1
    return {
        "predicted_type": pred,
        "probabilities": {f"type{i + 1}": float(probs[i]) for i in range(3)},
        "ordinal_probabilities": ordinal.tolist(),
    }


def main():
    parser = argparse.ArgumentParser(description="Predict DD Type from theta1/theta2/case with theta Goint model")
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--case", choices=["Case2", "Case3", "Case4"], default="Case4")
    parser.add_argument("--model", default="models/dd_laminate_theta_goint_v1/theta_goint.pt")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = predict(args.theta1, args.theta2, args.model, args.case, args.device)
    print(f"Predicted Type: {result['predicted_type']}")
    print("Probabilities:")
    for label, probability in result["probabilities"].items():
        print(f"  {label}: {probability:.4f}")
    print("Ordinal probabilities:")
    for idx, probability in enumerate(result["ordinal_probabilities"], start=1):
        print(f"  P(type > {idx}): {probability:.4f}")


if __name__ == "__main__":
    main()
