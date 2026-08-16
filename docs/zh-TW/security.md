# 安全模型

[English](../security.md) | 繁體中文

Release provider 與 uv 安裝器是分離的信任領域。provider metadata 永遠不能選擇執行檔、套件來源、腳本或任意安裝參數。唯一的變更路徑是 `uv tool upgrade <已驗證套件名稱>`；索引、限制、下載與環境替換仍由 uv 負責。

命令不會透過 `shell=True` 執行。產生的 helper 會依平台對絕對執行檔路徑與重啟參數陣列進行 literal quoting。工作階段名稱使用隨機值，狀態與結果以原子替換寫入；Unix 權限限制為目前使用者；清理只處理該工作階段明確擁有的檔案。

helper 只等待主程式正常退出。逾時會取消更新，不會終止程序。每套件目錄鎖可防止同時準備多個工作階段。記錄會對標示為 token、password 或 authorization 的值做基本遮罩；應用程式仍應避免把秘密放入重啟參數，因作業系統可能公開程序參數。

自訂 provider 必須採用適合其索引的傳輸與驗證方式。內建 PyPI provider 拒絕非 HTTPS base URL，也不會記錄 request header 或環境變數。
