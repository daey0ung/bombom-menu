"""오늘의 메뉴를 Teams 채널에 Adaptive Card로 게시한다.

Power Automate 'Workflows'의 "웹후크 요청을 받으면 채널에 게시" 템플릿이 만들어 준
HTTPS URL을 TEAMS_WEBHOOK_URL 시크릿에 넣어 두면 된다. 관리자 승인이 필요 없고
브라우저 자동화도 필요 없다.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

from common import (DATA_DIR, MENU_DIR, PAGES_URL, PLACE_NAME, RAW_BASE, iso,
                    load_json, today_kst)


def text_block(t, **kw):
    return {"type": "TextBlock", "text": t, "wrap": True, **kw}


def column(heading, items):
    if not items:
        return None
    return {
        "type": "Column", "width": "stretch",
        "items": [
            text_block(heading, weight="Bolder", size="Small", color="Accent", spacing="None"),
            text_block("\n".join(f"· {i}" for i in items), size="Small", spacing="Small"),
        ],
    }


def build_card(date_iso: str, title: str, image_rel: str, menu: dict | None) -> dict:
    body = [
        text_block(PLACE_NAME, size="Small", isSubtle=True, spacing="None"),
        text_block(title, size="Large", weight="Bolder", spacing="None"),
        {"type": "Image", "url": RAW_BASE + image_rel,
         "altText": f"{title} 포스터", "size": "Stretch"},
    ]

    if menu:
        cols = [c for c in (column("특식", menu.get("special")),
                            column("기본찬", menu.get("side"))) if c]
        if cols:
            body.append({"type": "ColumnSet", "columns": cols, "spacing": "Medium"})
        if menu.get("dessert"):
            body.append(text_block("후식", weight="Bolder", size="Small",
                                   color="Accent", spacing="Medium"))
            body.append(text_block(" · ".join(menu["dessert"]), size="Small", spacing="None"))
        if menu.get("notice"):
            body.append(text_block(menu["notice"], size="Small", isSubtle=True, spacing="Medium"))

    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "contentUrl": None,
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": body,
                "actions": [{"type": "Action.OpenUrl", "title": "전체 보기", "url": PAGES_URL}],
            },
        }],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        help="시험 게시할 기존 메뉴 날짜(YYYY-MM-DD). 생략하면 오늘 날짜를 사용한다.",
    )
    args = parser.parse_args()

    url = os.environ.get("TEAMS_WEBHOOK_URL", "").strip()
    if not url:
        print("TEAMS_WEBHOOK_URL 미설정 — Teams 알림 건너뜀 (Pages 게시는 계속됨)")
        return 0

    date_iso = args.date or iso(today_kst())
    images = sorted(MENU_DIR.glob(f"{date_iso}.*"))
    if not images:
        print(f"no image for {date_iso} — 알림 없음")
        return 0

    meta = load_json(DATA_DIR / f"{date_iso}.meta.json") or {}
    payload = build_card(
        date_iso,
        meta.get("title") or f"{date_iso} 메뉴",
        f"menu/{images[0].name}",
        load_json(DATA_DIR / f"{date_iso}.json"),
    )

    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"Teams 게시 완료 (http={r.status})")
    except urllib.error.HTTPError as e:
        # 알림 실패로 게시 파이프라인 전체를 실패시키지 않는다.
        print(f"Teams 게시 실패 http={e.code}: {e.read()[:300]!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
