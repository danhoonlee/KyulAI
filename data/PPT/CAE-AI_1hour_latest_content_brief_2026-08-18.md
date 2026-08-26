# CAE–AI 1시간 발표 최신 콘텐츠 브리프

기준일: 2026-08-18
중점 분야: Injection + Double-Double Laminate
용도: 다른 AI에게 전달하여 최신 1시간 발표용 PPT를 제작하기 위한 원본 콘텐츠

---

## 1. 이 문서의 사용 방법

이 문서는 기존 45장 발표자료의 흐름을 유지하면서 2026년 8월 중순까지의 모델, 검증,
웹 서비스 업데이트를 반영하기 위한 기준 문서다.

PPT 제작 AI에는 다음 파일을 함께 제공하는 것을 권장한다.

1. 이전 콘텐츠 기준본
   - `data/PPT/Samples/CAE-AI_Injection_Laminate_1hour_XAI_detailed.pptx`
2. ImperialAX 스타일로 정리된 45장 참고본
   - `data/PPT/Samples/CAE-AI_Injection_Laminate_ImperialAX_Standard.pptx`
3. 회사 PPT 템플릿
   - `data/PPT/ImperialAX_Company_Presentation_Template.pptx`
4. 흑백/모노톤 참고자료
   - `data/PPT/Samples/260810_Black_White_sbppt.pptx`
5. 공식 로고
   - `data/Logo/Original/PNG_new/1x/`

기존 자료를 단순 증보하기보다는, 오래된 성능 수치를 최신 검증 결과로 교체하고
운영 모델과 연구 후보를 분리해서 표현해야 한다.

---

## 2. 발표의 핵심 메시지

### 한 문장 메시지

> CAE–AI는 시뮬레이션을 대체하는 기술이 아니라, 넓은 설계공간에서 가치 있는 후보를
> 먼저 선별하고 CAE·시험 검증을 어디에 집중할지 결정하는 기술이다.

### 청중이 발표 후 이해해야 할 내용

1. CAE surrogate는 정의된 설계공간 안에서 반복 계산과 후보 비교를 가속한다.
2. Injection과 Laminate는 물리는 다르지만 `DOE → CAE → 학습 → 선별 → 재검증`이라는
   운영 구조가 같다.
3. 분류, 스칼라, 곡선 등 여러 출력을 동시에 사용할 때는 출력 간 일관성이 중요하다.
4. XAI는 인과관계의 증명이 아니라 현재 모델과 현재 입력에서의 국소 민감도다.
5. 불확실성, OOD, 잠금 검증, 새 CAE 캠페인이 모델 점수만큼 중요하다.
6. 최종 설계 승인에는 Moldex3D, Abaqus와 실험 검증이 계속 필요하다.

### 권장 청중 가정

- CAE를 사용하거나 관심이 있는 연구자, 설계자, 대학원생, 기술 리더
- AI 전문가는 아니지만 DOE, 해석 조건, 검증의 의미는 이해하는 청중
- 수식 중심보다 실제 워크플로와 데모 중심의 설명을 선호하는 청중

---

## 3. 권장 60분 구성

| 구간 | 시간 | 권장 장수 | 목적 |
| --- | ---: | ---: | --- |
| 도입과 공통 CAE–AI 원칙 | 7분 | 5–6장 | 왜 필요한지와 검증 원칙 설정 |
| Injection | 18분 | 11–13장 | 데이터, 모델 비교, 최신 운영 화면 데모 |
| Laminate | 25분 | 15–17장 | 3-size Pt 일관성, UQ, 최신 운영 화면 데모 |
| 공통 운영 구조와 다음 단계 | 5분 | 3–4장 | 두 분야의 공통점과 적용 방식 정리 |
| Q&A | 5분 | 1장 | 질문과 토론 |

권장 본편은 약 38–42장이다. 세부 성능표, UQ subgroup 표, XAI feature 목록은
백업 슬라이드로 분리한다. 라이브 데모가 불안정할 때 사용할 캡처 슬라이드를 각 파트에
2장씩 둔다.

### 발표에서 사용할 웹 서비스 구조

- 통합 진입점: `https://ai.imperialax.com`
- Laminate 운영 화면: `https://laminate.imperialax.com`
- Injection 운영 화면: `https://injection.imperialax.com`

발표와 캡처는 `/v2` 경로가 아니라 위의 루트 주소에 배포된 최신 수정본을 사용한다.
`ai.imperialax.com`에서 로그인한 뒤 각 예측 모듈로 이동하는 하나의 Forecast Workspace로
설명한다. 발표 자료에서는 두 모듈을 모두 `현재 v1 운영본`으로 표기한다.

---

## 4. 권장 전체 스토리라인

### Part A. 공통 CAE–AI 개요

#### Slide 1. CAE–AI 연계: Injection & Laminate

