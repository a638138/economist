# -*- coding: utf-8 -*-
"""
build_site.py — 從 2026/繁中版/*.html 產生可上傳 GitHub Pages 的靜態網站。

本檔位於網站 repo 的 tools/ 內（本機專案根目錄的 build_site.py 只是轉呼叫本檔），
所以手機端 Claude Code / GitHub Action 在 repo 裡也能重建筆記頁。

用法:  python build_site.py                      本機完整重建（會先 git pull 取得手機端新增的筆記）
       python tools/build_site.py --notes-only   只重建筆記頁（repo 內即可執行，不需雜誌原始檔）

輸出到 web/（即本 repo）：
  web/index.html          目錄首頁（封面卡牌牆）
  web/issues/2026-01-03.html ...  各期複本（英數檔名）
  web/covers/2026-01-03.jpg ...   各期封面縮圖（從 HTML 內嵌圖抽出）
  web/notes/index.html    個人筆記目錄（來源：web/notes_src/<分類>/*.html）
  web/.nojekyll           避免 GitHub Pages 用 Jekyll 處理

原始檔（2026/繁中版、notes_src/）完全不會被修改。
"""
import argparse
import base64
import hashlib
import json
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path
from html import escape, unescape
from urllib.parse import quote

OUT = Path(__file__).resolve().parents[1]     # 網站 repo（本機為 01_economist/web）
ROOT = OUT.parent                             # 本機專案根目錄（雲端上不存在雜誌原始檔）
SRC = ROOT / "2026" / "繁中版"
ISSUES = OUT / "issues"
COVERS = OUT / "covers"
ASSETS = OUT / "assets"

# 額外分頁：把其他專案的「自包含靜態網頁」併入本站當一個分頁。
# src 找得到就複製更新；找不到則保留 web/<slug>/ 既有複本（分頁仍會顯示）。
EXTRA_PAGES = [
    {"slug": "ai", "label": "AI 教材",
     "src": (ROOT.parents[2] / "code" / "ai_agent" / "機台AI教材_完整包"
             / "tutorials" / "dist" / "AI應用系統教材.html")
            if len(ROOT.parents) > 2 else None},
]

# 個人筆記分頁：notes_src/<分類資料夾>/*.html → web/notes/index.html。
# 新增筆記只要把自包含 HTML 丟進分類資料夾再重跑本腳本（規格見 repo 的 CLAUDE.md）。
NOTES_SRC = OUT / "notes_src"
NOTES = OUT / "notes"
NOTES_LABEL = "筆記"
NOTE_DATE_RE = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
TITLE_RE = re.compile(r"<title>(.*?)</title>", re.S | re.I)
# 第一張內嵌圖 = 雜誌封面（960x1281 直式）
COVER_RE = re.compile(r'<img[^>]*src="data:image/([a-zA-Z]+);base64,([^"]+)"')

EXT = {"jpeg": "jpg", "jpg": "jpg", "png": "png", "webp": "webp", "gif": "gif"}

# 主題（背景色）— 首頁與各期共用。頁面本來就用 --bg/--ink/--card/--line/--grey 變數，
# 切換主題只要覆寫這些變數即可。夜間再補幾個硬碼色的修正。
THEME_CSS = """<style>
html[data-theme="sepia"]{--bg:#f4ecd8;--ink:#3f342a;--card:#faf3e3;--line:#e3d7bd;--grey:#8a7a60}
html[data-theme="grey"]{--bg:#e9eaec;--ink:#1c1e21;--card:#f7f8fa;--line:#d4d7dc;--grey:#6b7078}
html[data-theme="dark"]{--bg:#15171a;--ink:#e4e1db;--card:#1e2126;--line:#333840;--grey:#9aa0a6}
html[data-theme="dark"] .note{background:#241a19;color:#d8cbc9}
html[data-theme="dark"] p.title-en{color:#8f8b85}
html[data-theme="dark"] h3.rubric{color:#b8b3ab}
html[data-theme="dark"] .card{background:var(--card)}
html[data-theme="dark"] img.cover{opacity:.94}
html{transition:background-color .2s}
</style>"""

# 進頁時最先執行：套用已存的背景色，避免先閃白再變色（FOUC）
EARLY_THEME = ('<script>try{var s=JSON.parse(localStorage.getItem("econ.settings")'
               '||"{}");if(s.theme&&s.theme!=="light")document.documentElement'
               '.setAttribute("data-theme",s.theme);}catch(e){}</script>')

# 注入到各期閱讀頁 <head> 的手機優化樣式（原始檔不動，只改 web/issues 複本）
MOBILE_STYLE = """<meta name="theme-color" content="#e3120b"/>
<style>
/* build_site.py 注入：小手機閱讀優化 */
html{-webkit-text-size-adjust:100%}
img,figure,table,pre{max-width:100%!important;height:auto}
p,li,h1,h2,h3{overflow-wrap:break-word;word-break:break-word}
#econ-progress{position:fixed;top:0;left:0;height:3px;width:0;background:var(--red);z-index:60;transition:width .1s}
@media(max-width:480px){
 body{font-size:16.5px;line-height:1.8}
 .wrap{padding:0 12px 84px}
 .cover{padding:22px 0 14px}
 .cover img{max-width:76vw}
 .masthead{max-width:90vw!important;margin-bottom:18px!important}
 .issue{font-size:16px}
 .note{padding:12px 14px;font-size:15px}
 h2.section-head{font-size:22px;margin:44px 0 16px}
 nav.toc{padding:16px 14px}
 nav.toc h3{font-size:19px}
 nav.toc a{font-size:16px}
 article.art{padding:20px 15px 24px;border-radius:8px}
 h1.title{font-size:23px;line-height:1.3}
 h3.rubric{font-size:17px}
 article.art h2{font-size:20px}
 article.art p{text-align:left}       /* 窄螢幕改左對齊，避免中英混排撐開字距 */
}
</style>"""


