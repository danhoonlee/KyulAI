#!/usr/bin/env python3
"""웨딩 데이터 백업 검증: 최신 일일 백업을 열어 복구 가능한지 확인한다.
- tar에서 rsvp-submissions.jsonl 추출 → JSON 파싱 → 레코드 수 집계
- 현재 운영 파일과 레코드 수 비교(급감 시 경고)
크론/수동으로 돌려 백업이 '실제로 복구되는지' 주기적으로 검증하는 용도.
"""
import json, glob, os, subprocess, sys

DIR = os.path.expanduser("~/projects/KyulAI/runtime/wedding")
CUR = os.path.join(DIR, "rsvp-submissions.jsonl")
BK = "/mnt/c/Users/user/ImperialAX-Backups"
INNER = "./kyulai/runtime/wedding/rsvp-submissions.jsonl"


def count(text):
    n = bad = deleted = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except Exception:
            bad += 1
            continue
        n += 1
        if isinstance(r, dict) and r.get("deleted"):
            deleted += 1
    return n, bad, deleted


def main():
    tars = sorted(glob.glob(os.path.join(BK, "imperialax-serving-*.tar.gz")))
    if not tars:
        print("FAIL: 백업 파일이 없습니다:", BK)
        return 1
    latest = tars[-1]
    try:
        text = subprocess.run(["tar", "-xzO", "-f", latest, INNER],
                              capture_output=True, text=True, check=True).stdout
    except subprocess.CalledProcessError as e:
        print("FAIL: 백업에서 데이터 추출 실패:", latest, e)
        return 1
    bn, bbad, bdel = count(text)
    cn, cbad, cdel = count(open(CUR, encoding="utf-8").read()) if os.path.exists(CUR) else (0, 0, 0)

    print(f"최신 백업 : {os.path.basename(latest)}")
    print(f"  백업 레코드: {bn} (파싱실패 {bbad}, 삭제 {bdel})")
    print(f"  현재 레코드: {cn} (파싱실패 {cbad}, 삭제 {cdel})")

    problems = []
    if bn == 0:
        problems.append("백업 레코드 0건")
    if bbad > 0:
        problems.append(f"백업 파싱 실패 {bbad}건")
    # 현재보다 백업이 20% 이상 많으면(=최근에 급감) 경고
    if cn and bn and cn < bn * 0.8:
        problems.append(f"현재({cn})가 백업({bn})보다 20%+ 적음 — 데이터 급감 의심")

    if problems:
        print("WARN:", "; ".join(problems))
        return 2
    print("OK: 백업 검증 통과 (복구 가능)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
