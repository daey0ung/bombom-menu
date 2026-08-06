"""메뉴 포스터 이미지를 Claude로 읽어 구조화 JSON으로 저장한다.

'병기' 방식이라 이 단계는 부가물이다 — 페이지에는 원본 이미지가 항상 함께
실리므로, OCR이 실패하거나 일부 틀려도 파이프라인 전체를 세우지 않는다.
"""
import base64
import json
import sys

import anthropic

from common import DATA_DIR, MENU_DIR, iso, today_kst

MODEL = "claude-opus-5"

SCHEMA = {
    "type": "object",
    "properties": {
        "date": {"type": "string", "description": "포스터에 적힌 날짜, YYYY-MM-DD"},
        "weekday": {"type": "string", "description": "요일 한 글자 (월/화/수/목/금/토/일)"},
        "special": {"type": "array", "items": {"type": "string"},
                    "description": "특식(SPECIAL MENU) 항목, 적힌 순서 그대로"},
        "side": {"type": "array", "items": {"type": "string"},
                 "description": "기본찬(SIDE DISHES) 항목, 적힌 순서 그대로"},
        "dessert": {"type": "array", "items": {"type": "string"},
                    "description": "후식(DESSERT) 항목, 적힌 순서 그대로"},
        "notice": {"type": "string", "description": "하단 안내 문구. 없으면 빈 문자열"},
    },
    "required": ["date", "weekday", "special", "side", "dessert", "notice"],
    "additionalProperties": False,
}

PROMPT = """이 이미지는 한식뷔페 '봄봄'의 오늘의 메뉴 포스터입니다.
적혀 있는 글자를 그대로 옮겨 적어 주세요.

- 메뉴명은 포스터에 인쇄된 표기를 정확히 따르세요. 띄어쓰기와 '&' 기호도 그대로 두고,
  임의로 표준어로 고치거나 순서를 바꾸지 마세요.
- 특식 / 기본찬 / 후식 세 영역을 구분해 각각의 목록에 담으세요.
- 장식용 음식 사진에 붙은 글자나 로고는 메뉴 항목이 아닙니다.
- 날짜는 포스터 상단에 큰 글씨로 적힌 값을 쓰되, 연도는 {year}년으로 두세요."""


def main() -> int:
    date_iso = iso(today_kst())
    images = sorted(MENU_DIR.glob(f"{date_iso}.*"))
    if not images:
        print(f"no image for {date_iso} — skip OCR")
        return 0

    img = images[0]
    media_type = {"png": "image/png", "jpg": "image/jpeg",
                  "gif": "image/gif", "webp": "image/webp"}[img.suffix.lstrip(".")]
    b64 = base64.standard_b64encode(img.read_bytes()).decode()
    print(f"OCR {img.name} ({img.stat().st_size:,} bytes, {media_type})")

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        # Opus 5는 thinking이 기본 ON이고 max_tokens가 thinking+응답을 함께
        # 제한하므로, 짧은 JSON이라도 여유를 둔다.
        max_tokens=16000,
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": b64}},
                {"type": "text", "text": PROMPT.format(year=date_iso[:4])},
            ],
        }],
    )

    if resp.stop_reason == "refusal":
        print(f"refused: {resp.stop_details}", file=sys.stderr)
        return 1
    if resp.stop_reason == "max_tokens":
        print("truncated (max_tokens) — max_tokens를 올려야 함", file=sys.stderr)
        return 1

    text = next(b.text for b in resp.content if b.type == "text")
    menu = json.loads(text)
    menu["_model"] = MODEL

    out = DATA_DIR / f"{date_iso}.json"
    out.write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")

    u = resp.usage
    print(f"saved {out.name} | in={u.input_tokens} out={u.output_tokens} "
          f"| 특식 {len(menu['special'])} / 기본찬 {len(menu['side'])} / 후식 {len(menu['dessert'])}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        # OCR은 부가 기능 — 실패해도 이미지 게시는 계속되어야 한다.
        print(f"OCR failed ({type(e).__name__}: {e}) — 이미지만으로 계속 진행", file=sys.stderr)
        sys.exit(0)
