# Host integration guide

English | [繁體中文](zh-TW/integration.md)

## Basic flow

Create one `Updater` for the installed distribution and the console entry point that should be restarted:

```python
from pathlib import Path
from uv_tool_updater import Updater

updater = Updater(
    package_name="fshot",
    command_name="fshot",
    state_dir=Path(application_state_directory) / "updates",
)
```

`state_dir` must be private to the current user. The core intentionally does not depend on `platformdirs`; the host should reuse its established application-data location.

## Checking

```python
from uv_tool_updater import UpdateStatus

check = updater.check(timeout=5.0, allow_prereleases=False)
if check.status is UpdateStatus.UPDATE_AVAILABLE:
    present_update(check.release)
elif check.status is UpdateStatus.UNSUPPORTED_INSTALLATION:
    present_manual_update_guidance(check)
```

`check()` is synchronous. GUI applications must call it on a worker thread and marshal the immutable `UpdateCheck` back to the UI thread. A provider/network failure is represented as `CHECK_FAILED`; it should normally be logged or shown only for an explicit manual check.

## Preparing and exiting

The host owns all data-loss decisions. Save documents or obtain explicit permission before preparing a session:

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
    # Do not exit: the helper was not safely established.
    raise

# Only after start_helper returned successfully:
application.quit_normally()
```

`prepare_update()` creates an immutable plan and acquires the session lock, but does not invoke uv. `start_helper()` launches a process outside the tool environment and performs a short liveness check. The updater never calls a GUI framework's quit API.

If the user cancels after preparation but before launch, call `session.cancel()` to remove the helper, plan, and lock.

## Reading results

At normal startup:

```python
result = updater.consume_latest_result()
if result is not None:
    show_update_result(result)
```

Consumption reads the actual installed version through `importlib.metadata`, reconciles it with the provisional helper result, and renames the JSON file with a `.consumed` suffix. Invalid or unknown-schema files are ignored by result discovery and retained for diagnosis.

## Custom release providers

Implement the structural `ReleaseProvider` protocol for private registries or offline metadata:

```python
from packaging.version import Version
from uv_tool_updater import ReleaseInfo

class CorporateProvider:
    def latest_release(self, package_name, *, allow_prereleases=False, timeout=5.0):
        metadata = fetch_internal_metadata(package_name, timeout=timeout)
        return ReleaseInfo(package_name=package_name, version=Version(metadata["version"]))
```

Pass the provider to `Updater(provider=CorporateProvider())`. Provider authentication must stay inside the provider and must never be copied into session files or logs.

## Host policy

Recommended automatic-check policy:

- delay startup checks by approximately five seconds;
- check automatically at most once every 24 hours;
- let manual checks bypass the interval;
- allow users to disable automatic checks and skip a version;
- do not show blocking dialogs for background network failures;
- keep prerelease selection explicit and disabled by default.

`JsonStateStore` and `check_is_due()` are optional helpers. Applications may instead use QSettings, the registry, a database, or their existing configuration layer.

## CLI smoke test

`show-version` exercises the package against itself. Before a PyPI release exists, `--latest-version` injects only the release metadata:

```console
show-version --latest-version 0.1.6
```

The real mutation is still `uv tool upgrade uv-tool-updater`; uv uses the source stored at installation. For a local-path test, install version N, change the source metadata to N+1 without reinstalling, then request N+1 with this flag.
