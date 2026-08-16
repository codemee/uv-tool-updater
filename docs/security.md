# Security model

English | [繁體中文](zh-TW/security.md)

The release provider and uv installer are separate trust domains. Provider metadata is never used to select an executable, package source, script, or arbitrary installer option. `uv tool upgrade <validated-package-name>` remains the only mutation path, and uv retains responsibility for indexes, constraints, downloads, and environment replacement.

Commands are never passed through `shell=True`. The generated helpers use platform-specific literal quoting for absolute executable paths and restart argument arrays. Session names are random, state/result writes use atomic replacement, Unix permissions are restricted to the current user, and cleanup targets only explicit files belonging to the session.

The helper waits for normal host exit. Timeout cancels the update without killing the process. A per-package directory lock prevents concurrent prepared sessions. Logs receive basic masking for values labelled token, password, or authorization; applications should still avoid placing secrets in restart arguments because operating systems can expose process arguments.

Custom providers must use transport and authentication appropriate to their index. The bundled PyPI provider rejects non-HTTPS base URLs and never logs request headers or environment variables.
