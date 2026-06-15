# DD Laminate AI Pipeline — Research Context Document

## 1. 연구 배경

### 연구 주제
Double-Double (DD) composite laminate의 최적 적층 구조 및 각도 탐색.
항공/우주 구조물 표면에 사용되는 복합재의 좌굴(buckling) 강성을 극대화하는 것이 목표.

### 기존 방식의 한계
기존에는 Quasi-isotropic laminate [0/±45/90]s를 사용했으나, DD laminate가 더 우수한 좌굴 성능을 보이는 연구 결과가 있음. DD laminate는 [±φ/±ψ] 형태의 4-ply sublaminate를 반복하는 구조로, 두 개의 자유 각도(θ₁, θ₂)만으로 layup을 정의할 수 있어 설계 공간이 단순하면서도 유연함.

### 연구자 정보
대학원생(석사/박사 과정), Abaqus를 사용한 비선형 정적 해석(nonlinear static analysis) + imperfection seeding을 수행 중.


## 2. 현재까지 진행된 연구 내용

### 시뮬레이션 설정
- **패널 크기**: 6 in × 4 in 직사각형 평판
- **경계 조건**: 측면 simply supported, x=0,a에서 clamped, x=a에서 하중 인가
- **재료**: Toray T800/3900S, lamina 두께 0.0075 in
- **해석 방법**: Abaqus nonlinear static (imperfection seeding 포함), eigenvalue buckling은 non-symmetric layup에서 critical load를 과대평가하므로 사용하지 않음

### Case 정의 (DD 적층 구조 변형)
총 4개 Case가 있으며, 현재 3개 Case의 결과가 확보됨:

