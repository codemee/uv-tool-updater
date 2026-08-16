from __future__ import annotations

import importlib.metadata
import os
from pathlib import Path

from .checker import check_for_update
from .errors import MetadataError, UpdaterError
from .installation import inspect_installation
from .models import InstalledTool, ReleaseInfo, UpdateCheck, UpdateStatus
from .providers import PyPIJsonProvider, ReleaseProvider
from .result import consume_result, read_result
from .session import UpdateSession, prepare_session


class Updater:
    def __init__(
        self,
        package_name: str,
        command_name: str,
        *,
        provider: ReleaseProvider | None = None,
        state_dir: str | os.PathLike[str] | None = None,
        uv_path: str | os.PathLike[str] | None = None,
    ) -> None:
        self.package_name = package_name
        self.command_name = command_name
        self.provider = provider or PyPIJsonProvider()
        self.state_dir = Path(state_dir).expanduser() if state_dir is not None else None
        self.uv_path = uv_path
        self._installed: InstalledTool | None = None

    def inspect(self) -> InstalledTool:
        self._installed = inspect_installation(
            self.package_name,
            self.command_name,
            uv_path=self.uv_path,
        )
        return self._installed

    def check(self, *, allow_prereleases: bool = False, timeout: float = 5.0) -> UpdateCheck:
        try:
            installed = self.inspect()
        except UpdaterError as exc:
            return UpdateCheck(
                status=UpdateStatus.CHECK_FAILED,
                installed=None,
                message=str(exc),
                error_code=exc.code,
            )
        return check_for_update(
            installed,
            self.provider,
            allow_prereleases=allow_prereleases,
            timeout=timeout,
        )

    def prepare_update(
        self,
        release: ReleaseInfo,
        *,
        restart_args: tuple[str, ...] | list[str] = (),
        restart_on_failure: bool = True,
        wait_timeout: float = 600.0,
    ) -> UpdateSession:
        if self.state_dir is None:
            raise ValueError("state_dir is required to prepare an update")
        installed = self._installed or self.inspect()
        return prepare_session(
            installed,
            release,
            state_dir=self.state_dir,
            restart_args=tuple(restart_args),
            restart_on_failure=restart_on_failure,
            wait_timeout=wait_timeout,
        )

    def consume_result(self, result_path: str | os.PathLike[str]):
        try:
            actual_version = importlib.metadata.version(self.package_name)
        except importlib.metadata.PackageNotFoundError as exc:
            raise MetadataError(f"Package {self.package_name!r} is not installed", cause=exc) from exc
        return consume_result(Path(result_path), actual_version)

    def pending_results(self) -> tuple[Path, ...]:
        """Return completed, unconsumed helper results, newest first."""
        if self.state_dir is None:
            return ()
        candidates = []
        for path in self.state_dir.glob("result-*.json"):
            try:
                result = read_result(path)
                if result.package_name == self.package_name:
                    candidates.append(path)
            except UpdaterError:
                continue
        return tuple(sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True))

    def consume_latest_result(self):
        pending = self.pending_results()
        if not pending:
            return None
        return self.consume_result(pending[0])
