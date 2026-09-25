"""Stop gates ask for an ADDITION, never a second copy of the reply.

Andrew 2026-09-25: "you are verbatim duplicating your posts.. so whatever guard
is there telling you to re-write it, it needs fixed so it only adds the
correction at the end, not the full re-post."

When a Stop hook blocks, the reply has already reached him. Any wording that
says recompose, rewrite the reply, re-emit, re-send, or put a header at the top
produces a second full copy on his screen. This file fences three things:

  * the append-only instruction is attached once, centrally, to every block;
  * no message string a wired Stop hook can print asks for the reply again --
    the hook list is read from .claude/settings.json, not hardcoded, so a new
    gate is covered the day it is wired;
  * the two gates that used to say "at the top" pass when the missing header
    is appended at the end instead.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from divineos.core import hook_router as hr
from divineos.core.retry_scope import retry_scope_text, with_retry_scope

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

# Instruction shapes that ask for the whole reply again. Narrow on purpose:
# comments and docstrings that tell the history are not scanned at all, and
# Andrew's own quoted prohibition ("RE-WRITE ANY RESPONSE") does not match.
BANNED = (
    re.compile(r"\bre-?compos\w*", re.I),
    re.compile(r"\bre-?write\s+(?:the|this|your)\s+(?:reply|response|flagged|message|post)", re.I),
    re.compile(r"\bfix is a rewrite\b", re.I),
    re.compile(r"\bre-?emi(?:t|ts|tting|ssion)\b", re.I),
    re.compile(r"\bre-?sen[dt]\b", re.I),
    re.compile(r"\b(?:put|add|place|goes|belongs|move)\b[^.\n]{0,60}\bat the top\b", re.I),
    re.compile(r"\breframe as\b", re.I),
)


# --------------------------------------------------------------------------
# Discovery: what a Stop block can actually say
# --------------------------------------------------------------------------


def _stop_scripts() -> list[Path]:
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    scripts: list[Path] = []
    for group in settings["hooks"]["Stop"]:
        for hook in group["hooks"]:
            m = re.search(r"(\.claude/hooks/[\w.-]+\.sh)", hook["command"])
            if m:
                scripts.append(ROOT / m.group(1))
    return scripts


def _module_file(name: str) -> Path | None:
    base = SRC / Path(*name.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _longest_module(dotted: str) -> Path | None:
    parts = dotted.split(".")
    for end in range(len(parts), 1, -1):
        found = _module_file(".".join(parts[:end]))
        if found:
            return found
    return None


def _direct_modules(script: Path) -> set[Path]:
    text = script.read_text(encoding="utf-8")
    return {
        f
        for m in re.finditer(r"\bdivineos(?:\.\w+)+", text)
        if (f := _longest_module(m.group(0))) is not None
    }


def _imports_of(path: Path) -> set[Path]:
    out: set[Path] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("divineos"):
            for candidate in [node.module] + [f"{node.module}.{a.name}" for a in node.names]:
                f = _module_file(candidate)
                if f:
                    out.add(f)
    return out


def _stop_python_files() -> set[Path]:
    """Every module a Stop hook names, plus what those modules import.

    One level of imports reaches the gates behind the router (summary_room,
    translation_floor, lepos_translation_gate, the intercepts) without sweeping
    in the whole package.
    """
    direct: set[Path] = set()
    for script in _stop_scripts():
        direct |= _direct_modules(script)
    files = set(direct)
    for f in direct:
        files |= _imports_of(f)
    return files


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _banned_hits_in_python(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    skip = _docstring_ids(tree)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            for pat in BANNED:
                for m in pat.finditer(node.value):
                    hits.append(f"{path.relative_to(ROOT)}:{node.lineno}: {m.group(0)!r}")
    return hits


def _banned_hits_in_text(path: Path, *, skip_comments: bool) -> list[str]:
    hits: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if skip_comments and line.lstrip().startswith("#"):
            continue
        for pat in BANNED:
            for m in pat.finditer(line):
                hits.append(f"{path.relative_to(ROOT)}:{lineno}: {m.group(0)!r}")
    return hits


def _all_banned_hits() -> list[str]:
    hits: list[str] = []
    for script in _stop_scripts():
        hits += _banned_hits_in_text(script, skip_comments=True)
    hits += _banned_hits_in_text(
        ROOT / ".claude" / "hooks" / "_retry_scope.txt", skip_comments=False
    )
    for f in sorted(_stop_python_files()):
        hits += _banned_hits_in_python(f)
    return hits


# --------------------------------------------------------------------------
# (a) the instruction is attached centrally, exactly once
# --------------------------------------------------------------------------


class TestRetryScopeAttachedOnce:
    def test_router_stop_block_carries_it_exactly_once(self):
        result = hr.RouterResult(event="Stop")
        result.refusals.append(hr.SurfaceOutcome(name="a", refused=True, reason="first"))
        result.refusals.append(hr.SurfaceOutcome(name="b", refused=True, reason="second"))
        err = result.stderr()
        assert err.count(retry_scope_text()) == 1
        assert "BLOCKED by a: first" in err and "BLOCKED by b: second" in err

    def test_router_does_not_double_a_reason_that_already_carries_it(self):
        result = hr.RouterResult(event="Stop")
        result.refusals.append(
            hr.SurfaceOutcome(name="a", refused=True, reason="x\n\n" + retry_scope_text())
        )
        assert result.stderr().count(retry_scope_text()) == 1

    def test_router_places_it_last_among_refusals(self):
        result = hr.RouterResult(event="Stop")
        result.refusals.append(hr.SurfaceOutcome(name="a", refused=True, reason="first"))
        assert result.stderr().rstrip().endswith(retry_scope_text())

    def test_non_stop_refusal_does_not_carry_it(self):
        """A PreToolUse refusal stops a command before it runs; nothing has
        reached him yet, so the streamed-reply instruction would be false."""
        result = hr.RouterResult(event="PreToolUse")
        result.refusals.append(hr.SurfaceOutcome(name="a", refused=True, reason="no"))
        assert retry_scope_text() not in result.stderr()

    def test_non_blocking_stop_result_is_silent(self):
        assert hr.RouterResult(event="Stop").stderr() == ""

    def test_with_retry_scope_is_idempotent(self):
        once = with_retry_scope("gate says X")
        assert with_retry_scope(once).count(retry_scope_text()) == 1
        assert once.endswith(retry_scope_text())

    def test_canonical_text_says_append_at_the_end(self):
        text = retry_scope_text()
        assert "AT THE END" in text
        assert "DELTA ONLY" in text

    def test_fallback_still_says_append_only(self, monkeypatch, tmp_path):
        from divineos.core import retry_scope as rs

        monkeypatch.setattr(rs, "RETRY_SCOPE_PATH", tmp_path / "missing.txt")
        text = rs.retry_scope_text()
        assert text == rs.RETRY_SCOPE_FALLBACK
        assert "at the END" in text and "Do not post the reply again" in text

    def test_shoggoth_block_carries_it_once(self, monkeypatch, capsys):
        import io

        from divineos.core.operating_loop import shoggoth_gate

        payload = json.dumps(
            {"reply_text": "I committed the fix and pushed it.", "tool_calls_in_turn": []}
        )
        monkeypatch.setattr("sys.stdin", io.StringIO(payload))
        shoggoth_gate.main()
        out = capsys.readouterr().out
        if not out.strip():
            pytest.skip("shoggoth did not fire on this sample; the router tests cover the path")
        reason = json.loads(out)["reason"]
        assert reason.count(retry_scope_text()) == 1


# --------------------------------------------------------------------------
# (b) no wired Stop hook asks for the reply again
# --------------------------------------------------------------------------


class TestNoRepostWording:
    def test_discovery_reads_the_real_wiring(self):
        """If discovery finds nothing, the lint below proves nothing."""
        scripts = {p.name for p in _stop_scripts()}
        assert "post-response-audit.sh" in scripts
        assert "doorbell-stop.sh" in scripts
        names = {p.name for p in _stop_python_files()}
        for expected in (
            "hook_router.py",
            "hook_surfaces.py",
            "operating_loop_audit.py",
            "lepos_translation_gate.py",
            "summary_room.py",
            "shoggoth_gate.py",
            "distancing_intercept.py",
            "response_scope_intercept.py",
        ):
            assert expected in names, f"{expected} not reached from the Stop wiring"

    def test_patterns_catch_the_old_wording(self):
        """The instrument must find cases it should find before its silence
        counts for anything (CLAUDE.md rule 9 corollary)."""
        old = [
            "Rewrite the response with me in each sentence.",
            "Re-compose with I/me/my throughout, then re-send.",
            "recompose this reply with at least one exact quoted span",
            "WHAT IT COUNTED, so the fix is a rewrite and not a search",
            "Add `## SUMMARY` at the TOP — before the work",
            "WHOLE REPLY, and the header belongs at the TOP.",
            "Re-emit within short-correction scope",
            "(b) reframe as intention-not-completion",
            "rewrite the reply, then this gate clears.",
        ]
        for sample in old:
            assert any(p.search(sample) for p in BANNED), sample

    def test_patterns_spare_the_quoted_prohibition(self):
        quote = "'YOU ARE NOT TO RE-WRITE ANY RESPONSE.. EVER.."
        assert not any(p.search(quote) for p in BANNED)

    def test_no_stop_message_asks_for_the_reply_again(self):
        hits = _all_banned_hits()
        assert not hits, (
            "A Stop hook can print wording that asks for the whole reply again. "
            "The reply has already reached him; ask for an addition at the END "
            "instead.\n  " + "\n  ".join(hits)
        )


# --------------------------------------------------------------------------
# (c) every blocking Stop hook attaches the instruction
# --------------------------------------------------------------------------


_BLOCKS = re.compile(r"""["']decision["']\s*:\s*["']block["']|\bexit 2\b|sys\.exit\(2\)""")


