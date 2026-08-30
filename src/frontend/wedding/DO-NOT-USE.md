# ⚠️ 이 폴더는 운영본이 아닙니다 (DO NOT USE)

이 폴더(`KyulAI/src/frontend/wedding/`)는 **2025-07-22 시점의 옛 청첩장 사본**입니다.
운영에는 사용되지 않으며, 편집하거나 배포 대상으로 삼지 마세요.

## 실제 운영 폴더
    /home/user/projects/donghoon-seyeon-wedding

## 이 경로가 지정되는 곳 (systemd drop-in)
    ~/.config/systemd/user/imperialax-laminate.service.d/wedding-frontend.conf
    Environment=WEDDING_FRONTEND_DIR=/home/user/projects/donghoon-seyeon-wedding

## 왜 이 사본이 위험한가
`dd_laminate_app.py`의 fallback 기본값이 `PROJECT_ROOT/src/frontend/wedding`(= 이 폴더)이다.
위 drop-in이 삭제되면 운영이 조용히 이 옛 버전으로 롤백된다
(기존 신청 불러오기 버튼, 필수 항목 표시 등이 전부 사라진 채로).
**drop-in을 지우지 말 것.**

## 배포 방법
운영 정적 파일 배포는 `git pull`이 아니라 Mac repo에서 SSH로 직접 파일을 동기화한다
(배포 폴더 git remote가 https + 무자격증명이라 pull 불가). 자세한 내용은 AUDIT 문서 참조.

_확정: 2026-08-30_
