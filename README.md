# 봄봄 메뉴 자동 게시

봄봄 한식뷔페 구로디지털단지점의 오늘의 메뉴를 매일 자동으로 수집해
GitHub Pages에 게시하고 Teams 채널로 알린다.

- 페이지: https://lepela.github.io/bombom-menu/
- 원문 출처: [네이버 플레이스 — 봄봄 한식뷔페 구로디지털단지점](https://m.place.naver.com/restaurant/2096511528/feed)

## 동작

```
09:50 / 10:50 / 11:50 KST (월~토)
  └ fetch_menu.py  네이버 소식에서 오늘 이미지 다운로드
      └ ocr_menu.py   Claude(claude-opus-5)로 메뉴 텍스트 판독
          └ render.py     index.html / archive.html 생성
              └ commit & push → GitHub Pages
                  └ notify_teams.py  Adaptive Card 게시
```

브라우저 자동화는 쓰지 않는다. 소식 페이지 HTML에 `window.__APOLLO_STATE__`로
데이터가 임베드되어 있어 GET 한 번으로 끝난다.

**이미지와 텍스트는 병기한다.** 원본 포스터가 항상 함께 실리므로 OCR이 실패하거나
일부 틀려도 페이지는 온전하고, 판독 결과에 대한 사람 검수 단계가 필요 없다.

## 설정

| 항목 | 위치 | 비고 |
|---|---|---|
| GitHub Pages | Settings → Pages → `main` 브랜치 `/docs` | |
| `ANTHROPIC_API_KEY` | Settings → Secrets → Actions | 없으면 OCR만 생략되고 이미지 게시는 계속됨 |
| `TEAMS_WEBHOOK_URL` | Settings → Secrets → Actions | 없으면 Teams 알림만 생략됨 |

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

## 로컬 실행

```sh
pip install -r requirements.txt
python scripts/fetch_menu.py    # 오늘 이미지 수집 (이미 있으면 no-op)
python scripts/ocr_menu.py      # ANTHROPIC_API_KEY 필요
python scripts/render.py        # docs/*.html 생성
```
