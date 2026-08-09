"""PaddleOCR로 봄봄 포스터를 읽고 기존 메뉴 JSON 형식으로 변환한다.

학습 포인트
-----------
AI-103: OCR은 컴퓨터 비전의 '텍스트 인식' 단계다. 모델 출력에는 글자뿐 아니라
좌표와 신뢰도(score)가 있으므로, 임계값과 업무 규칙으로 후처리해야 한다.
AB-100: 모델을 무조건 신뢰하지 않고 검증 실패 시 이미지 전용 경로로 전환한다.
이는 자동화의 Condition과 fallback을 명시적으로 설계한 예다.

이 스크립트는 외부 AI API를 호출하지 않는다. 최초 실행 때 공개 PaddleOCR 모델을
다운로드한 뒤 로컬 CPU에서 추론한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


MIN_SCORE = 0.55
WEEKDAYS = "월화수목금토일"

# 기존 포스터 회귀 테스트에서 확인된 '메뉴 단어 전체'만 보정한다. 임의의 한 글자를
# 전역 치환하면 새 메뉴를 훼손할 수 있으므로 정확히 일치하는 항목만 다룬다.
KNOWN_OCR_CORRECTIONS = {
    "백미밥& 혹미밥": "백미밥 & 흑미밥",
    "백미밥&혹미밥": "백미밥 & 흑미밥",
    "혹임자 연근 무침": "흑임자 연근 무침",
    "양념깨잎": "양념 깻잎",
    "간장 깨잎": "간장 깻잎",
    "식빵 & 사과쟁": "식빵 & 사과잼",
    "식빵& 사과쟁": "식빵 & 사과잼",
    "식빵&사과샘": "식빵 & 사과잼",
    "마늘쫓 볶음밥": "마늘쫑 볶음밥",
    "마늘쪽 볶음밥": "마늘쫑 볶음밥",
    "청포목 무침": "청포묵 무침",
    "청포목무침": "청포묵 무침",
    "야채 동그랑맹&케첩": "야채 동그랑땡 & 케첩",
}


@dataclass(frozen=True)
class TextBox:
    text: str
    score: float
    x: float
    y: float
    width: float
    height: float


def _result_dict(result) -> dict:
    """PaddleOCR 3.x 결과 객체를 버전 차이에 안전하게 dict로 바꾼다."""
    payload = getattr(result, "json", result)
    if callable(payload):
        payload = payload()
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, dict) and isinstance(payload.get("res"), dict):
        payload = payload["res"]
    if not isinstance(payload, dict):
        raise TypeError(f"지원하지 않는 PaddleOCR 결과 형식: {type(payload).__name__}")
    return payload


def recognize(image: Path) -> tuple[list[TextBox], int, int]:
    try:
        from paddleocr import PaddleOCR
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "PaddleOCR가 설치되지 않았습니다. README의 설치 절차를 먼저 실행하세요."
        ) from exc

    width, height = Image.open(image).size
    # 포스터는 회전·왜곡된 문서가 아니므로 불필요한 모델 세 개를 끈다.
    # 필요한 기능만 배포하면 실행 시간과 장애 지점이 줄어든다(AI-103 운영 관점).
    ocr = PaddleOCR(
        text_detection_model_name=os.environ.get(
            "PADDLE_OCR_DET_MODEL", "PP-OCRv5_mobile_det"
        ),
        text_recognition_model_name=os.environ.get(
            "PADDLE_OCR_REC_MODEL", "korean_PP-OCRv5_mobile_rec"
        ),
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        engine="paddle",
    )
    results = list(ocr.predict(str(image)))
    if not results:
        raise RuntimeError("PaddleOCR 결과가 비어 있습니다.")
    raw = _result_dict(results[0])

    texts = raw.get("rec_texts") or []
    scores = raw.get("rec_scores") or []
    boxes = raw.get("rec_boxes") or raw.get("dt_boxes") or []
    found: list[TextBox] = []
    for text, score, box in zip(texts, scores, boxes):
        text = str(text).strip()
        score = float(score)
        if not text or score < MIN_SCORE:
            continue
        if len(box) == 4 and not isinstance(box[0], (list, tuple)):
            x1, y1, x2, y2 = map(float, box)
        else:
            xs = [float(point[0]) for point in box]
            ys = [float(point[1]) for point in box]
            x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
        found.append(TextBox(text, score, (x1 + x2) / 2, (y1 + y2) / 2,
                             x2 - x1, y2 - y1))
    return sorted(found, key=lambda item: (item.y, item.x)), width, height


def _is_heading(text: str) -> bool:
    compact = re.sub(r"[\s·ㆍ.]+", "", text).upper()
    return any(word in compact for word in (
        "SPECIALMENU", "SIDEDISHES", "DESSERT", "특식", "기본찬", "후식"
    ))


def _is_decorative(text: str) -> bool:
    compact = re.sub(r"\s+", "", text)
    return compact in {
        "봄봄", "신선한재료", "건강한밥상", "정성가득", "당신을위한정성스런식탁",
        "매일신선한재료로정성껏준비한오늘의한상",
    }


def correct_known_menu(text: str) -> str:
    """검증 자료로 확인한 제한적 OCR 오타만 안전하게 교정한다."""
    return KNOWN_OCR_CORRECTIONS.get(text, text)


def classify(boxes: list[TextBox], width: int, height: int) -> dict[str, list[str] | str]:
    """현재 봄봄 포스터 템플릿의 상대 좌표로 OCR 줄을 업무 항목에 배치한다."""
    sections: dict[str, list[str]] = {"special": [], "side": [], "dessert": []}
    notice: list[str] = []
    for box in boxes:
        if _is_heading(box.text) or _is_decorative(box.text):
            continue
        nx, ny = box.x / width, box.y / height

        # 상단 날짜/슬로건을 제외하고, 중앙선 기준으로 두 열을 나눈다.
        if 0.30 <= ny <= 0.77 and nx < 0.50:
            sections["special"].append(correct_known_menu(box.text))
        elif 0.30 <= ny < 0.66 and nx >= 0.50:
            sections["side"].append(correct_known_menu(box.text))
        elif 0.69 <= ny <= 0.84 and nx >= 0.50:
            sections["dessert"].append(correct_known_menu(box.text))
        elif ny >= 0.86 and 0.18 <= nx <= 0.78:
            notice.append(box.text)

    return {**sections, "notice": " ".join(notice)}


def menu_from_image(image: Path, date_iso: str) -> tuple[dict, list[TextBox]]:
    boxes, width, height = recognize(image)
    parsed = classify(boxes, width, height)
    parsed["date"] = date_iso
    parsed["weekday"] = WEEKDAYS[date.fromisoformat(date_iso).weekday()]
    # 기존 JSON 키 순서를 유지해 diff와 사람 검수를 쉽게 한다.
    menu = {
        "date": parsed["date"],
        "weekday": parsed["weekday"],
        "special": parsed["special"],
        "side": parsed["side"],
        "dessert": parsed["dessert"],
        "notice": parsed["notice"],
    }
    return menu, boxes


def main() -> int:
    parser = argparse.ArgumentParser(description="봄봄 메뉴 포스터 무료 OCR")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--date", required=True, dest="date_iso")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--debug-output", type=Path,
                        help="좌표/신뢰도 디버그 JSON(선택)")
    args = parser.parse_args()

    # 로컬/Actions 어느 환경에서도 캐시 위치를 명시할 수 있게 한다.
    os.environ.setdefault("PADDLE_PDX_CACHE_HOME", str(Path.home() / ".paddlex"))
    # Hugging Face 연결이 느린 환경을 위한 Paddle 공식 모델 저장소다.
    os.environ.setdefault("PADDLE_PDX_MODEL_SOURCE", "BOS")
    menu, boxes = menu_from_image(args.image, args.date_iso)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    temp.write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(args.output)

    if args.debug_output:
        args.debug_output.parent.mkdir(parents=True, exist_ok=True)
        args.debug_output.write_text(json.dumps(
            [box.__dict__ for box in boxes], ensure_ascii=False, indent=2
        ), encoding="utf-8")
    print(f"OCR JSON 생성: {args.output} (인식 줄 {len(boxes)}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
