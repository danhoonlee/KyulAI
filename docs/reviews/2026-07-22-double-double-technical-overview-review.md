# Double-Double Technical Overview 검토 보고서

- 검토 대상: `data/PPT/double_double_composite_laminate_technical_overview.md`
- 검토일: 2026-07-22
- 목적: 문헌 정확성, 프로젝트 정의와의 일치 여부, 학습 데이터 및 모델 보완 방향 확인

## 1. 결론

이 문서는 Double-Double(DD) 적층의 기원, CLT, 반복 블록, homogenization, 장단점,
최근 연구 흐름을 폭넓게 다룬 좋은 기술 개요다. 특히 다음 사항은 적절하게 서술되어 있다.

- DD가 균형 적층을 쉽게 구성하지만 유한 적층에서 자동으로 대칭 적층이 되는 것은 아니다.
- homogenization은 등방성을 의미하지 않는다.
- 16 ply 또는 4개 블록이 모든 DD 적층의 보편적 최소 조건은 아니다.
- DD가 Legacy Quad보다 항상 가볍거나 항상 우수하다고 단정하지 않는다.
- 최근 연구의 질량, 충격, warpage 결과를 연구별 결과로 제한해 설명한다.

다만 현재 상태를 그대로 RAG의 확정 지식이나 학습용 정답 정의로 사용하면 안 된다.
적층 순서의 내부 불일치, 과도하게 단정적인 B matrix 설명, 스키마의 정의 부족,
그리고 현재 프로젝트 Case 3 정의 불일치가 먼저 해결되어야 한다.

## 2. 문헌과 일치하는 주요 내용

### 2.1 DD의 기본 개념과 설계 공간

두 각도군과 반복 블록으로 설계 변수를 줄이고, paired 및 staggered 계열처럼 ply order를
별도로 고려해야 한다는 설명은 문헌과 일치한다. 2023년 AIAA Journal 연구도 paired와
세 가지 staggered 순서를 구분하고, 적층 순서가 homogenization 성능을 바꾼다고 설명한다.

### 2.2 정규화 ABD와 반복 효과

문서에 적힌 다음 정규화는 현재 프로젝트 구현과도 일치한다.

```text
A* = A / h
B* = 2B / h^2
D* = 12D / h^3
```

반복 횟수가 늘어날 때 B*와 bending-twisting coupling의 영향이 감소한다는 방향도 타당하다.
다만 이 관계는 유효한 반복 블록, 동일 재료 및 두께, 해당 적층 순서를 전제로 한 경향으로
설명해야 한다.

### 2.3 Tsai modulus

`Q11 + Q22 + 2Q66`을 재료의 회전 불변 stiffness 지표로 다루는 설명은 Tsai modulus
문헌과 일치한다. 동일 재료 적층에서는 normalized A와 D의 trace를 비교하는 기준으로도
사용할 수 있다.

### 2.4 연구 결과의 제한적 표현

문서는 약 6% 질량 변화, 6.5% wing-box 질량 증가, 충격 및 CAI, SEDD 등의 결과를
보편적 보장으로 표현하지 않고 해당 연구의 조건에 제한한다. 이 태도는 정확하다.

## 3. 반드시 수정할 내용

### P0. Section 3의 building block과 예시 순서가 서로 다름

Section 3.1은 기본 블록을 다음처럼 정의한다.

```text
[+phi / -phi / +psi / -psi]
```

하지만 Section 3.2의 예시는 다음과 같다.

```text
[+22.5 / -67.5 / -22.5 / +67.5]_{4T}
```

이 예시는 앞의 paired 순서가 아니라 staggered-1 계열에 해당한다. 같은 각도 개수라도
순서가 달라지면 B, D, D16, D26 및 warpage가 달라질 수 있으므로 다음 중 하나로 고쳐야 한다.

1. 예시를 paired 순서인 `[+22.5/-22.5/+67.5/-67.5]_{4T}`로 바꾼다.
2. 현재 예시를 유지하고 `staggered-1 example`이라고 명시한다.

