# Changelog

All notable changes are documented here. Versions follow PEP 440 and this project uses semantic versioning while the public API is pre-1.0.

## 0.1.5 - 2026-08-16

### Added

- Complete Traditional Chinese README and technical documentation for architecture, integration, helper protocol, security, testing, troubleshooting, and release operations.
- Bidirectional English/Traditional Chinese navigation across the documentation set.

## 0.1.4 - 2026-08-16

Update-path validation release.

### Changed

- Published a higher version so installations of `0.1.3` can exercise the complete PyPI version-check, external-helper upgrade, and restart flow on real machines.
- Retained the cross-platform PowerShell encoding and timestamp compatibility fixes validated by the release CI matrix.

## 0.1.3 - 2026-08-16

Initial public release.

### Added

- `Updater` facade for release checks, update preparation, helper launch, and result consumption.
- PyPI JSON, static, and protocol-based custom release providers.
- PEP 440 stable/prerelease comparison and yanked-release filtering.
- Conservative uv tool installation detection with editable-install rejection.
- External Windows PowerShell and macOS/Linux `/bin/sh` helpers.
- Host PID waiting, bounded timeout, package session lock, restart-on-failure, and atomic result JSON.
- `JsonStateStore`, check scheduling helper, typed exceptions, stable error codes, and immutable models.
- Interactive `show-version` smoke-test command with offline `--latest-version` metadata injection.
- Windows PowerShell 5.1 handling for hidden helpers, native stderr capture, UTF-8 BOM results, and non-interactive console restarts.
- Unit and Windows process-level regression tests.

### Security

- Fixed argument-vector uv execution and validated distribution names.
- Absolute resolved executable paths and platform-specific restart quoting.
- User-private state permissions, non-recursive lock cleanup, atomic result publication, and basic credential masking.

## 0.1.2 - 2026-08-16

Development-only Windows helper and local self-update fixture; not intended as a public release.

## 0.1.1 - 2026-08-16

Development-only local update fixture; not intended as a public release.

## 0.1.0 - 2026-08-16

Initial development prototype.