- 부제: 시뮬레이션을 대체하는 AI가 아니라 탐색·판단·검증의 속도를 높이는 AI
- 시각자료: ImperialAX 로고 + Injection pressure curve + Laminate force-displacement curve
- 제목 슬라이드는 짧게 유지한다.

#### Slide 2. 전수 CAE가 어려운 이유는 설계공간이 너무 빨리 커지기 때문이다

- 형상, 공정, 재료, 적층 각도, Case, 패널 크기가 조합되면 후보 수가 급증한다.
- CAE–AI의 가치: 수천 후보 선별 → 수십 후보 CAE → 소수 후보 시험

#### Slide 3. Surrogate는 정의된 범위 안의 CAE 응답을 근사한다

- 입력: 형상·공정·재료·적층·경계조건
- 출력: 압력, Type, Pt, 최대 하중, 전체 곡선
- 범위 밖에서 물리 법칙을 대신하는 모델이 아님을 분명히 한다.

#### Slide 4. 좋은 모델보다 먼저 좋은 검증 프로토콜이 필요하다

- Case/각도/형상 그룹 분할
- 재사용 benchmark와 완전 미사용 외부 검증의 차이
- 모델 선택 중 최종 검증 데이터를 반복해서 보면 안 됨

#### Slide 5. 신뢰 가능한 운영 루프

- DOE → CAE → 학습 → 후보 선별 → CAE/시험 재검증
- AI output ≠ engineering approval

---

## 5. Injection 파트 최신 내용

### 5.1 문제 정의

Injection 모델은 Moldex3D DOE에서 다음 질문을 빠르게 선별하기 위한 surrogate다.

- 이 형상과 공정조건에서 Sprue Pressure의 시간 이력은 어떻게 변하는가?
- 최대 Sprue Pressure와 최대 시간은 어느 수준인가?
- Filling Pressure 분포가 낮은 압력 구간과 높은 압력 구간에 어떻게 나뉘는가?
- 어떤 형상·공정 feature에 현재 예측이 민감한가?

목표는 금형·장비의 최종 승인값을 직접 선언하는 것이 아니라, 상세 Moldex3D 재해석이
필요한 후보를 좁히는 것이다.

### 5.2 최신 데이터 계약

| 항목 | 현재 기준 |
| --- | --- |
| 표준 결과 수 | 360 Moldex3D cases |
| 형상 DOE | G01–G42, 총 42개 형상 그룹 |
| 공정 DOE | P01–P20, 총 20개 공정 조건 |
| 내부 입력 차원 | 23 features |
| 직접 입력 | L, W, t, D, R, gate width/height/type, melt/mold temperature, injection time, packing pressure/time |
| 파생 입력 | area, net area, volume, aspect ratio, hole ratio, gate area, flow-length/thickness 등 10개 descriptor |
| Sprue 출력 | 최대 시간, 최대 압력, 128-point pressure-time curve |
| Filling 출력 | min/max/avg/sd + 10개 pressure-volume histogram bins |

주의: Filling 출력은 압력 히스토그램 요약이다. 메시 좌표와 field mapping을 포함한 실제
공간 contour가 아니다.

### 5.3 운영 모델 구성

Sprue와 Filling은 각각 별도 모델을 선택한다. 따라서 준비 상태에 표시되는 모델 artifact는
총 6개다.

| 출력 | Classical | Neural baseline | Operator-learning |
| --- | --- | --- | --- |
| Sprue | ExtraTrees + PCA | GointMLP NN | DeepONet NN |
| Filling | ExtraTrees histogram | GointMLP NN | DeepONet NN |

발표에서는 “6개의 서로 경쟁하는 단일 모델”이라고 표현하지 않는다. 정확한 표현은
“Sprue 3종 + Filling 3종, 총 6개 예측 artifact”다.

### 5.4 최신 Injection 성능표

#### Sprue Pressure — 360 cases, grouped 3-fold validation

| Model | Max pressure MAE | Pressure curve RMSE | Max time MAE | Mean shape correlation |
| --- | ---: | ---: | ---: | ---: |
| ExtraTrees + PCA | **0.065 MPa** | **2.555 MPa** | **0.098 s** | **0.9965** |
| GointMLP | 0.714 MPa | 2.917 MPa | 0.154 s | 0.9941 |
| DeepONet | 0.901 MPa | 5.421 MPa | 0.154 s | 0.9786 |

해석:

- 현재 360-case DOE에서는 Classical ExtraTrees가 가장 안정적인 기본 모델이다.
- GointMLP는 신경망 계열 중 곡선 형태 보존이 가장 좋다.
- DeepONet은 operator-learning 연구 모델이며, 현재 데이터 규모에서는 Classical보다 약하다.
- 복잡한 모델이 항상 더 정확하지 않다는 사례로 활용하기 좋다.

#### Filling Pressure — 360 cases, grouped 3-fold validation

