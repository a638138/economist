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
- 使用者用來在新專案建立 agent 開發環境的一套檔案，全部顯示在筆記分頁的「Agent 開發環境」分類（`tools/build_site.py` 的 `NOTE_LINKED`）。網站上顯示的就是 agent 讀的同一份，這些 md 是唯一來源：
  - `agent/setup.md`：入口頁。新專案對 agent 說「讀這頁、照步驟建立環境」，agent 會下載下列檔案裝進專案的 `.claude/`。
  - `agent/ai-agent-guide.md`：工作守則，每個 session 都讀。**核心規則保持 20 條以內**，新增前先考慮能否併入同主題的既有條目；只收模型預設不一定會做的規則，沒有直接研究支持的要標「做法」或「專案經驗」；只在特定專案類型相關的規則放在標明「只在這類專案適用」的小節（目前是 C++／GPU／即時系統／碰硬體）。
  - `agent/skills/agent-config-writing/SKILL.md`：撰寫 CLAUDE.md、SKILL.md、MCP 工具時才載入的 skill；附檔 `windows-traps.md` 是 Windows（尤其非英文語系）的靜默陷阱檢查清單（每項：現象、怎麼查、怎麼修、必要時的二次陷阱、哨兵測試，每項都要有哨兵測試），專案經驗裡新發現的環境陷阱加在這裡；新增的修法要先確認不會引入另一個陷阱。
  - `agent/agents/reviewer.md`：只讀的獨立審查子 agent（守則「獨立審查」那條用它）；`agent/commands/review.md`、`handoff.md`：使用者指令 /review、/handoff。改守則的審查或交接規則時，這三個檔要一起對齊。
- **新增、改名或刪除 `agent/` 下的檔案時，三處要一起改**：`agent/setup.md` 的檔案清單、`tools/build_site.py` 的 `NOTE_LINKED`、`tools/install_agent_rules.py`（安裝到使用者電腦的 `~/.claude`）。
- 標「專案經驗」的條目（第 2 版起）來自使用者的實際專案，修改時保留這些條目與標示，不要用研究筆記覆蓋；證據整理在筆記（五）第五節，只用「專案甲／乙／丙」描述，不寫客戶、公司、人名、序號、主機名稱或路徑。
- **改到 AI重點 筆記的結論或「對你的意義」時，同步更新守則與 skill**：規則用祈使句、一行一條、句尾標出依據章節（例如「（二-1）」），不放數字細節（除非數字本身就是 agent 要用的判斷依據，例如計時器解析度）；更新檔頭的日期。改完提醒使用者在電腦上重跑 `python tools/install_agent_rules.py`，並在用到的專案裡請 agent 照 setup.md 更新。
- 只收對 agent 行為有影響的規則；只對使用者本人有用的建議（例如 effort 怎麼設）留在筆記裡。
- 網頁版格式：守則、setup.md、windows-traps.md 轉成一般筆記版面，只支援 `#`、`##`、段落、`- ` 與 `1. ` 清單（不可巢狀）、行內 `code`、`**粗體**`，不要用表格；skill、子 agent、指令是設定檔，原文照登（mode="raw"），不受此限。
- 提交與推送方式同筆記（Action 也會處理 `agent/` 的變動）。
