"""OCR 단계가 써 놓은 메뉴 JSON을 검증한다.

OCR은 Claude Code가 이미지를 직접 읽어 파일로 남기는 방식이라 스키마가
강제되지 않는다. 형식이 깨진 파일이 그대로 렌더링에 들어가지 않도록 여기서
걸러 내고, 문제가 있으면 파일을 지워 '이미지만' 경로로 되돌린다.
"""
import json
import sys

from common import DATA_DIR, iso, today_kst

LISTS = ("special", "side", "dessert")


def problems(m) -> list[str]:
    out = []
    if not isinstance(m, dict):
        return ["최상위가 객체가 아님"]

    date = m.get("date")
    if not isinstance(date, str) or len(date) != 10:
        out.append(f"date 형식 오류: {date!r}")

    if not isinstance(m.get("weekday"), str) or not m["weekday"]:
        out.append(f"weekday 누락/형식 오류: {m.get('weekday')!r}")

    for key in LISTS:
        v = m.get(key)
        if not isinstance(v, list):
            out.append(f"{key}가 배열이 아님: {type(v).__name__}")
        elif not all(isinstance(i, str) and i.strip() for i in v):
            out.append(f"{key}에 빈 값이나 문자열 아닌 항목이 있음")

    if not isinstance(m.get("notice", ""), str):
        out.append("notice가 문자열이 아님")

    # 세 목록이 모두 비면 판독에 실패한 것이다 (원본 포스터엔 항상 특식이 있다).
    if all(isinstance(m.get(k), list) and not m[k] for k in LISTS):
        out.append("특식/기본찬/후식이 모두 비어 있음")

    return out


def main() -> int:
    date_iso = iso(today_kst())
    path = DATA_DIR / f"{date_iso}.json"

    if not path.exists():
        print(f"{path.name} 없음 - 이미지만으로 게시 (OCR 생략됨)")
        return 0

    try:
        menu = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"{path.name} JSON 파싱 실패 ({e}) - 파일 삭제 후 이미지만으로 게시")
        path.unlink()
        return 0

    if (errs := problems(menu)):
        print(f"{path.name} 검증 실패 - 파일 삭제 후 이미지만으로 게시")
        for e in errs:
            print(f"  - {e}")
        path.unlink()
        return 0

    # 날짜가 어긋나면 다른 날 포스터를 읽은 것이므로 오늘 날짜로 바로잡는다.
    if menu["date"] != date_iso:
        print(f"date 불일치: {menu['date']} -> {date_iso} 로 교정")
        menu["date"] = date_iso

    # 렌더러가 기대하는 키를 채워 둔다.
    menu.setdefault("notice", "")
    path.write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"{path.name} 검증 통과 - "
          f"특식 {len(menu['special'])} / 기본찬 {len(menu['side'])} / 후식 {len(menu['dessert'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
