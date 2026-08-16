from importlib.metadata import PackageNotFoundError, version

from .errors import (
    HelperLaunchError,
    InstallationError,
    InvalidResponseError,
    InvalidSessionError,
    MetadataError,
    NetworkError,
    PackageNotInstalledError,
    ProviderError,
    ReleaseNotFoundError,
    SessionError,
    UnsupportedInstallationError,
    UpdaterError,
    UvNotFoundError,
)
from .models import (
    InstalledTool,
    InstallStatus,
    ReleaseInfo,
    UpdateCheck,
    UpdateResult,
    UpdateStatus,
)
from .providers import PyPIJsonProvider, ReleaseProvider, StaticProvider
from .session import UpdateSession
from .state import JsonStateStore, UpdateState, UpdateStateStore, check_is_due
from .updater import Updater

__all__ = [
    "HelperLaunchError",
    "InstallationError",
    "InstalledTool",
    "InstallStatus",
    "InvalidResponseError",
    "InvalidSessionError",
    "JsonStateStore",
    "MetadataError",
    "NetworkError",
    "PackageNotInstalledError",
    "ProviderError",
    "PyPIJsonProvider",
    "ReleaseInfo",
    "ReleaseNotFoundError",
    "ReleaseProvider",
    "SessionError",
    "StaticProvider",
    "UnsupportedInstallationError",
    "UpdateCheck",
    "UpdateResult",
    "UpdateSession",
    "UpdateState",
    "UpdateStateStore",
    "UpdateStatus",
    "Updater",
    "UpdaterError",
    "UvNotFoundError",
    "check_is_due",
]

try:
    __version__ = version("uv-tool-updater")
except PackageNotFoundError:  # Source tree imported without installation.
    __version__ = "0.0.0+unknown"
