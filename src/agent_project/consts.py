"""Limits and names for one agent run."""

MAX_MODEL_STEPS = 50
MAX_RUN_COST_USD = 0.10
MAX_READ_CHARS = 8000
MAX_SEARCH_HITS = 20
MAX_SEARCH_FILE_CHARS = 4000
MAX_LIST_ENTRIES = 100
MAX_IMAGE_FACTS = 8
MAX_FACT_LABEL_CHARS = 64
MAX_FACT_VALUE_CHARS = 160
MAX_QUERY_CHARS = 128
MAX_VIRTUAL_PATH_CHARS = 512
MAX_REPEAT_TOOL_CALLS = 15
MAX_ATTACHED_IMAGES = 4

DEFAULT_MOUNT_VIRTUAL = "/data"
DEFAULT_MOUNT_HOST_NAME = "data"
DEFAULT_TRACE_NAME = "agent.jsonl"
TRACES_DIR_NAME = "traces"

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
TEXT_SUFFIXES = (
    ".txt",
    ".md",
    ".json",
    ".csv",
    ".log",
    ".py",
    ".toml",
    ".yml",
    ".yaml",
)

TOOL_LIST_STORE = "list_store"
TOOL_SEARCH_STORE = "search_store"
TOOL_READ_FILE = "read_file"
TOOL_INSPECT_IMAGE = "inspect_image"
TOOL_IMAGE_FACTS = "image_facts"

STOP_COMPLETED = "completed"
STOP_MAX_STEPS = "max_steps"
STOP_MAX_COST = "max_cost"
STOP_REPEATED_TOOLS = "repeated_tools"
STOP_EMPTY_REPLY = "empty_reply"
EXIT_INTERRUPTED = 130

STOP_MESSAGES = {
    STOP_MAX_STEPS: f"Stopped: reached the {MAX_MODEL_STEPS}-step model limit.",
    STOP_MAX_COST: f"Stopped: reached the USD {MAX_RUN_COST_USD:.2f} run limit.",
    STOP_REPEATED_TOOLS: "Stopped: the same tool call repeated without progress.",
    STOP_EMPTY_REPLY: "Stopped: the model returned an empty reply.",
}