def pwa_head(prefix: str) -> str:
    """可加到主畫面當 App（全螢幕）的 <head> 標籤。prefix 為到站根的相對路徑。"""
    return (
        f'<link rel="manifest" href="{prefix}manifest.webmanifest"/>'
        '<meta name="mobile-web-app-capable" content="yes"/>'
        '<meta name="apple-mobile-web-app-capable" content="yes"/>'
        '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"/>'
        '<meta name="apple-mobile-web-app-title" content="Economist 中文"/>'
        f'<link rel="apple-touch-icon" href="{prefix}assets/icon-180.png"/>'
        f'<link rel="icon" type="image/png" sizes="192x192" href="{prefix}assets/icon-192.png"/>'
    )


def inject_extra_back(text: str, label: str = "← 雜誌目錄") -> str:
    """給併入的外部網頁加一個固定返回鈕，連到上一層 index.html（不改其原有版面）。"""
    # 放右下角：避開 AI 頁右上的「下一頁」pager 與左下的選單鈕
    head = ('<meta name="theme-color" content="#0f6f5c"/>'
            '<style>#econ-back{position:fixed;right:14px;bottom:14px;z-index:99999;'
            'padding:9px 15px;border-radius:999px;background:#0f6f5c;color:#fff;'
            'text-decoration:none;font:600 14px/1 "Noto Sans TC",system-ui,sans-serif;'
            'box-shadow:0 3px 12px rgba(0,0,0,.28);-webkit-tap-highlight-color:transparent}</style>')
    back = f'<a id="econ-back" href="../index.html">{label}</a>'
    if "</head>" in text:
        text = text.replace("</head>", head + "</head>", 1)
    if "</body>" in text:
        text = text.replace("</body>", back + "</body>", 1)
    else:
        text += back
    return text


def inject_mobile(text: str, slug: str) -> str:
    """注入：主題、手機樣式、PWA、閱讀器腳本（設定/進度/全螢幕，原始檔不動）。"""
    head = (EARLY_THEME + THEME_CSS + MOBILE_STYLE + pwa_head("../")
            + f'<script>window.__ISSUE__="{slug}";</script>'
            + '<script defer src="../assets/reader.js"></script>\n')
    return text.replace("</head>", head + "</head>", 1)


def tabs_html(active: str, prefix: str) -> str:
    """分頁列。active 為目前頁的 slug（"" = 雜誌首頁）；prefix 為到站根的相對路徑。"""
    pages = [("", "雜誌")] + [(p["slug"], p["label"]) for p in EXTRA_PAGES]
    if NOTES_SRC.exists() or (NOTES / "index.html").exists():
        pages.append(("notes", NOTES_LABEL))
    tabs = []
    for slug, label in pages:
        href = f"{prefix}{slug}/" if slug else (prefix or "./")
        cls = "tab on" if slug == active else "tab"
        tabs.append(f'<a class="{cls}" href="{href}">{escape(label)}</a>')
    return f'<nav class="tabs">{"".join(tabs)}</nav>'


def build_notes():
    """notes_src/<分類>/*.html → web/notes/index.html：仿「AI 教材」的側欄＋單篇閱讀版面。"""
    if not NOTES_SRC.exists():
        if (NOTES / "index.html").exists():
            print(f"筆記來源不存在，沿用現有：{NOTES}")
        return
    if NOTES.exists():
        shutil.rmtree(NOTES)        # 整個重建，來源刪掉的筆記網站上也會消失
    NOTES.mkdir(parents=True)
    nav, days, n = [], [], 0
    for group in sorted(d for d in NOTES_SRC.iterdir() if d.is_dir()):
        files = sorted(group.glob("*.html"))
        if not files:
            continue
        nav.append(f'<li class="nav-group">{escape(group.name)}</li>')
        for f in files:
            html = f.read_text(encoding="utf-8", errors="ignore")
            # 以檔名雜湊當 id：新增／刪除其他筆記時，舊連結與「上次讀到」仍指向同一篇
            nid = "n" + hashlib.md5(f"{group.name}/{f.name}".encode()).hexdigest()[:6]
            m = TITLE_RE.search(html)
            title = unescape(m.group(1)).strip() if m else f.stem
            m = NOTE_DATE_RE.search(html)
            date = f"{int(m.group(2))}/{int(m.group(3))}" if m else ""
            m = re.search(r"<main[^>]*>(.*?)</main>", html, re.S) or \
                re.search(r"<body[^>]*>(.*?)</body>", html, re.S)
            body = m.group(1) if m else html
            body = re.sub(r"<nav>.*?</nav>", "", body, count=1, flags=re.S)  # 原頁內目錄改由側欄提供
            # 多篇併成一頁：id 與頁內錨點加前綴避免互撞
            body = re.sub(r'\bid="([^"]+)"', rf'id="{nid}-\1"', body)
            body = re.sub(r'href="#([^"]+)"', rf'href="#{nid}-\1"', body)
            subs = []

            def h2_id(mm):
                attrs, inner = mm.group(1), mm.group(2)
                text = unescape(re.sub(r"<[^>]+>", "",
                                       re.sub(r'<span class="no">.*?</span>', "", inner))).strip()
                hid = f"{nid}-h{len(subs) + 1}"
                subs.append((hid, text))
                return f'<h2 id="{hid}"{attrs}>{inner}</h2>'
            body = re.sub(r"<h2([^>]*)>(.*?)</h2>", h2_id, body, flags=re.S)
            sub_html = "".join(f'<li><a href="#{h}">{escape(t)}</a></li>' for h, t in subs)
            nav.append(
                f'<li data-day="{nid}"><button class="nav-day" data-go="{nid}">'
                f'<span class="nav-title">{escape(title)}</span>'
                f'<span class="chk">{date}</span></button>'
                f'<ul class="nav-sub">{sub_html}</ul></li>')
            days.append(f'<article class="day" id="{nid}" data-title="{escape(title)}" hidden>'
                        f'{body}</article>')
            n += 1
    page = (NOTES_TMPL.replace("%%NAV%%", "".join(nav))
                      .replace("%%DAYS%%", "\n".join(days))
                      .replace("%%COUNT%%", str(n))
                      .replace("%%PWA%%", pwa_head("../")))
    (NOTES / "index.html").write_text(inject_extra_back(page), encoding="utf-8")
    print(f"筆記：{n} 篇 -> {NOTES / 'index.html'}")


MONTHS_ZH =["", "1 月", "2 月", "3 月", "4 月", "5 月", "6 月",
             "7 月", "8 月", "9 月", "10 月", "11 月", "12 月"]


