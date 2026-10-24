"""One agent loop: goal, tool, observation, next step or a cited answer."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_project.consts import (
    DEFAULT_MOUNT_VIRTUAL,
    MAX_ATTACHED_IMAGES,
    MAX_MODEL_STEPS,
    MAX_REPEAT_TOOL_CALLS,
    MAX_RUN_COST_USD,
    STOP_COMPLETED,
    STOP_EMPTY_REPLY,
    STOP_MAX_COST,
    STOP_MAX_STEPS,
    STOP_MESSAGES,
    STOP_REPEATED_TOOLS,
)
from agent_project.llm import ModelClient, image_part
from agent_project.mounts import Store
from agent_project.tools import TOOL_SPECS, execute_tool
from agent_project.tracing import append_trace
from agent_project.verbose import (
    report_action,
    report_context,
    report_stop,
    report_tool,
)

SYSTEM_PROMPT = """You are a personal desk assistant on one machine.
Use tools to inspect mounted stores. Never guess file or image contents.
Call independent tools together in one turn when you can.
Arguments must be virtual paths only (/data/..., never host drives).
Search and read text files. Look at images with inspect_image, then image_facts.
If one file is not enough, keep looking in the store before you answer.
Cite every virtual path or image field you used. Stop when you can answer."""


@dataclass
class AgentResult:
    """Outcome of one bounded run."""

    answer: str
    stop_reason: str
    steps: int
    cost_usd: float
    cited_paths: list[str] = field(default_factory=list)
    image_fields: list[str] = field(default_factory=list)


def _usage_cost(usage: dict[str, Any] | None) -> float:
    if not usage:
        return 0.0
    try:
        return float(usage.get("cost") or 0)
    except (TypeError, ValueError):
        return 0.0


def _tool_signature(tool_calls: list[dict[str, Any]]) -> tuple[tuple[str, str], ...]:
    return tuple(
        (call.get("name") or "", str(call.get("arguments") or ""))
        for call in tool_calls
    )


def _assistant_message(result: dict[str, Any]) -> dict[str, Any]:
    message: dict[str, Any] = {
        "role": "assistant",
        "content": result.get("text") or "",
    }
    tool_calls = result.get("tool_calls") or []
    if not tool_calls:
        return message
    message["tool_calls"] = [
        {
            "id": call["id"],
            "type": "function",
            "function": {"name": call["name"], "arguments": call["arguments"]},
        }
        for call in tool_calls
    ]
    return message


def _attach_images(store: Store, virtual_paths: list[str]) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for virtual in virtual_paths[:MAX_ATTACHED_IMAGES]:
        _normalized, host = store.resolve(virtual)
        parts.append(image_part(host))
    return parts


def _user_goal_message(
    goal: str, store: Store, attached_images: list[str]
) -> dict[str, Any]:
    mounts = ", ".join(store.virtual_roots) or DEFAULT_MOUNT_VIRTUAL
    text = (
        f"Goal: {goal}\nMounted stores: {mounts}\n"
        "Cite virtual paths in the final answer."
    )
    if not attached_images:
        return {"role": "user", "content": text}
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    content.extend(_attach_images(store, attached_images))
    return {"role": "user", "content": content}


def run_agent(
    goal: str,
    client: ModelClient,
    store: Store,
    *,
    trace_path: Path | None = None,
    attached_images: list[str] | None = None,
    max_steps: int = MAX_MODEL_STEPS,
    max_cost_usd: float = MAX_RUN_COST_USD,
    verbose: bool = False,
    messages: list[dict[str, Any]] | None = None,
) -> AgentResult:
    """Run the tool loop until an answer or a hard stop.

    Pass the same messages list on later goals to keep the agent context.
    Verbose runs print each step to stderr: cost so far, model context,
    and the action taken. Image bytes are omitted.
    """
    if max_steps < 1:
        max_steps = 1
    images = list(attached_images or [])
    if messages is None:
        messages = []
    if not messages:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.append(_user_goal_message(goal, store, images))
    cited_paths = list(images)
    image_fields: list[str] = []
    steps = 0
    cost_usd = 0.0
    last_signature: tuple[tuple[str, str], ...] | None = None
    repeat_count = 0

    if trace_path is not None:
        append_trace(
            trace_path,
            "start",
            {
                "goal": goal,
                "mounts": list(store.virtual_roots),
                "attached_images": images,
            },
        )

    while True:
        if steps >= max_steps:
            return _stop(
                STOP_MAX_STEPS,
                steps,
                cost_usd,
                cited_paths,
                image_fields,
                trace_path,
                verbose,
                messages,
            )
        if cost_usd >= max_cost_usd:
            return _stop(
                STOP_MAX_COST,
                steps,
                cost_usd,
                cited_paths,
                image_fields,
                trace_path,
                verbose,
                messages,
            )

        if verbose:
            report_context(steps + 1, cost_usd, messages)
        result = client.complete(messages, TOOL_SPECS)
        steps += 1
        step_cost_usd = _usage_cost(result.get("usage"))
        cost_usd += step_cost_usd
        tool_calls = result.get("tool_calls") or []
        if verbose:
            report_action(cost_usd, step_cost_usd, result)

        if trace_path is not None:
            append_trace(
                trace_path,
                "model",
                {
                    "step": steps,
                    "cost_usd": cost_usd,
                    "finish_reason": result.get("finish_reason"),
                    "tool_names": [call.get("name") for call in tool_calls],
                },
            )

        if not tool_calls:
            answer = (result.get("text") or "").strip()
            if not answer:
                return _stop(
                    STOP_EMPTY_REPLY,
                    steps,
                    cost_usd,
                    cited_paths,
                    image_fields,
                    trace_path,
                    verbose,
                    messages,
                )
            return _finish(
                answer,
                STOP_COMPLETED,
                steps,
                cost_usd,
                cited_paths,
                image_fields,
                trace_path,
                verbose,
                messages,
            )

        signature = _tool_signature(tool_calls)
        if signature == last_signature:
            repeat_count += 1
        else:
            repeat_count = 1
            last_signature = signature
        if repeat_count >= MAX_REPEAT_TOOL_CALLS:
            return _stop(
                STOP_REPEATED_TOOLS,
                steps,
                cost_usd,
                cited_paths,
                image_fields,
                trace_path,
                verbose,
                messages,
            )

        messages.append(_assistant_message(result))
        for call in tool_calls:
            observation = execute_tool(
                store, call["name"], call.get("arguments") or "{}"
            )
            if observation.virtual_path and observation.virtual_path not in cited_paths:
                cited_paths.append(observation.virtual_path)
            for label in observation.image_fields:
                if label not in image_fields:
                    image_fields.append(label)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": observation.text,
                }
            )
            attached_image = None
            if observation.image_host_path is not None:
                attached_image = observation.virtual_path or "image"
                visible = f"Visible image: {attached_image}"
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": visible},
                            image_part(observation.image_host_path),
                        ],
                    }
                )
            if verbose:
                report_tool(
                    call["name"],
                    call.get("arguments") or "",
                    observation.text,
                    attached_image,
                )
            if trace_path is not None:
                append_trace(
                    trace_path,
                    "tool",
                    {
                        "name": call["name"],
                        "virtual_path": observation.virtual_path,
                        "text": observation.text,
                    },
                )


def _stop(
    reason: str,
    steps: int,
    cost_usd: float,
    cited_paths: list[str],
    image_fields: list[str],
    trace_path: Path | None,
    verbose: bool,
    messages: list[dict[str, Any]],
) -> AgentResult:
    return _finish(
        STOP_MESSAGES[reason],
        reason,
        steps,
        cost_usd,
        cited_paths,
        image_fields,
        trace_path,
        verbose,
        messages,
    )


def _finish(
    answer: str,
    reason: str,
    steps: int,
    cost_usd: float,
    cited_paths: list[str],
    image_fields: list[str],
    trace_path: Path | None,
    verbose: bool,
    messages: list[dict[str, Any]],
) -> AgentResult:
    messages.append({"role": "assistant", "content": answer})
    if verbose:
        report_stop(reason, steps, cost_usd)
    if trace_path is not None:
        append_trace(
            trace_path,
            "stop",
            {
                "reason": reason,
                "steps": steps,
                "cost_usd": cost_usd,
                "cited_paths": cited_paths,
                "image_fields": image_fields,
            },
        )
    return AgentResult(
        answer=answer,
        stop_reason=reason,
        steps=steps,
        cost_usd=cost_usd,
        cited_paths=cited_paths,
        image_fields=image_fields,
    )
