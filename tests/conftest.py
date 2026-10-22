"""Shared store fixtures for agent tests."""

from pathlib import Path

import pytest

from agent_project.mounts import Mount, Store


def write_png(path: Path) -> None:
    path.write_bytes(b"\x89PNG\r\n\x1a\n")


@pytest.fixture
def store(tmp_path: Path) -> Store:
    host = tmp_path / "data"
    host.mkdir()
    (host / "inbox.md").write_text(
        "Hallway closet: the printer\n",
        encoding="utf-8",
    )
    write_png(host / "screen.png")
    return Store([Mount("/data", host)])
