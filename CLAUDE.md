# The Economist 繁中版網站（GitHub Pages）

網址：https://a638138.github.io/economist/ ・筆記分頁：https://a638138.github.io/economist/notes/

這個 repo 是**產生後的靜態網站**。雜誌各期是在使用者電腦上翻譯、產生後推上來的；
在這裡（手機端／雲端 session）**只做筆記的新增與修改**。

## 不要動的東西
- `index.html`、`issues/`、`covers/`、`assets/`、`ai/`、`manifest.webmanifest`：本機程式產生，手改會被下次更新覆蓋。
- `notes/index.html`：由 `notes_src/` 自動產生，**不要手改、不需要提交**。
- `tools/build_site.py`：本機與雲端共用的產生程式，除非使用者要求，否則不改。

## 新增筆記

1. **檔案位置**：`notes_src/<分類>/<檔名>.html`
   - 分類＝資料夾名稱，會成為側欄的分組標題（現有：`AI重點`）。沒有合適的分類才新增資料夾，先問使用者。
   - 檔名用中文＋底線、不含空白，例如 `RAG評測方法_研究整理.html`。同分類內依檔名排序。
   - **改名或搬移檔案會讓舊連結與「上次讀到」失效**（id 由「分類/檔名」雜湊而來），修改內容時保留原檔名。
2. **格式**：複製 `tools/note_template.html` 改寫。規則：
   - 只有 `<main>`（沒有就 `<body>`）裡的內容會被收進網站；`<head>` 裡的 `<style>`、`<script>` 會被丟掉，**不要自訂 CSS 或 JS**，只用範本裡出現的 class：
     `meta`、`lede`、`note`、`part`、`section`、`h2 .no`、`ol.points`、`src`、`new`、`cmp`、`table-wrap`、`pre`。
   - `<title>` 是側欄顯示的標題，與 `<h1>` 一致。
   - 一定要有「整理日期：YYYY 年 M 月 D 日」（放在 `.meta`），側欄靠它顯示日期。
   - 每個 `<h2>` 會變成側欄的子目錄；用 `<section>` 包住每個 h2 小節。
   - 引用文獻一律用 `<a class="src" href="原始網址">作者 年份</a>` 放在句尾，網址必須是真實可查的來源，不要編造。
   - 文字用台灣繁體中文與台灣慣用詞。
3. **使用者從別的對話貼來的內容**：保留其結論與數字，轉成上述格式即可；不要自行增刪論點。缺日期就用今天。
4. **檢查**：執行 `python3 tools/build_site.py --notes-only`，確認輸出的「筆記：N 篇」比原本多 1、沒有錯誤。
   這一步會改到 `notes/index.html`，不要提交它：`git checkout -- notes`。
5. **提交與推送**：只提交 `notes_src/`，訊息如 `新增筆記：<標題>`，推到目前的工作分支即可，**不需要開 PR**。
   GitHub Action（`.github/workflows/notes.yml`）會把 `claude/**` 分支或 main 上 `notes_src/` 的變動套用到 main、
   重建筆記頁並發佈，約 1～2 分鐘後網站更新。
6. **回報**：告訴使用者檔案路徑、筆記標題，以及上方筆記分頁網址。若想確認發佈結果，可請使用者到 repo 的 Actions 分頁看「發佈筆記」是否成功。

## 修改或刪除筆記
- 修改：直接改 `notes_src/` 內的檔案（檔名不變），流程同上。
- 刪除：`git rm` 該檔並推送，Action 會同步刪除網站上的那篇。
