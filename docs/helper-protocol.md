# External helper protocol

## Why an external helper exists

An application cannot safely replace its own uv-managed environment while it is executing from that environment. Windows may hold executable or module files open, and every platform risks a partially replaced runtime. The helper therefore runs under an operating-system shell outside the tool environment, waits for the host to disappear, performs the uv command, records the result, and restarts the resolved command.

The helper receives no arbitrary command string. Python generates a platform-specific script from validated fields and launches it with a positive integer host PID.

## Immutable plan

Each session records schema version 1 with:

- random UUID session ID;
- canonical package identity;
- absolute helper, uv, command, result, log, and lock paths;
- previous and requested PEP 440 versions;
- restart arguments as an array;
- restart-on-failure policy;
- finite positive host-exit timeout.

The adjacent plan JSON is diagnostic data, not an executable instruction source. The generated helper contains the already validated and platform-quoted values.

## Windows implementation

Windows uses the built-in Windows PowerShell baseline with these constraints:

- `CREATE_NO_WINDOW` hides the helper console.
- `DETACHED_PROCESS` is intentionally not used. Windows PowerShell 5.1 exits immediately when it is combined with null standard handles.
- `Get-Process -Id` polls the host every 250ms until exit or timeout.
- `Start-Process -Wait -PassThru` runs uv and supplies a reliable numeric `ExitCode`.
- uv stdout and stderr go to separate temporary files, then are decoded as UTF-8 and combined. This avoids PowerShell 5.1 turning ordinary native stderr progress into a terminating `NativeCommandError`.
- Restart uses `Start-Process` with an absolute file path and a literal argument array.
- The package lock is removed with non-recursive `Directory.Delete(path, false)`.

The helper may emit UTF-8 JSON with a BOM under Windows PowerShell 5.1. Result parsing uses `utf-8-sig` so both BOM and non-BOM files are accepted.

## macOS/Linux implementation

Unix platforms use `/bin/sh`, not bash or zsh:

- `kill -0` polls host liveness once per second;
- the timeout bounds PID-reuse exposure;
- all static values use `shlex.quote` and are never evaluated twice;
- uv stdout and stderr are redirected to a private UTF-8 log;
- restart is backgrounded with standard input disconnected;
- JSON is assembled from pre-encoded static fragments and controlled numeric/status values;
- result publication uses a temporary file followed by `mv`;
- cleanup names only the exact plan, helper, and empty lock directory.

## Result schema

```json
{
  "schema_version": 1,
  "session_id": "c7d9d7e7-8420-4c55-8274-ceb3b1f44095",
  "package_name": "fshot",
  "previous_version": "0.0.10",
  "requested_version": "0.0.11",
  "actual_version": null,
  "uv_exit_code": 0,
  "status": "succeeded",
  "started_at": "2026-08-16T12:00:00Z",
  "finished_at": "2026-08-16T12:00:09Z",
  "log_path": "...",
  "error": null
}
```

`actual_version` is null in helper output because the helper does not import the replaced environment. The restarted host fills it logically during consumption. A zero uv exit code with an unchanged installed version becomes `NO_CHANGE`.

## Failure behavior

| Condition | Result | Upgrade attempted | Restart |
| --- | --- | --- | --- |
| Host timeout | `app_exit_timeout` | No | No |
| uv exit non-zero | `failed` | Yes | When `restart_on_failure=True` |
| uv exit zero | provisional `succeeded` | Yes | Yes |
| Restart launch error | `restart_failed` | Maybe | Failed |

The helper never terminates the host and never retries a mutation automatically. Logs apply basic masking to values labelled token, password, or authorization, but secrets should not be placed in restart arguments or installer output.
