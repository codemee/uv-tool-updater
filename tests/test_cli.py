from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from packaging.version import Version

from uv_tool_updater.cli import default_state_dir, main, run
from uv_tool_updater.models import InstalledTool, ReleaseInfo, UpdateCheck, UpdateStatus


def installed(*, managed: bool = True) -> InstalledTool:
    return InstalledTool(
        "uv-tool-updater",
        "show-version",
        Version("1.0"),
        Path("C:/bin/show-version.exe"),
        Path("C:/tools/uv-tool-updater"),
        Path("C:/bin/uv.exe"),
        Path("C:/tools"),
        managed,
    )


class FakeUpdater:
    def __init__(self, check: UpdateCheck) -> None:
        self._check = check
        self.prepared = False
        self.started_with: int | None = None

    def consume_latest_result(self):
        return None

    def check(self) -> UpdateCheck:
        return self._check

    def prepare_update(self, release: ReleaseInfo, *, restart_args: list[str]):
        self.prepared = True
        self.restart_args = restart_args
        owner = self

        class Session:
            def start_helper(self, *, host_pid: int) -> int:
                owner.started_with = host_pid
                return 4321

        return Session()


def test_yes_starts_helper_and_reports_exit_flow() -> None:
    release = ReleaseInfo("uv-tool-updater", Version("2.0"))
    updater = FakeUpdater(UpdateCheck(UpdateStatus.UPDATE_AVAILABLE, installed(), release))
    lines: list[str] = []
    assert run(
        updater,
        input_fn=lambda prompt: "Y",
        output=lines.append,
        restart_args=("--latest-version", "2.0"),
    ) == 0  # type: ignore[arg-type]
    assert updater.prepared and updater.started_with is not None
    assert updater.restart_args == ["--latest-version", "2.0"]
    assert any("helper PID 4321" in line for line in lines)
    assert any("請再次執行本命令查看結果" in line for line in lines)


def test_non_yes_cancels_without_preparing() -> None:
    release = ReleaseInfo("uv-tool-updater", Version("2.0"))
    updater = FakeUpdater(UpdateCheck(UpdateStatus.UPDATE_AVAILABLE, installed(), release))
    lines: list[str] = []
    assert run(updater, input_fn=lambda prompt: "no", output=lines.append) == 0  # type: ignore[arg-type]
    assert not updater.prepared
    assert lines[-1] == "已取消更新。"


def test_unsupported_installation_does_not_prompt() -> None:
    release = ReleaseInfo("uv-tool-updater", Version("2.0"))
    updater = FakeUpdater(UpdateCheck(UpdateStatus.UNSUPPORTED_INSTALLATION, installed(managed=False), release))
    assert run(updater, input_fn=lambda prompt: (_ for _ in ()).throw(AssertionError()), output=lambda line: None) == 0  # type: ignore[arg-type]
    assert not updater.prepared


def test_check_failure_has_nonzero_exit() -> None:
    updater = FakeUpdater(UpdateCheck(UpdateStatus.CHECK_FAILED, installed(), message="offline"))
    lines: list[str] = []
    assert run(updater, output=lines.append) == 1  # type: ignore[arg-type]
    assert "offline" in lines[-1]


def test_missing_pypi_release_explains_local_test_mode() -> None:
    updater = FakeUpdater(
        UpdateCheck(
            UpdateStatus.CHECK_FAILED,
            installed(),
            message="Package was not found",
            error_code="release_not_found",
        )
    )
    lines: list[str] = []
    assert run(updater, output=lines.append) == 1  # type: ignore[arg-type]
    assert "--latest-version" in lines[-1]


def test_latest_version_rejects_non_pep440_value() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--latest-version", "not a version!"])
    assert caught.value.code == 2


def test_background_restart_without_tty_preserves_result(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("uv_tool_updater.cli.sys.stdin", SimpleNamespace(isatty=lambda: False))
    assert main(["--after-update", "--latest-version", "2.0"]) == 0


def test_state_directory_override_and_platform_defaults(tmp_path: Path) -> None:
    override = tmp_path / "custom"
    assert default_state_dir({"UV_TOOL_UPDATER_STATE_DIR": str(override)}, platform="linux") == override.resolve()
    assert default_state_dir({}, platform="linux", home=tmp_path) == (tmp_path / ".local/state/uv-tool-updater/show-version").resolve()
    assert default_state_dir({}, platform="darwin", home=tmp_path) == (tmp_path / "Library/Application Support/uv-tool-updater/show-version").resolve()
    assert default_state_dir({}, platform="win32", home=tmp_path) == (tmp_path / "AppData/Local/uv-tool-updater/show-version").resolve()
