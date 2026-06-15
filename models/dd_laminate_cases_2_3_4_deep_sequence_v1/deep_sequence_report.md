# DD Case2/3/4 Goint Sequence Classifier Report

GRU sequence encoder + GointMLP-style multi-branch head trained on the same
Case2/Case3/Case4 curated dataset as the Tree curve model.

- Samples: 900
- Validation: grouped 5-fold CV
- Accuracy: 0.9343 +/- 0.0131
- Macro F1: 0.9342 +/- 0.0203
- Weighted F1: 0.9347

Confusion matrix rows=true, columns=predicted `[Type1, Type2, Type3]`:

```text
[[300, 21, 0], [19, 411, 15], [1, 3, 130]]
```