| Model | Stats MAE | 10-bin volume-ratio MAE | 10-bin volume-ratio RMSE |
| --- | ---: | ---: | ---: |
| ExtraTrees histogram | **0.757 MPa** | 1.259 percentage points | **2.071 pp** |
| GointMLP | 1.112 MPa | **1.173 pp** | 2.147 pp |
| DeepONet | 0.807 MPa | 1.182 pp | 2.071 pp |

해석:

- Filling 통계량은 ExtraTrees가 가장 정확하다.
- 10-bin 비율 MAE는 GointMLP와 DeepONet이 근소하게 좋다.
- 압력 통계와 histogram shape를 함께 보고 모델을 선택해야 한다.

### 5.5 Injection XAI

- 현재 설명 대상 feature는 총 23개다.
- 직접 형상·Gate·공정 입력 13개와 파생 descriptor 10개를 포함한다.
- 방식은 현재 입력 주위의 local perturbation sensitivity다.
- feature 영향값을 최고 feature 대비 100%로 재정규화하지 않는다.
- 100%처럼 보이는 상대 막대만 제시하지 말고 실제 국소 민감도 값과 설명을 함께 보여준다.
- 중요도가 높다는 것은 모델이 많이 의존했다는 뜻이지 물리적 인과관계를 증명한 것이 아니다.

### 5.6 Injection 최신 운영 화면 시연

공개 경로: `https://injection.imperialax.com`

진입 경로: `https://ai.imperialax.com` → Injection 모듈

현재 주요 기능:

- 한국어/English 전환
- Sprue 모델과 Filling 모델을 별도로 선택
- Process DOE와 Geometry DOE 선택
- DOE 기반 3D Shape Preview
- Process details와 Geometry details 상시 표시
- 학습 DOE에 포함된 고정 Gate 조건 명시
- 최대 Sprue Pressure, max time, curve points, Filling max 요약
- 128-point Sprue curve와 10-bin Filling distribution
- local XAI와 계산 방식 펼쳐보기
- Moldex3D CSV 형식 안내와 샘플 파일
- 실행 결과 비교 목록
- 예측 기록 저장 및 이전 조건 재사용

권장 데모 입력:

- Process P01
- Geometry G01
- Sprue: Machine Learning / ExtraTrees
- Filling: Machine Learning / ExtraTrees

확인된 데모 기준값:

- Max Sprue Pressure: 69.00 MPa
- Max time: 22.053 s
- Sprue curve: 128 points
- Filling maximum: 35.98 MPa
- Filling histogram: 10 bins

권장 데모 순서:

1. `ai.imperialax.com`에서 Injection 모듈로 이동
2. Sprue/Filling 모델과 P01/G01 DOE 선택
3. 공정 세부값과 형상 세부값이 항상 표시되는지 확인
4. Shape Preview를 회전·확대해 DOE 형상 확인
5. 예측 실행 후 핵심 압력값과 128-point curve 확인
6. Filling distribution이 spatial contour가 아닌 10-bin 요약임을 설명
7. XAI feature와 계산 방식 펼쳐보기
8. Moldex3D CSV Validation과 예측 기록 확인

위 값은 G01/P01 운영 smoke prediction의 예시다. 일반 성능지표처럼 표현하지 말고
“데모 입력에서 나온 예측값”으로 표시한다.

### 5.7 Injection 한계와 다음 단계

- 현재 표준 DOE와 고정 Gate 조건 안에서 사용하는 screening 모델이다.
- 새로운 수지, 새로운 Gate family, 학습 범위를 벗어난 형상에 대한 extrapolation은 금지한다.
- Filling histogram을 실제 공간 contour로 해석하면 안 된다.
- true field surrogate를 위해서는 mesh coordinates, connectivity와 field export가 필요하다.
- 다음 단계는 재료 다양성, 새 형상 그룹 잠금 검증, active learning 후보 큐다.

---

## 6. Laminate 파트 최신 내용

### 6.1 문제 정의

Double-Double Laminate의 Case, 각도, 패널 크기에서 다음 항목을 예측한다.

- Response Type 1/2/3
- 전이 하중 Pt
- 최대 하중 Max. Force
- 128-point force-displacement curve

핵심 목표는 넓은 `Case × θ1 × θ2 × panel size` 공간을 빠르게 선별하고, 전이 경계와
불확실 후보를 Abaqus 재해석 대상으로 올리는 것이다.

### 6.2 최신 3-size 데이터와 검증 분할

| 항목 | 현재 기준 |
| --- | --- |
| 전체 데이터 | 2,700 rows |
| 패널 크기 | 6×4, 6×8, 8×8 |
| Case | Case 2, Case 3, Case 4 |
| 개발 데이터 | 2,154 rows / 718 Case+theta groups |
| 재사용 fixed benchmark | 546 rows / 182 groups |
| 그룹 키 | Case + theta1 + theta2 |
| 개발/benchmark group overlap | 0 |
| 입력 feature | 40 physics/geometry features |
| 곡선 길이 | 128 points |

라벨 provenance:

- 6×4: human-reviewed curated labels
- 6×8: curve-classifier labels
- 8×8: curve-classifier pseudo-labels