def parse(path: Path):
    m = DATE_RE.search(path.name)
    if not m:
        return None
    y, mo, d = (int(x) for x in m.groups())
    slug = f"{y:04d}-{mo:02d}-{d:02d}"
    text = path.read_text(encoding="utf-8", errors="ignore")
    tm = TITLE_RE.search(text)
    title = tm.group(1).strip() if tm else path.stem
    cm = COVER_RE.search(text)
    cover = None
    if cm:
        fmt = cm.group(1).lower()
        cover = (EXT.get(fmt, "jpg"), base64.b64decode(cm.group(2)))
    return {"y": y, "mo": mo, "d": d, "slug": slug,
            "title": title, "src": path, "cover": cover,
            "size_mb": path.stat().st_size / 1_048_576}


def solid_png(size: int, rgb: tuple[int, int, int]) -> bytes:
    """產生純色方形 PNG（當 App 圖示用，免額外套件）。"""
    r, g, b = rgb
    raw = (b"\x00" + bytes((r, g, b)) * size) * size  # 每列前置 filter byte 0

    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xffffffff))

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)  # RGB, 8-bit
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def write_pwa():
    """寫出 manifest 與 App 圖示（純經濟學人紅方塊）。"""
    red = (227, 18, 11)
    (ASSETS / "icon-192.png").write_bytes(solid_png(192, red))
    (ASSETS / "icon-512.png").write_bytes(solid_png(512, red))
    (ASSETS / "icon-180.png").write_bytes(solid_png(180, red))
    manifest = {
        "name": "The Economist 繁體中文版",
        "short_name": "Economist 中文",
        "start_url": "./",
        "scope": "./",
        "display": "standalone",
        "background_color": "#f7f5f2",
        "theme_color": "#e3120b",
        "icons": [
            {"src": "assets/icon-192.png", "sizes": "192x192",
             "type": "image/png", "purpose": "any maskable"},
            {"src": "assets/icon-512.png", "sizes": "512x512",
             "type": "image/png", "purpose": "any maskable"},
        ],
    }
    (OUT / "manifest.webmanifest").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")


def build():
    if not SRC.exists():
        raise SystemExit(f"找不到來源資料夾：{SRC}")

    items = [p for p in (parse(f) for f in SRC.glob("*.html")) if p]
    items.sort(key=lambda i: (i["y"], i["mo"], i["d"]))

    ISSUES.mkdir(parents=True, exist_ok=True)
    COVERS.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    (ASSETS / "reader.js").write_text(READER_JS, encoding="utf-8")
    (ASSETS / "index.js").write_text(INDEX_JS, encoding="utf-8")
    write_pwa()

    # 併入額外分頁（其他專案的靜態網頁）
    for p in EXTRA_PAGES:
        dest_dir = OUT / p["slug"]
        dest = dest_dir / "index.html"
        src = p["src"]
        if src and src.exists():
            dest_dir.mkdir(parents=True, exist_ok=True)
            html = src.read_text(encoding="utf-8", errors="ignore")
            dest.write_text(inject_extra_back(html), encoding="utf-8")
            print(f"併入分頁「{p['label']}」：{src.name} -> {dest}")
        elif dest.exists():
            print(f"分頁「{p['label']}」找不到來源，沿用現有：{dest}")
        else:
            print(f"⚠ 分頁「{p['label']}」來源不存在且無現有複本，略過：{src}")

    build_notes()

    n_cover = 0
    for it in items:
        src_html = it["src"].read_text(encoding="utf-8", errors="ignore")
        (ISSUES / f"{it['slug']}.html").write_text(
            inject_mobile(src_html, it["slug"]), encoding="utf-8")
        if it["cover"]:
            ext, data = it["cover"]
            (COVERS / f"{it['slug']}.{ext}").write_bytes(data)
            it["cover_href"] = f"covers/{it['slug']}.{ext}"
            n_cover += 1
        else:
            it["cover_href"] = None

    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    # 依月份分組（新月份在前）
    groups: dict[tuple[int, int], list] = {}
    for it in items:
        groups.setdefault((it["y"], it["mo"]), []).append(it)

    sections = []
    for (y, mo) in sorted(groups, reverse=True):
        cards = []
        for it in sorted(groups[(y, mo)], key=lambda i: i["d"], reverse=True):
            href = f"issues/{it['slug']}.html"
            date_label = f"{it['mo']}/{it['d']}"
            if it["cover_href"]:
                thumb = (f'<img class="cover" loading="lazy" '
                         f'src="{it["cover_href"]}" alt="{escape(date_label)} 封面"/>')
            else:
                thumb = '<div class="cover noimg">無封面</div>'
            cards.append(
                f'<a class="card" href="{href}">'
                f'{thumb}'
                f'<div class="meta"><span class="date">{date_label}</span>'
                f'<span class="size">{it["size_mb"]:.1f} MB</span></div>'
                f'</a>'
            )
        sections.append(
            f'<section class="month"><h2>{y} 年 {MONTHS_ZH[mo]}</h2>'
            f'<div class="grid">{"".join(cards)}</div></section>'
        )

    # 分頁列：雜誌（本頁）＋ 各額外分頁 ＋ 筆記
    html = INDEX_TMPL.format(count=len(items), body="".join(sections),
                             early_theme=EARLY_THEME, theme_css=THEME_CSS,
                             pwa_head=pwa_head(""), tabs=tabs_html("", ""))
    (OUT / "index.html").write_text(html, encoding="utf-8")

    print(f"完成：{len(items)} 期，封面 {n_cover} 張 -> {OUT}")
    print(f"首頁：{OUT / 'index.html'}")


