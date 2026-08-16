# Testing

Install test dependencies and run the isolated suite:

```console
uv sync --extra test
uv run pytest
```

Unit tests mock metadata, network, and subprocess boundaries. They cover PEP 440 selection, yanked/prerelease policy, conservative installation detection, structured commands, adversarial paths/arguments, session locking, atomic results, and post-restart version confirmation.

The next integration layer should build fixture-tool 1.0.0 and 1.1.0 into a temporary flat index. Always set both `UV_TOOL_DIR` and `UV_TOOL_BIN_DIR` to test-owned temporary directories before installation. The test must assert those resolved paths before any upgrade and must never inherit the developer's actual tool directories.
