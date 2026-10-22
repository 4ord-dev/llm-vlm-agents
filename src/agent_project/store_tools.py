"""List, search, and read files inside mounted stores."""

from dataclasses import dataclass
from pathlib import Path

from agent_project.consts import (
    MAX_LIST_ENTRIES,
    MAX_READ_CHARS,
    MAX_SEARCH_FILE_CHARS,
    MAX_SEARCH_HITS,
    TEXT_SUFFIXES,
)
from agent_project.mounts import Store, StorePathError


@dataclass(frozen=True)
class ToolObservation:
    """Text the model sees. Host paths stay off this text."""

    text: str
    virtual_path: str | None = None
    image_host_path: Path | None = None
    image_fields: tuple[str, ...] = ()


def list_store(store: Store, path: str) -> ToolObservation:
    """List a virtual directory or name a single file."""
    virtual, host = store.resolve(path)
    if not host.exists():
        raise StorePathError(f"{virtual} does not exist.")

    if host.is_file():
        return ToolObservation(text=f"file {virtual}", virtual_path=virtual)

    names = sorted(child.name for child in host.iterdir())[:MAX_LIST_ENTRIES]
    if not names:
        return ToolObservation(text=f"{virtual} is empty.", virtual_path=virtual)

    lines = []
    for name in names:
        child = host / name
        child_virtual = store.to_virtual(child)
        kind = "dir" if child.is_dir() else "file"
        lines.append(f"{kind} {child_virtual}")
    return ToolObservation(text="\n".join(lines), virtual_path=virtual)


def search_store(store: Store, query: str) -> ToolObservation:
    """Match a query against virtual paths and small text files."""
    needle = query.casefold()
    hits: list[str] = []

    for mount in store.iter_mounts():
        if not mount.host_root.exists():
            continue
        for child in sorted(mount.host_root.rglob("*")):
            if len(hits) >= MAX_SEARCH_HITS:
                break
            if not child.is_file():
                continue
            if not child.resolve().is_relative_to(mount.host_root):
                continue
            virtual = store.to_virtual(child)
            if needle in virtual.casefold():
                hits.append(virtual)
                continue
            if child.suffix.lower() not in TEXT_SUFFIXES:
                continue
            text = child.read_text(encoding="utf-8", errors="replace")
            text = text[:MAX_SEARCH_FILE_CHARS]
            if needle in text.casefold():
                hits.append(virtual)

    if not hits:
        return ToolObservation(text="No matches.")
    return ToolObservation(text="\n".join(hits), virtual_path=hits[0])


def read_file(store: Store, path: str) -> ToolObservation:
    """Read a text file. Images must go through inspect_image."""
    virtual, host = store.resolve(path)
    if not host.is_file():
        raise StorePathError(f"{virtual} is not a file.")
    if host.suffix.lower() not in TEXT_SUFFIXES:
        raise StorePathError(
            f"{virtual} is not a text file. Use inspect_image for pictures."
        )

    text = host.read_text(encoding="utf-8", errors="replace")
    if len(text) > MAX_READ_CHARS:
        text = text[:MAX_READ_CHARS] + "\n[truncated]"
    return ToolObservation(text=f"{virtual}\n{text}", virtual_path=virtual)
