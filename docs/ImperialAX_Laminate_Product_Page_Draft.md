# ImperialAX Laminate Forecast 제품소개 초안

작성일: 2026-07-10

용도: `imperialaxkorea.com > 제품소개` 탭에 추가할 수 있는 HTML 스타일 제품 설명 초안.

## 제품명 후보

- ImperialAX Laminate Forecast
- ImperialAX Composite Laminate AI
- Double-Double Laminate Forecast AI
- ImperialAX AI Laminate Design Assistant

추천 표기:

```html
<h2>ImperialAX Laminate Forecast</h2>
<p><strong>AI 기반 복합재 적층 구조 예측 및 설계 지원 솔루션</strong></p>
```

## 제품소개 HTML 초안

```html
<section class="product-detail">
  <h2>ImperialAX Laminate Forecast</h2>
  <p><strong>AI 기반 복합재 적층 구조 예측 및 설계 지원 솔루션</strong></p>

  <p>
    ImperialAX Laminate Forecast는 복합재 적층 구조, 특히 Double-Double Laminate 연구 및 설계 과정에서
    반복적인 해석 작업을 줄이고 유망한 적층 후보를 빠르게 선별하기 위해 개발된 AI 기반 예측 솔루션입니다.
    사용자는 적층 Case와 두 개의 각도 값 θ₁, θ₂를 입력하는 것만으로 Type, 전이하중 Pt,
    Force-Displacement 응답 곡선, u3 기반 변위 거동, 주요 영향 인자(XAI)를 확인할 수 있습니다.
  </p>

  <p>
    기존 복합재 설계에서는 적층 순서와 각도 조합에 따라 해석 결과가 크게 달라지기 때문에,
    많은 수의 후보를 Abaqus와 같은 구조해석으로 반복 검토해야 했습니다. ImperialAX Laminate Forecast는
    축적된 해석 데이터와 Classical Laminate Theory 기반 물리 feature를 결합하여,
    본격적인 상세 해석 전에 후보군을 빠르게 줄이고 설계 방향을 판단할 수 있도록 지원합니다.
  </p>

  <h3>주요 기능</h3>
  <ul>
    <li>
      <strong>Double-Double 적층 Type 예측</strong><br>
      θ₁, θ₂, Case 조건을 기반으로 Force-Displacement 응답 특성을 Type 1, Type 2, Type 3으로 예측합니다.
      이를 통해 bilinear 거동 또는 post-kink 이후 곡률 변화가 큰 후보를 빠르게 구분할 수 있습니다.
    </li>
    <li>
      <strong>전이하중 Pt 예측</strong><br>
      응답 곡선의 굴곡점 또는 전이점에 해당하는 Pt를 예측하여, 적층 구조의 안정성 변화가 시작되는
      하중 수준을 정량적으로 비교할 수 있습니다.
    </li>
    <li>
      <strong>예측 응답 곡선 시각화</strong><br>
      Force-Displacement 곡선을 AI surrogate model로 예측하고, bilinear fitting line과 예측 Pt를 함께 표시하여
      해석 결과를 직관적으로 검토할 수 있습니다.
    </li>
    <li>
      <strong>u3 Forecast</strong><br>
      u3 변위 기반 데이터에 대해 Pt 및 응답 곡선을 별도로 예측하여, 구조 변위 관점에서 적층 후보를 추가 검토할 수 있습니다.
    </li>
    <li>
      <strong>Physics XAI</strong><br>
      D11, D66, A11, A12, B16, B26, bending anisotropy 등 CLT 기반 물리 feature가 예측 결과에
      얼마나 영향을 주었는지 확인할 수 있습니다. 단순한 AI 예측값뿐 아니라 “왜 이런 예측이 나왔는지”를
      연구자와 엔지니어가 함께 해석할 수 있도록 지원합니다.
    </li>
    <li>
      <strong>Design-space Insight</strong><br>
      기존 실험/해석 데이터 공간에서 현재 입력값이 어느 위치에 있는지 확인하고, 유사 후보 및 개선 가능성이 있는
      θ 조합을 함께 검토할 수 있습니다.
    </li>
    <li>
      <strong>AI Assistant / RAG 기반 설명</strong><br>
      내부 연구 문서, PPT, XAI 결과, 복합재 관련 지식 기반을 활용하여 예측 결과에 대한 질문과 설명을 제공합니다.
      사용자는 D11 굽힘 강성, A12 membrane coupling, TAC vs DD 비교 등 복합재 설계 관점의 질문을 입력할 수 있습니다.
    </li>
  </ul>

  <h3>지원하는 적층 Case</h3>
  <ul>
    <li><strong>Case 2</strong>: [[±θ₁]/[±θ₂]]₄</li>
    <li><strong>Case 3</strong>: [[±θ₁]/[±θ₂]/[∓θ₂]/[∓θ₂]]₂</li>
    <li><strong>Case 4</strong>: [([±θ₁]/[±θ₂])₂ / ([∓θ₁]/[∓θ₂])₂]</li>
  </ul>
  <p>
    Case 2, Case 3, Case 4는 현재 학습 데이터와 검증 데이터가 구성된 범위이며,
    추가 적층 패턴은 실제 ply sequence로 전개한 뒤 CLT 기반 feature를 계산하여 확장 적용할 수 있습니다.
  </p>

  <h3>적용 분야</h3>
  <ul>
    <li>항공기 및 우주 구조물용 복합재 패널 적층 설계</li>
    <li>Double-Double Laminate 및 새로운 적층 패턴 후보 탐색</li>
    <li>복합재 구조해석 전 설계 후보 사전 선별</li>
    <li>CAE 해석 데이터 기반 surrogate model 구축</li>
    <li>복합재 연구/교육용 AI 기반 적층 거동 분석</li>
    <li>해석 결과의 XAI 기반 영향 인자 분석 및 설계 의사결정 지원</li>
  </ul>

  <h3>기대 효과</h3>
  <ul>
    <li><strong>해석 전 후보 선별</strong>: 많은 θ 조합을 모두 상세 해석하기 전에 유망 후보를 빠르게 압축할 수 있습니다.</li>
    <li><strong>설계 방향성 파악</strong>: 어떤 각도 조합과 강성 feature가 Type, Pt, 곡선 형상에 영향을 주는지 확인할 수 있습니다.</li>
    <li><strong>반복 작업 감소</strong>: 수백 개 이상의 해석 결과를 수작업으로 검토하던 과정을 AI 예측과 시각화로 보조합니다.</li>
    <li><strong>연구 설명력 강화</strong>: XAI와 AI Assistant를 통해 예측값뿐 아니라 물리적 의미와 설계 판단 근거를 함께 제공합니다.</li>
    <li><strong>확장 가능성</strong>: 새로운 Case, 새로운 ply sequence, 추가 Abaqus/CAE 데이터가 확보되면 모델을 재학습하여 적용 범위를 확장할 수 있습니다.</li>
  </ul>

  <h3>사용 흐름</h3>
  <ol>
    <li>적층 Case 선택</li>
    <li>θ₁, θ₂ 각도 입력</li>
    <li>Machine Learning 또는 Deep Learning 모델 선택</li>
    <li>Type, Pt, 응답 곡선, u3 예측 결과 확인</li>
    <li>XAI feature 영향도 및 Design-space 위치 검토</li>
    <li>유망 후보를 상세 CAE 해석으로 검증</li>
  </ol>

  <h3>기술 구성</h3>
  <p>
    ImperialAX Laminate Forecast는 해석 데이터 기반 Machine Learning / Deep Learning surrogate model과
    복합재 적층 이론 기반 feature engineering을 결합합니다. 입력된 θ₁, θ₂, Case 정보는 실제 ply sequence로 전개되며,
    T800/3900S 재료 물성과 ply thickness를 기준으로 ABD matrix 및 normalized stiffness feature가 계산됩니다.
    이후 예측 모델은 Type, Pt, 최대 Force, 최대 Displacement, 곡선 형상 및 u3 응답을 예측합니다.
  </p>

  <p>
    현재 모델은 내부 연구 데이터 기준으로 Case 2, Case 3, Case 4 범위에서 학습 및 검증되었으며,
    연구/설계 단계의 선별 도구로 사용하는 것을 권장합니다. 최종 설계 판단에는 반드시 상세 CAE 해석 및 실험 검증이 함께 수행되어야 합니다.
  </p>

  <h3>관련 키워드</h3>
  <p>
    Composite Laminate, Double-Double Laminate, Classical Laminate Theory, ABD Matrix,
    Surrogate Model, Machine Learning, Deep Learning, XAI, Abaqus Data, CAE Automation,
    Laminate Optimization, u3 Displacement, Transition Load Pt
  </p>

  <p>
    <a href="https://laminate.imperialax.com/" target="_blank" rel="noopener">Laminate Forecast 데모 보기</a>
  </p>
</section>
```

