from pathlib import Path

import pytest

from agent_project.mounts import Mount, Store, StorePathError, normalize_virtual_path


def test_normalize_rejects_host_and_parent_paths() -> None:
    with pytest.raises(StorePathError):
        normalize_virtual_path(r"D:\Projects\secret")
    with pytest.raises(StorePathError):
        normalize_virtual_path("/data/../etc/passwd")
    with pytest.raises(StorePathError):
        normalize_virtual_path("data/inbox.md")


def test_resolve_stays_inside_mount(tmp_path: Path) -> None:
    host = tmp_path / "data"
    host.mkdir()
    (host / "inbox.md").write_text("ok", encoding="utf-8")
    store = Store([Mount("/data", host)])

    virtual, resolved = store.resolve("/data/inbox.md")
    assert virtual == "/data/inbox.md"
    assert resolved == (host / "inbox.md").resolve()

    with pytest.raises(StorePathError):
        store.resolve("/etc/passwd")
    with pytest.raises(StorePathError):
        store.resolve("/projects/other.txt")
