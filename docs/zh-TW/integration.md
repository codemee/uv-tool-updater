# 主程式整合指南

[English](../integration.md) | 繁體中文

## 基本設定

為已安裝的 distribution 與需重新啟動的 console entry point 建立一個 `Updater`：

```python
from pathlib import Path
from uv_tool_updater import Updater

updater = Updater(
    package_name="fshot",
    command_name="fshot",
    state_dir=Path(application_state_directory) / "updates",
)
```

`state_dir` 必須是目前使用者專用的私人目錄。核心不依賴 `platformdirs`，主程式應沿用既有應用資料位置。

## 檢查更新

```python
from uv_tool_updater import UpdateStatus

check = updater.check(timeout=5.0, allow_prereleases=False)
if check.status is UpdateStatus.UPDATE_AVAILABLE:
    present_update(check.release)
elif check.status is UpdateStatus.UNSUPPORTED_INSTALLATION:
    present_manual_update_guidance(check)
```

`check()` 是同步操作。GUI 應在線程池執行，再把不可變的 `UpdateCheck` 傳回 UI thread。provider 或網路失敗會成為 `CHECK_FAILED`；背景自動檢查通常只記錄，手動檢查才向使用者顯示。

## 準備更新與結束程式

資料遺失決策屬於主程式。請先儲存文件或取得使用者同意，再準備工作階段：

```python
import os

session = updater.prepare_update(
    check.release,
    restart_args=[],
    restart_on_failure=True,
    wait_timeout=600,
)

try:
    session.start_helper(host_pid=os.getpid())
except Exception:
    # helper 尚未安全建立，不可退出主程式。
    raise

application.quit_normally()
```

`prepare_update()` 只建立不可變計畫與鎖，不會呼叫 uv。`start_helper()` 啟動工具環境之外的程序，並短暫檢查它仍存活。若使用者在啟動前取消，呼叫 `session.cancel()` 清除 helper、計畫與鎖。

## 讀取結果

在正常啟動流程中：

```python
result = updater.consume_latest_result()
if result is not None:
    show_update_result(result)
```

消費程序會以 `importlib.metadata` 讀取實際版本，與 helper 的暫定結果核對，再將 JSON 改名為 `.consumed`。無效或未知 schema 的檔案會保留供診斷。

## 自訂 Release Provider

私有 registry 或離線 metadata 可實作結構式 `ReleaseProvider` protocol：

```python
from packaging.version import Version
from uv_tool_updater import ReleaseInfo

class CorporateProvider:
    def latest_release(self, package_name, *, allow_prereleases=False, timeout=5.0):
        metadata = fetch_internal_metadata(package_name, timeout=timeout)
        return ReleaseInfo(package_name=package_name, version=Version(metadata["version"]))
```

以 `Updater(provider=CorporateProvider())` 注入。驗證資訊必須留在 provider 內，不可複製到工作階段檔案或記錄。

## 建議政策

- 啟動後延遲約五秒再自動檢查。
- 自動檢查最多每 24 小時一次，手動檢查可略過間隔。
- 允許停用自動檢查與略過特定版本。
- 背景網路失敗不要顯示阻塞式對話框。
- 預發布版本必須明確選用，預設關閉。

`JsonStateStore` 與 `check_is_due()` 是選用輔助；主程式也可使用 QSettings、registry、資料庫或既有設定層。

## CLI 實測

`show-version` 可讓套件更新自己。未發布版本可使用 `show-version --latest-version 0.1.6` 注入 metadata，但實際變更仍是 `uv tool upgrade uv-tool-updater`，來源由 uv 的安裝記錄決定。