INDEX_TMPL = """<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="#e3120b"/>
{pwa_head}
<title>The Economist 繁體中文版 · 目錄</title>
{early_theme}{theme_css}
<style>
/* mobile-first：預設為手機樣式，寬螢幕才展開 */
:root{{--red:#e3120b;--ink:#121212;--grey:#6b6b6b;--line:#e2e0dd;--bg:#f7f5f2;--card:#fff}}
*{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--ink);
 font-family:"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif;
 font-size:16px;line-height:1.6;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1180px;margin:0 auto;padding:0 12px 64px}}
header{{position:sticky;top:0;z-index:10;text-align:center;
 padding:14px 12px calc(12px + env(safe-area-inset-top));
 background:var(--bg);border-bottom:3px solid var(--red)}}
header .brand{{color:var(--red);font-weight:800;font-size:24px;letter-spacing:.02em}}
header .sub{{color:var(--grey);font-size:13px;margin-top:3px;letter-spacing:.06em}}
.month{{margin-top:26px}}
.month h2{{font-size:18px;color:var(--red);border-bottom:2px solid var(--line);
 padding-bottom:7px;margin:0 0 14px;font-weight:800}}
/* 手機固定兩欄 */
.grid{{display:grid;gap:14px;grid-template-columns:repeat(2,1fr)}}
.card{{display:block;text-decoration:none;color:var(--ink);background:var(--card);
 border:1px solid var(--line);border-radius:10px;overflow:hidden;
 box-shadow:0 1px 3px rgba(0,0,0,.08);
 -webkit-tap-highlight-color:transparent;transition:transform .14s,box-shadow .14s}}
.card:active{{transform:scale(.97)}}
.card{{position:relative}}
.badge{{position:absolute;top:8px;left:8px;z-index:2;
 font:700 12px/1 "Noto Sans TC",system-ui,sans-serif;padding:4px 9px;border-radius:999px;
 color:#fff;background:var(--red);box-shadow:0 1px 5px rgba(0,0,0,.35)}}
.badge.done{{background:#2e7d32}}
.card.read .cover{{opacity:.5}}
.hbtns{{position:absolute;top:6px;right:8px;display:flex;gap:2px}}
.hbtns button{{width:40px;height:40px;padding:0;border:0;border-radius:50%;color:var(--ink);
 background:transparent;font-size:20px;line-height:1;cursor:pointer;
 -webkit-tap-highlight-color:transparent}}
.hbtns button:active{{background:rgba(0,0,0,.10)}}
.card .cover{{display:block;width:100%;aspect-ratio:960/1281;object-fit:cover;
 background:#eee;border-bottom:1px solid var(--line)}}
.card .cover.noimg{{display:flex;align-items:center;justify-content:center;
 color:var(--grey);font-size:14px}}
.card .meta{{display:flex;align-items:baseline;justify-content:space-between;
 gap:6px;padding:9px 11px}}
.card .date{{color:var(--red);font-weight:800;font-size:18px;font-variant-numeric:tabular-nums}}
.card .size{{color:var(--grey);font-size:11px;font-variant-numeric:tabular-nums}}
.tabs{{display:flex;gap:6px;justify-content:center;flex-wrap:wrap;margin:12px 0 2px}}
.tabs .tab{{text-decoration:none;color:var(--grey);font-weight:700;font-size:15px;
 padding:8px 18px;border-radius:999px;border:1px solid var(--line);background:var(--card);
 -webkit-tap-highlight-color:transparent}}
.tabs .tab.on{{background:var(--red);color:#fff;border-color:var(--red)}}
footer{{text-align:center;color:var(--grey);font-size:12px;margin-top:44px;
 padding-top:18px;border-top:1px solid var(--line)}}
/* 平板／桌機：放大字級、自動展更多欄、加上 hover 浮起 */
@media (min-width:640px){{
 .wrap{{padding:0 20px 80px}}
 header{{position:static;padding:44px 0 26px;margin-bottom:8px}}
 header .brand{{font-size:36px}}
 header .sub{{font-size:15px;margin-top:8px}}
 .month{{margin-top:40px}}
 .month h2{{font-size:20px;margin-bottom:20px}}
 .grid{{gap:22px;grid-template-columns:repeat(auto-fill,minmax(180px,1fr))}}
 .card:hover{{transform:translateY(-4px);box-shadow:0 12px 28px rgba(0,0,0,.16)}}
 .hbtns{{top:50%;transform:translateY(-50%);right:16px}}
}}
</style></head>
<body><div class="wrap">
<header>
 <div class="brand">The Economist</div>
 <div class="sub">繁體中文版 · 共 {count} 期</div>
 <div class="hbtns">
  <button id="fsBtn" aria-label="全螢幕" title="全螢幕">⛶</button>
  <button id="themeBtn" aria-label="切換背景色" title="切換背景色">◐</button>
 </div>
</header>
{tabs}
{body}
<footer>個人翻譯存檔 · 由 build_site.py 自動產生</footer>
</div>
<script defer src="assets/index.js"></script>
</body></html>
"""

# 筆記頁（web/notes/index.html）：版面、配色比照「AI 教材」——左側欄目錄、一次讀一篇、上方進度列與上／下一篇
NOTES_TMPL = r"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
%%PWA%%
<title>個人筆記</title>
<script>try{var t=localStorage.getItem("notes.theme");if(t)document.documentElement.setAttribute("data-theme",t);}catch(e){}</script>
<style>
:root{
  --bg:#fbfaf8; --panel:#f3f1ed; --card:#ffffff; --ink:#22201d; --ink-2:#55504a;
  --ink-3:#847d74; --line:#e2ded7; --line-2:#cfc9c0; --accent:#0f6f5c; --accent-soft:#e3f1ed;
  --warn-bg:#fdf6e3; --warn-line:#e8d9a8; --code-bg:#f6f4f0; --sel:#cfe9e2;
  --sans:"Noto Sans TC","PingFang TC","Microsoft JhengHei","Hiragino Sans GB",
         -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
  --mono:"SFMono-Regular",Consolas,"Liberation Mono",Menlo,"Courier New",monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#16181a; --panel:#1c1f22; --card:#1f2225; --ink:#e6e3de; --ink-2:#b4afa7;
    --ink-3:#8a847b; --line:#2e3236; --line-2:#3d4247; --accent:#5fcfb4; --accent-soft:#1b2f2a;
    --warn-bg:#2a2519; --warn-line:#4a4028; --code-bg:#1a1d20; --sel:#22463d;
  }
}
:root[data-theme="dark"]{
  --bg:#16181a; --panel:#1c1f22; --card:#1f2225; --ink:#e6e3de; --ink-2:#b4afa7;
  --ink-3:#8a847b; --line:#2e3236; --line-2:#3d4247; --accent:#5fcfb4; --accent-soft:#1b2f2a;
  --warn-bg:#2a2519; --warn-line:#4a4028; --code-bg:#1a1d20; --sel:#22463d;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);
     font-size:16.5px;line-height:1.9;-webkit-text-size-adjust:100%}
