"""Inspect a mounted image and record typed facts from it."""

import json

from agent_project.consts import IMAGE_SUFFIXES
from agent_project.models import ImageFactsArgs
from agent_project.mounts import Store, StorePathError
from agent_project.store_tools import ToolObservation


def inspect_image(store: Store, path: str) -> ToolObservation:
    """Confirm the image is inside a mount and ask the loop to attach it."""
    virtual, host = store.resolve(path)
    if not host.is_file():
        raise StorePathError(f"{virtual} is not a file.")
    if host.suffix.lower() not in IMAGE_SUFFIXES:
        raise StorePathError(f"{virtual} is not an image.")

    return ToolObservation(
        text=f"Image ready: {virtual}. Record facts with image_facts, then answer.",
        virtual_path=virtual,
        image_host_path=host,
    )


def record_image_facts(store: Store, args: ImageFactsArgs) -> ToolObservation:
    """Validate typed image facts and return them as the observation."""
    virtual, host = store.resolve(args.path)
    if not host.is_file() or host.suffix.lower() not in IMAGE_SUFFIXES:
        raise StorePathError(f"{virtual} is not an image.")

    facts = [{"label": item.label, "value": item.value} for item in args.facts]
    fields = tuple(item.label for item in args.facts)
    payload = {"path": virtual, "facts": facts}
    return ToolObservation(
        text=json.dumps(payload, ensure_ascii=False),
        virtual_path=virtual,
        image_fields=fields,
    )
