"""기존 이미지/정답 JSON으로 무료 OCR 정확도를 측정하는 회귀 테스트."""
from __future__ import annotations

import argparse
import difflib
import json
import re
from pathlib import Path

from ocr_menu import menu_from_image


def normalized(value: str) -> str:
    return re.sub(r"\s+", "", value).lower()


def compare(expected: list[str], actual: list[str]) -> tuple[int, int, list[str]]:
    actual_norm = {normalized(item) for item in actual}
    matched = sum(normalized(item) in actual_norm for item in expected)
    missing = [item for item in expected if normalized(item) not in actual_norm]
    return matched, len(expected), missing


def closest(expected: str, actual: list[str]) -> str:
    if not actual:
        return "(인식 결과 없음)"
    return max(actual, key=lambda item: difflib.SequenceMatcher(
        None, normalized(expected), normalized(item)
    ).ratio())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--menu-dir", type=Path, default=Path("docs/menu"))
    parser.add_argument("--data-dir", type=Path, default=Path("docs/data"))
    args = parser.parse_args()

    total_match = total_expected = 0
    for image in sorted(args.menu_dir.glob("*.*")):
        gold_path = args.data_dir / f"{image.stem}.json"
        if not gold_path.exists():
            continue
        expected = json.loads(gold_path.read_text(encoding="utf-8"))
        actual, _ = menu_from_image(image, image.stem)
        print(f"\n[{image.name}]")
        for key in ("special", "side", "dessert"):
            matched, count, missing = compare(expected[key], actual[key])
            total_match += matched
            total_expected += count
            print(f"  {key}: {matched}/{count}")
            for item in missing:
                print(f"    정답: {item}")
                print(f"    OCR : {closest(item, actual[key])}")
    rate = 100 * total_match / total_expected if total_expected else 0
    print(f"\n전체 정확 일치율: {total_match}/{total_expected} ({rate:.1f}%)")
    return 0 if total_expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