이 provenance는 숨기지 않는다. 6×8/8×8 Type accuracy는 사람이 전수 검토한 외부 시험
라벨에 대한 정확도로 과장하면 안 된다.

### 6.3 Pt-consistency가 중요한 이유

Type, 직접 예측 Pt, 곡선, P1 fitting 결과를 각각 독립적으로 만들면 화면에 표시되는 Pt와
곡선상 두 선의 교점이 서로 어긋날 수 있다.

Pt-Consistent 모델은 다음 제품 계약을 보장한다.

- 표시되는 Predicted Pt와 곡선의 P1 교점이 일치한다.
- Type, Pt, curve의 해석이 화면에서 모순되지 않는다.
- 작은 수치 성능 차이보다 사용자에게 오해를 주지 않는 일관성을 우선한다.

### 6.4 최신 표준화 성능 비교

아래 표는 같은 fixed benchmark와 같은 mean per-row 128-point curve RMSE 정의를 사용한
최신 연구 비교다.

| Model | 상태 | Type accuracy | Pt MAE | Max. Force MAE | Mean row Curve RMSE |
| --- | --- | ---: | ---: | ---: | ---: |
| Pt-Consistent Tree | 현재 leader | **0.9359** | **191.79 kips** | **155.28 kips** | **116.77 kips** |
| GointMLP v2 fold-pretrained | 연구 challenger | 0.9194 | 766.17 kips | 1,077.71 kips | 852.75 kips |
| Hybrid v2 fold-pretrained | 주요 neural challenger | 0.9322 | 411.74 kips | 660.35 kips | 492.31 kips |

해석:

- Tree가 Type, Pt, Max. Force, curve 모두에서 현재 leader다.
- fold-local pretraining은 GointMLP와 Hybrid를 개선했지만 Tree를 넘지 못했다.
- Hybrid v2는 현재 가장 강한 neural reference다.
- neural challenger는 운영 모델을 대체하지 않았다고 명시한다.

### 6.5 곡선 RMSE 수치 사용 주의

이전 45장 자료에는 Tree curve RMSE `291.50 kips`가 사용되었다. 이 값은 과거 catalog의
집계 정의다. 최신 연구 비교는 모든 모델에 동일한 `mean per-row 128-point curve RMSE`
정의를 사용하며 Tree 값은 `116.77 kips`다.

PPT에서는 두 정의를 같은 표에 혼합하지 않는다. 최신 비교 슬라이드에는 위 표의
`116.77 kips`를 사용하고, 반드시 metric 정의를 각주로 적는다.

### 6.6 최신 불확실성 정량화: Tree UQ v3

생산 Tree point predictor는 고정하고, panel geometry + Case로 조건화된 conformal interval
sidecar를 연구했다.

| Target | Nominal coverage | Fixed-benchmark empirical coverage | Mean width |
| --- | ---: | ---: | ---: |
| Pt | 80% | 86.08% | 469.80 kips |
| Pt | 90% | 93.96% | 686.43 kips |
| Pt | 95% | 96.34% | 968.03 kips |
| Max. Force | 80% | 88.64% | 554.91 kips |
| Max. Force | 90% | 96.70% | 887.67 kips |
| Max. Force | 95% | 98.72% | 1,269.94 kips |

중요한 해석:

- interval 선택은 개발 OOF evidence만 사용한 뒤 fixed benchmark를 열었다.
- geometry-only보다 geometry + Case 조건화가 subgroup coverage gap을 줄였다.
- 이 sidecar는 아직 API/UI에 배포되지 않았다.
- 현재 UI의 Reliability나 screening range를 통계적 90% 신뢰구간으로 부르면 안 된다.
- 546-row benchmark는 여러 실험에서 재사용되었으므로 pristine external holdout이 아니다.

### 6.7 Deep Learning 연구에서 얻은 교훈

- fold-local response pretraining으로 GointMLP v2의 Pt error는 v1 대비 12.5%, Max. Force는
  20.8%, curve error는 20.0% 개선됐다.
- Hybrid v2의 Pt error는 v1 대비 17.6%, curve error는 8.9% 개선됐다.
- Hybrid v3b의 별도 Max. Force head는 fixed benchmark Max. Force MAE를 660.35에서
  624.17 kips로 5.48% 개선했다.
- 하지만 interval coverage와 폭의 trade-off 때문에 v3b/v3c는 연구 challenger로 남아 있다.
- 결론은 “Deep Learning이 실패했다”가 아니라 “현재 데이터와 검증 기준에서는 Tree가
  더 강하고, neural 모델은 구조·pretraining·uncertainty 측면의 연구 가치가 있다”이다.

### 6.8 완전 미사용 검증 캠페인 UV3S1

재사용 fixed benchmark의 한계를 해결하기 위해 기존 2,700-row 데이터와 각도쌍이 겹치지
않는 새 시뮬레이션 캠페인을 고정했다.

