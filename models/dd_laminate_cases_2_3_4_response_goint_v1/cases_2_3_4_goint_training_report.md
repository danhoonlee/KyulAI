# DD Case2/3/4 GointMLP Training Report

New GointMLP-style models trained on the same curated Case2/Case3/Case4 dataset as the Tree models.

## Theta + Case Classifier

- Accuracy: 0.9356 +/- 0.0163
- Macro F1: 0.9314 +/- 0.0143

## Laminate Forecast Surrogate

- Type accuracy: 0.9356 +/- 0.0134
- Type macro F1: 0.9338 +/- 0.0115
- Pt MAE: 893.28
- Max. Displacement MAE: 0.000376
- Max. Force MAE: 1651.29
- Normalized curve RMSE: 0.02370

The Tree models remain the safer default when they score higher; these models provide the matched deep-learning option.
