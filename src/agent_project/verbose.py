"""Stderr progress for one agent run. Image bytes stay out of the log."""

import json
import sys
from typing import Any

_COST_FORMAT = ".4f"


def report_context(step: int, cost_usd: float, messages: list[dict[str, Any]]) -> None:
    """Print the step header, cost so far, and the context about to be sent."""
    context_lines: list[str] = []
    for message in messages:
        context_lines.extend(_message_lines(message))
    prefix = "" if step == 1 else "\n"
    _write(
        f"{prefix}[step {step}]\n"
        f"cost_usd={cost_usd:{_COST_FORMAT}}\n"
        "context:\n"
        f"{_indent(context_lines)}"
    )


def report_action(
    cost_usd: float, step_cost_usd: float, result: dict[str, Any]
) -> None:
    """Print the cost after this model call and what the model chose to do."""
    _write(
        f"step_cost_usd={step_cost_usd:{_COST_FORMAT}}\n"
        f"cost_usd={cost_usd:{_COST_FORMAT}}\n"
        "action:\n"
        f"{_indent(_action_lines(result))}"
    )


def report_tool(
    name: str,
    arguments: Any,
    observation: str,
    attached_image: str | None,
) -> None:
    """Print one tool result. Host paths are not included."""
    lines = [f"{name} {_arguments(arguments)}".rstrip(), *observation.splitlines()]
    if attached_image:
        lines.append(f"attached_image: {attached_image}")
    _write("observation:\n" + _indent(lines))


def report_stop(reason: str, steps: int, cost_usd: float) -> None:
    """Print why the run ended and the cost at the stop."""
    _write(
        f"\n[stop]\nreason={reason}\nsteps={steps}\ncost_usd={cost_usd:{_COST_FORMAT}}"
    )


def _write(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


def _indent(lines: list[str]) -> str:
    return "\n".join(f"  {line}" for line in lines)


def _message_lines(message: dict[str, Any]) -> list[str]:
    lines = [f"[{message.get('role') or 'message'}]"]
    content = message.get("content")
    if isinstance(content, str):
        lines.extend(content.splitlines() or [""])
    elif isinstance(content, list):
        for part in content:
            lines.extend(_part_lines(part))
    elif content is not None:
        lines.append(str(content))
    for call in message.get("tool_calls") or []:
        if isinstance(call, dict):
            lines.append(_call_line(call))
    return lines


def _part_lines(part: Any) -> list[str]:
    if not isinstance(part, dict):
        return [str(part)]
    part_type = part.get("type")
    if part_type == "text":
        return (part.get("text") or "").splitlines() or [""]
    if part_type == "image_url":
        return ["[image]"]
    if part_type:
        return [f"[{part_type}]"]
    return ["[part]"]


def _action_lines(result: dict[str, Any]) -> list[str]:
    tool_calls = result.get("tool_calls") or []
    if tool_calls:
        return [_call_line(call) for call in tool_calls if isinstance(call, dict)]
    text = (result.get("text") or "").strip()
    if not text:
        return ["answer: (empty reply)"]
    return ["answer:", *text.splitlines()]


def _call_line(call: dict[str, Any]) -> str:
    function = call.get("function")
    source = function if isinstance(function, dict) else call
    name = source.get("name") or "tool"
    return f"call {name} {_arguments(source.get('arguments'))}".rstrip()


def _arguments(arguments: Any) -> str:
    if arguments is None:
        return ""
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments, ensure_ascii=False)
