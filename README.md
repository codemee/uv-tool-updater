# uv-tool-updater

`uv-tool-updater` coordinates safe updates for Python CLI, desktop, and tray applications installed by `uv tool install`. It does not modify an environment itself: installation is delegated to `uv tool upgrade`, after the host process exits.

> Status: early MVP (`0.1.4`). The public API and result schema may evolve before 1.0.

## Install

```console
uv add uv-tool-updater
```

The host must provide a private state directory. This avoids imposing a platform-directory dependency and lets GUI applications use their existing settings location.

## Interactive update smoke test

Install this project as a uv tool, then run the bundled test command:

```console
uv tool install uv-tool-updater
show-version
```

`show-version` prints the installed version, checks PyPI, and asks before updating when a newer release exists. Only `y` or `Y` starts the normal external-helper update flow. The command exits, `uv tool upgrade uv-tool-updater` runs after that process has ended, and `show-version` is restarted to report the result.

For an isolated test state directory, set `UV_TOOL_UPDATER_STATE_DIR` before running the command.

Before the project is published to PyPI, simulate release metadata with:

```console
show-version --latest-version 0.1.4
```

This option changes only the metadata used by the version check. The update itself still runs `uv tool upgrade uv-tool-updater` and therefore uses the source saved by uv. For a local-path installation, change the project version and source first, while leaving the installed tool on the older version, then run the command with that newer version number.

On Windows, a console command restarted by the hidden helper may not receive an interactive terminal. In that case it exits without consuming the result; run `show-version` once more in the existing terminal to display the completed update result.

## Minimal integration

```python
import os
from pathlib import Path

from uv_tool_updater import UpdateStatus, Updater

updater = Updater(
    package_name="fshot",
    command_name="fshot",
    state_dir=Path.home() / ".local" / "state" / "fshot" / "updates",
)

# Run this synchronous network operation on a worker thread in GUI applications.
check = updater.check()
if check.status is UpdateStatus.UPDATE_AVAILABLE and check.release is not None:
    # The host must first save data or receive explicit permission to discard it.
    session = updater.prepare_update(check.release, restart_args=[])
    session.start_helper(host_pid=os.getpid())
    # Only now ask the framework to quit normally.
```

On restart, use `updater.consume_latest_result()` (or consume a path returned by `pending_results()`). Consumption re-reads the actual installed distribution version; a zero `uv` exit code alone is never presented as proof that the version changed.

## Guarantees and limits

- Python 3.10–3.14; Windows, macOS, and Linux.
- Public PyPI metadata by default; inject `StaticProvider` or a custom `ReleaseProvider` for tests/private indexes.
- Stable releases by default; prereleases are opt-in.
- Automatic installation is refused outside a detected uv tool environment and for editable installs.
- The helper waits up to 10 minutes by default and never terminates the host.
- Failed upgrades restart the original command by default and preserve a local log.
- No telemetry and no GUI-framework dependency.

## Documentation

- [Architecture and lifecycle](https://github.com/codemee/uv-tool-updater/blob/main/docs/architecture.md)
- [Host integration guide](https://github.com/codemee/uv-tool-updater/blob/main/docs/integration.md)
- [External helper protocol](https://github.com/codemee/uv-tool-updater/blob/main/docs/helper-protocol.md)
- [Security model](https://github.com/codemee/uv-tool-updater/blob/main/docs/security.md)
- [Testing](https://github.com/codemee/uv-tool-updater/blob/main/docs/testing.md)
- [Troubleshooting](https://github.com/codemee/uv-tool-updater/blob/main/docs/troubleshooting.md)
- [Release procedure](https://github.com/codemee/uv-tool-updater/blob/main/docs/releasing.md)
- [Changelog](https://github.com/codemee/uv-tool-updater/blob/main/CHANGELOG.md)
