# 疑難排解

[English](../troubleshooting.md) | 繁體中文

## `Package 'uv-tool-updater' was not found`

目前版本可讀取，但預設 provider 在公開 PyPI 找不到專案。現在正式套件位於 `https://pypi.org/project/uv-tool-updater/`；若是本機路徑測試，可用：

```console
show-version --latest-version 0.1.6
```

此選項只模擬 metadata，`uv tool upgrade` 仍使用 uv 記錄的來源。

## `Update helper exited immediately`

請確認安裝的是 0.1.2 以上版本。早期 Windows build 將 `DETACHED_PROCESS` 與 null standard handles 合用，導致 Windows PowerShell 5.1 立即退出。可先以 `uv tool install --force uv-tool-updater` 手動 bootstrap。

## 記錄只有 `Building ...` 或 uv 退出碼為 null

請確認版本至少為 0.1.2。早期 helper 把 native stderr 送入 PowerShell pipeline，而 `$ErrorActionPreference` 為 `Stop`，使正常 uv 進度被誤判為例外。新版會分開重新導向 stdout/stderr，並直接讀取程序退出碼。

## 重啟後沒有顯示更新結果

Windows 隱藏 helper 啟動的 console command 可能沒有互動終端。`show-version` 會保留尚未消費的結果；請在原終端手動再執行一次 `show-version`。GUI 主程式不受影響。

## `A session is already pending`

先檢查是否仍有 PowerShell 或 `/bin/sh` helper 執行，並查看狀態目錄中的 plan/result。更新可能仍在進行時不可刪除鎖。

確認 helper 已停止後，只移除以下空目錄：

```text
.<canonical-package-name>.update.lock
```

不可刪除 uv tool 目錄或整個共用應用程式狀態根目錄。

## 安裝方式不受支援

執行 `uv tool list --show-version-specifiers`，確認應用程式是 uv tool。Editable checkout、`uv run`、一般 virtual environment、uvx cache、命令 shim 缺失及路徑不明確都會刻意拒絕自動更新。

## 蒐集診斷資訊

可安全提供的資料包括 updater 版本與作業系統、`UpdateStatus`/`InstallStatus`、uv 數字退出碼、已遮罩 helper log、結果 schema 與時間戳，以及套件來源類型。不要附上完整環境變數、registry 憑證、索引 token 或未遮罩的私有 URL。