- **Case 1**: [[±θ₁]/[±θ₂]]₄
- **Case 2**: [[±θ₁]/[±θ₂]/[∓θ₂]/[∓θ₂]]₂ (PPT 슬라이드 제목 기준: [±θ₁/±θ₂]₄)
- **Case 3**: [([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]
- **Case 4**: 아직 PPT에 미포함 (추후 추가 예정)

### 데이터 규모
- 각 Case마다 θ₁, θ₂를 랜덤으로 선택하여 **200개 조합** 생성
- 3개 Case × 200개 = 총 **600개 Abaqus 시뮬레이션** 수행 완료
- 각 시뮬레이션의 출력: Force-Displacement CSV (약 500 data points per curve)

### 결과 분류 (수동)
600개 시뮬레이션 결과의 Force-Displacement 곡선을 직접 눈으로 확인하여 3개 Type으로 분류:

- **Type 1 (Imperfection perfect)**: Critical point(transition load, P_t) 전후로 양쪽이 모두 linear한 bilinear curve. Transition load를 명확히 식별 가능. → **연구 목표에 가장 이상적인 형태**
- **Type 2 (Imperfection imperfect-1)**: 대략적 bilinear이나, post-buckling 구간(critical point 이후)이 curve 형태를 띔.
- **Type 3 (Imperfection imperfect-2)**: Post-buckling 구간이 심하게 curved이고, 그래프 끝부분도 curve로 이어짐. Transition load 결정이 어려움.

### Case별 Type 분포

| Case | Type 1 | Type 2 | Type 3 | Type 1 비율 |
|------|--------|--------|--------|------------|
| Case 1 | 58 | 124 | 18 | 29% |
| Case 2 | 61 | 114 | 25 | 30.5% |
| Case 3 | 82 | 98 | 20 | 41% |

Case 3이 Type 1 비율이 가장 높아 가장 유리한 구조.

### Cost Function (최적화 목적함수)
```
f = 0.3 × (ω_DD / ω₀) + 0.7 × (P_trans_DD / P_cr⁰)
```
- ω: 고유진동수 (eigenvalue analysis에서 도출)
- P_trans: transition load
- ω₀, P_cr⁰: reference 값 ([0]₁₆ layup 기준)
- 가중치: 좌굴 하중 70%, 고유진동수 30%
- Quasi-isotropic 기준값: P_cr = 13595.78 lbs, ω = 6.5888 Hz

### 현재 워크플로우 (PPT 기반)
- Stage 0: Abaqus에서 sample.inp 생성 (B.C., material properties)
- Stage 1: Python pre-process (imperfection seeding, orientation 설정)
- Stage 2: .inp 파일 생성 및 Abaqus 실행
- Stage 3: .dat, .odb에서 P_cr, ω 추출
- Stage 4: **수동 QC** — xy plot을 보면서 P_cr 확인 및 Type 분류 ← 병목
- Stage 5: .csv 파일로 데이터 정리


## 3. 연구 목표 (AI 적용)

### 목표 1: Automatic Type Classification
Abaqus 시뮬레이션 완료 후 Force-Displacement 곡선의 Type(1/2/3)을 자동 분류.
현재 수동으로 하는 Stage 4의 자동화.

### 목표 2: 최적 DD 적층 조건 탐색
Type 1 그래프를 보이면서 동시에 P_t(transition load)가 가장 높은 (θ₁, θ₂, Case) 조합을 찾기.
= 더 좋은 DD laminate 설계를 AI로 탐색.


## 4. 제안된 AI Pipeline (5단계)

### Phase 1: Data Preparation
- 600개 F-D curve에서 feature extraction
  - Pre-buckling slope (초기 기울기)
  - Post-buckling slope (transition 이후 기울기)
  - Slope ratio (post/pre)
  - Post-buckling linearity (R² of linear fit)
  - Curvature statistics (mean, max, std)
  - 커브 끝부분 slope 변화율
  - Transition point 위치 (normalized displacement)
- Label mapping table: Test번호 ↔ θ₁, θ₂, Case, Type

### Phase 2: Auto Classification (목표 1)
- **추천 모델**: Random Forest 또는 XGBoost (tree 기반)
- 이유: 600개 데이터에 적합, deep learning보다 해석 가능성 높음
- SHAP analysis로 어떤 feature가 Type 결정에 기여하는지 해석
- 대안 (데이터 증가 시): 1D-CNN 또는 LSTM on raw curve

### Phase 3: Surrogate Model
- **Input**: (θ₁, θ₂, Case type)
- **Output**: P_t (transition load), ω (frequency), predicted Type
- **추천 모델**: ANN (PyTorch MLP) 또는 GPR (Gaussian Process Regression)
  - GPR은 uncertainty estimation이 가능 → active learning과 시너지
- P_t landscape가 θ 공간에서 smooth한 surface이므로 surrogate 적합도 높음

### Phase 4: Optimization (목표 2)
- Cost function: f = 0.3(ω/ω₀) + 0.7(P_trans/P_cr⁰) 최대화
- **추천 방법**: Genetic Algorithm (DEAP) 또는 Bayesian Optimization (BoTorch)
- Surrogate 기반이므로 수만 개 후보를 빠르게 평가 가능
- Type 1 constraint를 추가하여 bilinear 거동을 보이는 조합만 탐색

### Phase 5: Validation Loop
- Optimization에서 도출된 top-N 후보를 실제 Abaqus로 검증
- 검증 결과를 surrogate 학습 데이터에 추가 (active learning)
- 2~3 iteration으로 surrogate 정확도 향상


## 5. 관련 논문 (핵심 5편)

1. **"Buckling Performance Evaluation of DD Laminates with Cutouts Using ANN and GA"** (PMC, 2024)
   - 가장 직접 관련: DD laminate 좌굴을 ANN으로 예측 + GA로 최적화
   - DD는 두 개의 ply angle만으로 정의 → ANN 적용에 특히 효과적
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11477685/

2. **"Design of laminates by a novel Double-Double layup"** (Composite Structures, 2021)
   - DD layup 원리 소개, DD가 기존 quad 대비 ~6% 중량 절감 달성
   - URL: https://www.sciencedirect.com/science/article/pii/S0263823121003177

3. **"NN-Based Surrogate Modeling for Buckling Performance Optimization"** (PMC, 2024)
   - 비선형 좌굴 예측 NN surrogate + NSGA-II 다목적 최적화
   - URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC11351399/

4. **"Predicting buckling behaviour of thin-walled structural elements using ML"** (Comp. Struct., 2023)
   - ANN으로 좌굴 하중 + 좌굴 모드 분류를 동시 수행, 평균 R² 98%
   - Type 분류 문제와 가장 유사한 "shape classification" 접근
   - URL: https://www.sciencedirect.com/science/article/pii/S0263823122010709

5. **"ML regression for predicting buckling load of VS composite cylinders"** (Acta Mechanica, 2021)
   - 11,000 cases, fiber angle → buckling load 예측
   - RF, DT, MLR, Deep Learning 비교 → DL이 가장 안정적
   - URL: https://link.springer.com/article/10.1007/s00707-020-02878-2


## 6. 제안 Tech Stack

| 구분 | 도구 |
|------|------|
| 데이터 처리 | Python + NumPy, Pandas |
| Feature extraction | SciPy (curve fitting, 미분), scikit-learn |
| Classification | XGBoost + SHAP |
| Surrogate model | PyTorch MLP 또는 GPyTorch (GPR) |
| Optimization | DEAP (GA) 또는 BoTorch (Bayesian Opt.) |
| Visualization | Matplotlib, Plotly |
| Abaqus 연동 | Python scripting (.inp 자동 생성) |


## 7. 다음 단계 (필요한 것)

코드 구현을 시작하려면 아래 데이터가 필요:
1. **전체 600개 시뮬레이션의 매핑 테이블**: Test번호 ↔ θ₁, θ₂, Case, Type (CSV or Excel)
2. **전체 600개의 Force-Displacement CSV 파일들**
3. **Transition point 결정 방법**: bilinear fitting 방식인지, 수동인지 (PPT의 cost function 슬라이드에 initial fit + post fit 교차점 방식이 보임)
4. **Case 4 데이터**: 추후 추가 예정

이 데이터가 확보되면 Phase 1~2 (feature extraction + classifier)의 prototype을 1~2주 내에 구현 가능.
