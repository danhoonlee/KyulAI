"""Data loading for DD laminate classification.

Loads force-displacement graph images and metadata from the DD dataset.
Supports Case3 and Case4 with Trial_1 (P1) and Trial_2 (P2) measurements.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image


@dataclass
class DDSample:
    """A single DD laminate simulation sample."""
    test_id: str
    case: str           # "Case3" or "Case4"
    theta1: float
    theta2: float
    pt: float           # transition load
    label: int          # 1, 2, or 3
    image_path_p1: Optional[Path] = None
    image_path_p2: Optional[Path] = None


class DDDataset:
    """Dataset for DD laminate response type classification.

    Loads from the directory structure:
        data/datasets/DD/{Case3,Case4}/transition_load.csv
        data/datasets/DD/{Case3,Case4}/Trial_1/type{1,2,3}/*.png
    """

    def __init__(
        self,
        data_dir: str | Path,
        cases: list[str] | None = None,
        trial: str = "Trial_1",
    ):
        self.data_dir = Path(data_dir)
        self.cases = cases or ["Case3", "Case4"]
        self.trial = trial
        self.samples: list[DDSample] = []
        self._load()

    def _load(self):
        """Load all samples from CSV and match with image files."""
        for case in self.cases:
            case_dir = self.data_dir / case
            csv_path = case_dir / "transition_load.csv"

            if not csv_path.exists():
                raise FileNotFoundError(f"CSV not found: {csv_path}")

            # Read CSV
            with open(csv_path) as f:
                reader = csv.DictReader(f)
                for row in reader:
                    test_id = row["Test_ID"]
                    label = int(row["type"])
                    suffix_p1 = "P1"
                    suffix_p2 = "P2"

                    # Find image paths
                    img_p1 = case_dir / self.trial.replace("2", "1") / f"type{label}" / f"plot_{test_id}_{suffix_p1}.png"
                    img_p2 = case_dir / self.trial.replace("1", "2") / f"type{label}" / f"plot_{test_id}_{suffix_p2}.png"

                    sample = DDSample(
                        test_id=test_id,
                        case=case,
                        theta1=float(row["Theta1"]),
                        theta2=float(row["Theta2"]),
                        pt=float(row["Pt"]),
                        label=label,
                        image_path_p1=img_p1 if img_p1.exists() else None,
                        image_path_p2=img_p2 if img_p2.exists() else None,
                    )
                    self.samples.append(sample)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> DDSample:
        return self.samples[idx]

    def get_by_label(self, label: int) -> list[DDSample]:
        return [s for s in self.samples if s.label == label]

    def get_by_case(self, case: str) -> list[DDSample]:
        return [s for s in self.samples if s.case == case]

    def to_angle_arrays(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return (features, labels, case_ids) as numpy arrays.

        Features: [theta1, theta2] for each sample
        Labels: type (1, 2, 3) for each sample
        Case IDs: 0 for Case3, 1 for Case4
        """
        features = np.array([[s.theta1, s.theta2] for s in self.samples])
        labels = np.array([s.label for s in self.samples])
        case_ids = np.array([0 if s.case == "Case3" else 1 for s in self.samples])
        return features, labels, case_ids

    def load_image(self, sample: DDSample, trial: str = "p1") -> np.ndarray | None:
        """Load a graph image as numpy array."""
        path = sample.image_path_p1 if trial == "p1" else sample.image_path_p2
        if path is None or not path.exists():
            return None
        img = Image.open(path).convert("RGB")
        return np.array(img)

    def summary(self) -> str:
        """Print dataset summary."""
        lines = ["DD Laminate Dataset Summary", "=" * 40]
        for case in self.cases:
            case_samples = self.get_by_case(case)
            lines.append(f"\n{case}: {len(case_samples)} samples")
            for t in [1, 2, 3]:
                count = sum(1 for s in case_samples if s.label == t)
                lines.append(f"  Type {t}: {count}")
        lines.append(f"\nTotal: {len(self.samples)} samples")
        return "\n".join(lines)


def load_dd_dataset(
    data_dir: str = "data/datasets/DD",
    cases: list[str] | None = None,
) -> DDDataset:
    """Convenience function to load the DD dataset."""
    return DDDataset(data_dir=data_dir, cases=cases)
