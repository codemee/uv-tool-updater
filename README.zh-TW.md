# uv-tool-updater

[English](README.md) | 繁體中文

`uv-tool-updater` 為透過 `uv tool install` 安裝的 Python CLI、桌面與系統匣應用程式協調安全更新。它不自行修改工具環境；主程式結束後，實際安裝工作會交由 `uv tool upgrade` 完成。

> 狀態：早期 MVP（`0.1.7`）。在 1.0 之前，公開 API 與結果結構仍可能調整。

## 安裝

```console
uv add uv-tool-updater
```

主程式必須提供目前使用者專用的狀態目錄。核心套件刻意不依賴 `platformdirs`，讓應用程式可沿用既有的設定與資料目錄。

## 互動式更新實測

將本專案安裝為 uv tool，然後執行隨附的測試命令：

```console
uv tool install uv-tool-updater
show-version
```

`show-version` 會顯示目前版本、查詢 PyPI，並在有新版時詢問是否更新。只有輸入 `y` 或 `Y` 才會啟動外部 helper。原程式結束後，helper 會以已驗證的目標版本執行 `uv tool upgrade uv-tool-updater==<版本>`，再重新啟動 `show-version` 以回報結果。

若要使用隔離的測試狀態目錄，請設定 `UV_TOOL_UPDATER_STATE_DIR`。若尚未發布新版，也可只模擬版本 metadata：

```console
show-version --latest-version 0.1.7
```

此參數只替換版本檢查資料；實際更新仍使用 uv 記錄的安裝來源。在 Windows 上，由隱藏 helper 重新啟動的主控台命令可能沒有互動終端；此時請在原本的終端再執行一次 `show-version`，即可讀取更新結果。

## 最小整合範例

```python
import os
from pathlib import Path

from uv_tool_updater import UpdateStatus, Updater

updater = Updater(
    package_name="fshot",
    command_name="fshot",
    state_dir=Path.home() / ".local" / "state" / "fshot" / "updates",
)

# GUI 應用程式應在線程池執行同步網路操作。
check = updater.check()
if check.status is UpdateStatus.UPDATE_AVAILABLE and check.release is not None:
    # 必須先儲存資料，或取得使用者同意放棄未儲存內容。
    session = updater.prepare_update(check.release, restart_args=[])
    session.start_helper(host_pid=os.getpid())
    # 只有 helper 成功啟動後，才讓框架正常結束程式。
```

重新啟動時呼叫 `updater.consume_latest_result()`，或處理 `pending_results()` 回傳的路徑。結果消費程序會重新讀取實際安裝版本；單憑 uv 回傳碼為零，不會宣稱版本已成功變更。

## 保證與限制

- 支援 Python 3.10–3.14，以及 Windows、macOS、Linux。
- 預設查詢公開 PyPI；測試或私有索引可注入 `StaticProvider` 或自訂 `ReleaseProvider`。
- 預設只選穩定版，預發布版本必須明確啟用。
- 非 uv tool、editable install 或無法確認的安裝方式會拒絕自動更新。
- helper 預設最多等待主程式 10 分鐘，而且永遠不會強制終止主程式。
- 更新失敗時預設仍會重新啟動原命令，並保留本機記錄。
- 無遙測，也不依賴特定 GUI 框架。

## 技術文件

- [架構與生命週期](docs/zh-TW/architecture.md)
- [主程式整合指南](docs/zh-TW/integration.md)
- [外部 helper 協定](docs/zh-TW/helper-protocol.md)
- [安全模型](docs/zh-TW/security.md)
- [測試指南](docs/zh-TW/testing.md)
- [疑難排解](docs/zh-TW/troubleshooting.md)
- [發布流程](docs/zh-TW/releasing.md)
- [繁體中文原始規格](docs/uv-tool-updater-spec.md)
- [版本紀錄](CHANGELOG.md)
