# Curve CSV Batch Input Guide

This guide explains how to prepare files for the DD Laminate `Curve CSV` classifier.

---

## 한국어 안내

### 1. 언제 사용하나요?

`Curve CSV`는 Force-Displacement 해석 결과 CSV와 Pt 값이 이미 있을 때 Type 1, Type 2, Type 3을 분류하는 기능입니다.

한 개 CSV만 넣을 수도 있고, 여러 CSV를 한 번에 넣을 수도 있습니다.

### 2. 단일 CSV 예측

CSV 1개만 예측할 때는 화면 입력값을 직접 넣으면 됩니다.

필요한 입력:

- `Force-displacement CSV`: 변위-하중 데이터 파일
- `θ₁`
- `θ₂`
- `Pt`
- `Case`
- `Test ID`

CSV 파일은 최소 2개 숫자 컬럼이 있어야 합니다.

예:

```csv
0.000000,0.000000
0.000150,32.421
0.000300,64.882
```

헤더가 있어도 되고 없어도 됩니다. 중요한 것은 각 행에서 displacement, force에 해당하는 숫자 2개를 읽을 수 있어야 한다는 점입니다.

### 3. 여러 CSV 일괄 예측

여러 CSV를 한 번에 예측하려면 `Force-displacement CSV` 입력에서 여러 파일을 동시에 선택하면 됩니다.

- 한 번에 최대 1,000개 CSV를 선택할 수 있습니다.
- 브라우저는 200개 단위로 자동 분할해 순서대로 전송합니다.
- 선택한 파일의 개수와 전체 용량, 처리 진행률이 화면에 표시됩니다.
- 전체 CSV 용량은 256 MiB 이하여야 하며, 파일 하나는 16 MiB 이하여야 합니다.

권장 구성은 다음과 같습니다.

```text
New_Data/
├── csv_6x8_Case2/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
├── csv_6x8_Case3/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
├── csv_6x8_Case4/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
└── metadata_case2.csv
```

웹에서 업로드할 때는 폴더 자체가 아니라, 폴더 안의 `force_disp_Test_###.csv` 파일들을 여러 개 선택합니다.

### 4. Batch metadata CSV

여러 파일을 정확히 분류하려면 `Batch metadata CSV`를 같이 넣는 것을 권장합니다.

metadata CSV에는 파일별 `θ₁`, `θ₂`, `Pt`, `Case`, `Test ID`가 들어갑니다.

필수/권장 컬럼:

```csv
filename,test_id,theta1,theta2,pt,case
force_disp_Test_001.csv,Test_001,65,19,7525.576895339104,Case2
force_disp_Test_002.csv,Test_002,40,-51,9876.031555208407,Case2
force_disp_Test_003.csv,Test_003,-44,65,9433.471421825043,Case2
```

컬럼 의미:

| 컬럼 | 의미 |
| --- | --- |
| `filename` | 업로드하는 실제 CSV 파일명입니다. 예: `force_disp_Test_001.csv` |
| `test_id` | 실험 번호입니다. 예: `Test_001` |
| `theta1` | θ₁ 각도입니다. |
| `theta2` | θ₂ 각도입니다. |
| `pt` | transition load Pt 값입니다. |
| `case` | `Case2`, `Case3`, `Case4` 중 하나입니다. |

`filename`은 업로드한 CSV 파일명과 정확히 맞는 것이 가장 좋습니다.

### 5. metadata CSV가 없으면 어떻게 되나요?

metadata CSV를 넣지 않으면, 화면에 입력한 `θ₁`, `θ₂`, `Pt`, `Case` 값이 선택한 모든 CSV에 동일하게 적용됩니다.

따라서 파일마다 각도나 Pt가 다르면 metadata CSV를 반드시 넣는 것이 좋습니다.

### 6. 현재 New_Data 기준 예시

현재 프로젝트의 새 데이터는 다음처럼 되어 있습니다.

```text
data/New_data/
├── 6x8_Case2/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
├── 6x8_Case3/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
├── 6x8_Case4/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
└── batch_metadata/
```

이 구조에서 웹에 올릴 때는:

1. 각 Case의 `csv` 폴더 안에서 `force_disp_Test_###.csv` 파일들을 선택합니다.
2. `batch_metadata/curve_batch_metadata_6x8_Case#.csv`를 metadata로 선택합니다.
3. metadata는 `scripts/dd_make_curve_batch_metadata.py`로 다시 만들 수 있습니다.

