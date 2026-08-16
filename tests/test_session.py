from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from packaging.version import Version

from uv_tool_updater.errors import InvalidSessionError, UnsupportedInstallationError
from uv_tool_updater.models import InstalledTool, ReleaseInfo
from uv_tool_updater.models import InstallStatus
from uv_tool_updater.result import read_result
from uv_tool_updater.session import prepare_session


def installed(tmp_path: Path, *, managed: bool = True) -> InstalledTool:
    uv = (tmp_path / "bin odd';&" / "uv.exe").resolve()
    command = (tmp_path / "命令 odd';&" / "demo.exe").resolve()
    uv.parent.mkdir(parents=True)
    command.parent.mkdir(parents=True)
    uv.touch()
    command.touch()
    root = (tmp_path / "tools").resolve()
    return InstalledTool("demo-tool", "demo", Version("1"), command, root / "demo", uv, root, managed)


def test_prepare_writes_quoted_helper_and_plan(tmp_path: Path) -> None:
    session = prepare_session(
        installed(tmp_path), ReleaseInfo("demo_tool", Version("2")), state_dir=tmp_path / "state",
        restart_args=("space value", "quote';&$()"), wait_timeout=3,
    )
    script = session.helper_path.read_text(encoding="utf-8")
    assert "tool" in script and "upgrade" in script
    assert "demo-tool==2" in script
    assert session.helper_path.with_suffix(".json").exists()
    assert session.plan.lock_path.is_dir()
    if os.name == "nt":
        powershell = shutil.which("powershell.exe")
        assert powershell is not None
        helper_literal = str(session.helper_path).replace("'", "''")
        parser = (
            "$tokens=$null;$errors=$null;"
            f"[System.Management.Automation.Language.Parser]::ParseFile('{helper_literal}',[ref]$tokens,[ref]$errors)|Out-Null;"
            "if($errors.Count -gt 0){$errors|ForEach-Object{$_.Message};exit 1}"
        )
        parsed = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", parser],
            capture_output=True,
            text=True,
        )
        assert parsed.returncode == 0, parsed.stderr or parsed.stdout
    session.cancel()
    assert not session.plan.lock_path.exists()


def test_rejects_duplicate_session(tmp_path: Path) -> None:
    tool = installed(tmp_path)
    first = prepare_session(tool, ReleaseInfo("demo-tool", Version("2")), state_dir=tmp_path / "state")
    with pytest.raises(InvalidSessionError, match="already pending"):
        prepare_session(tool, ReleaseInfo("demo-tool", Version("2")), state_dir=tmp_path / "state")
    first.cancel()


def test_rejects_unsupported_installation(tmp_path: Path) -> None:
    with pytest.raises(UnsupportedInstallationError):
        prepare_session(installed(tmp_path, managed=False), ReleaseInfo("demo-tool", Version("2")), state_dir=tmp_path)


def test_rejects_nul_restart_argument(tmp_path: Path) -> None:
    with pytest.raises(InvalidSessionError):
        prepare_session(
            installed(tmp_path), ReleaseInfo("demo-tool", Version("2")), state_dir=tmp_path / "state",
            restart_args=("bad\x00arg",),
        )


@pytest.mark.skipif(os.name != "nt", reason="Windows process creation regression test")
def test_windows_hidden_helper_stays_alive_and_times_out(tmp_path: Path) -> None:
    session = prepare_session(
        installed(tmp_path),
        ReleaseInfo("demo-tool", Version("2")),
        state_dir=tmp_path / "state",
        restart_on_failure=False,
        wait_timeout=0.2,
    )
    helper_pid = session.start_helper(host_pid=os.getpid())
    assert helper_pid > 0
    deadline = time.monotonic() + 5
    while not session.plan.result_path.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    result = read_result(session.plan.result_path)
    assert result.status is InstallStatus.APP_EXIT_TIMEOUT
    assert not session.plan.lock_path.exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows PowerShell native stderr regression test")
def test_windows_uv_progress_on_stderr_is_not_an_install_failure(tmp_path: Path) -> None:
    fake_uv = (tmp_path / "fake uv.cmd").resolve()
    fake_uv.write_text("@echo Building fixture 1>&2\r\n@exit /b 0\r\n", encoding="ascii")
    command = Path(shutil.which("cmd.exe") or "C:/Windows/System32/cmd.exe").resolve()
    root = (tmp_path / "tools").resolve()
    tool = InstalledTool(
        "demo-tool", "demo", Version("1"), command, root / "demo", fake_uv, root, True
    )
    session = prepare_session(
        tool,
        ReleaseInfo("demo-tool", Version("2")),
        state_dir=tmp_path / "state",
        restart_args=("/c", "exit", "0"),
        restart_on_failure=False,
    )
    powershell = shutil.which("powershell.exe")
    assert powershell is not None
    completed = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(session.helper_path),
            "2147483647",
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert completed.returncode == 0, completed.stderr
    result = read_result(session.plan.result_path)
    assert result.status is InstallStatus.SUCCEEDED
    assert result.uv_exit_code == 0
    assert "Building fixture" in session.plan.log_path.read_text(encoding="utf-8-sig")
