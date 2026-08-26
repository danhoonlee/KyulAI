"""Image-based classifier for DD laminate response types.

Uses a pretrained ResNet18 with transfer learning to classify
force-displacement graph images into Type 1 (bilinear),
Type 2 (linear + curve), or Type 3 (linear + heavy curve).
"""

import torch
import torch.nn as nn
from torchvision import models, transforms

NUM_CLASSES = 3  # Type 1, 2, 3


def get_image_transforms(training: bool = True) -> transforms.Compose:
    """Get image transforms for training or inference."""
    if training:
        return transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.RandomHorizontalFlip(p=0.3),
                transforms.ColorJitter(brightness=0.1, contrast=0.1),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225],
                ),
            ]
        )
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ]
    )


class DDImageClassifier(nn.Module):
    """ResNet18-based classifier for DD laminate graph images."""

    def __init__(self, pretrained: bool = True, dropout: float = 0.3):
        super().__init__()
        weights = models.ResNet18_Weights.DEFAULT if pretrained else None
        self.backbone = models.resnet18(weights=weights)

        # Freeze early layers, fine-tune later ones
        for param in list(self.backbone.parameters())[:-20]:
            param.requires_grad = False

        # Replace final FC layer
        in_features = self.backbone.fc.in_features
        self.backbone.fc = nn.Sequential(
            nn.Dropout(dropout),
            nn.Linear(in_features, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.backbone(x)

    def predict(self, x: torch.Tensor) -> torch.Tensor:
        """Return predicted class labels (1-indexed: 1, 2, or 3)."""
        self.eval()
        with torch.no_grad():
            logits = self.forward(x)
            return logits.argmax(dim=1) + 1  # Convert 0-indexed to 1-indexed


class DDAnglePredictor(nn.Module):
    """Predicts response type from (theta1, theta2, case_type).

    A simple MLP that maps angle combinations to type probabilities.
    Useful for optimization: find angles most likely to produce Type 1.
    """

    def __init__(self, hidden_dim: int = 64):
        super().__init__()
        # Input: [theta1, theta2, case_id (0 or 1)]
        self.net = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, NUM_CLASSES),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)

    def predict_proba(self, theta1: float, theta2: float, case_id: int) -> dict:
        """Get type probabilities for a given angle combination."""
        self.eval()
        with torch.no_grad():
            x = torch.tensor([[theta1, theta2, float(case_id)]], dtype=torch.float32)
            logits = self.forward(x)
            probs = torch.softmax(logits, dim=1).squeeze()
            return {
                "type1": probs[0].item(),
                "type2": probs[1].item(),
                "type3": probs[2].item(),
            }


class DDPtPredictor(nn.Module):
    """Predicts transition load (Pt) from (theta1, theta2, case_type).

    Regression model for the second optimization objective:
    maximize Pt while maintaining Type 1 behavior.
    """

    def __init__(self, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(3, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)

    def predict(self, theta1: float, theta2: float, case_id: int) -> float:
        """Predict Pt for a given angle combination."""
        self.eval()
        with torch.no_grad():
            x = torch.tensor([[theta1, theta2, float(case_id)]], dtype=torch.float32)
            return self.forward(x).item()
