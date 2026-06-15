# Simple Injection Dataset

이 문서는 `Simple_Injection` 데이터셋의 현재 구조, 생성 이력, 학습에 사용하는 파일 범위를 정리하기 위한 기준 문서입니다.

## 목적

이 데이터셋은 중앙 원형 홀이 있는 직육면체 형상에 edge gate로 PP 수지를 사출하는 Moldex3D 해석 결과를 AI surrogate 모델로 학습하기 위해 구성되었습니다.

현재 예측 목표는 두 가지입니다.

- `Sprue Pressure`: 시간에 따른 sprue pressure curve.
- `Filling Pressure`: Moldex3D histogram export 기반 filling pressure 분포 요약.

## 현재 표준 폴더 구조

현재 학습 데이터는 하나의 표준 위치로 통합되어 있습니다.

```text
data/datasets/Simple_Injection/
  DOE/
    geometry_doe_30.csv
    process_doe_10.csv
    supplemental_v02_v03_geometry_doe.csv
    supplemental_v02_v03_process_doe.csv
    supplemental_v02_v03_case_matrix_60.csv
  Training/
    Filling_Pressure/
      G01/
        P01/
        ...
        P10/
      ...
      G42/
    Sprue_Pressure/
      G01/
        P01/
        ...
        P10/
      ...
      G42/
    Source_Exports/
      Sprue_Pressure_Combined/
  Validation_1/
  Validation_2/
  Shape/
  step/
```

`Training`만 모델 학습에 사용합니다. `Validation_1`과 `Validation_2`는 모델 성능 확인용 hold-out 또는 참고 데이터이며, 기본 학습 loader에는 포함하지 않습니다.

## 데이터 구성

현재 학습 기준 record 수는 다음과 같습니다.

| Target | 학습 record 수 | 파일 구성 |
|---|---:|---|
| Filling Pressure | 360 cases | `G##_P##_Filling_Pressure.csv` |
| Sprue Pressure | 360 curves | `G##_P##_Sprue_Pressure.csv` |

현재 학습 파일은 Filling과 Sprue 모두 case별 `G##/P##` 폴더로 정리되어 있습니다. 과거 G01-G30 Sprue Pressure는 geometry별 P01-P10 묶음 CSV 30개로 export되었지만, 현재는 학습 일관성을 위해 case별 CSV 300개로 분리했습니다. 원본 묶음 CSV는 `Training/Source_Exports/Sprue_Pressure_Combined`에 보관합니다.

## 생성 이력

### 1. Original DOE: G01-G30, P01-P10

처음 만든 기본 DOE입니다.

- Geometry: `G01-G30`, 총 30개
- Process: `P01-P10`, 총 10개
- 조합 수: `30 x 10 = 300`

기본 geometry feature는 `geometry_doe_30.csv`에 있습니다.

- `L_mm`
- `W_mm`
- `t_mm`
- `D_mm`
- `R_mm`
- `gate_type`
- `gate_size_width_mm`
- `gate_size_height_mm`

기본 process feature는 `process_doe_10.csv`에 있습니다.

- `melt_temp_C`
- `mold_temp_C`
- `injection_time_s`
- `packing_pressure_MPa`
- `packing_time_s`

이 300건이 가장 먼저 생성된 기본 학습 데이터입니다.

### 2. Supplemental V02: G31-G34, P11-P15

Validation #2 조건에서 모델이 외삽 구간을 만났고, 특히 긴 유동거리, 얇은 두께, 높은 packing pressure 조합에서 보강 데이터가 필요하다고 판단했습니다.

그래서 V02 범위의 추가 DOE를 만들었습니다.

- Geometry: `G31-G34`, 총 4개
- Process: `P11-P15`, 총 5개
- 조합 수: `4 x 5 = 20`
- 목적: 긴 유동거리/얇은 두께/고압 조건 보강

V02 데이터는 기존 300건이 커버하지 못하던 high-pressure extrapolation 성향을 줄이기 위해 추가되었습니다.

### 3. Supplemental V03: G35-G42, P16-P20

Validation #3 조건에서는 짧은 유동거리, 두꺼운 두께, 빠른 injection time 쪽에서 Filling Pressure 분포 예측이 약했습니다.

그래서 V03 범위의 추가 DOE를 만들었습니다.

- Geometry: `G35-G42`, 총 8개
- Process: `P16-P20`, 총 5개
- 조합 수: `8 x 5 = 40`
- 목적: 짧은 유동거리/두꺼운 형상/빠른 충전 조건 보강

