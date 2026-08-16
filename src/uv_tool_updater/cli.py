from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

from .errors import UpdaterError
from .models import InstallStatus, ReleaseInfo, UpdateResult, UpdateStatus
from .providers import StaticProvider
from .updater import Updater

PACKAGE_NAME = "uv-tool-updater"
COMMAND_NAME = "show-version"
STATE_DIR_ENV = "UV_TOOL_UPDATER_STATE_DIR"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="顯示版本並測試 uv tool 自動更新流程。")
    parser.add_argument(
        "--latest-version",
        metavar="VERSION",
        help="以指定版本取代 PyPI metadata，供尚未發布套件的本機測試使用。",
    )
    parser.add_argument("--after-update", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    # A console program restarted by the hidden Windows helper may have no
    # interactive terminal. Leave the result unconsumed for the next visible
    # invocation instead of swallowing the update report in the background.
    if args.after_update and not sys.stdin.isatty():
        return 0
    provider = None
    restart_args: tuple[str, ...] = ("--after-update",)
    if args.latest_version is not None:
        try:
            version = Version(args.latest_version)
        except InvalidVersion:
            parser.error(f"無效的 PEP 440 版本：{args.latest_version!r}")
        provider = StaticProvider(ReleaseInfo(PACKAGE_NAME, version))
        restart_args = ("--latest-version", str(version), "--after-update")
    updater = Updater(
        package_name=PACKAGE_NAME,
        command_name=COMMAND_NAME,
        state_dir=default_state_dir(),
        provider=provider,
    )
    return run(updater, restart_args=restart_args)


def run(
    updater: Updater,
    *,
    input_fn: Callable[[str], str] = input,
    output: Callable[[str], Any] = print,
    restart_args: tuple[str, ...] = (),
) -> int:
    """Run the interactive smoke-test command with injectable console I/O."""
    try:
        previous_result = updater.consume_latest_result()
    except (UpdaterError, OSError) as exc:
        output(f"警告：無法讀取上次更新結果：{exc}")
    else:
        if previous_result is not None:
            _show_result(previous_result, output)

    check = updater.check()
    if check.installed is not None:
        output(f"目前版本：{check.installed.current_version}")
    else:
        output("目前版本：無法取得")

    if check.status is UpdateStatus.CHECK_FAILED:
        if check.error_code == "release_not_found":
            output(
                "無法檢查更新：公開 PyPI 找不到 uv-tool-updater。"
                "本機測試可使用 show-version --latest-version <版本>。"
            )
        else:
            output(f"無法檢查更新：{check.message or check.error_code or '未知錯誤'}")
        return 1

    if check.status is UpdateStatus.UP_TO_DATE:
        latest = check.release.version if check.release is not None else check.installed.current_version
        output(f"已是最新版本（{latest}）。")
        return 0

    if check.status is UpdateStatus.UNSUPPORTED_INSTALLATION:
        if (
            check.installed is not None
            and check.release is not None
            and check.release.version > check.installed.current_version
        ):
            output(f"有新版本 {check.release.version}，但目前不是由 uv tool 管理，無法自動更新。")
        else:
            output("沒有可用的新版本；目前安裝方式不支援自動更新。")
        return 0

    if check.release is None:
        output("無法檢查更新：provider 未提供 release metadata。")
        return 1

    try:
        answer = input_fn(f"有新版本 {check.release.version}，是否更新並重新啟動？ [y/N] ")
    except (EOFError, KeyboardInterrupt):
        output("已取消更新。")
        return 0
    if answer.strip().lower() != "y":
        output("已取消更新。")
        return 0

    try:
        session = updater.prepare_update(check.release, restart_args=list(restart_args))
        helper_pid = session.start_helper(host_pid=os.getpid())
    except (UpdaterError, OSError, ValueError) as exc:
        output(f"無法啟動更新程序：{exc}")
        return 1
    output(f"更新程序已啟動（helper PID {helper_pid}）；本程式即將結束，完成後會自動重新啟動。")
    return 0


def default_state_dir(
    environ: Mapping[str, str] | None = None,
    *,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    environment = os.environ if environ is None else environ
    override = environment.get(STATE_DIR_ENV)
    if override:
        return Path(override).expanduser().resolve(strict=False)
    platform = sys.platform if platform is None else platform
    home = Path.home() if home is None else home
    if platform == "win32":
        base = Path(environment.get("LOCALAPPDATA", home / "AppData" / "Local"))
    elif platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(environment.get("XDG_STATE_HOME", home / ".local" / "state"))
    return (base / PACKAGE_NAME / COMMAND_NAME).resolve(strict=False)


def _show_result(result: UpdateResult, output: Callable[[str], Any]) -> None:
    if result.status is InstallStatus.SUCCEEDED:
        output(f"上次更新成功：{result.previous_version} → {result.actual_version or '未知版本'}")
    elif result.status is InstallStatus.NO_CHANGE:
        output(f"上次更新完成，但版本仍為 {result.actual_version or result.previous_version}。")
    else:
        detail = f"：{result.error}" if result.error else ""
        output(f"上次更新結果：{result.status.value}{detail}")
        if result.log_path is not None:
            output(f"更新記錄：{result.log_path}")


if __name__ == "__main__":
    raise SystemExit(main())