## 짧은 제품 카드용 문안

```html
<h3>ImperialAX Laminate Forecast</h3>
<p>
  Double-Double 복합재 적층 구조의 Type, 전이하중 Pt, Force-Displacement 곡선,
  u3 거동을 θ₁, θ₂, Case 입력만으로 예측하는 AI 기반 설계 지원 솔루션입니다.
  CLT 기반 물리 feature와 XAI를 함께 제공하여, 단순 예측을 넘어 “왜 이런 결과가 나왔는지”까지
  엔지니어가 해석할 수 있도록 지원합니다.
</p>
```

## 아주 짧은 한 줄 소개

```html
<p>
  ImperialAX Laminate Forecast는 복합재 Double-Double 적층 구조의 Type, Pt, 응답 곡선, u3 거동을
  AI와 물리 feature 기반으로 예측하는 CAE 설계 지원 도구입니다.
</p>
```

## 영상 제작 방향

## 제품소개용 캡처 이미지

아래 이미지는 `https://laminate.imperialax.com/index-v2.ko.html` 기준으로 캡처했다.

- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-01-overview.png`
  - 제품 첫 화면, 연구 목적, AI Assistant, 작업 흐름, 입력 영역이 함께 보이는 overview.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-02-input-panel.png`
  - Case, θ₁, θ₂, 모델 선택 등 입력 패널 중심 이미지.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-03-result-top.png`
  - 예측 실행 후 Type, 확률, 입력 요약, 예측 곡선 상단이 보이는 결과 화면.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-04-response-curve.png`
  - Pt, 최대 변위, 최대 하중, Force-Displacement curve 중심 이미지.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-05-xai.png`
  - XAI feature 영향도와 설명.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-06-design-space.png`
  - Design-space map, 현재 입력 vs 추천 후보, Case별 영역, 추천 후보.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-07-u3-result.png`
  - u3 Forecast 결과 화면.
- `/Users/danlee/KyulAI_codex/docs/product-assets/screenshots/laminate-08-u3-curve.png`
  - u3 예측 곡선과 Pt 중심 이미지.

### 영상 목적

웹 제품소개 페이지에서 방문자가 1분 안에 다음을 이해하게 하는 것:

1. 복합재 적층 설계는 각도/Case 조합이 많아 해석 반복 비용이 크다.
2. ImperialAX Laminate Forecast는 θ₁, θ₂, Case만 입력해 Type, Pt, 곡선, XAI를 빠르게 보여준다.
3. 최종 해석을 대체하기보다, 상세 CAE 해석 전에 후보를 선별하고 설계 방향을 잡는 도구다.

### 권장 영상 길이

- 홈페이지 제품 카드용: 30초
- 제품 상세 페이지용: 60~90초
- 영업/미팅 데모용: 2~3분

### 60초 영상 스토리보드

| 시간 | 화면 | 내레이션/자막 |
| --- | --- | --- |
| 0-5초 | 복합재 적층 구조/패널 이미지, 여러 각도 조합이 펼쳐지는 장면 | “복합재 적층 설계에서는 각도와 적층 순서에 따라 구조 응답이 크게 달라집니다.” |
| 5-12초 | Abaqus/CAE 해석 결과 여러 개, 그래프가 반복 표시 | “모든 후보를 상세 해석으로 검토하면 많은 시간과 비용이 필요합니다.” |
| 12-20초 | ImperialAX Laminate Forecast 화면, Case와 θ₁/θ₂ 입력 | “ImperialAX Laminate Forecast는 Case와 두 개의 각도만으로 주요 응답을 예측합니다.” |
| 20-32초 | Type, Pt, Force-Displacement 곡선, u3 Forecast 결과 표시 | “Type, 전이하중 Pt, 응답 곡선, u3 거동을 빠르게 확인할 수 있습니다.” |
| 32-45초 | XAI feature bar, D11/A11/B16 등 영향 인자 표시 | “Physics XAI는 D11 굽힘 강성, 막-굽힘 커플링, 적층 이방성 등 예측에 영향을 준 인자를 설명합니다.” |
| 45-55초 | Design-space map, 후보 추천, 현재 입력 위치 표시 | “기존 해석 데이터 공간에서 현재 후보의 위치와 개선 가능성을 함께 검토합니다.” |
| 55-60초 | ImperialAX 로고와 데모 URL | “AI와 CAE를 연결하는 복합재 설계 지원 솔루션, ImperialAX Laminate Forecast.” |

### 필요한 영상 소재

- 앱/웹 화면 녹화:
  - Case/θ 입력
  - Predict 실행
  - Type/Pt/곡선 결과
  - XAI feature 영향도
  - Design-space map
  - AI Assistant 질문/답변
- 시각 자료:
  - Double-Double ply stack 이미지
  - 복합재 패널 또는 탄소섬유 이미지
  - Force-Displacement 그래프
  - u3 displacement 그래프
  - ImperialAX 로고
- 선택 자료:
  - PPT에 있는 연구 목적/적층 구조 이미지
  - Abaqus ply stack 또는 해석 결과 이미지

### 제작 방법 후보

1. 빠른 제작:
   - 웹 화면을 녹화하고, Keynote/PowerPoint에서 간단한 인트로/아웃트로를 붙인다.
   - 가장 빠르고 실제 제품 화면 신뢰도가 높다.

2. 고급 제작:
   - After Effects, Premiere Pro, DaVinci Resolve, 또는 Canva/CapCut을 사용한다.
   - 그래프와 ply stack을 모션으로 표현해 제품 느낌을 강화할 수 있다.

3. AI 영상 제작:
   - AI로 배경 영상이나 복합재 질감 장면을 만들고, 실제 웹 화면 녹화와 섞는다.
   - 단, 기술 제품은 실제 UI 화면과 실제 데이터 그래프가 들어가야 신뢰도가 높다.

### 추천 제작 방향

처음에는 “실제 UI 녹화 + 간단한 모션 자막 + ImperialAX 로고” 방식이 가장 좋다.
제품이 아직 발전 중이므로 과하게 광고 영상처럼 만들기보다, 실제로 입력하고 결과가 나오는 장면을 보여주는 편이 설득력이 높다.

## 영상 내레이션 초안

```text
복합재 적층 구조는 각도와 적층 순서에 따라 강성, 전이하중, 변위 응답이 크게 달라집니다.
하지만 모든 후보를 상세 CAE 해석으로 검토하는 것은 많은 시간과 비용이 필요합니다.

ImperialAX Laminate Forecast는 Double-Double 적층 구조 연구를 위해 개발된 AI 기반 예측 도구입니다.
Case와 θ₁, θ₂ 값을 입력하면 Type, 전이하중 Pt, Force-Displacement 응답 곡선,
그리고 u3 기반 변위 거동을 빠르게 예측합니다.

또한 Physics XAI를 통해 D11 굽힘 강성, A11 막 강성, B16/B26 커플링,
적층 이방성 등 예측에 영향을 준 물리 feature를 확인할 수 있습니다.

엔지니어는 이를 통해 상세 해석 전에 유망한 적층 후보를 선별하고,
왜 특정 적층 조합이 더 좋은 응답을 보이는지 설계 관점에서 검토할 수 있습니다.

AI와 CAE를 연결하는 복합재 설계 지원 솔루션,
ImperialAX Laminate Forecast.
```
