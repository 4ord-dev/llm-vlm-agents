import json

from agent_project.consts import TOOL_IMAGE_FACTS, TOOL_INSPECT_IMAGE, TOOL_READ_FILE
from agent_project.tools import execute_tool


def test_list_search_and_read(store) -> None:
    listing = execute_tool(store, "list_store", {"path": "/data"})
    assert "/data/inbox.md" in listing.text
    assert "/data/screen.png" in listing.text

    search = execute_tool(store, "search_store", {"query": "printer"})
    assert "/data/inbox.md" in search.text

    note = execute_tool(store, TOOL_READ_FILE, {"path": "/data/inbox.md"})
    assert "printer" in note.text
    assert note.virtual_path == "/data/inbox.md"


def test_tools_reject_paths_outside_mount(store) -> None:
    result = execute_tool(store, TOOL_READ_FILE, {"path": "/etc/passwd"})
    assert result.text.startswith("Tool error:")
    assert "etc/passwd" in result.text or "mounted" in result.text


def test_inspect_image_and_image_facts(store) -> None:
    inspected = execute_tool(store, TOOL_INSPECT_IMAGE, {"path": "/data/screen.png"})
    assert inspected.virtual_path == "/data/screen.png"
    assert inspected.image_host_path is not None
    assert inspected.image_host_path.name == "screen.png"

    facts = execute_tool(
        store,
        TOOL_IMAGE_FACTS,
        {
            "path": "/data/screen.png",
            "facts": [{"label": "object", "value": "terminal window"}],
        },
    )
    payload = json.loads(facts.text)
    assert payload["path"] == "/data/screen.png"
    assert facts.image_fields == ("object",)
