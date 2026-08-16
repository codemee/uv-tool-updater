# 測試指南

[English](../testing.md) | 繁體中文

安裝測試依賴並執行測試套件：

```console
uv sync --extra test
uv run pytest
```

單元測試會模擬 metadata、網路與 subprocess 邊界，涵蓋 PEP 440 版本選擇、yanked/預發布政策、保守式安裝偵測、結構化命令、惡意路徑與參數、工作階段鎖、原子結果，以及重啟後的版本確認。

CI 在 Windows、macOS、Linux 與支援的 Python 版本上執行，並額外建置 wheel/sdist、從 wheel 隔離安裝及確認公開版本。

後續整合測試可把 fixture tool 1.0.0 與 1.1.0 建置到暫時 flat index。安裝前必須將 `UV_TOOL_DIR` 與 `UV_TOOL_BIN_DIR` 都指向測試專用暫存目錄，並在任何升級前斷言解析後路徑正確；不得繼承開發者真正的 tool 目錄。