### P0. 프로젝트 Case 3 정의가 모델 코드와 UI/RAG에서 다름

**Resolution (2026-07-22):** canonical registry를 추가하고 Case 3를
`[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`로 확정했다. 기존 artifact는
`legacy_case3_v1` 호환 경로로 보존하고, corrected feature pack으로 Tree,
GointMLP, Hybrid Student, u3 및 XAI 모델을 다시 학습했다.

현재 physics feature 코드는 Case 3를 다음 sequence로 전개한다.

```text
[[±theta1]/[±theta2]/[∓theta2]/[∓theta2]]2
```

반면 웹, iOS, Android 및 RAG는 다음처럼 사용자에게 설명한다.

```text
[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2
```

이 상태에서는 화면에 표시되는 적층과 XAI/ABD 계산에 실제 사용된 적층이 서로 다르다.
모델의 의미와 연구 재현성을 훼손할 수 있는 높은 우선순위 문제다.

권장 조치:

1. 실제 Abaqus layup script 또는 input deck을 기준으로 Case 2, 3, 4의 정답 sequence를 확정한다.
2. 하나의 `case_definitions.yaml` 또는 JSON을 만든다.
3. feature builder, dataset builder, 웹, 앱, RAG가 모두 이 파일을 사용하게 한다.
4. 정답이 현재 feature 코드와 다르면 physics feature와 관련 모델을 다시 학습한다.

2026-07-22 사용자 확인으로 프로젝트의 canonical Case 3는
`[[±theta1]/[±theta2]/[∓theta1]/[∓theta2]]2`로 확정되었다. 따라서 현재 physics feature
코드의 `∓theta2/∓theta2` 전개가 잘못된 구현이다. 원본 해석이 canonical Case 3로 수행된
것이라면 Abaqus 결과와 label은 유지하고, 파생 physics feature와 이를 사용한 모델을 다시
학습해야 한다.

### P1. `unsymmetric -> B != 0`를 필연처럼 서술함

Section 5.2의 `Consequently, B != 0`는 너무 강한 표현이다. 비대칭 적층은 일반적으로
B가 0이 아닐 수 있지만, 특수한 각도와 순서에서는 일부 또는 전체 성분이 상쇄될 수 있다.

권장 문장:

> A finite repeated DD laminate is generally unsymmetric, so B is generally nonzero, although
> special angle and stacking combinations can cancel individual or all coupling terms.

### P1. A* 반복 독립성을 `approximately`만으로 표현함

동일 재료, 동일 두께의 같은 balanced block을 정확히 반복하는 이상적 조건에서는 A/h가
repeat count와 무관한 것은 근사라기보다 정확한 결과다. 실제 제조 공차, 혼합 재료,
두께 변화 및 불완전한 블록에서는 근사적 경향이 된다. 조건을 나눠 서술하는 편이 정확하다.

### P1. 16 ply 기준의 조건을 표에 더 명확히 명시해야 함

16 ply 또는 네 블록 기준은 모든 DD 적층에 적용되는 최소 조건이 아니다. 해당 연구의
2% Tsai-modulus homogenization criterion과 특정 staggered order 조합에서 조사 설계공간을
포괄한 결과임을 표 안에도 직접 적는 것이 안전하다.

### P1. 제안 데이터 스키마에 수학적 정의가 부족함

다음 항목은 이름만으로 재현할 수 없다.

- `A16`, `A26`: normalized stiffness 아래에서는 `A16_star`, `A26_star`로 명명해야 한다.
- `B_norm_percent`: matrix norm의 종류와 분모를 명시해야 한다.
- homogenization: `||A* - D*|| / Tsai`, `||B*|| / Tsai` 같은 기준식과 단위를 저장해야 한다.
- sequence: compact formula뿐 아니라 실제 16-ply expanded sequence를 정답으로 저장해야 한다.
- provenance: 해석 파일, 생성 코드 버전, material/mesh/BC/load hash가 필요하다.

