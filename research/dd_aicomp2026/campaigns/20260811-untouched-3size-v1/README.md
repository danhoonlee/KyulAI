# UV3S1 새 시뮬레이션 검증 캠페인

이 폴더는 기존 학습 데이터 및 재사용 Holdout과 겹치지 않는 새로운 Double-Double
시뮬레이션 목록입니다. 모델을 더 튜닝하기 위한 데이터가 아니라, 현재 고정된 모델의
일반화 성능과 불확실성 구간을 처음 보는 데이터에서 검증하기 위한 자료입니다.

## 파일 구성

- `pilot_simulation_manifest.csv`: 먼저 실행할 180개 시뮬레이션
- `confirmatory_simulation_manifest.csv`: pilot 품질 확인 후 실행할 360개 시뮬레이션
- `simulation_manifest.csv`: 전체 540개 통합 목록
- `blind_results_template.csv`: 결과를 입력할 통합 양식
- `campaign_freeze.json`: 선택 코드, 데이터, 모델 및 manifest 해시 기록
- `campaign_summary.md`: 캠페인 설계 요약

## 실행 순서

1. `pilot_simulation_manifest.csv`의 180개를 먼저 실행합니다.
2. 각 행의 `geometry`, `case`, `theta1`, `theta2`를 그대로 사용합니다.
3. 결과 Force-Displacement CSV는 `simulation_id`가 식별되도록 보관합니다.
4. solver 실패, 단위 오류, 누락 행, 비정상 종료가 없는지만 확인합니다.
5. pilot 결과를 본 뒤 모델 재학습, 보정 방식 변경, 임계값 조정은 하지 않습니다.
6. 품질 문제가 없으면 `confirmatory_simulation_manifest.csv`의 360개를 실행합니다.
7. 전체 결과를 `blind_results_template.csv`에 입력합니다.

## 결과 입력 항목

- `actual_type`: 검토된 Type 1, 2, 3 중 하나
- `actual_pt_kips`: 동일한 P1 fitting 규칙으로 계산한 Pt
- `actual_max_force_kips`: 해당 곡선의 최대 Force
- `p1_fit_pt_kips`: P1 fitting 교점의 Force 값
- `curve_csv_path`: 원본 Force-Displacement CSV 위치
- `quality_status`: `accepted`, `review_required`, `rejected` 중 하나
- `reviewer`: 검토자 이름 또는 식별자
- `notes`: solver 또는 그래프 특이사항

`actual_pt_kips`와 `p1_fit_pt_kips`는 같은 P1 규칙을 사용했다면 같아야 합니다. 다를 경우
임의로 한 값을 덮어쓰지 말고 `quality_status=review_required`로 표시합니다.

## 결과 완성 검사

전체 결과 양식이 채워진 후 아래 검사를 실행합니다.

```bash
python scripts/dd_prepare_untouched_validation_campaign.py \
  --config research/dd_aicomp2026/configs/20260811-untouched-3size-campaign-v1.json \
  --validate-results /path/to/completed_blind_results.csv
```

검사가 통과하기 전에는 모델 성능 비교를 시작하지 않습니다. 누락 ID, 중복 ID, 잘못된 Type,
음수 또는 빈 Pt/Max. Force, 누락된 Curve CSV 경로를 자동으로 찾습니다.

## Pre-registered evaluation rule

The 30 `uniform_grid` theta pairs and 30 `maximin_gap` theta pairs must be reported separately and
combined. Metrics must also be split by geometry, Case, and geometry + Case. The primary weak-subgroup
diagnostic is `6x8 | Case2`. Once any campaign target is read, changing a model, calibration method,
conformal grouping, or threshold requires a separate untouched campaign.