- 새 integer angle pairs: 60개
  - uniform-grid 30개
  - maximin-gap stress pairs 30개
- 3 panel geometries × 3 Cases에 반복
- 총 540 Abaqus simulations
- Pilot 180 + Confirmatory 360
- 기존 source theta-pair overlap: 0
- 사전 지정 약점 subgroup: 6×8 | Case 2

Pilot 결과를 본 뒤 모델, calibration, interval grouping이나 threshold를 바꾸지 않는다.
이 캠페인은 발표에서 “다음 단계”가 아니라 이미 설계와 freeze가 끝난 external-validation
프로토콜로 소개할 수 있다. 단, 결과가 아직 들어오지 않았다면 성능 결과가 있는 것처럼
표현하지 않는다.

### 6.9 Laminate 최신 운영 화면 시연

공개 경로: `https://laminate.imperialax.com`

진입 경로: `https://ai.imperialax.com` → Laminate 모듈

현재 응답 예측에서 선택 가능한 3-size Pt-consistent 모델:

1. Machine Learning · Tree
2. Deep Learning · GointMLP
3. Hybrid · Teacher–Student

발표의 기본 시연 모델은 마지막으로 채택한 `Machine Learning · Tree`로 통일한다.
내부 model key의 `v1`/`v2` 표기와 공개 웹페이지 URL 버전을 혼동하지 않는다.

현재 주요 기능:

- 한국어/English 전환과 `ai.imperialax.com` 모듈 선택 링크
- 응답 예측 / u3 예측 / Stack Lab / 곡선 CSV 작업 모드
- θ1, θ2, Case 2/3/4, panel size 입력
- Case와 각도에 따라 갱신되는 16-ply preview
- Type, confidence, Pt, Max. Force와 전체 response curve
- Pt와 Max. Force 소수점 둘째 자리 표시
- 예측 Pt에 맞는 두 개의 P1 fitting line
- curve zoom/pan, mobile pinch interaction
- 실제 선택 모델을 직접 설명하는 local XAI
- 40개 physics/geometry feature 중 상위 5개 + 추가 feature disclosure
- XAI 영향도를 max=100%로 정규화하지 않은 실제 local sensitivity 표시
- 설계공간 지도, Case 위험도, 가까운 해석 데이터와 추천 후보
- 설계공간 점의 desktop hover와 touch selection tooltip
- 예측 기록과 이전 조건 재사용

권장 데모 입력:

- Model: Machine Learning · Tree
- Case 2
- θ1 = +30°, θ2 = −30°
- Panel = 6×4 in

권장 데모 순서:

1. `ai.imperialax.com`에서 Laminate 모듈로 이동
2. 응답 예측에서 각도를 움직이며 16-ply preview 변화 확인
3. Tree 모델로 예측 실행
4. Type, confidence, Pt와 Max. Force 확인
5. 곡선을 확대해 두 P1 line과 Predicted Pt 일치 확인
6. XAI 상위 5개와 추가 feature 펼치기
7. 설계공간 지도에서 점 hover, Case 위험도와 가까운 해석 데이터 확인
8. 예측 기록에서 이전 조건을 다시 불러오기
9. 마지막에 u3 예측·Stack Lab·곡선 CSV 모드가 분리돼 있음을 짧게 소개

### 6.10 Laminate 한계와 다음 단계

- 546-row benchmark는 내부 regression comparison에는 유효하지만 pristine external validation은 아니다.
- UQ v3 sidecar와 neural v2/v3 challengers는 아직 product UI에 배포되지 않았다.
- 6×8/8×8 Type labels의 provenance를 명확히 해야 한다.
- 새로운 Case 5나 arbitrary stacking sequence는 별도의 sequence model과 독립 데이터가 필요하다.
- UV3S1 540 simulations가 완료된 뒤에만 publication-grade external-validation 결과를 말한다.

---

## 7. Injection과 Laminate를 연결하는 통합 메시지

| 구분 | Injection | Laminate | 공통 운영 원칙 |
| --- | --- | --- | --- |
| CAE | Moldex3D | Abaqus | solver provenance 유지 |
| 설계변수 | 형상·공정·Gate | Case·θ1·θ2·panel size | 명시적 data contract |
| 주요 출력 | Sprue curve, Filling histogram | Type, Pt, Max. Force, F–u curve | multi-output consistency |
| 현재 기본 모델 | ExtraTrees | Pt-Consistent Tree | 복잡도보다 검증 성능 |
| XAI | 23-feature local perturbation | 40-feature local masking/sensitivity | 인과가 아닌 screening 근거 |
| 큰 위험 | 새 재료, histogram/contour 혼동 | 전이 경계, label provenance, reused benchmark | OOD와 재검증 |
| 최종 검증 | Moldex3D + 시험 | Abaqus + 시험 | AI output ≠ approval |

권장 마무리 문장:

