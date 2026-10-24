import pytest

from agent_project.__main__ import build_parser, execute, run_goals
from agent_project.agent import run_agent
from agent_project.consts import (
    EXIT_INTERRUPTED,
    MAX_MODEL_STEPS,
    MAX_REPEAT_TOOL_CALLS,
    STOP_COMPLETED,
    STOP_MAX_COST,
    STOP_MAX_STEPS,
    STOP_REPEATED_TOOLS,
)
from agent_project.llm import MockClient


def _reply(text=None, tool_calls=None, cost=0.001) -> dict:
    return {
        "text": text,
        "tool_calls": tool_calls or [],
        "usage": {"cost": cost},
        "finish_reason": "stop",
    }


def _read_inbox(call_id: str) -> dict:
    return {
        "id": call_id,
        "name": "read_file",
        "arguments": '{"path":"/data/inbox.md"}',
    }


def test_agent_answers_from_store(store) -> None:
    client = MockClient(
        [
            _reply(tool_calls=[_read_inbox("call_1")]),
            _reply(text="The printer is in the hallway closet. Source: /data/inbox.md"),
        ]
    )
    result = run_agent("Where is the printer?", client, store)

    assert result.stop_reason == STOP_COMPLETED
    assert result.steps == 2
    assert "/data/inbox.md" in result.answer
    assert "/data/inbox.md" in result.cited_paths


def test_agent_stops_at_step_limit(store) -> None:
    replies = [
        _reply(
            tool_calls=[
                {
                    "id": f"call_{index}",
                    "name": "list_store",
                    "arguments": f'{{"path":"/data","note":"{index}"}}',
                }
            ]
        )
        for index in range(MAX_MODEL_STEPS + 1)
    ]
    result = run_agent("List the store", MockClient(replies), store)

    assert result.stop_reason == STOP_MAX_STEPS
    assert result.steps == MAX_MODEL_STEPS


def test_agent_stops_before_another_call_when_budget_is_spent(store) -> None:
    client = MockClient(
        [
            _reply(tool_calls=[_read_inbox("call_1")], cost=0.10),
            _reply(text="should not be requested"),
        ]
    )
    result = run_agent("Where is the printer?", client, store)

    assert result.stop_reason == STOP_MAX_COST
    assert result.steps == 1
    assert result.cost_usd == 0.10


def test_verbose_prints_steps_cost_context_and_actions(store, capsys) -> None:
    client = MockClient(
        [
            _reply(tool_calls=[_read_inbox("call_1")], cost=0.004),
            _reply(
                text="The printer is in the hallway closet. Source: /data/inbox.md",
                cost=0.006,
            ),
        ]
    )
    result = run_agent("Where is the printer?", client, store, verbose=True)

    captured = capsys.readouterr()
    assert captured.out == ""
    step1, step2 = captured.err.split("[step 2]", maxsplit=1)
    assert "[step 1]" in step1
    assert "cost_usd=0.0000" in step1
    assert "context:" in step1
    assert "Goal: Where is the printer?" in step1
    assert 'call read_file {"path":"/data/inbox.md"}' in step1
    assert "step_cost_usd=0.0040" in step1
    assert "cost_usd=0.0040" in step1
    assert "Hallway closet: the printer" in step1
    assert "cost_usd=0.0100" in step2
    assert "step_cost_usd=0.0060" in step2
    assert "The printer is in the hallway closet." in step2
    assert "reason=completed" in step2
    assert result.stop_reason == STOP_COMPLETED
    assert result.cost_usd == 0.01


def test_verbose_hides_image_bytes(store, capsys) -> None:
    client = MockClient([_reply(text="A captured screen.")])
    run_agent(
        "What is on the screen?",
        client,
        store,
        attached_images=["/data/screen.png"],
        verbose=True,
    )

    err = capsys.readouterr().err
    assert "[image]" in err
    assert "base64" not in err


def test_run_agent_is_quiet_without_verbose(store, capsys) -> None:
    client = MockClient(
        [
            _reply(tool_calls=[_read_inbox("call_1")]),
            _reply(text="The printer is in the hallway closet."),
        ]
    )
    run_agent("Where is the printer?", client, store)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_verbose_flags_are_optional() -> None:
    assert build_parser().parse_args(["-v", "goal"]).verbose is True
    assert build_parser().parse_args(["--verbose", "goal"]).verbose is True
    assert build_parser().parse_args(["goal"]).verbose is False


def test_later_goal_keeps_agent_context(store) -> None:
    seen: list[str] = []

    class RecordingClient:
        def complete(self, messages, tools=None):
            del tools
            seen.append(
                "\n".join(
                    message["content"]
                    for message in messages
                    if isinstance(message.get("content"), str)
                )
            )
            if len(seen) == 1:
                return _reply(text="The printer is in the hallway closet.")
            return _reply(text="The lamp was already in the notes.")

    context: list[dict] = []
    client = RecordingClient()
    run_agent("Where is the printer?", client, store, messages=context)
    run_agent("Where is the lamp?", client, store, messages=context)

    assert "Where is the printer?" in seen[1]
    assert "hallway closet" in seen[1]
    assert "Where is the lamp?" in seen[1]
    assert context[0]["role"] == "system"
    assert context[-1]["content"] == "The lamp was already in the notes."


def test_session_runs_one_goal_without_a_reader(store, capsys) -> None:
    run_goals(
        "Where is the printer?",
        MockClient([_reply(text="In the closet.")]),
        store,
    )

    assert "In the closet." in capsys.readouterr().out


def test_ctrl_c_during_the_model_call_exits(store, capsys) -> None:
    class Client:
        def complete(self, messages, tools=None):
            del messages, tools
            raise KeyboardInterrupt

    with pytest.raises(SystemExit) as caught:
        execute(lambda: run_goals("Where is the printer?", Client(), store))

    assert caught.value.code == EXIT_INTERRUPTED
    assert capsys.readouterr().out.strip() == "exit"


def test_session_exits_on_ctrl_c(store, capsys) -> None:
    replies = iter(
        [
            _reply(text="First answer."),
            _reply(text="Second answer."),
        ]
    )

    class Client:
        def complete(self, messages, tools=None):
            del messages, tools
            return next(replies)

    prompts = iter(["Second goal"])

    def next_goal() -> str:
        try:
            return next(prompts)
        except StopIteration:
            raise KeyboardInterrupt from None

    with pytest.raises(SystemExit) as caught:
        execute(lambda: run_goals("First goal", Client(), store, next_goal=next_goal))

    assert caught.value.code == EXIT_INTERRUPTED
    output = capsys.readouterr().out
    assert "First answer." in output
    assert "Second answer." in output
    assert output.strip().endswith("exit")


def test_agent_stops_on_repeated_tool_calls(store) -> None:
    same_call = _read_inbox("call_same")
    replies = [_reply(tool_calls=[same_call]) for _ in range(MAX_REPEAT_TOOL_CALLS + 1)]
    result = run_agent("Where is the printer?", MockClient(replies), store)

    assert result.stop_reason == STOP_REPEATED_TOOLS
    assert result.steps == MAX_REPEAT_TOOL_CALLS
