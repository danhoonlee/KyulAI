# Simple Injection Next DOE Proposal

이 DOE는 현재 360건 학습 모델에서 약하게 보이는 구간을 보강하기 위한 추가 Moldex3D 해석 후보입니다.

## 구성

| Family | Geometry | Process | Cases | 목적 |
|---|---:|---:|---:|---|
| `V01_filling_refine` | G43-G47 | P21-P25 | 25 | V01 계열 Filling Pressure max 과예측 보정 |
| `V02_sprue_refine` | G48-G51 | P26-P30 | 20 | 긴 유동거리/얇은 두께/고압 조건의 Sprue curve 보강 |
| `bridge_mid_range` | G52-G53 | P31-P35 | 10 | Original DOE와 V02/V03 사이 연결 구간 보강 |

총 55 cases입니다.

## 생성 파일

```text
data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_geometry_doe.csv
data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_process_doe.csv
data/datasets/Simple_Injection/DOE/supplemental_v01_v02_bridge_case_matrix_55.csv
```

## 결과 저장 규칙

해석 결과를 가져올 때는 현재 표준 구조에 맞춰 저장합니다.

```text
Training/Filling_Pressure/G43/P21/G43_P21_Filling_Pressure.csv
Training/Filling_Pressure/G43/P21/G43_P21_Filling_Pressure_chart.png
Training/Sprue_Pressure/G43/P21/G43_P21_Sprue_Pressure.csv
```

새 결과를 추가한 뒤 loader count가 `360 + 추가 case 수`로 증가하는지 확인하고 재학습합니다.