> 두 사례 모두 AI가 정답을 대신 내리는 것이 아니라, 다음 CAE를 더 가치 있는 위치에
> 배치하게 한다.

---

## 8. 권장 40장 본편 구성

아래는 다른 AI가 바로 슬라이드로 변환할 수 있는 권장 목차다.

1. CAE–AI 연계: Injection & Laminate
2. 설계공간이 커질수록 전수 CAE는 급격히 무거워진다
3. 오늘 답할 세 가지 질문
4. Surrogate는 무엇을 학습하는가
5. DOE와 그룹 검증이 모델보다 먼저다
6. AI는 다음 계산을 추천하는 조수다
7. Injection × AI
8. Injection 문제를 AI 문제로 번역하기
9. 360-case Injection data contract
10. Sprue 3종 + Filling 3종 모델 구조
11. Sprue 모델 성능: Classical이 현재 기준선
12. Filling 모델 성능과 histogram 해석
13. Sprue curve는 스칼라가 아니라 함수 출력이다
14. Filling histogram은 공간 contour가 아니다
15. Injection 운영 화면 workflow
16. Injection live demo
17. Injection capture: 핵심 결과 + Sprue curve
18. Injection capture: Filling + XAI + Validation
19. Injection XAI 23 features와 올바른 해석
20. Injection 적용 범위와 다음 단계
21. Laminate × AI
22. Double-Double laminate와 Case 정의
23. 핵심 출력: Type + Pt + Max. Force + 128-point curve
24. 2,700-row 3-size dataset과 label provenance
25. 2,154 development / 546 fixed benchmark grouped protocol
26. Pt-consistency: 화면에서 출력이 모순되지 않게
27. 최신 표준화 비교: Tree vs neural challengers
28. Tree가 leader인 이유
29. 불확실성은 reliability badge와 다르다
30. Tree UQ v3 geometry + Case coverage
31. Deep Learning pretraining과 Hybrid 연구에서 얻은 교훈
32. UV3S1: 겹치지 않는 540개 새 시뮬레이션
33. Laminate 운영 화면 workflow
34. Laminate live demo
35. Laminate capture: 핵심 결과 + Curve + P1/Pt
36. Laminate capture: 16-ply preview + XAI
37. Laminate capture: 설계공간 + 예측 기록
38. Injection과 Laminate의 공통 운영 구조
39. 도입 로드맵: screening → calibrated uncertainty → active learning
40. Three takeaways + Q&A

### 권장 백업 슬라이드

1. Injection Sprue 전체 세부 metric 표
2. Injection Filling 전체 세부 metric 표
3. Laminate UQ v3 80/90/95% coverage와 subgroup 표
4. Neural v1/v2/v3b/v3c 비교
5. 23개 Injection feature 목록
6. 40개 Laminate feature category 목록
7. UV3S1 manifest 구조
8. `ai.imperialax.com` 허브와 두 운영 모듈의 연결 구조

---

## 9. 스크린샷 촬영 계획

스크린샷은 화면 전체를 반복해서 넣기보다, 한 슬라이드의 주장에 맞춰 핵심 영역을
crop해서 사용한다. 모든 캡처는 같은 16:9 데스크톱 viewport와 같은 브라우저 zoom으로
촬영한다.

### Injection 권장 캡처 5장

1. `I-01-setup-shape-preview.png`
   - 운영 화면의 Process/Geometry DOE와 Shape Preview
   - 주장: DOE 입력이 즉시 형상 미리보기와 연결된다.
2. `I-02-core-results.png`
   - G01/P01 실행 후 핵심 metric
   - 주장: pressure screening 결과를 한눈에 확인한다.
3. `I-03-sprue-curve.png`
   - 128-point Sprue Pressure curve
   - 주장: 최대값만 아니라 시간 이력을 예측한다.
4. `I-04-filling-xai.png`
   - Filling distribution과 XAI 상위 feature
   - 주장: histogram과 예측 driver를 함께 검토한다.
5. `I-05-validation.png`
   - Moldex3D CSV Validation 안내/샘플
   - 주장: surrogate 결과는 CAE와 비교해 루프를 닫는다.

### Laminate 권장 캡처 6장

1. `L-01-setup-stack-preview.png`
   - θ, Case, panel size와 16-ply preview
2. `L-02-core-results.png`
   - Type, probability, Pt, Max. Force, displacement
3. `L-03-curve-p1.png`
   - 확대된 curve와 두 P1 line, Predicted Pt
4. `L-04-ply-sequence.png`
   - Case별 ply sequence
5. `L-05-xai-expanded.png`
   - 상위 5개 + 추가 feature disclosure
6. `L-06-design-space-tooltip.png`
   - 설계공간 지도, 현재 입력 또는 해석점 tooltip, 가까운 해석 데이터

### 캡처 원칙