::selection{background:var(--sel)}

/* ---------- 版面 ---------- */
.wrap{display:flex;min-height:100vh}
.side{width:296px;flex:0 0 296px;background:var(--panel);border-right:1px solid var(--line);
      position:sticky;top:0;height:100vh;overflow-y:auto;overscroll-behavior:contain}
.main{flex:1;min-width:0;display:flex;flex-direction:column;align-items:center}
.day{width:100%;max-width:830px;padding:44px 32px 140px}
.day[hidden]{display:none}

/* ---------- 側欄 ---------- */
.brand{padding:22px 20px 14px;border-bottom:1px solid var(--line)}
.brand h2{margin:0;font-size:15px;letter-spacing:.02em}
.brand p{margin:6px 0 0;font-size:12.5px;color:var(--ink-3);line-height:1.6}
.brand a{color:var(--accent);text-decoration:none}
.tools{padding:12px 16px;border-bottom:1px solid var(--line);display:flex;gap:8px}
.tools input{flex:1;min-width:0;padding:7px 10px;border:1px solid var(--line-2);border-radius:7px;
  background:var(--card);color:var(--ink);font:inherit;font-size:13.5px}
.tools button{padding:7px 10px;border:1px solid var(--line-2);border-radius:7px;background:var(--card);
  color:var(--ink-2);cursor:pointer;font:inherit;font-size:13px}
.tools button:hover{color:var(--accent);border-color:var(--accent)}
nav ul{list-style:none;margin:0;padding:0}
nav>ul{padding:6px 0 60px}
.nav-group{padding:16px 18px 4px;font-size:12px;font-weight:700;color:var(--ink-3);letter-spacing:.08em}
.nav-day{width:100%;display:flex;align-items:center;gap:8px;background:none;border:0;cursor:pointer;
  font:inherit;font-size:14px;color:var(--ink-2);text-align:left;padding:8px 18px;line-height:1.5}
.nav-day:hover{color:var(--accent);background:var(--accent-soft)}
li.active>.nav-day{color:var(--accent);font-weight:600;background:var(--accent-soft);
  box-shadow:inset 3px 0 0 var(--accent)}
.nav-title{flex:1;min-width:0}
.chk{font-size:11px;color:var(--ink-3);font-variant-numeric:tabular-nums;white-space:nowrap}
.nav-sub{display:none;padding:0 0 10px}
li.active>.nav-sub{display:block}
.nav-sub a{display:block;padding:4px 18px 4px 32px;font-size:13px;color:var(--ink-3);
  text-decoration:none;line-height:1.55}
.nav-sub a:hover{color:var(--accent);background:var(--accent-soft)}
li.hide{display:none}

/* ---------- 內文 ---------- */
h1{font-size:30px;line-height:1.4;margin:0 0 10px;letter-spacing:.01em}
h2{font-size:22.5px;margin:0 0 16px;padding-top:6px;line-height:1.45;letter-spacing:.01em;
   scroll-margin-top:60px}
h3{font-size:18px;margin:30px 0 12px;line-height:1.5}
h4{font-size:16px;margin:0 0 6px;color:var(--ink)}
p{margin:0 0 17px}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid transparent}
a:hover{border-bottom-color:var(--accent)}
ul,ol{margin:0 0 17px;padding-left:1.6em}
li{margin:6px 0}
b,strong{font-weight:650}
.meta{color:var(--ink-3);font-size:13.5px;line-height:1.7;margin:0 0 26px;padding-bottom:14px;
  border-bottom:2px solid var(--accent)}
.lede{background:var(--accent-soft);border-left:4px solid var(--accent);border-radius:6px;
  padding:14px 18px;margin:0 0 18px}
.note{background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:9px;
  padding:12px 16px;margin:0 0 22px;font-size:15px;line-height:1.8}
section{margin:0;padding:34px 0 6px;border-top:1px solid var(--line)}
.part{margin:48px 0 0;padding:10px 0;font-size:13px;font-weight:700;color:var(--accent);
  letter-spacing:.1em}
.part+section{border-top:2px solid var(--accent)}
h2 .no{display:inline-block;margin-right:10px;padding:0 9px;border-radius:6px;font-size:14px;
  line-height:1.9;vertical-align:3px;color:#fff;background:var(--accent)}
:root[data-theme="dark"] h2 .no{color:var(--bg)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]) h2 .no{color:var(--bg)}}
ol.points li{margin:9px 0}
.src{display:inline-block;margin-left:5px;padding:0 7px;border:1px solid var(--line);border-radius:5px;
  background:var(--panel);color:var(--ink-3);font-size:12px;line-height:1.75;white-space:nowrap;
  vertical-align:1px}
.src:hover{color:var(--accent);border-color:var(--accent)}
.new{display:inline-block;margin-left:5px;padding:0 6px;border-radius:5px;background:var(--accent-soft);
  color:var(--accent);font-size:11.5px;font-weight:700;line-height:1.75;white-space:nowrap}
.cmp{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:12px;margin:4px 0 20px}
.cmp>div{border:1px solid var(--line);border-radius:9px;background:var(--card);padding:12px 15px;
  font-size:15px;line-height:1.8}
.table-wrap{overflow-x:auto;margin:0 0 22px}
table{border-collapse:collapse;width:100%;min-width:34rem;font-size:15px}
th,td{border:1px solid var(--line);padding:9px 12px;text-align:left;vertical-align:top;line-height:1.7}
th{background:var(--panel);font-weight:650;font-size:14.5px}
tbody tr:nth-child(even){background:color-mix(in srgb,var(--panel) 45%,transparent)}
pre{margin:0 0 22px;padding:15px 16px;border:1px solid var(--line);border-radius:9px;
  background:var(--code-bg);overflow-x:auto;font-family:var(--mono);font-size:13.6px;line-height:1.72}
footer{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);font-size:13px;
  color:var(--ink-3);line-height:1.8}

/* 進度列 */
.progress{position:sticky;top:0;z-index:5;background:color-mix(in srgb,var(--bg) 92%,transparent);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line);width:100%;
  display:flex;justify-content:center}
