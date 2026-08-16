import os
from pathlib import Path

import pytest

from uv_tool_updater.backend import upgrade_command


def test_upgrade_is_a_structured_command() -> None:
    uv_path = Path("C:/bin/uv.exe") if os.name == "nt" else Path("/bin/uv")
    command = upgrade_command(uv_path, "demo-tool", options=("--offline",))
    assert command == (str(uv_path), "tool", "upgrade", "--offline", "demo-tool")


@pytest.mark.parametrize("name", ["", "-demo", "demo; calc", "demo/other"])
def test_rejects_unsafe_package_names(name: str) -> None:
    with pytest.raises(ValueError):
        upgrade_command(Path("C:/bin/uv.exe"), name)


def test_rejects_arbitrary_uv_options() -> None:
    with pytest.raises(ValueError):
        upgrade_command(Path("C:/bin/uv.exe"), "demo", options=("--index-url",))