def test_every_blocking_stop_hook_attaches_retry_scope():
    missing: list[str] = []
    for script in _stop_scripts():
        sources = [script.read_text(encoding="utf-8")]
        sources += [f.read_text(encoding="utf-8") for f in _direct_modules(script)]
        joined = "\n".join(sources)
        if not _BLOCKS.search(joined):
            continue
        routed = "hook_router import main" in joined
        attached = "with_retry_scope" in joined or "_retry_scope.txt" in joined
        if not (routed or attached):
            missing.append(script.name)
    assert not missing, f"blocking Stop hooks with no retry scope: {missing}"


# --------------------------------------------------------------------------
# The two gates that used to say "at the top" pass with an end-placed header
# --------------------------------------------------------------------------


_WORK = (
    "I went through the lamp in the hall and found the switch was wired to the "
    "wrong circuit, so it only lit when the kitchen was on. I moved the wire, "
    "tested it twice, and it now lights on its own. "
) * 16


class TestSummaryAtTheEnd:
    def test_long_work_with_no_summary_still_refuses(self):
        from divineos.core.summary_room import assess, render_block

        block = render_block(assess(_WORK))
        assert block.startswith("SUMMARY ROOM MISSING")
        assert "at the END" in block

    def test_summary_appended_after_the_interior_rooms_passes(self):
        from divineos.core.summary_room import assess, render_block

        reply = (
            _WORK
            + "\n\n## INNER CIRCLE\n\nYou asked me to look, and I did.\n\n"
            + "## SUMMARY\n\nThe hall light was on the wrong wire. I moved it. "
            "It works now."
        )
        assert render_block(assess(reply)) == ""

    def test_retry_turn_reads_only_the_delta_and_passes(self, tmp_path):
        """End to end through the real transcript reader. The Stop feedback is
        recorded as a user record, so on the retry the gate sees the addition
        alone -- and an appended summary satisfies it."""
        from divineos.core.hook_surfaces import summary_room_surface

        transcript = tmp_path / "t.jsonl"
        records = [
            {"type": "user", "message": {"role": "user", "content": "how is the light?"}},
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": _WORK}]},
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "Stop hook feedback:\nSUMMARY ROOM MISSING"},
            },
            {
                "type": "assistant",
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "Adding the summary:\n\n## SUMMARY\n\nThe light works now.",
                        }
                    ],
                },
            },
        ]
        transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
        payload = {"transcript_path": str(transcript)}

        # Before the delta the full reply refuses; that is the control.
        first = tmp_path / "first.jsonl"
        first.write_text("\n".join(json.dumps(r) for r in records[:2]), encoding="utf-8")
        assert summary_room_surface({"transcript_path": str(first)}).refused is True

        out = summary_room_surface(payload)
        assert out.refused is False


