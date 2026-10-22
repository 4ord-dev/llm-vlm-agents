"""Tool schemas and dispatch. Arguments are validated at the call site."""

from typing import Any

import openai
from pydantic import ValidationError

from agent_project.consts import (
    TOOL_IMAGE_FACTS,
    TOOL_INSPECT_IMAGE,
    TOOL_LIST_STORE,
    TOOL_READ_FILE,
    TOOL_SEARCH_STORE,
)
from agent_project.models import (
    ImageFactsArgs,
    InspectImageArgs,
    ListStoreArgs,
    ReadFileArgs,
    SearchStoreArgs,
)
from agent_project.mounts import Store, StorePathError
from agent_project.store_tools import (
    ToolObservation,
    list_store,
    read_file,
    search_store,
)
from agent_project.vision_tools import inspect_image, record_image_facts

TOOL_SPECS: list[dict[str, Any]] = [
    openai.pydantic_function_tool(
        ListStoreArgs,
        name=TOOL_LIST_STORE,
        description="List files under a virtual store path such as /data.",
    ),
    openai.pydantic_function_tool(
        SearchStoreArgs,
        name=TOOL_SEARCH_STORE,
        description="Search mounted stores by file name or text content.",
    ),
    openai.pydantic_function_tool(
        ReadFileArgs,
        name=TOOL_READ_FILE,
        description="Read a text file by virtual path.",
    ),
    openai.pydantic_function_tool(
        InspectImageArgs,
        name=TOOL_INSPECT_IMAGE,
        description=(
            "Load a local image from a virtual path so the next step can see it."
        ),
    ),
    openai.pydantic_function_tool(
        ImageFactsArgs,
        name=TOOL_IMAGE_FACTS,
        description="Record a short typed list of facts from a visible image.",
    ),
]


def _parse_args(model, arguments: str | dict[str, Any]):
    if isinstance(arguments, dict):
        return model.model_validate(arguments)
    return model.model_validate_json(arguments)


def execute_tool(
    store: Store, name: str, arguments: str | dict[str, Any]
) -> ToolObservation:
    """Run one named tool. Errors stay user-facing and use virtual paths."""
    try:
        if name == TOOL_LIST_STORE:
            args = _parse_args(ListStoreArgs, arguments)
            return list_store(store, args.path)
        if name == TOOL_SEARCH_STORE:
            args = _parse_args(SearchStoreArgs, arguments)
            return search_store(store, args.query)
        if name == TOOL_READ_FILE:
            args = _parse_args(ReadFileArgs, arguments)
            return read_file(store, args.path)
        if name == TOOL_INSPECT_IMAGE:
            args = _parse_args(InspectImageArgs, arguments)
            return inspect_image(store, args.path)
        if name == TOOL_IMAGE_FACTS:
            args = _parse_args(ImageFactsArgs, arguments)
            return record_image_facts(store, args)
    except (StorePathError, ValidationError, ValueError, OSError) as error:
        return ToolObservation(text=f"Tool error: {error}")

    return ToolObservation(text=f"Tool error: unknown tool {name}.")
