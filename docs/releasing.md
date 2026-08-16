# Release procedure

English | [繁體中文](zh-TW/releasing.md)

## Preconditions

1. Choose a PEP 440 version not already present on PyPI; published filenames cannot be replaced.
2. Update `[project].version` in `pyproject.toml`.
3. Add a dated changelog entry.
4. Confirm the tag will be `v<version>` and matches package metadata.
5. Ensure the GitHub release and PyPI project links point to this repository.

## Local validation

```console
uv sync --extra test
uv run pytest
uv build
```

Inspect metadata from the wheel and sdist, then install the wheel in an isolated environment:

```console
uv run --isolated --with dist/uv_tool_updater-<version>-py3-none-any.whl \
  python -c "import uv_tool_updater; print(uv_tool_updater.__version__)"
```

Before publishing, verify the exact `dist` directory contains only artifacts intended for that version.

## GitHub

Commit the release, push the default branch, tag the exact commit, and create a GitHub Release containing the changelog section. CI must pass on Windows, macOS, and Linux for supported Python versions.

## PyPI

Preferred automation is PyPI Trusted Publishing from the GitHub `pypi` environment. The repository workflow requests only `id-token: write` and publishes artifacts built after tests pass.

For an authorized first local release:

```console
uv publish dist/uv_tool_updater-<version>*
```

Use a scoped PyPI API token through `UV_PUBLISH_TOKEN` or the interactive secure credential mechanism. Never place credentials in arguments, repository files, logs, or shell history.

After upload, query the version-specific JSON endpoint and verify both wheel and sdist filenames, hashes, `requires_python`, project URLs, and version metadata.

## Post-release smoke test

```console
uv tool install uv-tool-updater==<version>
show-version
```

The first published release cannot update a previously unpublished local install automatically without one manual bootstrap. Test the updater again when a higher release exists.