- 예시 결과와 실제 모델 실행 결과를 혼동하지 않게 표시한다.
- 주소창과 개인 계정 정보는 crop한다.
- 툴팁이 필요한 Design Space는 cursor가 점을 가리지 않게 둔다.
- 그래프 축, 단위, Pt label이 모두 보이도록 한다.
- 화면의 Reliability나 screening band를 통계 신뢰구간으로 자막 처리하지 않는다.

---

## 10. 시연 영상 계획

PPT에 직접 삽입할 영상은 긴 화면 녹화보다 60–90초짜리 무음 또는 짧은 자막 영상 두 개가
안정적이다. 발표자가 영상 위에서 설명하고, 필요하면 별도의 라이브 시연을 추가한다.

### Video A — Injection 최신 운영 화면, 약 75초

1. 0–7초: `ai.imperialax.com`에서 Injection 모듈 진입
2. 7–17초: G01/P01, Sprue/Filling Classical 선택
3. 17–27초: 공정·형상 세부값과 Shape Preview 확인
4. 27–42초: 예측 실행 및 핵심 결과 확인
5. 42–55초: Sprue curve와 Filling distribution 확인
6. 55–67초: XAI와 계산 방식 펼치기
7. 67–75초: Validation CSV와 예측 기록으로 이동

권장 자막:

- “360-case DOE 기반 screening”
- “128-point Sprue Pressure curve”
- “Filling histogram, not a spatial contour”
- “XAI = local sensitivity, not causality”

### Video B — Laminate 최신 운영 화면, 약 90초

1. 0–7초: `ai.imperialax.com`에서 Laminate 모듈 진입
2. 7–20초: Case 2, +30°/−30°, 6×4 설정
3. 20–30초: 각도 변경과 16-ply preview 변화
4. 30–45초: Tree 예측 실행과 핵심 결과
5. 45–60초: Curve zoom, P1 line/Pt 일치 확인
6. 60–72초: XAI 추가 feature 펼치기
7. 72–84초: 설계공간 point tooltip과 가까운 해석 데이터
8. 84–90초: 예측 기록과 다른 작업 모드 소개

권장 자막:

- “3-size Pt-consistent Tree”
- “Type + Pt + Max. Force + 128-point curve”
- “Prediction Pt matches the displayed P1 intersection”
- “Design Space supports hover and touch inspection”

### 영상 제작 규격

- 1920×1080, 16:9
- 30 fps
- 브라우저 zoom 100%
- cursor highlight는 작고 중립적으로 사용
- 빠른 scroll보다 섹션 사이 0.3–0.5초 pause 사용
- 개인정보, 계정 이메일, 관리자 UI는 녹화하지 않음
- PPT 삽입용 MP4(H.264)와 백업용 GIF 또는 정지 캡처를 함께 준비

---

## 11. 이전 45장 자료에서 반드시 업데이트할 항목

### 그대로 활용 가능한 내용

- CAE–AI가 solver를 대체하지 않는다는 핵심 메시지
- DOE → CAE → 학습 → 선별 → 재검증 루프
- 그룹 분할과 OOD의 기본 설명
- Filling histogram과 spatial contour의 구분
- Pt-consistency의 개념
- XAI는 인과가 아니라는 설명
- Injection/Laminate 공통 운영 구조

### 교체가 필요한 내용

1. Injection slide 20의 historical 300-record 수치
   - 현재 360-case grouped validation 표로 교체
2. Injection 데모 URL과 UI
   - `ai.imperialax.com`에서 진입하는 `injection.imperialax.com` 최신 운영 화면으로 교체
3. Laminate 모델 비교표의 curve RMSE
   - 최신 공통 정의의 116.77 / 852.75 / 492.31 사용
4. Laminate 모델 상태
   - Tree leader, neural v2/v3 research challenger 구분
5. Laminate 검증 설명
   - 546-row는 reused fixed benchmark로 표현
6. 새 UQ 내용
   - Tree UQ v3 coverage 추가, 단 미배포 표시
7. 새 external-validation 계획
   - UV3S1 540 simulations 추가
8. Laminate UI
   - `laminate.imperialax.com`의 응답 예측/적층 미리보기/곡선/XAI/설계공간/예측 기록 흐름으로 교체
9. Injection UI
   - 공정·형상 세부값 상시 표시, Shape Preview, XAI, Validation, 예측 기록, 한/영 UI 반영

### 삭제 또는 백업으로 이동할 내용

- 같은 개념을 반복하는 일반 AI 설명
- 현재 모델과 직접 연결되지 않는 과거 theta-only/curve-classifier 세부 이력
- 정의가 다른 metric을 한 표에서 비교하는 슬라이드
- 실제 field contour처럼 보일 수 있는 Filling surrogate animation 설명

---

## 12. 다른 AI에 전달할 제작 요청 문안

아래 문안을 이 브리프와 기존 PPT 파일과 함께 전달할 수 있다.

