# 外部 helper 協定

[English](../helper-protocol.md) | 繁體中文

## 為何需要外部 helper

應用程式執行於自己的 uv 管理環境時，不能安全替換該環境。Windows 可能仍鎖住執行檔或模組，其他平台也可能留下部分更新的 runtime。helper 因此使用工具環境外的作業系統 shell，等待主程式消失後執行 uv、保存結果，再重新啟動已解析的命令。

helper 不接收任意命令字串。Python 只會以已驗證欄位產生平台專用腳本，並傳入正整數 host PID。

## 不可變更新計畫

每個 schema version 1 工作階段包含：隨機 UUID、canonical 套件識別、helper/uv/命令/結果/記錄/鎖的絕對路徑、前後 PEP 440 版本、陣列形式的重啟參數、失敗時是否重啟，以及有限且大於零的主程式退出逾時。旁邊的 plan JSON 只供診斷；helper 內已嵌入驗證與平台引用後的值。

## Windows

- 使用系統內建 Windows PowerShell；`CREATE_NO_WINDOW` 隱藏 helper 主控台。
- 不使用 `DETACHED_PROCESS`，避免 PowerShell 5.1 搭配 null standard handles 時立即退出。
- 每 250ms 以 `Get-Process -Id` 輪詢 host。
- 透過 `Start-Process -Wait -PassThru` 取得可靠的 uv 數字退出碼。
- stdout/stderr 分別導向暫存檔，以 UTF-8 解碼後合併，避免正常 stderr 進度被當成 `NativeCommandError`。
- 使用絕對路徑與 literal argument array 重新啟動。
- 只用非遞迴 `Directory.Delete(path, false)` 移除套件鎖。
- helper 腳本以含 BOM 的 UTF-8 寫入，確保 PowerShell 5.1 正確解析非 ASCII 路徑；結果讀取接受有 BOM 與無 BOM 的 UTF-8。

## macOS/Linux

- 使用 `/bin/sh`，不依賴 bash 或 zsh。
- 每秒以 `kill -0` 檢查 host，逾時可限制 PID 重用風險。
- 所有靜態值使用 `shlex.quote`，不會二次 eval。
- uv stdout/stderr 導向私人 UTF-8 記錄，重新啟動時斷開 stdin 並置於背景。
- JSON 由預先編碼的片段與受控數值/狀態組成，先寫暫存檔再以 `mv` 發布。
- 清理只點名確切 plan、helper 與空鎖目錄。

## 結果 schema

```json
{
  "schema_version": 1,
  "session_id": "c7d9d7e7-8420-4c55-8274-ceb3b1f44095",
  "package_name": "fshot",
  "previous_version": "0.0.10",
  "requested_version": "0.0.11",
  "actual_version": null,
  "uv_exit_code": 0,
  "status": "succeeded",
  "started_at": "2026-08-16T12:00:00Z",
  "finished_at": "2026-08-16T12:00:09Z",
  "log_path": "...",
  "error": null
}
```

helper 不會匯入被替換的環境，因此 `actual_version` 為 null；重新啟動的主程式會在消費結果時補上邏輯值。uv 退出碼為零但版本未變時，狀態會改為 `NO_CHANGE`。

## 失敗行為

| 條件 | 結果 | 是否嘗試升級 | 是否重啟 |
| --- | --- | --- | --- |
| 主程式退出逾時 | `app_exit_timeout` | 否 | 否 |
| uv 非零退出碼 | `failed` | 是 | `restart_on_failure=True` 時 |
| uv 零退出碼 | 暫定 `succeeded` | 是 | 是 |
| 重啟失敗 | `restart_failed` | 可能 | 失敗 |

helper 不會終止主程式，也不會自動重試會改變狀態的操作。記錄會對標示為 token、password、authorization 的值做基本遮罩，但敏感資料仍不應出現在重啟參數或安裝器輸出中。