### P2. 인용이 문단별로 연결되지 않음

Section 10의 수치와 결론은 대체로 문헌과 맞지만, Section 20에 URL만 모아 놓아 어떤 문장이
어느 논문에 근거하는지 자동 추적하기 어렵다. 저자, 연도, 제목, DOI를 기록하고 연구별 수치에
inline citation ID를 붙여야 RAG가 출처를 잘못 결합하는 문제를 줄일 수 있다.

## 4. 이 문서만으로는 부족한 프로젝트 정의

이 문서는 일반 DD 기술 자료로는 좋지만 현재 ImperialAX Laminate 연구의 ground truth는 아니다.
다음 프로젝트 정의가 별도 문서 또는 schema에 필요하다.

- Case 2, Case 3, Case 4의 canonical formula와 expanded ply sequence
- 프로젝트의 Type 1, Type 2, Type 3 force-displacement 정의
- 문헌의 paired/staggered Type과 프로젝트의 response Type을 구분하는 명명 규칙
- Pt 산출 알고리즘, fit window, kink 탐지, R2, 알고리즘 버전
- Type 1, 2, 3별 Force와 U3 사용 규칙
- T800/3900S 물성, ply thickness, 6x4/6x8/8x8 panel 조건
- boundary condition, load, mesh, imperfection 및 nonlinear analysis 설정
- 수동 label, 자동 reclassification, reviewer 및 confidence 정보

특히 문헌에서 말하는 `four DD stacking-order types`와 이 프로젝트의 `response Type 1/2/3`은
전혀 다른 분류 축이므로 같은 `Type`이라는 단어만 사용하면 RAG와 사용자가 혼동할 수 있다.

## 5. 현재 학습 데이터 및 모델 상태에서의 보완안

### 5.1 Physics Feature Pack v3

현재 feature pack에 다음을 추가하는 것이 우선이다.

- full A*, B*, D* component
- Tsai modulus 또는 stiffness trace
- `||A* - D*|| / Tsai`
- `||B*|| / Tsai`
- D16*, D26* residual 및 최대 normalized coupling
- lamination parameters: xiA, xiB, xiD
- repeat count, total ply count, total thickness
- exact ply sequence와 stacking-order family
- material ID와 실제 material constants

현재 compact feature는 B16/B26 중심이라 B11/B22/B12/B66 및 전체 B norm을 충분히 표현하지
못한다. DD homogenization과 warpage를 설명하려면 full B*와 A*-D* residual이 중요하다.

### 5.2 Case 번호 대신 sequence-aware model 추가

현재 Case 2, 3, 4 one-hot 모델은 새로운 Case 5 또는 실시간 수식에 일반화하기 어렵다.
각 ply를 다음 벡터로 인코딩하는 sequence branch를 추가하는 것이 적합하다.

```text
[sin(2theta), cos(2theta), sin(4theta), cos(4theta), normalized z,
 ply thickness, material embedding]
```

이 branch를 geometry branch와 CLT physics branch에 결합해 Type, Pt, curve를 함께 예측하면
새로운 ply order를 Case 번호 없이 비교할 수 있다. 다만 학습 범위를 벗어난 stacking family에는
FEA labels와 out-of-domain 경고가 반드시 필요하다.

### 5.3 Pt 및 Type label을 물리 규칙과 함께 저장

학습 manifest에 다음을 추가한다.

- `response_type_label`
- `label_source`: human, rule, reviewed
- `label_confidence`
- `pt_force`, `pt_u3`, `pt_final`
- `pt_method_version`
- left/right fit windows와 R2
- full Force curve와 U3 curve 경로

Force CSV 하나만으로는 U3를 사용하는 Type 2/3 Pt 정의를 완전히 재현할 수 없다. Curve CSV
batch classifier와 Forecast 학습에서도 이 한계를 명시해야 한다.

