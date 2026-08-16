from __future__ import annotations

import json
import math
import os
import shlex
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import asdict
from pathlib import Path

from packaging.utils import canonicalize_name
from packaging.version import Version

from .backend import upgrade_command
from .errors import HelperLaunchError, InvalidSessionError, UnsupportedInstallationError
from .models import InstalledTool, ReleaseInfo, UpdatePlan
from .result import atomic_write_json


class UpdateSession:
    def __init__(self, plan: UpdatePlan, helper_path: Path) -> None:
        self.plan = plan
        self.helper_path = helper_path
        self._started = False

    def start_helper(self, *, host_pid: int) -> int:
        if self._started:
            raise InvalidSessionError("This update helper has already been started")
        if not isinstance(host_pid, int) or host_pid <= 0:
            raise InvalidSessionError("host_pid must be a positive integer")
        try:
            if os.name == "nt":
                powershell = _windows_powershell()
                # Windows PowerShell exits immediately when DETACHED_PROCESS is
                # combined with DEVNULL standard handles. CREATE_NO_WINDOW keeps
                # the helper invisible without tying its lifetime to the host.
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
                process = subprocess.Popen(
                    [
                        str(powershell),
                        "-NoLogo",
                        "-NoProfile",
                        "-NonInteractive",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(self.helper_path),
                        str(host_pid),
                    ],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    close_fds=True,
                )
            else:
                process = subprocess.Popen(
                    ["/bin/sh", str(self.helper_path), str(host_pid)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True,
                )
        except (OSError, ValueError) as exc:
            self.cancel()
            raise HelperLaunchError("Could not launch the external update helper", cause=exc) from exc
        try:
            exit_code = process.wait(timeout=0.25)
        except subprocess.TimeoutExpired:
            pass
        else:
            self.cancel()
            raise HelperLaunchError(f"Update helper exited immediately with code {exit_code}")
        self._started = True
        return process.pid

    def cancel(self) -> None:
        """Release a session that has not been handed to a helper."""
        if self._started:
            raise InvalidSessionError("A running helper cannot be cancelled by the host")
        self.helper_path.unlink(missing_ok=True)
        self.helper_path.with_suffix(".json").unlink(missing_ok=True)
        try:
            self.plan.lock_path.rmdir()
        except FileNotFoundError:
            pass


def prepare_session(
    installed: InstalledTool,
    release: ReleaseInfo,
    *,
    state_dir: Path,
    restart_args: tuple[str, ...] = (),
    restart_on_failure: bool = True,
    wait_timeout: float = 600.0,
) -> UpdateSession:
    if not installed.managed_by_uv or installed.uv_path is None:
        raise UnsupportedInstallationError("Automatic update requires a uv tool installation")
    if canonicalize_name(release.package_name) != canonicalize_name(installed.package_name):
        raise InvalidSessionError("Release package does not match the installed package")
    if wait_timeout <= 0 or not math.isfinite(wait_timeout):
        raise InvalidSessionError("wait_timeout must be a positive finite number")
    command_path = installed.executable_path.resolve(strict=False)
    uv_path = installed.uv_path.resolve(strict=False)
    if not command_path.is_absolute() or not uv_path.is_absolute():
        raise InvalidSessionError("Command and uv paths must be absolute")
    if any("\x00" in arg for arg in restart_args):
        raise InvalidSessionError("Restart arguments cannot contain NUL bytes")

    state_dir = state_dir.expanduser().resolve(strict=False)
    state_dir.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        state_dir.chmod(0o700)
    lock_path = state_dir / f".{canonicalize_name(installed.package_name)}.update.lock"
    try:
        lock_path.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise InvalidSessionError("An update session is already pending for this package", cause=exc) from exc

    session_id = str(uuid.uuid4())
    suffix = ".ps1" if os.name == "nt" else ".sh"
    descriptor, helper_name = tempfile.mkstemp(prefix=f"update-{session_id}-", suffix=suffix, dir=state_dir)
    os.close(descriptor)
    helper_path = Path(helper_name)
    plan = UpdatePlan(
        schema_version=1,
        session_id=session_id,
        package_name=installed.package_name,
        helper_path=helper_path,
        command_path=command_path,
        restart_args=tuple(restart_args),
        uv_path=uv_path,
        previous_version=str(installed.current_version),
        requested_version=str(release.version),
        restart_on_failure=restart_on_failure,
        wait_timeout=wait_timeout,
        result_path=state_dir / f"result-{session_id}.json",
        log_path=state_dir / f"update-{session_id}.log",
        lock_path=lock_path,
    )
    try:
        script = _powershell_helper(plan) if os.name == "nt" else _sh_helper(plan)
        # Windows PowerShell 5.1 treats BOM-less script files as the active ANSI
        # code page.  A BOM is therefore required when paths or arguments contain
        # non-ASCII characters.  POSIX helpers remain plain UTF-8.
        helper_encoding = "utf-8-sig" if os.name == "nt" else "utf-8"
        helper_path.write_text(script, encoding=helper_encoding, newline="\n")
        if os.name != "nt":
            helper_path.chmod(0o700)
        plan_payload = {key: _json_value(value) for key, value in asdict(plan).items()}
        atomic_write_json(helper_path.with_suffix(".json"), plan_payload)
    except BaseException:
        helper_path.unlink(missing_ok=True)
        try:
            lock_path.rmdir()
        except OSError:
            pass
        raise
    return UpdateSession(plan, helper_path)


def _json_value(value: object) -> object:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _windows_powershell() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    builtin = Path(system_root) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if builtin.is_file():
        return builtin
    found = shutil.which("powershell.exe") or shutil.which("powershell")
    if not found:
        raise HelperLaunchError("Windows PowerShell could not be found")
    return Path(found).resolve()


def _ps(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _powershell_helper(plan: UpdatePlan) -> str:
    uv_args = ", ".join(
        _ps(item)
        for item in upgrade_command(plan.uv_path, plan.package_name, Version(plan.requested_version))[1:]
    )
    restart_args = ", ".join(_ps(item) for item in plan.restart_args)
    restart_on_failure = "$true" if plan.restart_on_failure else "$false"
    return f"""param([Parameter(Mandatory=$true)][int]$HostPid)
$ErrorActionPreference = 'Stop'
$started = [DateTime]::UtcNow
$status = 'failed'
$uvExit = $null
$errorMessage = $null
$deadline = [DateTime]::UtcNow.AddSeconds({plan.wait_timeout!r})
while (Get-Process -Id $HostPid -ErrorAction SilentlyContinue) {{
    if ([DateTime]::UtcNow -ge $deadline) {{ $status = 'app_exit_timeout'; $errorMessage = 'Host did not exit before timeout'; break }}
    Start-Sleep -Milliseconds 250
}}
if ($status -ne 'app_exit_timeout') {{
    $stdoutPath = {_ps(str(plan.log_path) + '.stdout')}
    $stderrPath = {_ps(str(plan.log_path) + '.stderr')}
    try {{
        $uvProcess = Start-Process -FilePath {_ps(plan.uv_path)} -ArgumentList @({uv_args}) -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath
        $uvExit = $uvProcess.ExitCode
        $stdoutText = if (Test-Path -LiteralPath $stdoutPath) {{ [System.IO.File]::ReadAllText($stdoutPath, [System.Text.Encoding]::UTF8) }} else {{ '' }}
        $stderrText = if (Test-Path -LiteralPath $stderrPath) {{ [System.IO.File]::ReadAllText($stderrPath, [System.Text.Encoding]::UTF8) }} else {{ '' }}
        $utf8 = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText({_ps(plan.log_path)}, $stdoutText + $stderrText, $utf8)
        if ($uvExit -eq 0) {{ $status = 'succeeded' }} else {{ $status = 'failed'; $errorMessage = 'uv tool upgrade failed' }}
    }} catch {{ $status = 'failed'; $errorMessage = $_.Exception.Message }}
    finally {{
        Remove-Item -Force -LiteralPath $stdoutPath -ErrorAction SilentlyContinue
        Remove-Item -Force -LiteralPath $stderrPath -ErrorAction SilentlyContinue
    }}
    if (($status -eq 'succeeded') -or {restart_on_failure}) {{
        try {{ Start-Process -FilePath {_ps(plan.command_path)} -ArgumentList @({restart_args}) | Out-Null }}
        catch {{ $status = 'restart_failed'; $errorMessage = $_.Exception.Message }}
    }}
}}
if (Test-Path -LiteralPath {_ps(plan.log_path)}) {{
    $log = Get-Content -Raw -LiteralPath {_ps(plan.log_path)}
    $log = $log -replace '(?i)(token|password|authorization)(\\s*[:=]\\s*)\\S+', '$1$2[REDACTED]'
    Set-Content -LiteralPath {_ps(plan.log_path)} -Value $log -Encoding utf8
}}
$result = [ordered]@{{
    schema_version = 1; session_id = {_ps(plan.session_id)}; package_name = {_ps(plan.package_name)}
    previous_version = {_ps(plan.previous_version)}; requested_version = {_ps(plan.requested_version)}
    actual_version = $null; uv_exit_code = $uvExit; status = $status
    started_at = $started.ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ'); finished_at = [DateTime]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ss.ffffffZ')
    log_path = {_ps(plan.log_path)}; error = $errorMessage
}}
$temporary = {_ps(str(plan.result_path) + '.tmp')}
$result | ConvertTo-Json -Compress | Set-Content -LiteralPath $temporary -Encoding utf8
Move-Item -Force -LiteralPath $temporary -Destination {_ps(plan.result_path)}
try {{ [System.IO.Directory]::Delete({_ps(plan.lock_path)}, $false) }} catch {{}}
Remove-Item -Force -LiteralPath {_ps(plan.helper_path.with_suffix('.json'))} -ErrorAction SilentlyContinue
Remove-Item -Force -LiteralPath {_ps(plan.helper_path)} -ErrorAction SilentlyContinue
"""


def _sh_helper(plan: UpdatePlan) -> str:
    command = " ".join(
        shlex.quote(item)
        for item in upgrade_command(plan.uv_path, plan.package_name, Version(plan.requested_version))
    )
    restart = " ".join(shlex.quote(item) for item in (str(plan.command_path), *plan.restart_args))
    timeout = max(1, math.ceil(plan.wait_timeout))
    restart_condition = '[ "$status" = succeeded ] || [ "$restart_on_failure" = 1 ]'
    static = {
        "prefix": '{"schema_version":1,"session_id":' + json.dumps(plan.session_id) + ',"package_name":' + json.dumps(plan.package_name) + ',"previous_version":' + json.dumps(plan.previous_version) + ',"requested_version":' + json.dumps(plan.requested_version) + ',"actual_version":null,"uv_exit_code":',
        "status": ',"status":',
        "started": ',"started_at":',
        "finished": ',"finished_at":',
        "log": ',"log_path":' + json.dumps(str(plan.log_path)) + ',"error":',
        "end": '}\n',
    }
    emit = lambda value: f"printf '%s' {shlex.quote(value)}"  # noqa: E731
    return f"""#!/bin/sh
host_pid=$1
started=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
status=failed
uv_exit_json=null
error_json=null
elapsed=0
while kill -0 "$host_pid" 2>/dev/null; do
    if [ "$elapsed" -ge {timeout} ]; then status=app_exit_timeout; error_json='"Host did not exit before timeout"'; break; fi
    sleep 1
    elapsed=$((elapsed + 1))
done
restart_on_failure={1 if plan.restart_on_failure else 0}
if [ "$status" != app_exit_timeout ]; then
    {command} >{shlex.quote(str(plan.log_path))} 2>&1
    uv_exit=$?
    uv_exit_json=$uv_exit
    if [ "$uv_exit" -eq 0 ]; then status=succeeded; else status=failed; error_json='"uv tool upgrade failed"'; fi
    if {restart_condition}; then
        {restart} </dev/null >>{shlex.quote(str(plan.log_path))} 2>&1 &
        if [ $? -ne 0 ]; then status=restart_failed; error_json='"Could not restart application"'; fi
    fi
fi
if [ -f {shlex.quote(str(plan.log_path))} ]; then
    sed -E 's/([Tt][Oo][Kk][Ee][Nn]|[Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|[Aa][Uu][Tt][Hh][Oo][Rr][Ii][Zz][Aa][Tt][Ii][Oo][Nn])([[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\\1\\2[REDACTED]/g' {shlex.quote(str(plan.log_path))} >{shlex.quote(str(plan.log_path) + '.redacted')} 2>/dev/null && mv {shlex.quote(str(plan.log_path) + '.redacted')} {shlex.quote(str(plan.log_path))}
fi
finished=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
{{
    {emit(static['prefix'])}; printf '%s' "$uv_exit_json"
    {emit(static['status'])}; printf '"%s"' "$status"
    {emit(static['started'])}; printf '"%s"' "$started"
    {emit(static['finished'])}; printf '"%s"' "$finished"
    {emit(static['log'])}; printf '%s' "$error_json"
    {emit(static['end'])}
}} >{shlex.quote(str(plan.result_path) + '.tmp')}
mv {shlex.quote(str(plan.result_path) + '.tmp')} {shlex.quote(str(plan.result_path))}
rmdir {shlex.quote(str(plan.lock_path))} 2>/dev/null || true
rm -f {shlex.quote(str(plan.helper_path.with_suffix('.json')))} {shlex.quote(str(plan.helper_path))}
"""
