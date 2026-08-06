"""docs/ 안의 이미지와 OCR JSON으로 index.html / archive.html 을 만든다.

OCR JSON이 없어도 이미지만으로 온전한 페이지가 나오도록 설계했다.
"""
import html
import sys

from common import (DATA_DIR, DOCS, MENU_DIR, PLACE_NAME, SOURCE_URL,
                    load_json)

CSS = """
*,*::before,*::after{box-sizing:border-box}
:root{
  --bg:#faf8f3; --card:#fff; --ink:#2b2724; --muted:#7a726a;
  --line:#e6dfd4; --accent:#9a5b2f; --chip:#f2ece2;
}
:root[data-theme=dark]{
  --bg:#17150f; --card:#211e18; --ink:#ece6dc; --muted:#a49a8d;
  --line:#332e26; --accent:#e0a468; --chip:#2a251d;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme=light]){
    --bg:#17150f; --card:#211e18; --ink:#ece6dc; --muted:#a49a8d;
    --line:#332e26; --accent:#e0a468; --chip:#2a251d;
  }
}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Pretendard","Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif;
  line-height:1.6;-webkit-text-size-adjust:100%}
.wrap{max-width:760px;margin:0 auto;padding:24px 16px 56px}
header{text-align:center;margin-bottom:20px}
.place{font-size:.82rem;letter-spacing:.14em;color:var(--muted);text-transform:uppercase}
h1{font-size:1.6rem;margin:.35em 0 .1em;font-weight:700}
.sub{color:var(--muted);font-size:.87rem;margin:0}
.poster{display:block;width:100%;height:auto;border-radius:14px;
  border:1px solid var(--line);margin:22px 0}
.cols{display:grid;gap:14px;grid-template-columns:1fr}
@media (min-width:620px){.cols{grid-template-columns:1fr 1fr}
  .cols .full{grid-column:1/-1}}
section.card{background:var(--card);border:1px solid var(--line);
  border-radius:14px;padding:16px 18px}
section.card h2{margin:0 0 10px;font-size:.78rem;letter-spacing:.16em;
  color:var(--accent);text-transform:uppercase;font-weight:700}
ul{list-style:none;margin:0;padding:0}
li{padding:5px 0;border-bottom:1px dashed var(--line);font-size:.97rem}
li:last-child{border-bottom:0}
.notice{margin-top:16px;padding:12px 16px;background:var(--chip);
  border-radius:12px;color:var(--muted);font-size:.85rem;white-space:pre-line}
footer{margin-top:28px;text-align:center;color:var(--muted);font-size:.8rem}
footer a{color:var(--accent)}
.nav{margin:18px 0 0;text-align:center}
.nav a{display:inline-block;padding:8px 16px;border:1px solid var(--line);
  border-radius:999px;color:var(--accent);text-decoration:none;font-size:.86rem;
  background:var(--card)}
.arch{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));
  margin-top:20px;padding:0;list-style:none}
.arch li{border:0;padding:0}
.arch a{display:block;text-decoration:none;color:inherit;background:var(--card);
  border:1px solid var(--line);border-radius:12px;overflow:hidden}
.arch img{display:block;width:100%;height:auto}
.arch span{display:block;padding:8px 10px;font-size:.84rem}
"""

THEME_JS = """
(function(){var s=localStorage.getItem('bombom-theme');
if(s)document.documentElement.setAttribute('data-theme',s);})();
"""


def esc(s) -> str:
    return html.escape(str(s or ""))


def page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
<script>{THEME_JS}</script>
</head>
<body><div class="wrap">
{body}
<footer>
  <p>메뉴 정보 출처 · <a href="{SOURCE_URL}" rel="noopener">네이버 플레이스 — {esc(PLACE_NAME)}</a></p>
  <p>이미지 저작권은 매장에 있습니다. 사내 참고용으로만 사용해 주세요.</p>
</footer>
</div></body></html>
"""


def menu_list(heading: str, items, full=False) -> str:
    if not items:
        return ""
    lis = "\n".join(f"    <li>{esc(i)}</li>" for i in items)
    cls = "card full" if full else "card"
    return f'  <section class="{cls}">\n    <h2>{esc(heading)}</h2>\n    <ul>\n{lis}\n    </ul>\n  </section>'


def entries() -> list[dict]:
    """날짜 역순. 이미지가 있는 날짜만."""
    out = []
    for img in sorted(MENU_DIR.glob("*.*"), reverse=True):
        date = img.stem
        if len(date) != 10:
            continue
        meta = load_json(DATA_DIR / f"{date}.meta.json") or {}
        menu = load_json(DATA_DIR / f"{date}.json")
        out.append({
            "date": date,
            "image": f"menu/{img.name}",
            "title": meta.get("title") or date,
            "menu": menu,
        })
    return out


def render_index(e: dict) -> str:
    m = e["menu"]
    body = [
        "<header>",
        f'  <p class="place">{esc(PLACE_NAME)}</p>',
        f"  <h1>{esc(e['title'])}</h1>",
        f'  <p class="sub">{esc(e["date"])}</p>',
        "</header>",
        f'<img class="poster" src="{esc(e["image"])}" alt="{esc(e["title"])} 포스터">',
    ]
    if m:
        cols = [
            menu_list("특식 · Special", m.get("special")),
            menu_list("기본찬 · Side", m.get("side")),
            menu_list("후식 · Dessert", m.get("dessert"), full=True),
        ]
        body.append('<div class="cols">')
        body += [c for c in cols if c]
        body.append("</div>")
        if m.get("notice"):
            body.append(f'<p class="notice">{esc(m["notice"])}</p>')
        body.append('<p class="notice">텍스트는 위 포스터를 자동 판독한 것입니다. '
                    '차이가 있으면 포스터 원본이 기준입니다.</p>')
    else:
        body.append('<p class="notice">텍스트 판독 결과가 없습니다. 위 포스터를 확인해 주세요.</p>')
    body.append('<p class="nav"><a href="archive.html">지난 메뉴 보기 &rsaquo;</a></p>')
    return page(f"{e['title']} · {PLACE_NAME}", "\n".join(body))


def render_archive(es: list[dict]) -> str:
    items = "\n".join(
        f'  <li><a href="{esc(e["image"])}"><img src="{esc(e["image"])}" alt="" loading="lazy">'
        f'<span>{esc(e["title"])}</span></a></li>'
        for e in es
    )
    body = (
        "<header>\n"
        f'  <p class="place">{esc(PLACE_NAME)}</p>\n'
        "  <h1>지난 메뉴</h1>\n"
        f'  <p class="sub">총 {len(es)}일</p>\n'
        "</header>\n"
        f'<ul class="arch">\n{items}\n</ul>\n'
        '<p class="nav"><a href="index.html">&lsaquo; 오늘의 메뉴</a></p>'
    )
    return page(f"지난 메뉴 · {PLACE_NAME}", body)


def main() -> int:
    es = entries()
    if not es:
        print("no menu images yet — nothing to render")
        return 0
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "index.html").write_text(render_index(es[0]), encoding="utf-8")
    (DOCS / "archive.html").write_text(render_archive(es), encoding="utf-8")
    (DOCS / ".nojekyll").write_text("", encoding="utf-8")
    print(f"rendered index.html (latest={es[0]['date']}, ocr={'yes' if es[0]['menu'] else 'no'}) "
          f"and archive.html ({len(es)} days)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