### 5.4 Type 발생 원인 분석을 위한 해석 입력 추가

현재 theta/case/geometry만으로는 `왜` 특정 nonlinear response Type이 발생했는지 인과적으로
설명하기 어렵다. 다음 항목을 Abaqus 결과와 함께 저장하는 것이 효과적이다.

- initial imperfection mode와 amplitude
- eigenvalue buckling mode 및 critical load
- initial curvature 또는 cure-induced warpage
- boundary condition 및 load introduction metadata
- local strain, out-of-plane displacement U3, damage initiation variables
- mesh and solver settings

CLT 또는 plate buckling 식으로 baseline transition load를 계산하고, AI가 nonlinear 및
imperfection correction residual을 예측하도록 구성하면 물리 해석성과 일반화가 좋아질 수 있다.

### 5.5 8x8을 외부 geometry holdout으로 사용

현재 curated geometry dataset은 6x4와 6x8이 중심이다. 새 8x8 자료는 학습에 바로 섞기보다
먼저 외부 검증 세트로 사용해 geometry generalization을 측정하는 편이 연구적으로 더 가치 있다.

필요 조치:

- 8x8 Case3의 누락 CSV 70개를 복구한다.
- 8x8 Case3/Case4 label과 Pt를 동일 규칙으로 curate한다.
- 가능하면 8x8 Case2도 생성한다.
- 첫 평가에서는 8x8 전체를 unseen geometry holdout으로 고정한다.
- 평가 후에만 일부를 training에 추가하고 remaining external holdout을 유지한다.

### 5.6 불확실성과 active learning

- Type probability calibration
- case/geometry별 conformal Pt interval
- training design-space coverage와 OOD flag
- ensemble disagreement가 큰 theta/sequence/geometry를 다음 해석 후보로 선택

이 방식은 dense angle grid를 무조건 늘리는 것보다 새 simulation budget을 효율적으로 사용할 수 있다.

## 6. 권장 실행 순서

1. 확정된 Case 2/3/4 canonical sequence를 중앙 `case_definitions` registry로 만든다.
2. feature builder, 코드, UI, 앱, RAG를 이 registry로 통합한다.
3. 새 기술 문서의 Section 3, 5, 10, 17을 수정한 후 RAG에 반영한다.
4. Physics Feature Pack v3를 구현하고 기존 모델과 strict grouped CV로 비교한다.
5. 8x8을 외부 geometry holdout으로 평가한다.
6. U3, imperfection, eigenvalue 정보를 포함한 label/data schema를 구축한다.
7. sequence-aware multi-task model을 별도 실험으로 시작한다.

## 7. 근거 자료

- DD design space and homogenization, AIAA Journal, DOI `10.2514/1.J062639`
- Design of laminates by a novel double-double layup, Thin-Walled Structures, DOI `10.1016/j.tws.2021.107954`
- Trace-based laminate stiffness and Tsai modulus, Composite Structures, DOI `10.1016/j.compstruct.2020.113389`
- Homogenisation, warpage mitigation and SEDD, Journal of Composite Materials, DOI `10.1177/00219983251362358`
- Impact and compression-after-impact comparison, Composite Structures, DOI `10.1016/j.compstruct.2024.118615`
- Wing-box DD optimization comparison, Composite Structures, DOI associated with the 2025 DLR study
- Broad DD mechanical comparison, Composites Part B, DOI `10.1016/j.compositesb.2025.113115`
- Extended DD design space, Thin-Walled Structures, DOI `10.1016/j.tws.2025.114296`

## 8. 최종 판정

- 일반 기술 설명 정확도: 높음
- 수치 및 연구 결과의 표현 태도: 양호
- 프로젝트 학습 정답으로서의 준비도: 수정 전 사용 비권장
- 가장 큰 위험: 확정된 Case 3와 physics feature 코드의 sequence 불일치
- 가장 큰 학습 기회: full normalized ABD + homogenization residual + ply-sequence encoder + U3/imperfection data
