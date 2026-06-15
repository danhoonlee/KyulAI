"""
DD Dataset Sorting Script
- Trial_1의 type 매핑을 기반으로 Trial_2 파일을 type1/type2/type3 폴더로 분류
- transition_load.csv에 'type' column 추가
"""

import os
import shutil
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
MOTHER_FOLDER = Path("/Users/danlee/KyulAI/data/datasets/DD")
CASES = ["Case3", "Case4"]
TYPES = ["type1", "type2", "type3"]


def extract_number(filename: str) -> str:
    """
    'plot_Test_###_P1.png' 또는 'plot_Test_###_P2.png' 에서 '###' 추출
    반환값: 문자열 (예: '001', '124')
    """
    stem = Path(filename).stem  # 'plot_Test_124_P2'
    parts = stem.split("_")  # ['plot', 'Test', '124', 'P2']
    return parts[2]  # '124'


def build_type_map(trial1_path: Path) -> dict:
    """
    Trial_1/type#/ 폴더를 순회하여 {번호: type번호} 딕셔너리 반환
    예: {'001': '1', '124': '1', '053': '2', ...}
    """
    type_map = {}
    for type_folder in TYPES:
        folder = trial1_path / type_folder
        if not folder.exists():
            print(f"  [경고] 폴더 없음: {folder}")
            continue
        for f in folder.iterdir():
            if f.suffix == ".png" and f.name.startswith("plot_Test_"):
                num = extract_number(f.name)
                type_map[num] = type_folder.replace("type", "")  # '1', '2', '3'
    return type_map


def sort_trial2(trial2_path: Path, type_map: dict):
    """
    Trial_2 안의 png 파일을 type_map 기반으로 type1/type2/type3 폴더로 이동
    """
    # type1/type2/type3 폴더 생성
    for t in TYPES:
        (trial2_path / t).mkdir(exist_ok=True)

    moved = 0
    skipped = 0

    for f in sorted(trial2_path.iterdir()):
        if f.suffix != ".png" or not f.name.startswith("plot_Test_"):
            continue  # 폴더 or 무관 파일 skip

        num = extract_number(f.name)
        if num not in type_map:
            print(f"  [경고] 매핑 없음: {f.name} (번호: {num})")
            skipped += 1
            continue

        dest_folder = trial2_path / f"type{type_map[num]}"
        shutil.move(str(f), str(dest_folder / f.name))
        moved += 1

    print(f"  Trial_2 정렬 완료: {moved}개 이동, {skipped}개 스킵")


def update_csv(csv_path: Path, type_map: dict):
    """
    transition_load.csv의 Test_ID를 기준으로 'type' column 추가/업데이트
    Test_ID 형식: 'Test_124' → 번호 '124'
    """
    df = pd.read_csv(csv_path)

    if "Test_ID" not in df.columns:
        print(f"  [오류] 'Test_ID' column 없음: {csv_path}")
        return

    def get_type(test_id: str) -> str:
        """'Test_124' → type_map에서 type 번호 반환"""
        try:
            num = test_id.strip().split("_")[1]  # '124'
            return type_map.get(num, "unknown")
        except Exception:
            return "unknown"

    df["type"] = df["Test_ID"].apply(get_type)

    # unknown이 있으면 경고
    unknown = df[df["type"] == "unknown"]
    if not unknown.empty:
        print(
            f"  [경고] type 매핑 실패 행 {len(unknown)}개: {unknown['Test_ID'].tolist()}"
        )

    df.to_csv(csv_path, index=False)
    print(f"  CSV 업데이트 완료: {csv_path.name} ({len(df)}행)")


# ──────────────────────────────────────────────
# 메인 실행
# ──────────────────────────────────────────────
def main():
    for case in CASES:
        case_path = MOTHER_FOLDER / case
        if not case_path.exists():
            print(f"[스킵] 폴더 없음: {case_path}")
            continue

        print(f"\n{'='*40}")
        print(f"처리 중: {case}")
        print(f"{'='*40}")

        trial1_path = case_path / "Trial_1"
        trial2_path = case_path / "Trial_2"
        csv_path = case_path / "transition_load.csv"

        # 1. Trial_1에서 type 매핑 추출
        print("\n[1] Trial_1에서 type 매핑 추출 중...")
        type_map = build_type_map(trial1_path)
        print(f"  매핑된 파일 수: {len(type_map)}개")
        # 매핑 미리보기 (최대 5개)
        preview = list(type_map.items())[:5]
        print(f"  매핑 미리보기: {preview} ...")

        # 2. Trial_2 파일 정렬
        print("\n[2] Trial_2 파일 정렬 중...")
        sort_trial2(trial2_path, type_map)

        # 3. CSV 업데이트
        print("\n[3] transition_load.csv 업데이트 중...")
        if csv_path.exists():
            update_csv(csv_path, type_map)
        else:
            print(f"  [오류] CSV 파일 없음: {csv_path}")

    print(f"\n{'='*40}")
    print("모든 작업 완료!")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
