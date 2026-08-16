# Troubleshooting

## `Package 'uv-tool-updater' was not found`

The installed version was read successfully, but the default provider could not find the project on public PyPI. For local-path testing, use:

```console
show-version --latest-version 0.1.4
```

This simulates metadata only. The source used by `uv tool upgrade` remains the source recorded by uv.

## `Update helper exited immediately`

Confirm the installed updater includes version 0.1.2 or later. Earlier Windows builds combined `DETACHED_PROCESS` with null standard handles, which caused Windows PowerShell 5.1 to exit immediately. Bootstrap once with `uv tool install --force .` or a fixed published release.

## Log contains only `Building ...` or uv exit code is null

Confirm version 0.1.2 or later. Earlier helpers merged native stderr through a PowerShell pipeline while `$ErrorActionPreference` was `Stop`; normal uv progress was interpreted as a PowerShell exception. Current helpers redirect native stdout/stderr separately and use the process exit code.

## Update result did not appear after restart

On Windows, a console command launched by the hidden helper may have no interactive terminal. `show-version` detects this and leaves the result unconsumed. Run `show-version` manually in the existing terminal to display it. GUI hosts are unaffected.

## A session is already pending

First check for a running PowerShell or `/bin/sh` helper and inspect the state directory for a plan/result. Do not delete a lock while an update could still be active.

After confirming the helper is gone, remove only the empty lock directory:

```text
.<canonical-package-name>.update.lock
```

Never remove the uv tool directory or an entire shared application-state root.

## Installation is unsupported

Run `uv tool list --show-version-specifiers` to confirm the application was installed as a uv tool. Editable checkouts, `uv run`, ordinary virtual environments, uvx cache environments, missing command shims, and ambiguous path layouts are intentionally refused.

## Collecting diagnostics

Useful, non-secret data includes:

- updater version and operating system;
- `UpdateStatus` or `InstallStatus`;
- numeric uv exit code;
- redacted helper log;
- result JSON schema and timestamps;
- whether the package came from PyPI, a local path, Git, or a private index.

Do not attach environment dumps, registry credentials, index tokens, or unredacted private URLs.