V03 데이터는 특히 Filling Pressure max와 histogram volume ratio 예측을 안정화하기 위해 추가되었습니다.

## DOE 파일의 역할

`DOE/geometry_doe_30.csv`와 `DOE/process_doe_10.csv`는 original DOE의 기준입니다.

`DOE/supplemental_v02_v03_geometry_doe.csv`와 `DOE/supplemental_v02_v03_process_doe.csv`는 G31 이후 geometry와 P11 이후 process를 정의합니다.

`DOE/supplemental_v02_v03_case_matrix_60.csv`는 V02/V03 추가 데이터의 전체 조합을 설명하는 traceability table입니다. 나중에 왜 G31 이후 번호가 생겼는지 확인해야 할 때 이 파일을 보면 됩니다.

## 파일명 규칙

Filling Pressure는 case별 process 폴더에 저장합니다.

```text
Training/Filling_Pressure/G01/P01/G01_P01_Filling_Pressure.csv
Training/Filling_Pressure/G01/P01/G01_P01_Filling_Pressure_chart.png
Training/Filling_Pressure/G31/P11/G31_P11_Filling_Pressure.csv
Training/Filling_Pressure/G31/P11/G31_P11_Filling_Pressure_chart.png
```

Sprue Pressure도 동일하게 case별 process 폴더에 저장합니다.

```text
Training/Sprue_Pressure/G01/P01/G01_P01_Sprue_Pressure.csv
Training/Sprue_Pressure/G31/P11/G31_P11_Sprue_Pressure.csv
```

파일명에는 공백을 쓰지 않습니다. 새 데이터를 추가할 때도 `_` 기반 이름을 사용합니다.

원본 Moldex3D export를 따로 보관해야 할 때는 학습 폴더 안에 섞지 않고 `Training/Source_Exports` 아래에 둡니다.

## 학습 loader 기준

현재 `src/ml/simple_injection/data.py`의 기본 loader는 다음 순서로 데이터를 읽습니다.

1. `Training/Filling_Pressure`
2. `Training/Sprue_Pressure`
3. supplemental DOE 포함 geometry/process table

예전 개발 과정에서 사용하던 `Training_1`, `Training_2`, `Validation_Set` 구조는 더 이상 표준 학습 위치가 아닙니다.

## Validation 데이터 사용 원칙

`Validation_1`과 `Validation_2`는 학습 데이터와 분리합니다.

- `Validation_1/validation#1`: original DOE 밖 manual check.
- `Validation_1/validation#2`: V02를 만들게 된 긴 유동거리/얇은 두께 계열 check.
- `Validation_1/validation#3`: V03를 만들게 된 짧은 유동거리/두꺼운 두께 계열 check.
- `Validation_2`: 이후 비교용으로 추가된 validation 결과.

Validation 결과를 학습에 넣을 경우에는 먼저 DOE 번호를 새로 부여하고, `Training` 아래로 이동한 뒤, supplemental DOE 파일에도 같은 ID를 추가해야 합니다.

## 현재 데이터 한계

- Resin은 현재 모두 PP로 가정하고 있으며, 물성 차이는 feature에 들어가지 않았습니다.
- Gate type과 gate size는 대부분 동일합니다. 향후 gate 조건을 다양화하면 별도 보강 DOE가 필요합니다.
- Filling Pressure CSV는 Moldex3D histogram export라서 mesh point 좌표가 없습니다. 즉, 현재 학습 target은 진짜 spatial contour field가 아니라 pressure distribution summary입니다.
- Parametric preview의 contour와 filling animation은 histogram을 기반으로 한 surrogate visualization입니다.

## 새 데이터를 추가할 때

새로운 학습 데이터를 추가할 때는 다음 규칙을 지킵니다.

1. 새 geometry는 기존 번호 다음인 `G43`부터 부여합니다.
2. 새 process는 기존 번호 다음인 `P21`부터 부여합니다.
3. DOE CSV에 geometry/process 정보를 먼저 추가합니다.
4. Filling 파일은 `Training/Filling_Pressure/G##/P##/G##_P##_Filling_Pressure.csv` 형식으로 넣습니다.
5. Filling chart는 `Training/Filling_Pressure/G##/P##/G##_P##_Filling_Pressure_chart.png` 형식으로 넣습니다.
6. Sprue 파일은 `Training/Sprue_Pressure/G##/P##/G##_P##_Sprue_Pressure.csv` 형식으로 넣습니다.
7. 파일명에는 공백을 넣지 않습니다.
8. 학습 전 loader count가 기대 record 수와 맞는지 확인합니다.