> ImperialAX의 최신 CAE–AI 1시간 발표자료를 제작해 주세요. 청중은 CAE와 복합재/사출
> 분야의 연구자·설계자이며, AI 비전문가도 이해할 수 있어야 합니다. 핵심 메시지는
> “AI가 CAE를 대체하는 것이 아니라 설계공간 선별과 재검증 우선순위를 가속한다”입니다.
> Injection과 Double-Double Laminate를 중심으로 38–42장 본편과 백업 슬라이드를 구성해
> 주세요. 제공한 최신 콘텐츠 브리프의 수치, 상태, 제한사항을 source of truth로 사용하고,
> 운영 모델과 연구 challenger, heuristic reliability와 calibrated interval, reused benchmark와
> untouched validation을 명확히 구분해 주세요. 기존 45장 자료의 장점은 재사용하되 오래된
> Injection 300-case 지표와 Laminate curve RMSE 정의는 최신 표로 교체해 주세요. 회사
> 템플릿과 ImperialAX 로고를 사용하고, 전체를 과도한 카드형 UI가 아닌 발표용 시각 구조로
> 정리해 주세요. 각 주요 주장과 외부 자산은 speaker notes에 출처를 남겨 주세요. 웹 화면은
> 제공된 screenshot plan을 기준으로 사용하고, 라이브 데모가 실패해도 발표 가능한 backup
> capture 슬라이드를 포함해 주세요.

---

## 13. 주요 근거 파일

### Injection

- 모델 registry/API: `src/backend/api/v1/simple_injection.py`
- Classical Sprue report:
  `models/simple_injection_sprue_pressure_v1/sprue_pressure_surrogate_report.md`
- Goint Sprue report:
  `models/simple_injection_sprue_goint_v1/sprue_pressure_goint_report.md`
- DeepONet Sprue report:
  `models/simple_injection_sprue_deeponet_v1/sprue_pressure_deeponet_report.md`
- Classical Filling report:
  `models/simple_injection_filling_pressure_v1/filling_pressure_surrogate_report.md`
- Goint Filling report:
  `models/simple_injection_filling_pressure_goint_v1/filling_pressure_goint_report.md`
- DeepONet Filling report:
  `models/simple_injection_filling_pressure_deeponet_v1/filling_pressure_deeponet_report.md`
- 최신 운영 UI: `src/frontend/simple-injection/`
- UI contract tests: `tests/backend/test_simple_injection_model_labels.py`

### Laminate

- Frozen 3-size baseline:
  `research/dd_aicomp2026/baselines/dd_3size_pt_consistent_v1.json`
- Latest standardized neural comparison:
  `reports/dd_aicomp2026_v1/20260811-uq-deep-fold-pretrain-v2/model_comparison.md`
- Tree UQ v3 report:
  `reports/dd_aicomp2026_v1/20260811-uq-geometry-case-tree-v3/report.md`
- Hybrid v3b evidence:
  `reports/dd_aicomp2026_v1/20260811-uq-deep-force-head-v3b/`
- Hybrid v3c evidence:
  `reports/dd_aicomp2026_v1/20260811-uq-deep-force-robust-v3c/`
- UV3S1 campaign:
  `research/dd_aicomp2026/campaigns/20260811-untouched-3size-v1/`
- AIComp relevance review:
  `docs/reviews/2026-08-11-aicomp-2026-dd-laminate-review.md`
- 최신 운영 UI: `src/frontend/dd-laminate/`
- UI/API contract tests: `tests/backend/test_dd_laminate_ios_contract.py`

### 프로젝트 작업 이력

- `docs/session-memory.md`

주의: `docs/DD_Laminate_AI_Current_Summary.md`는 초기 400/500-sample 단계의 이력을 설명하는
자료이며 현재 2,700-row 3-size 발표의 primary source로 사용하면 안 된다.

---

## 14. 발표 시 지켜야 할 표현 경계

다음 표현은 사용하지 않는다.

- “AI가 Moldex3D/Abaqus를 대체한다.”
- “Filling 화면은 실제 공간 압력 contour다.”
- “XAI 중요도는 물리적 원인이다.”
- “Reliability 75%는 통계적으로 보장된 75% 정확도다.”
- “546-row benchmark는 완전히 처음 보는 external test다.”
- “UQ v3와 neural v2/v3가 production에 배포됐다.”
- “UV3S1 540개 시뮬레이션 결과가 이미 검증됐다.”
- “6×8/8×8 Type label은 모두 사람의 독립 검토를 받았다.”

권장 표현:

- “설계공간 screening과 CAE 우선순위 결정”
- “현재 학습 DOE 안에서의 surrogate prediction”
- “local sensitivity for model interpretation”
- “reused fixed benchmark for internal regression comparison”
- “pre-registered untouched simulation campaign”
- “research challenger, not deployed”

---

## 15. 최종 세 문장

1. 범위를 먼저 정의해야 모델 점수가 의미를 가진다.
2. 분류, 스칼라와 곡선은 화면과 물리 해석에서 서로 일치해야 한다.
3. AI 선별은 Moldex3D, Abaqus와 시험 검증으로 반드시 닫혀야 한다.
