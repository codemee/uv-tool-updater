# 架構與生命週期

[English](../architecture.md) | 繁體中文

## 設計目標

`uv-tool-updater` 只負責更新協調，不成為第二套套件安裝器。它不下載 wheel、不覆寫 `site-packages`、不修改 uv receipt，也不決定套件索引。唯一會改變安裝狀態的命令是：

```text
<uv 絕對路徑> tool upgrade <已驗證的 distribution 名稱>
```

uv 持續負責依賴解析、索引驗證、版本限制、快取與工具環境替換；updater 則負責版本發現、主程式生命週期、結果保存與重新啟動。

## 元件

| 模組 | 職責 | 副作用 |
| --- | --- | --- |
| `models.py` | 不可變公開資料類別與狀態 enum | 無 |
| `errors.py` | 帶有穩定錯誤碼的型別化例外 | 無 |
| `providers.py` | 查詢發布 metadata | `PyPIJsonProvider` 會使用 HTTPS |
| `installation.py` | 偵測安裝 metadata、uv、工具根目錄與命令 | 執行 `uv tool dir` |
| `checker.py` | PEP 440 比較與檢查狀態映射 | 無 |
| `backend.py` | 驗證套件名稱並建立固定參數向量 | 無 |
| `session.py` | 鎖定、更新計畫、helper 產生與啟動 | 建立工作階段檔案並啟動 helper |
| `result.py` | 原子化 JSON、解析與重啟後確認 | 原子改名與結果消費標記 |
| `state.py` | 選用的 JSON 主程式政策狀態 | 原子化 JSON 寫入 |
| `updater.py` | 公開 facade | 委派給上述模組 |
| `cli.py` | 互動式自我更新測試 | 主控台 I/O 與 facade 呼叫 |

## 狀態流程

```text
CHECK
  ├─ provider 失敗 ───────────────> CHECK_FAILED
  ├─ 非支援的 uv tool 安裝 ───────> UNSUPPORTED_INSTALLATION
  ├─ 最新版 <= 已安裝版 ──────────> UP_TO_DATE
  └─ 最新版 > 已安裝版 ───────────> UPDATE_AVAILABLE
                                          │
PREPARE <─────────────────────────────────┘
  驗證套件、版本、路徑與參數；取得每套件鎖；寫入計畫與 helper
                                          │
START
  啟動隱藏 PowerShell 或獨立 /bin/sh；確認 helper 未立即退出
                                          │
HOST EXIT
  主程式儲存資料並正常退出；updater 不會強制終止它
                                          │
HELPER
  等待逾時 ───────────────────────> APP_EXIT_TIMEOUT
  uv tool upgrade 非零 ───────────> FAILED
  重新啟動失敗 ───────────────────> RESTART_FAILED
  uv 暫定成功 ────────────────────> SUCCEEDED
                                          │
RESTARTED HOST
  重新讀取 importlib.metadata.version()
  版本未變 ───────────────────────> NO_CHANGE
  版本已變 ───────────────────────> SUCCEEDED
  原子改名為 .consumed
```

helper 寫入的 `SUCCEEDED` 只是暫定結果。只有重新啟動後的主程式能從新環境讀取 metadata，確認版本確實已改變。

## 安裝偵測

偵測採保守策略：讀取 distribution metadata；依序從明確路徑、`UV` 與 `PATH` 尋找 uv；執行 `uv tool dir`；確認 `sys.prefix` 位於工具根目錄下；拒絕 editable install；最後確認 console command 是真實本機檔案。路徑會盡可能解析 symlink，Windows 則使用不分大小寫比較。證據缺漏或矛盾時會回傳 `managed_by_uv=False`，不影響主程式啟動。

## Provider 與 backend 分離

`ReleaseProvider` 只能提供 distribution 名稱、PEP 440 版本、選用 URL、發布時間與顯示旗標，不能提供執行檔、腳本、安裝參數、索引或憑證。預設 provider 經 HTTPS 讀取 PyPI JSON，拒絕名稱不符、沒有檔案、全部 yanked 的版本，且預設排除預發布版本。

## 並行與復原

準備階段會建立以 canonical distribution 命名的原子目錄鎖，第二個工作階段會被拒絕。取消或完成時只刪除明確且為空的鎖目錄，不會遞迴刪除工具環境。當機可能留下 stale lock；因重新開機與 PID 重用使存活判斷不可靠，所以不會自動破鎖。確認 helper 已停止後，才可依[疑難排解](troubleshooting.md)移除該套件的空鎖目錄。

## 相容性契約

結果 JSON 從 schema version 1 開始。未知 schema 會產生型別化診斷並保留檔案。公開 enum 使用字串值，方便主程式保存與翻譯。1.0 前的資料欄位與 helper 細節仍可能演進，所有相容性變更應記錄於 changelog。