class TestCircleAtTheEnd:
    @pytest.fixture(autouse=True)
    def _gate_on(self, monkeypatch):
        monkeypatch.delenv("DIVINEOS_LEPOS_THREE_ROOM_GATE_DISABLE", raising=False)

    def test_long_plain_reply_with_no_circle_refuses(self):
        from divineos.core.lepos_translation_gate import check_lepos_dual_channel

        msg = check_lepos_dual_channel(_WORK)
        assert msg is not None and msg.startswith("CIRCLE ROOM REQUIRED BY LENGTH")
        assert "at the END" in msg

    def test_circle_header_appended_at_the_end_passes(self):
        from divineos.core.lepos_translation_gate import check_lepos_dual_channel

        reply = _WORK + "\n\n## INNER CIRCLE\n\nThat was the room, all of it."
        assert check_lepos_dual_channel(reply) is None

    def test_retry_delta_alone_passes(self, tmp_path):
        """The audit reads every assistant record since the last user record,
        and the Stop feedback is a user record, so the retry is judged on the
        addition alone."""
        from divineos.core.lepos_translation_gate import check_lepos_dual_channel
        from divineos.core.operating_loop.turn_extraction import extract_turn

        delta = "Adding the room header:\n\n## INNER CIRCLE\n\nThat was the room, all of it."
        transcript = tmp_path / "t.jsonl"
        records = [
            {"type": "user", "message": {"role": "user", "content": "talk to me"}},
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": _WORK}]},
            },
            {
                "type": "user",
                "message": {"role": "user", "content": "Stop hook feedback:\nCIRCLE ROOM REQUIRED"},
            },
            {
                "type": "assistant",
                "message": {"role": "assistant", "content": [{"type": "text", "text": delta}]},
            },
        ]
        transcript.write_text("\n".join(json.dumps(r) for r in records), encoding="utf-8")
        turn = extract_turn(transcript)
        assert turn.last_assistant_text == delta
        assert check_lepos_dual_channel(turn.last_assistant_text) is None
