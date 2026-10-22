"""Run one local agent goal from the command line."""

import argparse
from pathlib import Path

from agent_project.agent import run_agent
from agent_project.consts import DEFAULT_TRACE_NAME, TRACES_DIR_NAME
from agent_project.llm import OpenRouterClient
from agent_project.mounts import default_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Personal desk assistant")
    parser.add_argument("goal", help="What the owner wants done")
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
    args = parser.parse_args()

    result = run_agent(
        args.goal,
        OpenRouterClient(),
        default_store(),
        trace_path=args.trace,
        attached_images=args.image,
    )
    print(result.answer)
    print(
        f"\nstop={result.stop_reason} steps={result.steps} "
        f"cost_usd={result.cost_usd:.4f}"
    )
    if result.cited_paths:
        print("cited: " + ", ".join(result.cited_paths))
    if result.image_fields:
        print("image_fields: " + ", ".join(result.image_fields))


if __name__ == "__main__":
    main()
