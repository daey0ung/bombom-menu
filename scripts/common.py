"""봄봄 메뉴 파이프라인 공통 상수/헬퍼."""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windows 콘솔은 cp949라 em dash 같은 문자에서 UnicodeEncodeError로 죽는다.
# 로그 한 줄 때문에 파이프라인이 멈추지 않도록 인코딩 실패를 무시한다.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

PLACE_ID = "2096511528"
FEED_URL = f"https://m.place.naver.com/restaurant/{PLACE_ID}/feed"
SOURCE_URL = FEED_URL
PLACE_NAME = "봄봄 한식뷔페 구로디지털단지점"

# 무헤더 요청은 429로 차단된다. 이 UA 조합은 로컬/Actions 양쪽에서 200 확인됨.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Referer": "https://m.search.naver.com/",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}

KST = timezone(timedelta(hours=9))

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
MENU_DIR = DOCS / "menu"
DATA_DIR = DOCS / "data"

REPO = os.environ.get("GITHUB_REPOSITORY", "daey0ung/bombom-menu")
REF = os.environ.get("GITHUB_REF_NAME", "codex/dy_modify01")
REPO_OWNER, REPO_NAME = REPO.split("/", 1)
PAGES_URL = f"https://{REPO_OWNER}.github.io/{REPO_NAME}/"
# Pages 배포는 push 후 1분 가량 지연되므로, 알림 카드 이미지는 즉시 제공되는 raw를 쓴다.
RAW_BASE = f"https://raw.githubusercontent.com/{REPO}/{REF}/docs/"


def today_kst() -> str:
    """러너는 UTC로 돌기 때문에 날짜 판정은 반드시 KST 기준."""
    return datetime.now(KST).strftime("%Y%m%d")


def iso(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"


def emit(**kv) -> None:
    """GITHUB_OUTPUT으로 값 전달 (로컬 실행 시엔 stdout에만 표시)."""
    out = os.environ.get("GITHUB_OUTPUT")
    for k, v in kv.items():
        print(f"[out] {k}={v}")
    if not out:
        return
    with open(out, "a", encoding="utf-8") as f:
        for k, v in kv.items():
            f.write(f"{k}={v}\n")


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
