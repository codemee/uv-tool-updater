from __future__ import annotations


class UpdaterError(Exception):
    """Base error carrying a stable, localizable error code."""

    code = "updater_error"

    def __init__(self, message: str, *, cause: BaseException | None = None) -> None:
        super().__init__(message)
        self.cause = cause
        if cause is not None:
            self.__cause__ = cause


class MetadataError(UpdaterError):
    code = "metadata_error"


class PackageNotInstalledError(MetadataError):
    code = "package_not_installed"


class InvalidVersionError(MetadataError):
    code = "invalid_version"


class ProviderError(UpdaterError):
    code = "provider_error"


class NetworkError(ProviderError):
    code = "network_error"


class InvalidResponseError(ProviderError):
    code = "invalid_response"


class ReleaseNotFoundError(ProviderError):
    code = "release_not_found"


class InstallationError(UpdaterError):
    code = "installation_error"


class UvNotFoundError(InstallationError):
    code = "uv_not_found"


class UnsupportedInstallationError(InstallationError):
    code = "unsupported_installation"


class ToolDirectoryError(InstallationError):
    code = "tool_directory_error"


class SessionError(UpdaterError):
    code = "session_error"


class InvalidSessionError(SessionError):
    code = "invalid_session"


class HelperLaunchError(SessionError):
    code = "helper_launch_error"


class RestartError(UpdaterError):
    code = "restart_error"
