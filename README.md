# 봄봄 메뉴 수동 게시 — 무료 PaddleOCR 버전

봄봄 한식뷔페 구로디지털단지점의 메뉴 이미지를 네이버 플레이스에서 받아
무료 로컬 OCR로 판독하고 GitHub에 게시한다.

- 원문: [네이버 플레이스](https://m.place.naver.com/restaurant/2096511528/feed)
- 결과: `docs/index.html`, `docs/archive.html`, `docs/latest-menu.txt`
- 비용: 외부 AI API를 호출하지 않는다. 공개 저장소의 표준 GitHub-hosted runner는
  GitHub 정책상 무료다.
- Teams: 현재 완전히 비활성화되어 있다.

## 실행 흐름

Power Automate 용어와 나란히 보면 다음과 같다.

| 프로젝트 단계 | Power Automate | 역할 |
|---|---|---|
| `workflow_dispatch` | Trigger | 사용자가 Run workflow를 눌러 시작 |
| `fetch_menu.py` | HTTP Action | 오늘 네이버 이미지 수집 |
| `ocr_menu.py` | AI/Computer Vision Action | 로컬 PaddleOCR로 글자와 좌표 인식 |
| `validate_menu.py` | Condition | JSON이 안전한 형식인지 검사 |
| `render.py` | Create file Action | HTML 생성 |
| `write_summary.py` | Compose Action | 텍스트와 Actions Summary 생성 |
| `git push` | Update file Action | 선택한 브랜치에 결과 저장 |

```text
Run workflow
  -> 오늘 이미지 확인
  -> PaddleOCR(로컬 CPU, API Key 없음)
  -> 좌표로 특식/기본찬/후식 분류
  -> JSON 검증
     -> 성공: 이미지 + 메뉴 텍스트
     -> 실패: 이미지 전용 fallback
  -> HTML + docs/latest-menu.txt + Actions Summary
  -> 현재 선택한 브랜치에 push
```

자동 `schedule`은 없다. 같은 날짜 이미지를 이미 가지고 있으면 중복 실행 방지 로직이
정상 종료한다.

## GitHub에서 수동 실행

1. 저장소의 **Actions** 탭을 연다.
2. **daily-menu-manual** 워크플로를 선택한다.
3. **Run workflow**를 누른다.
4. 테스트 중에는 `codex/dy_modify01` 브랜치를 선택한다.
5. 실행 후 **Summary** 또는 `docs/latest-menu.txt`를 확인한다.

`workflow_dispatch` 버튼이 보이려면 해당 워크플로가 기본 브랜치에도 존재해야 한다.
이 프로젝트는 기존 워크플로에 이미 수동 Trigger가 있었다.

## 로컬 설치와 회귀 테스트

Python 3.12 기준 CPU 버전이다. 가상환경 사용을 권장한다.

```powershell
python -m venv .venv-paddleocr
.\.venv-paddleocr\Scripts\Activate.ps1
python -m pip install paddlepaddle==3.2.0 `
  -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
python -m pip install -r requirements-ocr.txt
```

기존 이미지 세 장을 정답 JSON과 비교한다.

```powershell
$env:PADDLE_PDX_MODEL_SOURCE = "BOS"
python scripts/evaluate_ocr.py
```

최초 실행은 공개 OCR 모델을 다운로드하므로 오래 걸린다. GitHub Actions에서는 모델
디렉터리를 캐시해 다음 실행부터 재사용한다.

## OCR 설계와 한계

- `PP-OCRv5_mobile_det`: 실행 시간을 줄인 경량 글자 검출 모델
- `korean_PP-OCRv5_mobile_rec`: 검출된 줄의 한글을 읽는 경량 인식 모델
- 신뢰도 0.55 미만 결과는 버린다.
- 포스터 상대 좌표로 왼쪽 특식, 오른쪽 기본찬/후식을 구분한다.
- 기존 이미지에서 반복 확인된 메뉴 단어의 오인식만 제한적으로 교정한다.
- 모르는 단어를 추측하지 않는다. 결과가 이상하면 원본 이미지가 최종 기준이다.

서버 검출 모델도 비교했지만 기존 이미지 3장에 5분 이상 걸려 기본값에서 제외했다.
모바일 모델은 훨씬 빠르지만 일부 긴 메뉴 줄의 앞뒤 단어를 놓칠 수 있다.

새 포스터 디자인이 나오면 `scripts/ocr_menu.py`의 `classify()` 상대 좌표를 조정해야
한다. 무료 OCR은 생성형 AI처럼 문맥을 이해하지 않으므로 사람 확인이 권장된다.

## 실패 안전 설계

OCR 단계는 `continue-on-error: true`다. OCR 패키지 오류, 모델 다운로드 오류 또는
판독 오류가 나도 다음 단계로 간다. `validate_menu.py`는 깨진 JSON을 제거하고,
`render.py`는 JSON이 없으면 원본 이미지만 포함한 페이지를 만든다.

따라서 OCR 실패가 이미지 게시 실패로 번지지 않는다.

## Secret과 Teams

현재 필요한 외부 AI Secret은 없다.

- `CLAUDE_CODE_OAUTH_TOKEN`: 사용하지 않음
- `OPENAI_API_KEY`: 사용하지 않음
- `TEAMS_WEBHOOK_URL`: 사용하지 않음

워크플로에는 Teams Action이 없다. 테스트가 끝난 뒤 Teams를 추가할 때는 별도 변경으로
다루고, 웹후크 URL은 반드시 Repository Secret에 저장해야 한다.

## 자격증 학습

코드와 워크플로의 `GH-300`, `AI-103`, `AB-100` 주석은 각 개념이 실제 자동화에서
어디에 나타나는지 표시한다. 자세한 매핑은 [docs/cert-study.md](docs/cert-study.md)를
참고한다.
