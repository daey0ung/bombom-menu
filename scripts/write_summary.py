"""최신 메뉴를 사람이 읽는 텍스트와 GitHub Actions Summary로 만든다.

GH-300: GITHUB_STEP_SUMMARY는 실행 로그보다 읽기 쉬운 결과 보고 채널이다.
AB-100: 기술 출력(JSON)을 업무 사용자가 읽는 결과로 변환하는 마지막 Action이다.
"""
from __future__ import annotations

import os
from pathlib import Path

from common import DATA_DIR, DOCS, MENU_DIR, load_json


def latest_entry() -> tuple[str, dict, dict | None] | None:
    images = sorted(MENU_DIR.glob("*.*"), reverse=True)
    if not images:
        return None
    date_iso = images[0].stem
    meta = load_json(DATA_DIR / f"{date_iso}.meta.json") or {}
    menu = load_json(DATA_DIR / f"{date_iso}.json")
    return date_iso, meta, menu


def text_report(date_iso: str, meta: dict, menu: dict | None) -> str:
    title = meta.get("title") or f"{date_iso} 메뉴"
    lines = ["봄봄 한식뷔페 오늘의 메뉴", title, f"날짜: {date_iso}", ""]
    if not menu:
        lines += ["OCR 판독 결과가 없어 원본 이미지만 게시했습니다."]
    else:
        for heading, key in (("특식", "special"), ("기본찬", "side"), ("후식", "dessert")):
            lines.append(f"[{heading}]")
            lines += [f"- {item}" for item in menu.get(key, [])]
            lines.append("")
        if menu.get("notice"):
            lines += ["[안내]", menu["notice"], ""]
    lines += ["원문 이미지와 함께 확인해 주세요."]
    return "\n".join(lines).rstrip() + "\n"


def markdown_report(date_iso: str, meta: dict, menu: dict | None) -> str:
    title = meta.get("title") or f"{date_iso} 메뉴"
    lines = [f"## {title}", f"- 날짜: `{date_iso}`"]
    if not menu:
        lines.append("- OCR 결과: 실패 또는 없음 — 이미지 전용 게시")
    else:
        lines.append("- OCR 결과: 검증 통과")
        for heading, key in (("특식", "special"), ("기본찬", "side"), ("후식", "dessert")):
            lines += ["", f"### {heading}", *[f"- {item}" for item in menu.get(key, [])]]
    lines += ["", "Teams 알림은 현재 비활성화되어 있습니다."]
    return "\n".join(lines) + "\n"


def main() -> int:
    entry = latest_entry()
    if not entry:
        print("메뉴 이미지가 없어 요약을 만들지 않습니다.")
        return 0
    date_iso, meta, menu = entry
    DOCS.mkdir(parents=True, exist_ok=True)
    output = DOCS / "latest-menu.txt"
    output.write_text(text_report(date_iso, meta, menu), encoding="utf-8")
    print(f"텍스트 요약 생성: {output}")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as file:
            file.write(markdown_report(date_iso, meta, menu))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
