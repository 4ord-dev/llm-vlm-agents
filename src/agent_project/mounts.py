"""Virtual store mounts. Tools never see raw host paths."""

from dataclasses import dataclass
from pathlib import Path

from agent_project.consts import DEFAULT_MOUNT_HOST_NAME, DEFAULT_MOUNT_VIRTUAL


class StorePathError(ValueError):
    """A path is missing, not virtual, or outside a mount."""


@dataclass(frozen=True)
class Mount:
    """One host folder shown to the model as a virtual root."""

    virtual_root: str
    host_root: Path


def normalize_virtual_path(path: str) -> str:
    """Accept only Linux-style virtual paths. Reject host paths and parent segments."""
    if path is None or not str(path).strip():
        raise StorePathError("Use a virtual path such as /data/notes.txt.")

    cleaned = str(path).strip().replace("\\", "/")
    if cleaned.startswith("//") or ":" in cleaned:
        raise StorePathError("Use a virtual path such as /data/notes.txt.")
    if not cleaned.startswith("/"):
        raise StorePathError("Use a virtual path such as /data/notes.txt.")

    parts: list[str] = []
    for part in cleaned.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            raise StorePathError("Parent segments are not allowed.")
        parts.append(part)
    return "/" + "/".join(parts)


class Store:
    """Resolve virtual paths onto owner-selected host folders."""

    def __init__(self, mounts: list[Mount]) -> None:
        if not mounts:
            raise StorePathError("At least one mount is required.")
        self._mounts = tuple(
            Mount(normalize_virtual_path(item.virtual_root), item.host_root.resolve())
            for item in mounts
        )

    @property
    def virtual_roots(self) -> tuple[str, ...]:
        return tuple(item.virtual_root for item in self._mounts)

    def resolve(self, virtual_path: str) -> tuple[str, Path]:
        """Return the normalized virtual path and the host path inside a mount."""
        virtual = normalize_virtual_path(virtual_path)
        mount = self._mount_for(virtual)
        relative = virtual[len(mount.virtual_root) :].lstrip("/")
        host = mount.host_root / relative if relative else mount.host_root
        host = host.resolve()
        if not host.is_relative_to(mount.host_root):
            raise StorePathError("That path is outside the mount.")
        return virtual, host

    def to_virtual(self, host_path: Path) -> str:
        """Map a host path back to the virtual path the model may see."""
        host = host_path.resolve()
        for mount in self._mounts:
            if not host.is_relative_to(mount.host_root):
                continue
            relative = host.relative_to(mount.host_root).as_posix()
            if relative == ".":
                return mount.virtual_root
            return f"{mount.virtual_root}/{relative}"
        raise StorePathError("That host path is not on a mounted store.")

    def iter_mounts(self) -> tuple[Mount, ...]:
        return self._mounts

    def _mount_for(self, virtual: str) -> Mount:
        matches = [
            mount
            for mount in self._mounts
            if virtual == mount.virtual_root
            or virtual.startswith(f"{mount.virtual_root}/")
        ]
        if not matches:
            raise StorePathError("That path is not on a mounted store.")
        return max(matches, key=lambda mount: len(mount.virtual_root))


def default_store(project_root: Path | None = None) -> Store:
    """Map this repository's data folder to /data."""
    root = project_root or Path.cwd()
    return Store([Mount(DEFAULT_MOUNT_VIRTUAL, root / DEFAULT_MOUNT_HOST_NAME)])
