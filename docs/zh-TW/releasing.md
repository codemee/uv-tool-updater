# 發布流程

[English](../releasing.md) | 繁體中文

## 前置條件

1. 選擇 PyPI 尚未使用的 PEP 440 版本；已發布檔案不可覆寫。
2. 更新 `pyproject.toml` 的 `[project].version`。
3. 新增帶日期的 changelog 條目。
4. 確認 tag 為 `v<version>`，並與套件 metadata 一致。
5. 確認 GitHub Release 與 PyPI 專案連結指向本儲存庫。

## 本機驗證

```console
uv sync --extra test
uv run pytest
uv build --clear
```

檢查 wheel 與 sdist metadata，並在隔離環境安裝 wheel：

```console
uv run --isolated --with dist/uv_tool_updater-<version>-py3-none-any.whl \
  python -c "import uv_tool_updater; print(uv_tool_updater.__version__)"
```

發布前確認 `dist` 只有該版本預期的 wheel 與 sdist。

## GitHub

提交 release、推送預設分支、在精確提交上建立 tag，並用 changelog 內容建立 GitHub Release。支援的 Python 版本必須在 Windows、macOS 與 Linux CI 全數通過。

## PyPI

建議使用 GitHub `pypi` environment 的 PyPI Trusted Publishing。workflow 只需要 `id-token: write`，而且會在測試通過後重新建置並發布成品。

首次授權的本機發布也可使用：

```console
uv publish dist/uv_tool_updater-<version>*
```

API token 必須透過 `UV_PUBLISH_TOKEN` 或安全的互動式憑證機制提供，不能放入命令參數、儲存庫檔案、記錄或 shell history。上傳後應查詢特定版本 JSON endpoint，核對 wheel/sdist 檔名、hash、`requires_python`、專案 URL 與版本 metadata。

## 發布後實測

```console
uv tool install uv-tool-updater==<version>
show-version
```

第一個公開版本無法自動更新尚未發布的本機安裝，需要一次手動 bootstrap。存在較高公開版本後，再測試完整更新流程。
