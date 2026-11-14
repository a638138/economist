# 建立 Agent 開發環境

整理日期：2026 年 11 月 14 日。在新專案裡建立一套 coding agent 開發環境：工作守則、審查用子 agent、交接與審查指令、撰寫設定檔的 skill。這一頁同時寫給人和 agent 讀。

## 怎麼用

在新專案的 Claude Code 裡說：

「請讀 https://a638138.github.io/economist/agent/setup.md ，照上面的步驟在這個專案建立 agent 開發環境。」

已經建過的專案，同一句話也能用來更新到最新版：agent 會比對差異，問過你再覆蓋。

## 檔案清單

每個檔案的原文網址與安裝到專案裡的位置：

- 工作守則：https://a638138.github.io/economist/agent/ai-agent-guide.md → `.claude/ai-agent-guide.md`
- 子 agent reviewer：https://a638138.github.io/economist/agent/agents/reviewer.md → `.claude/agents/reviewer.md`
- 指令 /review：https://a638138.github.io/economist/agent/commands/review.md → `.claude/commands/review.md`
- 指令 /handoff：https://a638138.github.io/economist/agent/commands/handoff.md → `.claude/commands/handoff.md`
- skill agent-config-writing：https://a638138.github.io/economist/agent/skills/agent-config-writing/SKILL.md → `.claude/skills/agent-config-writing/SKILL.md`

## 給 agent 的步驟

1. 預設裝在專案裡（`.claude/` 會跟著 repo，手機與雲端的 Claude Code session 也讀得到）。只有使用者明確要求時，才改裝到全域 `~/.claude/`（只在那台電腦有效）。
2. 逐一下載上面每個檔案的原文，內容不得改寫或摘要，開頭 --- 之間的設定也要原樣保留。下載失敗就停下來告訴使用者，不要憑記憶重寫。
3. 目標位置已有同名檔案時，先比較差異；內容不同就列出差異，問使用者要覆蓋、保留還是合併。
4. 專案根目錄的 CLAUDE.md：沒有就建立。在檔案最前面加一行 `@.claude/ai-agent-guide.md` 引用守則（已有就不重複加），原有內容一律保留。
5. 用 agent-config-writing skill 的原則，幫使用者補上 CLAUDE.md 的專案專屬內容：先讀專案找出能查到的，查不到的再問使用者。必要項目：建置與測試指令；目前已知會失敗的測試，**註明在哪台機器或哪個環境**（守則規定要列在這裡）；硬體與即時限制；不可違反的規則及原因；**違反了也不會報錯的環境陷阱**（例如編碼、換行、建置快取、會靜默退回的設定），在 CLAUDE.md 裡緊接在 `@.claude/ai-agent-guide.md` 那一行之後獨立成一節。這一類要主動查、主動問使用者，因為從程式碼看不出來。不要寫架構介紹或目錄說明。
6. 對使用者列出的不可違反規則，提出能機械檢查的做法（hook、lint 規則、編譯期檢查、CI 測試），由使用者決定要做哪些；不要擅自安裝 hook。優先替「違反了也不會報錯」那一節的項目提機械檢查。
7. 不是 C++／GPU／即時系統的專案，守則裡那一節本來就標明不適用，不要刪改守則檔。
8. 看一次版本控制狀態，把這些檔案作為一個提交：「建立 agent 開發環境」。
9. 回報：裝了哪些檔、在哪裡、有沒有覆蓋或跳過既有檔案、CLAUDE.md 還缺哪些需要使用者補的內容。並提醒使用者：新的指令與子 agent 在下一個 session 才會生效。

## 裝好之後

- 每個 session 都會讀守則；寫 CLAUDE.md、SKILL.md 或 MCP 工具時會自動載入 skill。
- 非小型的工作做完，agent 應該自己派 reviewer 審查；它忘了就下 `/review`。
- 換 session 前下 `/handoff`，把它給的開場訊息貼到新 session。
- 守則與這些檔案的依據、研究證據，見筆記分頁「AI重點」。