2026-07-22 확인 기준으로 Case3의 `csv` 폴더에는 230개만 있으며 `Test_031`부터
`Test_100`까지 70개 CSV가 없습니다. Case4의 `csv` 폴더에는 300개가 모두 있습니다.

업로드용 metadata 예:

```csv
filename,test_id,theta1,theta2,pt,case
force_disp_Test_001.csv,Test_001,65.0,19.0,7525.576895339104,Case2
```

---

## English Guide

### 1. When should I use Curve CSV?

Use `Curve CSV` after force-displacement simulation CSV files and Pt values are available.

It classifies each curve into Type 1, Type 2, or Type 3.

You can run either a single CSV or multiple CSV files at once.

### 2. Single CSV Prediction

For one CSV, fill in the form values directly.

Required inputs:

- `Force-displacement CSV`
- `θ₁`
- `θ₂`
- `Pt`
- `Case`
- `Test ID`

The force-displacement CSV should contain at least two numeric columns.

Example:

```csv
0.000000,0.000000
0.000150,32.421
0.000300,64.882
```

A header row is allowed, but each data row must contain readable numeric displacement and force values.

### 3. Batch Prediction with Multiple CSV Files

For batch prediction, select multiple `force_disp_Test_###.csv` files in the `Force-displacement CSV` input.

- You can select up to 1,000 CSV files at once.
- The browser automatically sends large selections in sequential chunks of 200 files.
- The UI shows the selected count, total size, and processing progress.
- The combined CSV size must not exceed 256 MiB, and each file must not exceed 16 MiB.

Recommended structure:

```text
New_Data/
├── csv_6x8_Case2/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
├── csv_6x8_Case3/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
├── csv_6x8_Case4/
│   ├── force_disp_Test_001.csv
│   ├── force_disp_Test_002.csv
│   └── ...
└── metadata_case2.csv
```

In the browser, upload the CSV files themselves. Do not upload the folder.

### 4. Batch Metadata CSV

For accurate batch classification, use a `Batch metadata CSV`.

The metadata file provides per-file `θ₁`, `θ₂`, `Pt`, `Case`, and `Test ID`.

Recommended columns:

```csv
filename,test_id,theta1,theta2,pt,case
force_disp_Test_001.csv,Test_001,65,19,7525.576895339104,Case2
force_disp_Test_002.csv,Test_002,40,-51,9876.031555208407,Case2
force_disp_Test_003.csv,Test_003,-44,65,9433.471421825043,Case2
```

Column meanings:

| Column | Meaning |
| --- | --- |
| `filename` | The exact uploaded CSV filename. Example: `force_disp_Test_001.csv` |
| `test_id` | Test identifier. Example: `Test_001` |
| `theta1` | θ₁ angle. |
| `theta2` | θ₂ angle. |
| `pt` | Transition load Pt. |
| `case` | One of `Case2`, `Case3`, or `Case4`. |

The `filename` value should match the uploaded CSV filename.

### 5. What happens without metadata?

If no metadata CSV is uploaded, the shared form values for `θ₁`, `θ₂`, `Pt`, and `Case` are reused for every selected CSV.

If each CSV has different angles or Pt values, provide a metadata CSV.

### 6. Current New_Data Example

The current project data is organized like this:

```text
data/New_data/
├── 6x8_Case2/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
├── 6x8_Case3/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
├── 6x8_Case4/
│   ├── Original/
│   ├── csv/
│   └── transition load.csv
└── batch_metadata/
```

For web upload:

1. Select the `force_disp_Test_###.csv` files from the relevant Case `csv` folder.
2. Select the matching `batch_metadata/curve_batch_metadata_6x8_Case#.csv` file.
3. Regenerate these files with `scripts/dd_make_curve_batch_metadata.py` when transition data changes.

As checked on 2026-07-22, the Case3 `csv` directory contains only 230 files: `Test_031`
through `Test_100` are missing. The Case4 `csv` directory contains all 300 files.

Upload metadata example:

```csv
filename,test_id,theta1,theta2,pt,case
force_disp_Test_001.csv,Test_001,65.0,19.0,7525.576895339104,Case2
```
