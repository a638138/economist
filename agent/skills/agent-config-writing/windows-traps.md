# Windows 靜默陷阱檢查清單

agent-config-writing skill 的附檔，整理日期：2026 年 11 月 14 日。適用於在 Windows 上開發、建置或執行的專案，非英文語系（例如繁體中文 cp950）的陷阱特別多。建立或檢查專案的 CLAUDE.md 時使用：逐項查專案現況，有風險的寫進 CLAUDE.md「違反了也不會報錯」那一節，並向使用者提議哨兵測試（專門確認陷阱不存在的小測試，環境一變就失敗）。只提議，不要擅自改建置設定、轉檔或安裝 hook，由使用者決定。

## 用法

1. 逐項執行「怎麼查」，記下結果：沒問題、有風險、不適用（例如沒有 C++ 的專案跳過 MSVC 項目）、無法判斷。
2. 有風險的項目：寫進 CLAUDE.md 陷阱一節（一行說明現象，一行說明正確做法），並提議對應的修正與哨兵測試。
3. 無法判斷的項目：列出來問使用者，不要猜。
4. 專案特有、這份清單沒有的陷阱：問使用者過去踩過哪些，一併寫進陷阱一節。
5. 每一項的修法都要先確認不會引入另一個陷阱；下面已標出常見的二次陷阱。

## C++ 原始碼與字串的編碼（MSVC）

- 現象：MSVC 讀沒有 BOM 的原始碼時用系統編碼（cp950），UTF-8 的中文註解可能吃掉換行，下一行程式碼消失；一般字串常值 `"中文"` 也會以 cp950 存進執行檔。通常只有 C4819 警告，編譯照樣通過。
- 怎麼查：每個 C／C++ 編譯是否都有 `/utf-8`（看 compile_commands.json 或專案檔）；建置 log 有沒有 C4819；用嚴格 UTF-8 解碼掃過所有原始碼，找出不是 UTF-8 的檔（台灣的舊專案常有 Big5）。
- 怎麼修：先把非 UTF-8 的原始碼列給使用者，轉成 UTF-8 後，再對所有 C++ 目標加 `/utf-8`。CMake 用 `$<$<COMPILE_LANGUAGE:CXX>:/utf-8>`；CUDA 的 .cu 要另外加 `-Xcompiler=/utf-8`，否則主機端程式碼一樣被當成 cp950。.rc 資源檔加 `#pragma code_page(65001)`。可以加 `/we4819` 把警告變成錯誤。
- 二次陷阱：還有 Big5 原始碼時就加 `/utf-8`，那些檔的字串會靜默變成別的位元組。
- 哨兵測試：CI 檢查 compile_commands.json 每一筆 C／C++ 編譯都有 `/utf-8`；在每個目標都會 include 的標頭放 `static_assert(sizeof(u8"中文") == 7, "source not read as UTF-8");` 與 `static_assert(sizeof("中文") == 7, "execution charset is not UTF-8");`。

## 含中文的路徑

- 現象：MSVC 上 char* 路徑用系統編碼解讀，包括 `fopen`、`std::ifstream(std::string)`、`LoadLibraryA`、`std::filesystem::path(std::string)`；UTF-8 的路徑字串會打不開，cp950 沒有的字元一律失敗。使用者名稱是中文時，TEMP 路徑也含中文，部分工具會失敗。
- 怎麼查：搜尋用 char* 或 std::string 開檔、載入 DLL 的地方；專案路徑或使用者資料夾是否含中文。
- 怎麼修：Windows 上用寬字元 API（`_wfopen`、`std::filesystem::path` 搭配 wstring 或 `u8path`）；跨語言介面明確約定路徑的編碼。
- 哨兵測試：在含中文與 ✓ 的暫存資料夾裡，用專案自己的開檔函式寫入再讀回。

## 建置相依（CMake＋Ninja＋MSVC）

