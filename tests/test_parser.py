"""Tests for the chat parser."""

import json
import pytest
from divineos.core.parser import (
    parse_jsonl,
    parse_markdown_chat,
    ParsedMessage,
)


@pytest.fixture
def tmp_jsonl(tmp_path):
    """Create a temporary JSONL file with Claude Code format."""
    data = [
        {
            "type": "user",
            "timestamp": "2026-03-14T10:00:00Z",
            "uuid": "user-1",
            "message": {"content": "Hello, how are you?"},
        },
        {
            "type": "assistant",
            "timestamp": "2026-03-14T10:00:01Z",
            "uuid": "asst-1",
            "message": {
                "model": "claude-opus-4-6",
                "content": [
                    {"type": "text", "text": "I'm doing well, thanks!"},
                    {
                        "type": "tool_use",
                        "id": "tool-1",
                        "name": "Read",
                        "input": {"file_path": "/tmp/test.py"},
                    },
                ],
            },
        },
    ]
    path = tmp_path / "session.jsonl"
    with open(path, "w") as f:
        for entry in data:
            f.write(json.dumps(entry) + "\n")
    return path


@pytest.fixture
def tmp_markdown(tmp_path):
    """Create a temporary markdown chat file."""
    content = """## User

What is Python?

## Assistant

Python is a programming language.

## User

Thanks!
"""
    path = tmp_path / "chat.md"
    path.write_text(content)
    return path


class TestParseJsonl:
    def test_parses_user_message(self, tmp_jsonl):
        result = parse_jsonl(tmp_jsonl)
        assert result.message_count >= 1
        user_msgs = [m for m in result.messages if m.role == "user"]
        assert len(user_msgs) == 1
        assert user_msgs[0].content == "Hello, how are you?"

    def test_parses_assistant_text(self, tmp_jsonl):
        result = parse_jsonl(tmp_jsonl)
        asst_msgs = [m for m in result.messages if m.role == "assistant"]
        assert len(asst_msgs) == 1
        assert asst_msgs[0].content == "I'm doing well, thanks!"
        assert asst_msgs[0].model == "claude-opus-4-6"

    def test_parses_tool_call(self, tmp_jsonl):
        result = parse_jsonl(tmp_jsonl)
        tool_msgs = [m for m in result.messages if m.role == "tool_call"]
        assert len(tool_msgs) == 1
        assert tool_msgs[0].tool_name == "Read"
        assert tool_msgs[0].tool_input == {"file_path": "/tmp/test.py"}

    def test_total_message_count(self, tmp_jsonl):
        result = parse_jsonl(tmp_jsonl)
        assert result.message_count == 3  # user + assistant text + tool_use

    def test_file_not_found(self, tmp_path):
        result = parse_jsonl(tmp_path / "nonexistent.jsonl")
        assert result.message_count == 0
        assert len(result.parse_errors) == 1

    def test_malformed_json(self, tmp_path):
        path = tmp_path / "bad.jsonl"
        path.write_text("not json\n{}\n")
        result = parse_jsonl(path)
        assert len(result.parse_errors) == 1


class TestParseMarkdown:
    def test_parses_messages(self, tmp_markdown):
        result = parse_markdown_chat(tmp_markdown)
        assert result.message_count == 3

    def test_roles_correct(self, tmp_markdown):
        result = parse_markdown_chat(tmp_markdown)
        assert result.messages[0].role == "user"
        assert result.messages[1].role == "assistant"
        assert result.messages[2].role == "user"

    def test_content_correct(self, tmp_markdown):
        result = parse_markdown_chat(tmp_markdown)
        assert "Python" in result.messages[0].content
        assert "programming language" in result.messages[1].content

    def test_file_not_found(self, tmp_path):
        result = parse_markdown_chat(tmp_path / "nope.md")
        assert result.message_count == 0


class TestParsedMessage:
    def test_to_dict_minimal(self):
        msg = ParsedMessage(role="user", content="hello", timestamp="now")
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "hello"
        assert "tool_name" not in d

    def test_to_dict_with_tool(self):
        msg = ParsedMessage(
            role="tool_call",
            content="{}",
            timestamp="now",
            tool_name="Read",
            tool_input={"file_path": "/tmp/x"},
        )
        d = msg.to_dict()
        assert d["tool_name"] == "Read"
        assert d["tool_input"]["file_path"] == "/tmp/x"
