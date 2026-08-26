"""Predict DD laminate Type from one CSV using the Goint sequence model."""

from __future__ import annotations

import argparse
from functools import lru_cache
from pathlib import Path

import torch

from .deep_sequence import (
    DDGointSequenceClassifier,
    DDSequenceDataset,
    DDSequenceSample,
    predict_from_logits,
)


@lru_cache(maxsize=4)
def _load_model_cached(model_path: str, device_name: str):
    device = torch.device(device_name)
    checkpoint = torch.load(model_path, map_location=device, weights_only=False)
    config = checkpoint["model_config"]
    model = DDGointSequenceClassifier(
        input_size=config["input_size"],
        hidden_size=config["hidden_size"],
        gru_layers=config["gru_layers"],
        branch_dim=config["branch_dim"],
        num_branches=config["num_branches"],
        dropout=config["dropout"],
    ).to(device)
    model.load_state_dict(checkpoint["model_state_dict"])
    model.eval()
    return model, checkpoint


def load_model(model_path: str | Path, device: torch.device):
    return _load_model_cached(str(Path(model_path).resolve()), str(device))


def predict_deep_type(
    model_path: str | Path,
    csv_path: str | Path,
    pt: float,
    case: str,
    theta1: float,
    theta2: float,
    test_id: str = "Unknown",
    device: str = "cpu",
) -> dict:
    torch_device = torch.device(device)
    model, checkpoint = load_model(model_path, torch_device)
    sample = DDSequenceSample(
        case=case,
        test_id=test_id,
        theta1=theta1,
        theta2=theta2,
        pt=pt,
        label=1,
        csv_path=Path(csv_path),
    )
    seq_len = int(checkpoint["model_config"].get("seq_len", 128))
    pt_scale = float(checkpoint.get("pt_scale", max(pt, 1.0)))
    dataset = DDSequenceDataset([sample], seq_len=seq_len, pt_scale=pt_scale)
    x = dataset[0]["x"].unsqueeze(0).to(torch_device)
    with torch.no_grad():
        logits, ordinal_logits = model(x)
        probabilities = torch.softmax(logits, dim=1).squeeze(0).cpu()
        predicted = int(predict_from_logits(logits).item()) + 1
    return {
        "predicted_type": predicted,
        "probabilities": {f"type{i + 1}": float(probabilities[i]) for i in range(3)},
        "ordinal_probabilities": torch.sigmoid(ordinal_logits).squeeze(0).cpu().tolist(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Predict DD Type with the deep sequence model")
    parser.add_argument("csv_path")
    parser.add_argument(
        "--model", default="models/dd_laminate_deep_sequence_v1/dd_goint_sequence.pt"
    )
    parser.add_argument("--pt", type=float, required=True)
    parser.add_argument("--case", required=True)
    parser.add_argument("--theta1", type=float, required=True)
    parser.add_argument("--theta2", type=float, required=True)
    parser.add_argument("--test-id", default="Unknown")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    result = predict_deep_type(
        model_path=args.model,
        csv_path=args.csv_path,
        pt=args.pt,
        case=args.case,
        theta1=args.theta1,
        theta2=args.theta2,
        test_id=args.test_id,
        device=args.device,
    )
    print(f"Predicted Type: {result['predicted_type']}")
    print("Probabilities:")
    for label, probability in result["probabilities"].items():
        print(f"  {label}: {probability:.4f}")
    print("Ordinal probabilities:")
    for idx, probability in enumerate(result["ordinal_probabilities"], start=1):
        print(f"  P(type > {idx}): {probability:.4f}")


if __name__ == "__main__":
    main()
