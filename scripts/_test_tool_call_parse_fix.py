#!/usr/bin/env python3
"""Regression: Claude Code "tool call could not be parsed (retry also failed)".

Root causes fixed in v1.9.90:
1) stop_reason=tool_use with zero tool_use content blocks
2) empty-schema tools (EnterPlanMode/TaskList/...) never emitted when args=""
3) incomplete args shipped as {"_raw": "..."} which Claude Code rejects
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grok2api.protocol.anthropic_compat import (  # noqa: E402
    AnthropicStreamAssembler,
    _effective_tool_arguments_json,
    is_complete_tool_arguments_json,
    map_finish_to_stop_reason,
    openai_completion_to_anthropic,
)


def _sse_payloads(frames: list[str]) -> list[dict]:
    out: list[dict] = []
    for frame in frames:
        for line in frame.splitlines():
            if not line.startswith("data:"):
                continue
            raw = line[5:].strip()
            if not raw or raw == "[DONE]":
                continue
            out.append(json.loads(raw))
    return out


def _stop_reasons(payloads: list[dict]) -> list[str | None]:
    return [
        (p.get("delta") or {}).get("stop_reason")
        for p in payloads
        if p.get("type") == "message_delta"
    ]


def _starts(payloads: list[dict]) -> list[dict]:
    return [
        p.get("content_block") or {}
        for p in payloads
        if p.get("type") == "content_block_start"
    ]


def main() -> None:
    # map_finish: tool_calls alone is NOT tool_use
    assert map_finish_to_stop_reason("tool_calls", has_tool_calls=False) == "end_turn"
    assert map_finish_to_stop_reason("tool_calls", has_tool_calls=True) == "tool_use"
    assert map_finish_to_stop_reason("stop", has_tool_calls=True) == "tool_use"

    # empty-schema completeness
    assert is_complete_tool_arguments_json("{}", tool_name="EnterPlanMode") is True
    assert is_complete_tool_arguments_json("{}", tool_name="TaskList") is True
    assert is_complete_tool_arguments_json("{}", tool_name="Bash") is False
    assert _effective_tool_arguments_json("", tool_name="EnterPlanMode") == "{}"
    assert _effective_tool_arguments_json("", tool_name="Bash") == ""

    # non-stream: empty EnterPlanMode → tool_use + input {}
    msg = openai_completion_to_anthropic(
        content="",
        finish="tool_calls",
        tool_calls=[
            {
                "id": "1",
                "type": "function",
                "function": {"name": "EnterPlanMode", "arguments": ""},
            }
        ],
        model="x",
    )
    assert msg["stop_reason"] == "tool_use", msg
    assert len(msg["content"]) == 1 and msg["content"][0]["type"] == "tool_use"
    assert msg["content"][0]["input"] == {}

    # non-stream: incomplete Bash dropped → end_turn, no tool_use
    # (empty text block may still be present when content="")
    msg = openai_completion_to_anthropic(
        content="",
        finish="tool_calls",
        tool_calls=[
            {
                "id": "1",
                "type": "function",
                "function": {"name": "Bash", "arguments": '{"command":'},
            }
        ],
        model="x",
    )
    assert msg["stop_reason"] == "end_turn", msg
    assert not any(
        isinstance(b, dict) and b.get("type") == "tool_use" for b in (msg.get("content") or [])
    ), msg
    assert not any(
        isinstance(b, dict)
        and isinstance(b.get("input"), dict)
        and set(b.get("input") or {}) == {"_raw"}
        for b in (msg.get("content") or [])
    ), msg

    # non-stream: finish tool_calls with zero tools → end_turn
    msg = openai_completion_to_anthropic(
        content="hi", finish="tool_calls", tool_calls=[], model="x"
    )
    assert msg["stop_reason"] == "end_turn", msg
    assert msg["content"] and msg["content"][0]["type"] == "text"

    # stream: empty EnterPlanMode args filled at finish
    a = AnthropicStreamAssembler(
        message_id="m1",
        model="x",
        tools_requested=True,
        allowed_tool_names={"EnterPlanMode"},
    )
    frames = a.feed(
        tool_calls=[
            {
                "index": 0,
                "id": "t1",
                "function": {"name": "EnterPlanMode", "arguments": ""},
            }
        ]
    )
    frames += a.finish("tool_calls")
    payloads = _sse_payloads(frames)
    starts = _starts(payloads)
    assert any(s.get("type") == "tool_use" and s.get("name") == "EnterPlanMode" for s in starts), starts
    assert _stop_reasons(payloads) == ["tool_use"]
    assert a._saw_tool is True

    # stream: incomplete Bash only → no tool_use, stop end_turn
    a = AnthropicStreamAssembler(
        message_id="m2",
        model="x",
        tools_requested=True,
        allowed_tool_names={"Bash"},
    )
    a.feed(
        tool_calls=[
            {
                "index": 0,
                "id": "t1",
                "function": {"name": "Bash", "arguments": '{"command":'},
            }
        ]
    )
    payloads = _sse_payloads(a.finish("tool_calls"))
    assert not any(s.get("type") == "tool_use" for s in _starts(payloads)), payloads
    assert _stop_reasons(payloads) == ["end_turn"]
    assert a._saw_tool is False

    # stream: complete Bash still works
    a = AnthropicStreamAssembler(
        message_id="m3",
        model="x",
        tools_requested=True,
        allowed_tool_names={"Bash"},
    )
    frames = a.feed(
        tool_calls=[
            {
                "index": 0,
                "id": "t1",
                "function": {"name": "Bash", "arguments": '{"command":"ls"}'},
            }
        ]
    )
    frames += a.finish("tool_calls")
    payloads = _sse_payloads(frames)
    assert any(s.get("type") == "tool_use" and s.get("name") == "Bash" for s in _starts(payloads))
    assert _stop_reasons(payloads) == ["tool_use"]
    # full args should be present in deltas or start input
    joined = json.dumps(payloads, ensure_ascii=False)
    assert "ls" in joined

    print("OK: tool call parse fix regressions passed")


if __name__ == "__main__":
    main()
