"""Pydantic argument schemas for the course tools."""

from pydantic import BaseModel, Field

from agent_project.consts import (
    DEFAULT_MOUNT_VIRTUAL,
    MAX_FACT_LABEL_CHARS,
    MAX_FACT_VALUE_CHARS,
    MAX_IMAGE_FACTS,
    MAX_QUERY_CHARS,
    MAX_VIRTUAL_PATH_CHARS,
)


class ListStoreArgs(BaseModel):
    """List files under a virtual store path."""

    path: str = Field(
        default=DEFAULT_MOUNT_VIRTUAL,
        min_length=1,
        max_length=MAX_VIRTUAL_PATH_CHARS,
        description="Virtual path to list, for example /data.",
    )


class SearchStoreArgs(BaseModel):
    """Search file names and text under mounted stores."""

    query: str = Field(
        min_length=1,
        max_length=MAX_QUERY_CHARS,
        description="Case-insensitive text to match in virtual paths or file text.",
    )


class ReadFileArgs(BaseModel):
    """Read a text file by virtual path."""

    path: str = Field(
        min_length=1,
        max_length=MAX_VIRTUAL_PATH_CHARS,
        description="Virtual path of a text file, for example /data/inbox.md.",
    )


class InspectImageArgs(BaseModel):
    """Load a local image so the next step can see it."""

    path: str = Field(
        min_length=1,
        max_length=MAX_VIRTUAL_PATH_CHARS,
        description="Virtual path of an image, for example /data/screen.png.",
    )


class ImageFact(BaseModel):
    """One typed field read from a visible image."""

    label: str = Field(min_length=1, max_length=MAX_FACT_LABEL_CHARS)
    value: str = Field(min_length=1, max_length=MAX_FACT_VALUE_CHARS)


class ImageFactsArgs(BaseModel):
    """Record a short typed list of facts from a visible image."""

    path: str = Field(
        min_length=1,
        max_length=MAX_VIRTUAL_PATH_CHARS,
        description="Virtual path of the image these facts come from.",
    )
    facts: list[ImageFact] = Field(
        min_length=1,
        max_length=MAX_IMAGE_FACTS,
        description="Short list of label/value facts visible in the image.",
    )
