# 봄봄 메뉴 자동 게시

봄봄 한식뷔페 구로디지털단지점의 오늘의 메뉴를 매일 자동으로 수집해
GitHub Pages에 게시하고 Teams 채널로 알린다.

- 페이지: https://lepela.github.io/bombom-menu/
- 원문 출처: [네이버 플레이스 — 봄봄 한식뷔페 구로디지털단지점](https://m.place.naver.com/restaurant/2096511528/feed)

## 동작

```
09:50 / 10:50 / 11:50 KST (월~토)
  └ fetch_menu.py      네이버 소식에서 오늘 이미지 다운로드
      └ claude-code-action  이미지를 읽어 메뉴 JSON 작성 (구독 인증)
          └ validate_menu.py    JSON 스키마 검증, 깨졌으면 폐기
              └ render.py       index.html / archive.html 생성
                  └ commit & push → GitHub Pages
                      └ notify_teams.py  Adaptive Card 게시
```

파이썬 스크립트는 표준 라이브러리만 쓴다. 설치할 의존성이 없다.

브라우저 자동화는 쓰지 않는다. 소식 페이지 HTML에 `window.__APOLLO_STATE__`로
데이터가 임베드되어 있어 GET 한 번으로 끝난다.

**이미지와 텍스트는 병기한다.** 원본 포스터가 항상 함께 실리므로 OCR이 실패하거나
일부 틀려도 페이지는 온전하고, 판독 결과에 대한 사람 검수 단계가 필요 없다.

## 설정

둘 다 **Repository secret** 이다 (Settings → Secrets and variables → Actions →
Repository secrets). Environment secret 쪽에 넣으면 job이 읽지 못한다.

| 항목 | 값을 얻는 법 | 없을 때 |
|---|---|---|
| GitHub Pages | Settings → Pages → `main` 브랜치 `/docs` | 게시 안 됨 |
| `CLAUDE_CODE_OAUTH_TOKEN` | 터미널에서 `claude setup-token` | OCR만 생략, 이미지 게시는 계속 |
| `TEAMS_WEBHOOK_URL` | 아래 참고 | Teams 알림만 생략, Pages 게시는 계속 |

**OCR은 Claude 구독으로 돌린다.** `claude setup-token`으로 발급한 OAuth 토큰을 쓰면
API 크레딧이 아니라 구독 한도에서 차감된다 (Pro/Max/Team/Enterprise). 토큰은 발급한
사람의 구독에 묶이므로 조직 공유 용도로는 맞지 않는다. `ANTHROPIC_API_KEY`는 쓰지 않는다.

Teams 웹훅은 대상 채널 → `⋯` → **워크플로(Workflows)** →
"웹후크 요청을 받으면 채널에 게시" 템플릿으로 만든다. 관리자 승인이 필요 없다.

## 구현상 주의점

수집 대상 페이지의 실제 동작에서 확인한 것들이라, 손대기 전에 읽어 두는 게 좋다.

- **날짜 판정은 `createdString`으로만 한다.** 매장이 제목에 오타를 내는 일이 있다
  (7/25 게시물 제목이 "9월 25일"로 적혀 있었다). `title`은 표시용이다.
- **User-Agent 헤더가 필수다.** 없이 요청하면 HTTP 429로 막힌다.
- **확장자를 믿지 않는다.** URL은 `.jpg`인데 실제 바이트는 PNG인 경우가 있어
  매직 바이트로 판정한다.
- **날짜는 KST로 계산한다.** 러너는 UTC로 돈다.
- **게시물이 없는 날은 실패가 아니다.** 일요일 휴무와 미게시를 정상 종료로 처리한다.
- `robots.txt`가 `Disallow: /`이므로 요청은 하루 1회로 제한하고, 페이지에 출처를
  명시한다. 사내 참고용 이상으로 쓰지 않는다.

- **OCR 결과는 신뢰하지 말고 검증한다.** Claude가 파일로 직접 쓰는 방식이라 스키마가
  강제되지 않는다. `validate_menu.py`가 형식을 확인하고, 깨졌으면 파일을 지워
  '이미지만' 경로로 되돌린다.

## 로컬 실행

```sh
python scripts/fetch_menu.py    # 오늘 이미지 수집 (이미 있으면 no-op)
python scripts/render.py        # docs/*.html 생성
```

OCR은 GitHub Actions에서 `claude-code-action`이 담당한다. 로컬에서 붙이고 싶으면
Claude Code로 `docs/menu/<날짜>.png`를 읽어 `docs/data/<날짜>.json`을 쓰게 한 뒤
`python scripts/validate_menu.py`를 돌리면 된다.