- 現象：Ninja 靠比對 MSVC `/showIncludes` 訊息的前綴記錄標頭相依；中文版 MSVC 的前綴與編碼對不上時，專案標頭沒被記下，改了標頭也不會重編，連進舊的目標檔。
- 怎麼查：建置後對一個一定 include 專案標頭的目標檔執行 `ninja -t deps <目標檔>`，看有沒有列出那個標頭（Ninja 本來就不記錄 Program Files、Visual Studio 底下的系統標頭，所以只 include 系統標頭的目標檔顯示 0 筆是正常的）；或改一個專案標頭的時間戳，執行 `ninja -n` 看相關目標檔是否會重編。也可以比對 CMakeCache.txt 的 `CMAKE_CL_SHOWINCLUDES_PREFIX` 和目前 cl 實際輸出的前綴。
- 怎麼修：先更新 CMake（舊版有這個編碼問題）；或在建置環境設 `VSLANG=1033` 讓 MSVC 輸出英文（需裝有英文語言套件）。
- 二次陷阱：CMake 在 configure 時就記下前綴。在已經 configure 過的建置目錄才改 `VSLANG`，或之後從沒設的 shell、IDE 建置，前綴反而對不上。改完要刪掉建置目錄重新 configure，而且每次建置的環境都要一致。
- 哨兵測試：放一個一定 include 某個專案標頭的哨兵 .cpp，建置腳本最後用 `ninja -t deps` 確認它記到那個標頭，沒有就讓建置失敗。

## Python 的文字編碼

- 現象：Python 3.15 以前，沒指定 encoding 的 `open()`、`read_text()` 都用系統編碼（cp950）：中文會「成功」以 cp950 寫出，下游工具當 UTF-8 讀就變亂碼；遇到 ✓、µ 等 cp950 沒有的字元則出錯或截斷檔案。stdout 被導向管線或檔案時（agent 透過工具執行時幾乎都是），`print` 這些字元會 UnicodeEncodeError。
- 怎麼查：用 `python -X warn_default_encoding -W error::EncodingWarning -m pytest`（3.10 起）找出沒指定編碼的地方，或用 ruff 規則 PLW1514；查 Python 版本與是否設了 `PYTHONUTF8`。
- 怎麼修：讀寫檔案一律寫 `encoding="utf-8"`；給 Excel 開的 CSV 用 `utf-8-sig`；既有的 cp950 資料檔要照它實際的編碼讀，不能直接改成 utf-8。輸出用 `PYTHONIOENCODING=utf-8` 或 `sys.stdout.reconfigure(encoding="utf-8")`。
- 二次陷阱：subprocess 的輸出編碼由子程序決定，cl.exe、cmd 內建指令等原生工具在 cp950 環境輸出 cp950。3.15 預設 UTF-8 之後，`text=True` 會用 UTF-8 解碼這些輸出而失敗；有 `errors="replace"` 時則變成靜默亂碼。subprocess 的 encoding 要對應子程序實際的輸出編碼（例如 cp950 或 oem）。
- 哨兵測試：用 `-X utf8=0` 執行一個測試：以專案自己的寫檔函式寫入 `"✓µ中文"`，用 `read_bytes()` 和 `"✓µ中文".encode("utf-8")` 比對。開發機已是 3.15 或設了 `PYTHONUTF8=1` 時，不加 `-X utf8=0` 會遮住問題。

## 換行

- 現象：Windows 上 Python 用文字模式寫檔會把 `\n` 變成 `\r\n`；git 的 `core.autocrlf` 也會轉換。只改幾行的修改可能變成整個檔案的 diff。
- 怎麼查：有沒有 `.gitattributes`；`git config core.autocrlf`；`git ls-files --eol` 的 `i/` 欄（repo 內的換行）。
- 怎麼修：加 `.gitattributes`（例如 `* text=auto`，二進位檔標 `binary`），既有 repo 要 `git add --renormalize .`，會產生一個大的正規化提交，先告訴使用者。Python 改寫既有檔案時，讀和寫都用 `newline=""`（或用 bytes 讀寫）保留原本的換行；新檔用 `newline="\n"`。
- 哨兵測試：CI 檢查 `git ls-files --eol`，文字檔的 `i/` 欄全部是 `i/lf`（或 `i/none`），出現 `i/crlf` 或 `i/mixed` 就失敗。

## Shell、PowerShell 與管線

