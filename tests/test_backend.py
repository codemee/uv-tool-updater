from pathlib import Path

import pytest

from uv_tool_updater.backend import upgrade_command


def test_upgrade_is_a_structured_command() -> None:
    command = upgrade_command(Path("C:/bin/uv.exe"), "demo-tool", options=("--offline",))
    assert command == ("C:\\bin\\uv.exe", "tool", "upgrade", "--offline", "demo-tool")


@pytest.mark.parametrize("name", ["", "-demo", "demo; calc", "demo/other"])
def test_rejects_unsafe_package_names(name: str) -> None:
    with pytest.raises(ValueError):
        upgrade_command(Path("C:/bin/uv.exe"), name)


def test_rejects_arbitrary_uv_options() -> None:
    with pytest.raises(ValueError):
        upgrade_command(Path("C:/bin/uv.exe"), "demo", options=("--index-url",))
