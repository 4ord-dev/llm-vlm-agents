"""Run the desk assistant. Later goals keep the agent context. Ctrl+C exits."""

import argparse
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from agent_project.agent import AgentResult, run_agent
from agent_project.consts import DEFAULT_TRACE_NAME, EXIT_INTERRUPTED, TRACES_DIR_NAME
from agent_project.llm import ModelClient, OpenRouterClient
from agent_project.mounts import Store, default_store

_GOAL_PROMPT = "\nGoal (Ctrl+C to exit): "


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal desk assistant")
    parser.add_argument("goal", help="What the owner wants done")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print each step, the running cost, the model context, and the action",
    )
    parser.add_argument(
        "--image",
        action="append",
        default=[],
        help="Virtual path of an image to attach, for example /data/screen.png",
    )
    parser.add_argument(
        "--trace",
        type=Path,
        default=Path(TRACES_DIR_NAME) / DEFAULT_TRACE_NAME,
        help="JSON Lines trace file",
    )
    return parser


def _print_result(result: AgentResult) -> None:
    print(result.answer)
    print(
        f"\nstop={result.stop_reason} steps={result.steps} "
        f"cost_usd={result.cost_usd:.4f}"
    )
    if result.cited_paths:
        print("cited: " + ", ".join(result.cited_paths))
    if result.image_fields:
        print("image_fields: " + ", ".join(result.image_fields))


def run_goals(
    goal: str,
    client: ModelClient,
    store: Store,
    *,
    trace_path: Path | None = None,
    attached_images: list[str] | None = None,
    verbose: bool = False,
    next_goal: Callable[[], str] | None = None,
) -> None:
    """Answer goals in order. One message list is the agent context."""
    messages: list[dict[str, Any]] = []
    images = list(attached_images or [])
    while True:
        result = run_agent(
            goal,
            client,
            store,
            trace_path=trace_path,
            attached_images=images,
            verbose=verbose,
            messages=messages,
        )
        _print_result(result)
        if next_goal is None:
            return
        goal = next_goal()
        images = []


def _prompt_goal() -> str:
    while True:
        goal = input(_GOAL_PROMPT).strip()
        if goal:
            return goal


def execute(action: Callable[[], None]) -> None:
    """Run until the action returns. Ctrl+C and end of input leave quietly."""
    try:
        action()
    except KeyboardInterrupt:
        print("\nexit")
        raise SystemExit(EXIT_INTERRUPTED) from None
    except EOFError:
        print("\nexit")


def main() -> None:
    args = build_parser().parse_args()
    next_goal = _prompt_goal if sys.stdin.isatty() else None

    def action() -> None:
        run_goals(
            args.goal,
            OpenRouterClient(),
            default_store(),
            trace_path=args.trace,
            attached_images=args.image,
            verbose=args.verbose,
            next_goal=next_goal,
        )

    execute(action)


if __name__ == "__main__":
    main()
