# Architecture and lifecycle

English | [繁體中文](zh-TW/architecture.md)

## Design objective

`uv-tool-updater` coordinates updates without becoming a second package installer. It never downloads wheels, rewrites `site-packages`, edits uv receipts, or chooses a package index. The only installation mutation is the structured command:

```text
<absolute uv path> tool upgrade <validated distribution name>
```

This division preserves uv's ownership of dependency resolution, index authentication, version constraints, cache behavior, and tool-environment replacement. The updater owns release discovery, host lifecycle coordination, result persistence, and restart.

## Components

| Module | Responsibility | Side effects |
| --- | --- | --- |
| `models.py` | Immutable public dataclasses and status enums | None |
| `errors.py` | Typed exceptions with stable error codes | None |
| `providers.py` | Release metadata discovery | HTTPS for `PyPIJsonProvider` |
| `installation.py` | Installed metadata, uv path, tool root, and command discovery | Runs `uv tool dir` |
| `checker.py` | PEP 440 comparison and check status mapping | None |
| `backend.py` | Package validation and fixed uv argument vector | None |
| `session.py` | Locking, immutable plan, helper generation and launch | Creates session files; starts helper |
| `result.py` | Atomic JSON persistence, parsing and post-restart confirmation | Atomic rename and consume marker |
| `state.py` | Optional JSON host-policy state | Atomic JSON write |
| `updater.py` | Public facade | Delegates to the modules above |
| `cli.py` | Interactive self-update smoke test | Console I/O; invokes the facade |

## State machine

```text
CHECK
  ├─ metadata/provider failure ───────────────> CHECK_FAILED
  ├─ not a supported uv tool installation ───> UNSUPPORTED_INSTALLATION
  ├─ latest <= installed ─────────────────────> UP_TO_DATE
  └─ latest > installed ──────────────────────> UPDATE_AVAILABLE
                                                   │
PREPARE <──────────────────────────────────────────┘
  validate package/release/paths/arguments
  atomically acquire per-package lock directory
  write immutable plan and platform helper
                                                   │
START
  spawn hidden PowerShell or detached /bin/sh
  verify helper does not exit immediately
  return control to host
                                                   │
HOST EXIT
  host saves data and exits normally; updater never kills it
                                                   │
HELPER
  wait for PID ── timeout ─────────────────────> APP_EXIT_TIMEOUT
  uv tool upgrade ── non-zero ─────────────────> FAILED
  restart failure ─────────────────────────────> RESTART_FAILED
  provisional zero exit ───────────────────────> SUCCEEDED
                                                   │
RESTARTED HOST
  read importlib.metadata.version()
  unchanged after provisional success ─────────> NO_CHANGE
  changed version ─────────────────────────────> SUCCEEDED
  atomically rename result to .consumed
```

`SUCCEEDED` written by the helper is deliberately provisional. Only the restarted host can import metadata from the replacement environment and determine whether a version actually changed.

## Installation detection

Detection is intentionally conservative:

1. Read the installed distribution with `importlib.metadata`.
2. Resolve uv from an explicit path, the `UV` environment variable, then `PATH`.
3. Run `uv tool dir` and normalize the returned root.
4. Resolve `sys.prefix` and require it to be below the uv tool root.
5. Reject editable installs using `direct_url.json`.
6. Resolve the console command and require it to be a real local file.

Path comparisons resolve symlinks where possible. Windows comparisons use normalized case. Any missing or ambiguous evidence produces `managed_by_uv=False`; inspection errors must not prevent the host application from starting.

## Provider/backend separation

A `ReleaseProvider` supplies only a distribution name, PEP 440 version, optional release URL, publication time, and display flags. Provider data never supplies executable paths, installer arguments, scripts, indexes, or credentials.

The default provider reads the PyPI JSON API over HTTPS, rejects mismatched names, ignores releases with no files, excludes fully yanked releases, and excludes prereleases unless explicitly allowed. Private-index consumers inject their own provider; uv independently retains the source and authentication used for installation.

## Concurrency and recovery

Preparation creates an atomic directory lock named after the canonical distribution. A second session is refused. Cancellation or a completed helper deletes the lock only if the exact directory is empty. The updater never recursively removes a tool directory or follows a cleanup glob.

A machine crash can leave a stale lock. It is not automatically broken because liveness cannot be proven safely across reboot and PID reuse. After confirming no helper is running, an operator may remove only the package lock directory described in [troubleshooting](troubleshooting.md).

## Compatibility contract

Result JSON starts at schema version 1. Unknown schemas raise a typed diagnostic and remain on disk. Public enums use string values so hosts can persist and translate them. Before 1.0, dataclass fields and helper details may evolve; schema and behavior changes are recorded in the changelog.
