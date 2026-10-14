#!/usr/bin/env python3
"""식 후 보관기간이 지나면 하객 PII(전화번호)를 익명화한다.

- 전화번호(phone)만 제거하고 이름·참석·인원·분류·메시지는 유지한다.
- 보관기간: WEDDING_PII_CUTOFF(기본 2027-01-10) 이후에만 동작. 그 전엔 아무 것도 안 함.
- 매일 systemd 타이머에서 실행. 멱등(이미 익명화돼 있으면 변화 없음).
- 운영 앱과 같은 fcntl 락을 잡고, 백업 후 원자적으로 교체한다.

사용법:
  anonymize_wedding_pii.py          # 타이머용: 컷오프 이후면 실행
  anonymize_wedding_pii.py --dry    # 미리보기(변경 없음)
  anonymize_wedding_pii.py --force  # 날짜 무관 지금 실행 (수동 파기)
"""
from __future__ import annotations

import fcntl
import json
import os
import shutil
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.environ.get("WEDDING_DATA_DIR", str(Path.home() / "projects/KyulAI/runtime/wedding")))
SUB = DATA_DIR / "rsvp-submissions.jsonl"
LOCK = DATA_DIR / ".rsvp-submissions.lock"
AUDIT = DATA_DIR / "wedding-audit.jsonl"
CUTOFF = os.environ.get("WEDDING_PII_CUTOFF", "2027-01-10")  # YYYY-MM-DD (식+3개월)
PII_FIELDS = ("phone",)


def _audit(action: str, count: int) -> None:
    try:
        with AUDIT.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "action": action,
                "count": count,
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main() -> int:
    dry = "--dry" in sys.argv
    force = "--force" in sys.argv

    today = date.today()
    try:
        cutoff = date.fromisoformat(CUTOFF)
    except ValueError:
        print(f"잘못된 WEDDING_PII_CUTOFF: {CUTOFF!r}")
        return 1

    if not force and today < cutoff:
        print(f"{today}: 보관기간 중 (파기 예정일 {cutoff}) — 아무것도 안 함")
        return 0

    if not SUB.exists():
        print("데이터 파일 없음:", SUB)
        return 0

    with open(LOCK, "w") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            lines = [l for l in SUB.read_text(encoding="utf-8").splitlines() if l.strip()]
            out: list[str] = []
            changed = 0
            for line in lines:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    out.append(line)
                    continue
                data = rec.get("data") if isinstance(rec, dict) else None
                has_pii = isinstance(data, dict) and any(data.get(k) for k in PII_FIELDS)
                if not has_pii:
                    out.append(line)
                    continue
                changed += 1
                if dry:
                    out.append(line)
                    continue
                for k in PII_FIELDS:
                    data.pop(k, None)
                rec["anonymizedAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                out.append(json.dumps(rec, ensure_ascii=False))

            if dry:
                print(f"[dry] 익명화 대상(전화번호 보유): {changed} / 총 {len(lines)}  (변경 없음)")
                return 0
            if changed:
                shutil.copy2(SUB, SUB.with_name(SUB.name + ".bak-anonymize-" + time.strftime("%Y%m%d-%H%M%S")))
                tmp = SUB.with_name(SUB.name + ".tmp.anon")
                with tmp.open("w", encoding="utf-8") as handle:
                    handle.write("\n".join(out) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                tmp.replace(SUB)
                _audit("pii-anonymize", changed)
            print(f"익명화 완료: {changed}건 전화번호 제거 / 총 {len(lines)}")
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
