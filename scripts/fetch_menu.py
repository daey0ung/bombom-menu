"""네이버 플레이스 '소식' 탭에서 오늘 날짜 메뉴 이미지를 받아온다.

브라우저 자동화가 필요 없다 — 페이지 HTML에 window.__APOLLO_STATE__ 로
소식 데이터 전체가 임베드되어 있어 GET 1회로 끝난다.
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

from common import (DATA_DIR, FEED_URL, HEADERS, MENU_DIR, SOURCE_URL, emit,
                    iso, today_kst)

# 확장자는 .jpg지만 실제 바이트는 PNG인 경우가 있어 매직 바이트로 판정한다.
MAGIC = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpg"),
    (b"GIF8", "gif"),
    (b"RIFF", "webp"),
]


def sniff_ext(data: bytes) -> str:
    for sig, ext in MAGIC:
        if data.startswith(sig):
            return ext
    return "jpg"


def existing_image(date_iso: str) -> Path | None:
    for p in MENU_DIR.glob(f"{date_iso}.*"):
        return p
    return None


def fetch_feeds() -> list[dict]:
    req = urllib.request.Request(FEED_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", "replace")

    m = re.search(r"window\.__APOLLO_STATE__\s*=\s*(\{)", html)
    if not m:
        raise RuntimeError(
            "__APOLLO_STATE__ 없음 — 캡차/차단 페이지일 가능성. "
            f"응답 앞부분: {html[:200]!r}"
        )
    obj, _ = json.JSONDecoder().raw_decode(html[m.start(1):])
    feeds = [
        v for v in obj.values()
        if isinstance(v, dict) and v.get("__typename") == "Feed" and not v.get("isDeleted")
    ]
    feeds.sort(key=lambda f: f.get("createdString") or "", reverse=True)
    return feeds


def main() -> int:
    MENU_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ymd = today_kst()
    date_iso = iso(ymd)
    print(f"target date (KST): {date_iso}")

    # 멱등성 가드 — 하루 3회 스케줄 중 2·3회차는 여기서 no-op으로 끝난다.
    if (found := existing_image(date_iso)):
        print(f"already have today's image: {found.name} — nothing to do")
        emit(found="false", already="true", date=date_iso)
        return 0

    feeds = fetch_feeds()
    print(f"feeds={len(feeds)} latest={[f.get('createdString') for f in feeds[:5]]}")

    # 매장이 제목에 오타를 내는 사례가 있다(7/25 게시물 제목이 '9월 25일').
    # 따라서 날짜 판정은 title이 아니라 createdString으로만 한다.
    hit = next((f for f in feeds if f.get("createdString") == ymd), None)
    if hit is None:
        print(f"no post for {date_iso} (일요일/휴무 또는 아직 미게시) — 정상 종료")
        emit(found="false", already="false", date=date_iso)
        return 0

    title = (hit.get("title") or "").strip() or f"{date_iso} 메뉴"
    url = (hit.get("thumbnail") or {}).get("url")
    if not url:
        media = hit.get("media") or []
        url = media[0].get("thumbnail") if media else None
    if not url:
        print("게시물은 있으나 이미지 URL이 없음 — 정상 종료")
        emit(found="false", already="false", date=date_iso)
        return 0

    print(f"title={title}")
    print(f"image={url}")

    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if len(data) < 1024:
        raise RuntimeError(f"이미지가 너무 작음 ({len(data)} bytes)")

    ext = sniff_ext(data)
    path = MENU_DIR / f"{date_iso}.{ext}"
    path.write_bytes(data)
    print(f"saved {path.relative_to(path.parents[2])} ({len(data):,} bytes, {ext})")

    meta = DATA_DIR / f"{date_iso}.meta.json"
    meta.write_text(json.dumps({
        "date": date_iso,
        "title": title,
        "image": f"menu/{path.name}",
        "origin_image_url": url,
        "source_url": SOURCE_URL,
        "feed_id": hit.get("id"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    emit(found="true", already="false", date=date_iso,
         title=title, image_path=str(path), image_rel=f"menu/{path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
