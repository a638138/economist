# The Economist 繁中版網站（GitHub Pages）

網址：https://a638138.github.io/economist/ ・筆記分頁：https://a638138.github.io/economist/notes/ ・投資分頁：https://a638138.github.io/economist/invest/

這個 repo 是**產生後的靜態網站**。雜誌各期是在使用者電腦上翻譯、產生後推上來的；
在這裡（手機端／雲端 session）**只做筆記的新增與修改**。

## 不要動的東西
- `index.html`、`issues/`、`covers/`、`assets/`、`ai/`、`manifest.webmanifest`：本機程式產生，手改會被下次更新覆蓋。
- `notes/index.html`、`invest/index.html`：由 `notes_src/` 自動產生，**不要手改、不需要提交**。
- `tools/build_site.py`：本機與雲端共用的產生程式，除非使用者要求，否則不改。

## 新增筆記

1. **檔案位置**：`notes_src/<分類>/<檔名>.html`
   - 分類＝資料夾名稱，會成為側欄的分組標題（現有：`AI重點`、`投資`）。沒有合適的分類才新增資料夾，先問使用者。
   - **哪個分類放到哪個分頁**由 `tools/build_site.py` 的 `NOTE_PAGES` 決定：`投資` → 「投資」分頁（`invest/`），其他分類 → 「筆記」分頁（`notes/`）。
   - **網站是公開的**：`投資` 分類只放一般化的原則與研究整理，**不可包含個人金額、持股比例、帳戶、券商、工作或家庭資訊**。使用者貼來的個人投資內容，先移除這些資訊並請使用者確認，再提交。
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
4. **檢查**：執行 `python3 tools/build_site.py --notes-only`，確認對應分頁的「筆記：N 篇」或「投資：N 篇」比原本多 1、沒有錯誤。
   這一步會改到 `notes/`、`invest/`，不要提交它們：`git checkout -- notes invest`。
5. **提交與推送**：只提交 `notes_src/`，訊息如 `新增筆記：<標題>`，推到目前的工作分支即可，**不需要開 PR**。
   GitHub Action（`.github/workflows/notes.yml`）會把 `claude/**` 分支或 main 上 `notes_src/` 的變動套用到 main、
   重建筆記頁並發佈，約 1～2 分鐘後網站更新。
6. **回報**：告訴使用者檔案路徑、筆記標題，以及上方筆記分頁網址。若想確認發佈結果，可請使用者到 repo 的 Actions 分頁看「發佈筆記」是否成功。

## 修改或刪除筆記
- 修改：直接改 `notes_src/` 內的檔案（檔名不變），流程同上。
- 刪除：`git rm` 該檔並推送，Action 會同步刪除網站上的那篇。

## AI Agent 工作守則（`agent/`）
- 由 `notes_src/AI重點/` 五篇筆記整理出、給使用者的 coding agent 讀的規則。網站上顯示的就是 agent 讀的同一份，只有兩個檔：
  - `agent/ai-agent-guide.md`：工作守則，每個 session 都讀。**核心規則保持 15 條以內**，只收模型預設不一定會做的規則，沒有直接研究支持的要標「做法」；C++／GPU 規則放在標明「只在這類專案適用」的小節。
  - `agent/skills/agent-config-writing/SKILL.md`：撰寫 CLAUDE.md、SKILL.md、MCP 工具時才載入的 skill。
- 另有不顯示在網站上的：`agent/agents/reviewer.md`（只讀的獨立審查子 agent，守則「獨立審查」那條用它）、`agent/commands/review.md` 與 `handoff.md`（使用者指令 /review、/handoff）。改守則的審查或交接規則時，這三個檔要一起對齊。
- 守則第 2 版的內容來自使用者的專案經驗（標「專案經驗」），修改時保留這些條目與標示，不要用研究筆記覆蓋。
- 使用者在電腦上執行 `python tools/install_agent_rules.py` 安裝到 `~/.claude`。
- **改到 AI重點 筆記的結論或「對你的意義」時，同步更新這兩個檔**：規則用祈使句、一行一條、句尾標出依據章節（例如「（二-1）」），不放數字細節；更新檔頭的日期。改完提醒使用者在電腦上重跑安裝腳本。
- 只收對 agent 行為有影響的規則；只對使用者本人有用的建議（例如 effort 怎麼設）留在筆記裡。
- 網頁版：產生程式會把它轉成 HTML，列在筆記分頁「AI重點」的最後一篇（`tools/build_site.py` 的 `NOTE_LINKED`）；只支援 `#`、`##`、段落、`- ` 清單、行內 `code`、`**粗體**`，不要用表格或巢狀清單。
- 這份 md 是唯一來源，直接改它；提交與推送方式同筆記（Action 也會處理 `agent/` 的變動）。