.progress-in{width:100%;max-width:830px;padding:9px 32px;display:flex;align-items:center;gap:14px;
  font-size:13px;color:var(--ink-3)}
#pos{font-variant-numeric:tabular-nums;white-space:nowrap}
.bar{flex:1;height:5px;background:var(--line);border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);width:0;transition:width .1s}
.pager{display:flex;gap:8px}
.pager button{font:inherit;font-size:12.5px;padding:4px 11px;border:1px solid var(--line-2);
  border-radius:6px;background:var(--card);color:var(--ink-2);cursor:pointer;white-space:nowrap}
.pager button:hover:not(:disabled){color:var(--accent);border-color:var(--accent)}
.pager button:disabled{opacity:.38;cursor:default}

/* 手機 */
.menu-btn{display:none;position:fixed;left:12px;bottom:14px;z-index:30;width:46px;height:46px;
  border-radius:50%;border:1px solid var(--line-2);background:var(--card);color:var(--ink);
  font-size:19px;cursor:pointer;box-shadow:0 3px 14px rgba(0,0,0,.18)}
@media(max-width:900px){
  .side{position:fixed;z-index:25;left:0;top:0;transform:translateX(-100%);transition:transform .2s;
    box-shadow:0 0 30px rgba(0,0,0,.2)}
  .side.open{transform:none}
  .menu-btn{display:block}
  .day{padding:28px 18px 120px}
  .progress-in{padding:9px 18px}
  h1{font-size:25px}h2{font-size:20px}
  body{font-size:16px}
}
@media print{
  .side,.progress,.menu-btn,#econ-back{display:none!important}
  .day{max-width:none;padding:0 0 30px}
  body{font-size:11pt;line-height:1.7;background:#fff;color:#000}
}
</style></head>
<body>
<div class="wrap">
  <aside class="side" id="side">
    <div class="brand">
      <h2>個人筆記</h2>
      <p>研究整理・共 %%COUNT%% 篇<br><a href="../index.html">← 回雜誌目錄</a></p>
    </div>
    <div class="tools">
      <input id="q" type="search" placeholder="搜尋筆記…" autocomplete="off">
      <button id="theme" type="button" title="切換亮色／暗色">◐</button>
    </div>
    <nav><ul id="nav">%%NAV%%</ul></nav>
  </aside>
  <div class="main" id="main">
    <div class="progress"><div class="progress-in">
      <span id="pos"></span><div class="bar"><i id="bar"></i></div>
      <div class="pager"><button id="prev" type="button">← 上一篇</button><button id="next" type="button">下一篇 →</button></div>
    </div></div>
%%DAYS%%
  </div>
</div>
<button class="menu-btn" id="menu" type="button" aria-label="目錄">☰</button>
<script>
(function(){
  "use strict";
  var KEY="notes.last", TKEY="notes.theme";
  function get(k){try{return localStorage.getItem(k);}catch(e){return null;}}
  function set(k,v){try{localStorage.setItem(k,v);}catch(e){}}
  var days=[].slice.call(document.querySelectorAll(".day"));
  var items=[].slice.call(document.querySelectorAll("#nav li[data-day]"));
  var side=document.getElementById("side"), prev=document.getElementById("prev"),
      next=document.getElementById("next"), bar=document.getElementById("bar"), cur=-1;
  if(!days.length)return;

  document.getElementById("theme").onclick=function(){
    var d=document.documentElement, now=d.getAttribute("data-theme");
    if(!now)now=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";
    var nx=now==="dark"?"light":"dark"; d.setAttribute("data-theme",nx); set(TKEY,nx);
  };

  function paint(){
    var h=document.documentElement.scrollHeight-innerHeight;
    bar.style.width=(h>0?Math.min(100,scrollY/h*100):100)+"%";
  }
  function show(i,anchor){
    days.forEach(function(d,j){d.hidden=j!==i;});
    items.forEach(function(li,j){li.classList.toggle("active",j===i);});
    cur=i; set(KEY,days[i].id);
    document.getElementById("pos").textContent="第 "+(i+1)+" / "+days.length+" 篇";
    prev.disabled=i===0; next.disabled=i===days.length-1;
    document.title=days[i].getAttribute("data-title")+" · 個人筆記";
    var el=anchor&&document.getElementById(anchor);
    if(el)el.scrollIntoView(); else window.scrollTo(0,0);
    paint();
  }
  function route(){
    var h=decodeURIComponent(location.hash.slice(1)), el=h&&document.getElementById(h);
    var d=el&&el.closest(".day");
    if(d){show(days.indexOf(d),d.id===h?null:h);return;}
    var k=days.map(function(x){return x.id;}).indexOf(get(KEY));
    show(k<0?0:k);
  }
  function go(id){side.classList.remove("open");
    if(location.hash==="#"+id)route(); else location.hash=id;}

  document.querySelectorAll(".nav-day").forEach(function(b){
    b.onclick=function(){go(b.getAttribute("data-go"));};});
  document.querySelectorAll(".nav-sub a").forEach(function(a){
    a.addEventListener("click",function(){side.classList.remove("open");});});
  prev.onclick=function(){if(cur>0)go(days[cur-1].id);};
  next.onclick=function(){if(cur<days.length-1)go(days[cur+1].id);};
  document.getElementById("menu").onclick=function(){side.classList.toggle("open");};
  document.getElementById("main").addEventListener("click",function(){side.classList.remove("open");});

  // 搜尋：比對整篇內文，隱藏不符合的筆記與空分類
  document.getElementById("q").addEventListener("input",function(){
    var q=this.value.trim().toLowerCase();
    items.forEach(function(li,j){
      li.classList.toggle("hide",!!q&&days[j].textContent.toLowerCase().indexOf(q)<0);});
    document.querySelectorAll(".nav-group").forEach(function(g){
      var n=g.nextElementSibling, any=false;
      while(n&&!n.classList.contains("nav-group")){if(!n.classList.contains("hide"))any=true;n=n.nextElementSibling;}
      g.classList.toggle("hide",!any);});
  });

  window.addEventListener("hashchange",route);
  window.addEventListener("scroll",paint,{passive:true});
  route();
})();
</script>
</body></html>
"""


# ---- 各期閱讀頁：設定面板 + 閱讀進度（存在 localStorage）----
READER_JS = r'''
(function(){
  var SKEY='econ.settings', PKEY='econ.progress';
  var slug=window.__ISSUE__||'';
  var doc=document.documentElement, body=document.body;
  function rj(k,d){try{return JSON.parse(localStorage.getItem(k))||d;}catch(e){return d;}}
  function wj(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  var st=rj(SKEY,{});
  var SANS='"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif';
  var SERIF='"Noto Serif TC","Source Han Serif TC","PingFang TC","Microsoft JhengHei",Georgia,serif';

  function applySettings(){
    if(st.theme&&st.theme!=='light')doc.setAttribute('data-theme',st.theme);
    else doc.removeAttribute('data-theme');
    body.style.fontSize   = st.fontPx? st.fontPx+'px' : '';
    body.style.lineHeight = st.lineHeight? st.lineHeight : '';
    body.style.fontFamily = st.font==='sans'? SANS : (st.font==='serif'? SERIF : '');
  }
  function save(){ wj(SKEY,st); applySettings(); syncUI(); }

  // 樣式（面板 / 浮動鈕）
  var css=document.createElement('style');
  css.textContent=`
  .rd-fabs{position:fixed;right:14px;bottom:14px;z-index:70;display:flex;flex-direction:column;gap:10px}
  .rd-fab{width:46px;height:46px;border-radius:50%;border:0;cursor:pointer;
   display:flex;align-items:center;justify-content:center;text-decoration:none;
   background:var(--red);color:#fff;font:700 15px/1 "Noto Sans TC",system-ui,sans-serif;
   box-shadow:0 4px 14px rgba(0,0,0,.28);-webkit-tap-highlight-color:transparent}
  .rd-fab:active{transform:scale(.94)}
  .rd-panel{position:fixed;right:14px;bottom:70px;z-index:71;width:250px;max-width:calc(100vw - 28px);
   background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:14px;
   box-shadow:0 12px 34px rgba(0,0,0,.30);padding:14px 16px;
   font-family:"Noto Sans TC","PingFang TC",system-ui,sans-serif}
  .rd-panel[hidden]{display:none}
  .rd-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:10px 0}
  .rd-row>span{color:var(--grey);font-size:14px;flex:0 0 auto}
  .rd-seg,.rd-step{display:flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}
  .rd-seg button,.rd-step button{border:0;background:transparent;color:var(--ink);
   padding:7px 10px;font-size:14px;cursor:pointer;-webkit-tap-highlight-color:transparent}
  .rd-seg button.on{background:var(--red);color:#fff}
  .rd-step b{min-width:44px;text-align:center;align-self:center;font-size:14px;font-variant-numeric:tabular-nums}
  .rd-reset{width:100%;border:1px solid var(--line);background:transparent;color:var(--grey);
   border-radius:9px;padding:8px;cursor:pointer;font-size:13px}
  .rd-toast{position:fixed;left:50%;bottom:78px;transform:translateX(-50%);z-index:80;
   background:rgba(0,0,0,.82);color:#fff;padding:9px 15px;border-radius:999px;font-size:13px;
   opacity:0;transition:opacity .25s;pointer-events:none}
  .rd-toast.show{opacity:1}
  `;
  document.head.appendChild(css);

  var fabs=document.createElement('div'); fabs.className='rd-fabs';
  fabs.innerHTML='<a class="rd-fab" href="../index.html" title="回目錄">☰</a>'
    +'<button class="rd-fab" id="rdFull" title="全螢幕">⛶</button>'
    +'<button class="rd-fab" id="rdSet" title="閱讀設定">Aa</button>';
  document.body.appendChild(fabs);

  // 全螢幕（桌機/Android Chrome）。iOS Safari 不支援時自動隱藏，請改用「加到主畫面」。
  var fullBtn=document.getElementById('rdFull');
  function fsEl(){return document.fullscreenElement||document.webkitFullscreenElement;}
  function reqFs(el){var fn=el.requestFullscreen||el.webkitRequestFullscreen;
    return fn?fn.call(el):null;}   // 必須在點擊事件內「同步」呼叫，否則失去使用者手勢
  function exitFs(){var fn=document.exitFullscreen||document.webkitExitFullscreen;if(fn)fn.call(document);}
  var canFs=!!(document.documentElement.requestFullscreen||document.documentElement.webkitRequestFullscreen);
  if(!canFs){fullBtn.style.display='none';}
  else{
    fullBtn.onclick=function(){
      if(fsEl()){exitFs();return;}
      var p;
      try{p=reqFs(document.documentElement);}
      catch(e){toast('無法全螢幕：'+(e.name||e.message)+'。可改用選單「加到主畫面」');return;}
      if(p&&p.catch)p.catch(function(err){
        toast('此瀏覽器擋下全螢幕（'+(err&&err.name||'error')+'）。請用 Chrome 選單「加到主畫面」以全螢幕開啟');});
    };
    ['fullscreenchange','webkitfullscreenchange'].forEach(function(ev){
      document.addEventListener(ev,function(){fullBtn.textContent=fsEl()?'✕':'⛶';});});
  }

  var panel=document.createElement('div'); panel.className='rd-panel'; panel.hidden=true;
  panel.innerHTML=
    '<div class="rd-row"><span>背景</span><div class="rd-seg" data-k="theme">'
    +'<button data-v="light">白</button><button data-v="sepia">米</button>'
    +'<button data-v="grey">灰</button><button data-v="dark">夜</button></div></div>'
    +'<div class="rd-row"><span>字型</span><div class="rd-seg" data-k="font">'
    +'<button data-v="serif">明體</button><button data-v="sans">黑體</button></div></div>'
    +'<div class="rd-row"><span>字級</span><div class="rd-step" data-k="fontPx">'
    +'<button data-d="-1">A−</button><b id="rdFs">–</b><button data-d="1">A＋</button></div></div>'
    +'<div class="rd-row"><span>行距</span><div class="rd-step" data-k="lineHeight">'
    +'<button data-d="-1">−</button><b id="rdLh">–</b><button data-d="1">＋</button></div></div>'
    +'<div class="rd-row"><button id="rdReset" class="rd-reset">恢復預設</button></div>';
  document.body.appendChild(panel);

  document.getElementById('rdSet').onclick=function(){panel.hidden=!panel.hidden;};

  function curFs(){return st.fontPx||Math.round(parseFloat(getComputedStyle(body).fontSize))||18;}
  function curLh(){return st.lineHeight||1.85;}

  panel.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    var seg=b.closest('.rd-seg'), step=b.closest('.rd-step');
    if(b.id==='rdReset'){st={};save();return;}
    if(seg){st[seg.dataset.k]=b.dataset.v;save();return;}
    if(step){
      var k=step.dataset.k, d=parseInt(b.dataset.d,10);
      if(k==='fontPx'){st.fontPx=Math.min(26,Math.max(13,curFs()+d));}
      else{st.lineHeight=Math.round((curLh()+d*0.05)*100)/100;
           st.lineHeight=Math.min(2.4,Math.max(1.35,st.lineHeight));}
      save();return;
    }
  });

  function syncUI(){
    panel.querySelectorAll('.rd-seg[data-k="theme"] button').forEach(function(x){
      x.classList.toggle('on', x.dataset.v===(st.theme||'light'));});
    panel.querySelectorAll('.rd-seg[data-k="font"] button').forEach(function(x){
      x.classList.toggle('on', x.dataset.v===(st.font||'serif'));});
    var fs=document.getElementById('rdFs'), lh=document.getElementById('rdLh');
    if(fs)fs.textContent=curFs()+'px';
    if(lh)lh.textContent=st.lineHeight?st.lineHeight.toFixed(2):'標準';
  }

  // ---- 閱讀進度 ----
  var bar=document.createElement('div'); bar.id='econ-progress'; document.body.appendChild(bar);
  function maxScroll(){return Math.max(1,doc.scrollHeight-window.innerHeight);}
  function curPct(){return Math.min(1,Math.max(0,(window.scrollY||window.pageYOffset)/maxScroll()));}
  var prog=rj(PKEY,{}), tmr;
  function paint(){bar.style.width=(curPct()*100)+'%';}
  function saveProg(){var pct=curPct(),prev=prog[slug]||{};
    prog[slug]={pct:pct,read:(prev.read||pct>=0.9),ts:Date.now()};wj(PKEY,prog);}
  var toastEl;
  function toast(msg){if(!toastEl){toastEl=document.createElement('div');toastEl.className='rd-toast';
    document.body.appendChild(toastEl);} toastEl.textContent=msg; toastEl.classList.add('show');
    setTimeout(function(){toastEl.classList.remove('show');},1800);}

  applySettings(); syncUI();
  window.addEventListener('load',function(){
    var p=prog[slug];
    if(p&&p.pct>0.02&&p.pct<0.985){window.scrollTo(0,p.pct*maxScroll());toast('已回到上次閱讀位置');}
    paint();
  });
  window.addEventListener('scroll',function(){paint();clearTimeout(tmr);tmr=setTimeout(saveProg,400);},{passive:true});
  window.addEventListener('pagehide',saveProg);
  document.addEventListener('visibilitychange',function(){if(document.hidden)saveProg();});
})();
'''

# ---- 首頁：套用主題、右上角切換背景、卡片顯示已讀/進度 ----
INDEX_JS = r'''
(function(){
  var SKEY='econ.settings', PKEY='econ.progress';
  function rj(k,d){try{return JSON.parse(localStorage.getItem(k))||d;}catch(e){return d;}}
  function wj(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  var st=rj(SKEY,{}), prog=rj(PKEY,{}), doc=document.documentElement;
  function applyTheme(){if(st.theme&&st.theme!=='light')doc.setAttribute('data-theme',st.theme);
    else doc.removeAttribute('data-theme');}
  applyTheme();

  var btn=document.getElementById('themeBtn'), order=['light','sepia','grey','dark'];
  function icon(){btn.textContent=st.theme==='dark'?'🌙':(st.theme==='sepia'?'📖':(st.theme==='grey'?'▧':'◐'));}
  if(btn){icon();btn.onclick=function(){var i=order.indexOf(st.theme||'light');
    st.theme=order[(i+1)%order.length];wj(SKEY,st);applyTheme();icon();};}

  var fs=document.getElementById('fsBtn');
  function fsEl(){return document.fullscreenElement||document.webkitFullscreenElement;}
  if(fs){
    if(!(document.fullscreenEnabled||document.webkitFullscreenEnabled)){fs.style.display='none';}
    else{fs.onclick=function(){var el=document.documentElement;
      if(!fsEl()){(el.requestFullscreen||el.webkitRequestFullscreen).call(el);}
      else{(document.exitFullscreen||document.webkitExitFullscreen).call(document);}};
      document.addEventListener('fullscreenchange',function(){fs.textContent=fsEl()?'✕':'⛶';});}
  }

  document.querySelectorAll('a.card').forEach(function(a){
    var m=(a.getAttribute('href')||'').match(/issues\/(.+)\.html/); if(!m)return;
    var p=prog[m[1]]; if(!p)return;
    var b=document.createElement('span'); b.className='badge';
    if(p.read){a.classList.add('read');b.className='badge done';b.textContent='✓ 已讀';}
    else if(p.pct>0.02){b.textContent='繼續 '+Math.round(p.pct*100)+'%';}
    else return;
    a.appendChild(b);
  });
})();
'''


def pull_repo():
    """先拉下 GitHub 上的新提交（手機端新增的筆記），避免本機重建後推不上去或蓋掉筆記。"""
    if not (OUT / ".git").exists():
        return
    r = subprocess.run(["git", "-C", str(OUT), "pull", "--rebase", "--autostash", "origin", "main"])
    if r.returncode != 0:
        print("⚠ git pull 失敗（可能離線或有衝突），以本機現有內容繼續產生。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="產生 The Economist 繁中版網站")
    ap.add_argument("--notes-only", action="store_true",
                    help="只重建筆記頁 notes/index.html（雲端／GitHub Action 用）")
    ap.add_argument("--no-pull", action="store_true", help="產生前不要 git pull")
    args = ap.parse_args()
    if args.notes_only:
        build_notes()
    else:
        if not args.no_pull:
            pull_repo()
        build()
