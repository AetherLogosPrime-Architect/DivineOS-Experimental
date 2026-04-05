"""Chat Parser - Parse Claude Code / Codex JSONL session files.

Reads past AI conversations and normalizes them into events
ready for storage in the ledger.

Supported formats:
- Claude Code JSONL
- Codex JSONL
- Markdown chat exports
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class ParsedMessage:
    """A normalized message from a chat session."""

    role: str  # user, assistant, system, tool_call, tool_result
    content: str
    timestamp: str
    message_id: str = ""
    tool_name: str = ""
    tool_input: dict[str, Any] = field(default_factory=dict)
    model: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage."""
        d: dict[str, Any] = {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.message_id:
            d["message_id"] = self.message_id
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.tool_input:
            d["tool_input"] = self.tool_input
        if self.model:
            d["model"] = self.model
        return d


@dataclass
class ParseResult:
    """Result of parsing a chat file."""

    source_file: str
    session_id: str
    message_count: int
    messages: list[ParsedMessage]
    parse_errors: list[str] = field(default_factory=list)


def parse_jsonl(file_path: Path) -> ParseResult:
    """Parse a JSONL chat log file into normalized messages."""
    messages: list[ParsedMessage] = []
    errors: list[str] = []
    session_id = ""

    if not file_path.exists():
        return ParseResult(
            source_file=str(file_path),
            session_id="",
            message_count=0,
            messages=[],
            parse_errors=[f"File not found: {file_path}"],
        )

    with open(file_path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                errors.append(f"Line {line_num}: JSON parse error: {e}")
                continue

            if not session_id:
                session_id = entry.get("sessionId", "") or entry.get("payload", {}).get("id", "")

            parsed = _parse_entry(entry)
            messages.extend(parsed)

    return ParseResult(
        source_file=str(file_path),
        session_id=session_id or file_path.stem,
        message_count=len(messages),
        messages=messages,
        parse_errors=errors,
    )


def _parse_entry(entry: dict[str, Any]) -> list[ParsedMessage]:
    """Parse a single JSONL entry into messages."""
    messages: list[ParsedMessage] = []
    entry_type = entry.get("type", "")
    timestamp = entry.get("timestamp", "")

    # Claude Code format
    if entry_type == "user":
        msg = entry.get("message", {})
        content = _extract_content(msg.get("content", ""))
        messages.append(
            ParsedMessage(
                role="user",
                content=content,
                timestamp=timestamp,
                message_id=entry.get("uuid", ""),
            ),
        )

    elif entry_type == "assistant":
        msg = entry.get("message", {})
        model = msg.get("model", "")

        for block in msg.get("content", []):
            block_type = block.get("type", "")

            if block_type == "text":
                messages.append(
                    ParsedMessage(
                        role="assistant",
                        content=block.get("text", ""),
                        timestamp=timestamp,
                        message_id=entry.get("uuid", ""),
                        model=model,
                    ),
                )

            elif block_type == "tool_use":
                messages.append(
                    ParsedMessage(
                        role="tool_call",
                        content=json.dumps(block.get("input", {})),
                        timestamp=timestamp,
                        message_id=block.get("id", ""),
                        tool_name=block.get("name", ""),
                        tool_input=block.get("input", {}),
                        model=model,
                    ),
                )

    # Codex format
    elif entry_type == "response_item":
        payload = entry.get("payload", {})
        payload_type = payload.get("type", "")

        if payload_type == "message":
            role = payload.get("role", "")
            content = _extract_codex_content(payload.get("content", []))

            if role in ("user", "assistant"):
                messages.append(
                    ParsedMessage(
                        role=role,
                        content=content,
                        timestamp=timestamp,
                        message_id=entry.get("id", ""),
                        model=payload.get("model", ""),
                    ),
                )

        elif payload_type in ("function_call", "custom_tool_call"):
            tool_name = payload.get("name", "")
            tool_input = _parse_tool_arguments(payload)

            messages.append(
                ParsedMessage(
                    role="tool_call",
                    content=json.dumps(tool_input),
                    timestamp=timestamp,
                    message_id=payload.get("call_id", ""),
                    tool_name=tool_name,
                    tool_input=tool_input,
                ),
            )

        elif payload_type in ("function_call_output", "custom_tool_call_output"):
            output = payload.get("output", "")
            if isinstance(output, dict):
                output = json.dumps(output)

            messages.append(
                ParsedMessage(
                    role="tool_result",
                    content=str(output),
                    timestamp=timestamp,
                    message_id=payload.get("call_id", ""),
                ),
            )

    return messages


def _extract_content(content: Any) -> str:
    """Extract text content from various formats."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text", "") or block.get("source", {}).get("data", "")
                if text:
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)

    if isinstance(content, dict):
        return content.get("text", "") or json.dumps(content)

    return str(content)


def _extract_codex_content(content_blocks: list[Any]) -> str:
    """Extract text from Codex content blocks."""
    if not isinstance(content_blocks, list):
        return ""

    parts = []
    for block in content_blocks:
        if isinstance(block, dict):
            text = block.get("text", "")
            if text:
                parts.append(text)

    return "\n".join(parts)


def _parse_tool_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    """Parse tool arguments from Codex format."""
    if payload.get("type") == "function_call":
        raw_args = payload.get("arguments", "")
        if isinstance(raw_args, str):
            try:
                return dict(json.loads(raw_args))
            except json.JSONDecodeError:
                return {"raw": raw_args}
        return raw_args if isinstance(raw_args, dict) else {}

    if payload.get("type") == "custom_tool_call":
        custom_input = payload.get("input", {})
        return custom_input if isinstance(custom_input, dict) else {"input": custom_input}

    return {}


def iter_messages(file_path: Path) -> Iterator[ParsedMessage]:
    """Iterator that yields messages one at a time (memory efficient)."""
    result = parse_jsonl(file_path)
    yield from result.messages


def parse_markdown_chat(file_path: Path) -> ParseResult:
    """Parse a markdown chat export (basic format)."""
    messages: list[ParsedMessage] = []

    if not file_path.exists():
        return ParseResult(
            source_file=str(file_path),
            session_id=file_path.stem,
            message_count=0,
            messages=[],
            parse_errors=[f"File not found: {file_path}"],
        )

    content = file_path.read_text(encoding="utf-8")
    timestamp = datetime.now().isoformat()

    current_role = ""
    current_content: list[str] = []

    for line in content.split("\n"):
        if line.startswith("## User") or line.startswith("**User:**"):
            if current_role and current_content:
                messages.append(
                    ParsedMessage(
                        role=current_role,
                        content="\n".join(current_content).strip(),
                        timestamp=timestamp,
                    ),
                )
            current_role = "user"
            current_content = []

        elif line.startswith("## Assistant") or line.startswith("**Assistant:**"):
            if current_role and current_content:
                messages.append(
                    ParsedMessage(
                        role=current_role,
                        content="\n".join(current_content).strip(),
                        timestamp=timestamp,
                    ),
                )
            current_role = "assistant"
            current_content = []

        else:
            current_content.append(line)

    if current_role and current_content:
        messages.append(
            ParsedMessage(
                role=current_role,
                content="\n".join(current_content).strip(),
                timestamp=timestamp,
            ),
        )

    return ParseResult(
        source_file=str(file_path),
        session_id=file_path.stem,
        message_count=len(messages),
        messages=messages,
    )