- 現象：bash 的 heredoc 分隔字沒加引號時，`\\` 會變成 `\`、`$` 與反引號會被展開。PowerShell 5.1 的 `>` 與 `Out-File` 預設寫 UTF-16，`Set-Content` 預設寫系統編碼；`$OutputEncoding` 預設 ASCII，`"中文" | python x.py` 送進去的是 `??`；解碼原生程式的輸出用 cp950，程式輸出 UTF-8 時變成亂碼，連 agent 讀到的錯誤訊息都會是亂碼。
- 怎麼查：搜尋腳本裡沒加引號的 heredoc（`<<`、`<< `、`<<-` 後面接分隔字）與 PowerShell 的重導向寫檔。
- 怎麼修：heredoc 一律用 `<<'EOF'`，並在 CLAUDE.md 寫明 agent 自己用 shell 寫檔也一律如此。PowerShell 5.1 寫無 BOM 的 UTF-8 用 `[IO.File]::WriteAllText($p, $s, [Text.UTF8Encoding]::new($false))`，或改用 PowerShell 7 的 `-Encoding utf8NoBOM`；管線前設 `$OutputEncoding` 與 `[Console]::OutputEncoding` 為 UTF-8。
- 二次陷阱：PowerShell 5.1 的 `-Encoding utf8` 會寫出帶 BOM 的 UTF-8，shebang 會失效、`json.load` 會失敗、CSV 第一欄名稱多一個看不見的字元。
- 哨兵測試：CI 掃描 repo 的文字檔，必須能用嚴格 UTF-8 解碼，而且沒有 UTF-16 或 UTF-8 BOM。

## 字元處理

- 現象：`"µ".upper()` 會變成希臘字母 `Μ`，看起來像 M，單位或代號被大寫化後意思就變了。C 的 `isspace`、`toupper` 等函式收到 UTF-8 中文的位元組（負的 char）是未定義行為：Debug 版觸發 assert，Release 版靜默得到錯的結果。
- 怎麼查：搜尋對單位字串、識別碼做 `upper()`、`lower()` 的地方；搜尋把 char 直接傳給 `<cctype>` 函式的地方。
- 怎麼修：單位與識別碼不做大小寫轉換；`<cctype>` 函式的參數先轉成 `unsigned char`。
- 哨兵測試：單元測試確認專案的單位處理函式保留 `"µs"` 不變。

## 靜默退回與載入錯的版本

- 現象：GPU 後端初始化失敗時自動改用 CPU；DLL 名稱或路徑不對時從 PATH 載入到另一個版本。結果可能正確，只是慢或行為不同，沒有任何警告。
- 怎麼查：搜尋 fallback、自動退回的程式路徑；確認啟動時有沒有記錄實際用的後端與載入的 DLL 完整路徑。
- 怎麼修：啟動時記錄實際後端與 DLL 路徑；退回時至少發出警告。
- 哨兵測試：測試讀環境變數指定預期的後端（例如 `EXPECTED_BACKEND=CUDA`），實際不符就失敗；檢查載入的 DLL 來自建置輸出資料夾。

## 吞掉的例外

- 現象：例外被 catch 後當成正常情況處理，問題只表現為偶發的卡住或資料錯誤，log 裡什麼都沒有。
- 怎麼查：搜尋 `catch (...)`、空的 catch 區塊、`except:`、`except Exception: pass`。
- 怎麼修：至少記錄例外；只 catch 預期中的例外型別。
- 哨兵測試：CI 用 grep 或 lint 規則擋下新的空 catch。

## 路徑長度

- 現象：Windows 預設路徑上限 260 字元，超過時檔案或 DLL 會讀不到，有時只表現為退回到別的實作。
- 怎麼查：建置輸出與相依套件的實際路徑長度；系統是否啟用長路徑。
- 怎麼修：縮短建置目錄的路徑；必要時啟用長路徑支援，並確認相關工具也支援。
- 哨兵測試：CI 檢查建置輸出裡最長的路徑小於一個門檻（例如 200 字元）。

## 計時與等待

- 現象：`GetTickCount` 等預設計時器約 15.6 ms 才跳一次，量比這短的間隔會得到 0 或 15.6 ms 的倍數。`Sleep(1)` 預設也可能睡到約 15.6 ms，即時迴圈的節奏會被拉長。
- 怎麼查：搜尋計時與等待用的函式。
- 怎麼修：量時間用 `QueryPerformanceCounter`、`std::chrono::steady_clock`、Python 的 `time.perf_counter()`；需要短而準的等待時用 `timeBeginPeriod` 或高解析度 waitable timer（`CREATE_WAITABLE_TIMER_HIGH_RESOLUTION`），並先跟使用者確認對耗電與系統的影響。
- 哨兵測試：重複讀專案用的時鐘函式，取最小的非零差值，要求小於一個門檻（例如 1 ms）。
