from agent_project.agent import run_agent
from agent_project.consts import (
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


def test_agent_stops_on_repeated_tool_calls(store) -> None:
    same_call = _read_inbox("call_same")
    replies = [_reply(tool_calls=[same_call]) for _ in range(MAX_REPEAT_TOOL_CALLS + 1)]
    result = run_agent("Where is the printer?", MockClient(replies), store)

    assert result.stop_reason == STOP_REPEATED_TOOLS
    assert result.steps == MAX_REPEAT_TOOL_CALLS
