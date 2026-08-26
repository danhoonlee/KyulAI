# KyulAI 저장공간 정리안 — 2026-08-24

## 실행 결과

- 안전 1차 정리 완료
- 프로젝트 크기: 약 47 GB → 약 27 GB
- Git 저장소: 약 23 GB → 약 9.8 GB
- `dist`: 약 8.6 GB → 약 6.2 GB
- `.tmp`: 약 4.0 GB → 약 1.0 GB
- Git 임시 pack: 51개 → 0개
- 이동된 항목: `/Users/danlee/.Trash/KyulAI_cleanup_20260824/` 약 20 GB
- Git 연결성 검사 통과 및 Git garbage 0 bytes 확인
- `.tmp/openradioss/`, `data/`, `models/` 유지 확인

모든 정리 항목은 전용 휴지통 폴더에 보관되어 있다. 해당 폴더를 비우기 전까지 복구할 수 있으며, Mac의 실제 여유 공간은 비운 후 증가한다.

## 현재 상태

- 프로젝트 전체: 약 47 GB
- Mac 여유 공간: 약 73 GiB
- Git 저장소 내부: 약 23 GB
- `dist`: 약 8.6 GB
- `models`: 약 6.3 GB
- `.tmp`: 약 4.0 GB

## 반드시 유지

- `.tmp/openradioss/` — 현재 OpenRadioss 비교·재실행 결과
- `data/` — 입력 및 기준 데이터
- `models/` 전체 — 코드 참조 및 Git LFS 추적 모델이 섞여 있으므로 별도 감사 전 유지
- 현재 수정·추가된 소스 파일 전체
- 압축본이 없거나 보관 여부가 정해지지 않은 `dist` 결과

## 안전 1차 정리 후보 — 약 19.6 GB

### 1. 중단된 Git 작업 임시 파일 — 약 13.34 GiB

- 위치: `.git/objects/pack/tmp_pack_*`
- 수량: 51개
- Git이 `garbage`로 판정한 미완성 pack 파일
- `git fsck --connectivity-only` 통과로 현재 참조 가능한 Git 이력은 정상임을 확인
- 실행 직전 Git 작업이 없는지 다시 확인한 뒤 제거

### 2. OpenRadioss를 제외한 작업용 임시 폴더 — 약 3.0 GB

- `.tmp/unist-layout-polish/`
- `.tmp/unist-native-repair/`
- `.tmp/unist-variation-proposal/`
- `.tmp/unist-monotone.BcS9JN/`
- `.tmp/unist-brand-proposal/`
- `.tmp/imperialax-v5-brand-remap/`
- `.tmp/unist-company-rename/`
- `.tmp/kyulai_company_template/`
- `.tmp/standardize_cae/`
- 기타 `.tmp` 내 소형 임시 산출물
- 루트의 `.tmp_imperialax_template/`, `.tmp_presentation_xai*/`

일반 임시 파일은 복구 가능하도록 Mac 휴지통의 전용 폴더로 이동한다.

### 3. 재생성 가능한 빌드·분석 캐시 — 약 0.9 GB

- `ios/ImperialAXMVP/.build/`
- `ios/InjectionMVP/.build/`
- `ios/DDLaminateMVP/.build/`
- `android/ImperialAXMVP/app/build/`
- `.mypy_cache/`
- 프로젝트 내부 `__pycache__/`
- `.pytest_cache/`

### 4. 정상 압축본이 확인된 `dist` 전개 폴더 — 약 2.4 GB

- `dist/LaminateForecast(share)/`
  - 유지할 압축본: `dist/LaminateForecast(share).zip`
- `dist/laminate_existing_exe_buildkit_20260715/`
  - 유지할 압축본: `dist/laminate_existing_exe_buildkit_20260715.zip`
- `dist/c2es-laminate-product-page-20260710/`
  - 유지할 압축본: `dist/c2es-laminate-product-page-20260710.zip`

세 압축본 모두 무결성 검사를 통과했다. 전개 폴더는 우선 휴지통으로 이동한다.

## 별도 보관 결정 필요 — 약 3.3 GB

다음 폴더는 압축 대응본 또는 현재 사용 여부가 명확하지 않아 자동 정리하지 않는다.

- `dist/KyulAI_separated_current_20260514_090104/` — 약 892 MB
- `dist/KyulAI_DD_Injection_windows_bundle_20260512_151719/` — 약 888 MB
- `dist/KyulAI_DD_Injection_windows_bundle_20260512_151457/` — 약 888 MB
- `dist/laminate_greenfield_codex_20260715/` — 약 595 MB

NAS가 연결되면 `archive/dist/YYYY-MM/` 형태로 이전하는 방식을 권장한다.

## 이번 정리에서 제외

- Git LFS의 정리 가능 객체 약 924 MB: 원격 저장소 보존 여부를 확인한 뒤 별도 실행
- `.venv` 약 1.0 GB: 재설치 시간을 피하기 위해 유지
- `models` 약 6.3 GB: 런타임 참조와 실험 계보를 먼저 정리한 후 별도 단계에서 판단

## 예상 결과

- 안전 1차 정리 후 약 19.6 GB 확보 가능
- Mac 여유 공간은 약 73 GiB에서 약 92 GiB 수준으로 증가 예상
- 휴지통으로 이동한 항목은 휴지통을 비우기 전까지 복구 가능하며, 실제 공간 확보량에는 반영되지 않음
