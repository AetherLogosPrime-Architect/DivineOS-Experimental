"""The session-init launcher must deliver what its children print.

Aria asked for this test by name in her letter of 2026-09-23: count the
characters arriving THROUGH the launcher against the same child run alone,
per child, "because 'it ran' and 'it arrived' are the gap here."

The integration tests below FAIL against the launcher as it stood before
this change, which is the only thing that makes them worth trusting. The
launcher ran every child with ``2>&1 >/dev/null`` -- stderr kept, stdout
discarded -- so 18,931 measured characters were prepared and thrown away at
every session start.

The seam (Feathers, walk-d34ecb4259a9) is that the roster resolves against
REPO_ROOT, which comes from git. So a scratch repo carrying children with
the real roster names drives the real launcher without touching the ten live
loaders, and HOME redirects the session markers and the liveness log.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from divineos.core.hook_context_merge import (
    collect_dir,
    merge_contexts,
    read_child_context,
)

from tests._bash_resolver import bash_executable

_BASH = bash_executable()
_needs_bash = pytest.mark.skipif(_BASH is None, reason="no usable bash interpreter found")

LAUNCHER = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "session-init-once.sh"

PAYLOAD = json.dumps(
    {
        "session_id": "launcher-delivery-test",
        "transcript_path": "/tmp/launcher-delivery.jsonl",
        "hook_event_name": "UserPromptSubmit",
        "prompt": "hello",
    }
)


# --------------------------------------------------------------------------
# The reader, at every boundary Knuth's lens enumerated for the walk.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected_context", "expected_reason"),
    [
        ("", None, "empty"),
        ("   \n  ", None, "empty"),
        ("plain surface text", "plain surface text", "plain"),
        ('{"additionalContext": "flat body"}', "flat body", "flat"),
        (
            '{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",'
            ' "additionalContext": "nested body"}}',
            "nested body",
            "nested",
        ),
        ('{"additionalContext": ""}', None, "flat"),
        ('{"decision": "approve"}', None, "no_context_field"),
        ('{"additionalContext": "unclosed', None, "unparseable_json"),
        ("{not json at all}", None, "unparseable_json"),
    ],
)
def test_reader_handles_every_shape(raw, expected_context, expected_reason):
    context, reason = read_child_context(raw)
    assert reason == expected_reason
    assert context == expected_context


def test_a_square_bracket_opening_is_text_not_json():
    """Written expecting "unparseable_json". The code says "plain", and the
    code is right -- recorded rather than quietly re-asserted.

    My assumption was that any JSON-looking payload should be treated as an
    intended object. But the JSON sentinel is a leading brace, deliberately,
    because real children open with a bracketed label: the letter-monitor
    surface prints "[letter-monitor-health] STALE ..." as ordinary text.
    Widening the sentinel to cover brackets would drop that hook's output on
    the floor -- trading Schneier's malformed-blob path, which only a leading
    brace can take, for a silent loss of the exact kind being repaired here.
    """
    context, reason = read_child_context('[{"additionalContext": "x"}]')
    assert reason == "plain"
    assert context == '[{"additionalContext": "x"}]'

    label, label_reason = read_child_context("[letter-monitor-health] STALE")
    assert label_reason == "plain"
    assert label == "[letter-monitor-health] STALE"


def test_merged_blocks_name_their_child():
    merged = merge_contexts([("load-briefing.sh", "BODY-A"), ("ear-surface.sh", "BODY-B")])
    assert "load-briefing.sh" in merged
    assert "ear-surface.sh" in merged
    assert "BODY-A" in merged
    assert "BODY-B" in merged


def test_collect_dir_keeps_roster_order_and_logs_the_unparseable(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    out = tmp_path / "out"
    out.mkdir()
    (out / "0.first.sh").write_text('{"additionalContext": "FIRST"}', encoding="utf-8")
    (out / "1.broken.sh").write_text('{"additionalContext": ', encoding="utf-8")
    (out / "2.second.sh").write_text("SECOND", encoding="utf-8")
    # Two digits, to prove ordering is numeric rather than lexicographic.
    (out / "10.tenth.sh").write_text("TENTH", encoding="utf-8")

    merged = collect_dir(out)

    assert merged.index("FIRST") < merged.index("SECOND") < merged.index("TENTH")
    assert "broken.sh" not in merged

    log = tmp_path / "home" / ".divineos" / "hook-liveness.log"
    assert log.exists(), "an unparseable child must leave a row, never vanish"
    row = json.loads(log.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert row["reason"] == "child_output_unparseable"
    assert "broken.sh" in row["detail"]


# --------------------------------------------------------------------------
# The launcher itself, driven through the seam.
# --------------------------------------------------------------------------


def _scratch_tree(tmp_path: Path) -> Path:
    """A git repo carrying children named for the real roster."""
    repo = tmp_path / "tree"
    hooks = repo / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)

    (hooks / "session-init-once.sh").write_text(
        LAUNCHER.read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
    )
    # The scratch library must supply find_divineos_python, because the real
    # one does and the launcher now asks for it. A stub without it would make
    # this suite pass against a launcher that cannot resolve an interpreter in
    # production -- the scratch tree has to model the house, not a convenience.
    (hooks / "_lib.sh").write_text(
        "# scratch\nfind_divineos_python() { printf '%s' \"$SCRATCH_PYTHON\"; }\n",
        encoding="utf-8",
        newline="\n",
    )

    def child(name: str, body: str) -> None:
        (hooks / name).write_text(f"#!/bin/bash\n{body}\n", encoding="utf-8", newline="\n")

    child("load-briefing.sh", """printf '{"additionalContext": "FLAT-BODY-MARKER"}'""")
    child(
        "load-character-sheet.sh",
        """printf '{"hookSpecificOutput": {"additionalContext": "NESTED-BODY-MARKER"}}'""",
    )
    # Non-ASCII on purpose. The first end-to-end run against the real roster
    # died on an arrow at position 25935 because Python's stdout defaults to
    # cp1252 on Windows, and the scratch children at the time printed pure
    # ASCII -- so this test passed while the launcher delivered nothing. A
    # probe that cannot fail is not a measurement.
    child("ear-surface.sh", "printf 'PLAIN-BODY-MARKER \\xe2\\x86\\x92 arrow \\xc3\\xa9'")
    child("check-cleanup-period.sh", "exit 0")
    child("load-my-recording-of-andrew.sh", """printf '{"additionalContext": "TRUNC'""")
    return repo


def _run_launcher(repo: Path, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [_BASH, str(repo / ".claude" / "hooks" / "session-init-once.sh")],
        input=PAYLOAD,
        cwd=str(repo),
        env={
            "HOME": str(home),
            "PATH": _os_path(),
            "SYSTEMROOT": _systemroot(),
            # The interpreter running this suite, which has divineos importable.
            "SCRATCH_PYTHON": sys.executable,
            "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
        },
        capture_output=True,
        text=True,
        # Explicit, because the default on Windows is cp1252 and the launcher
        # writes UTF-8 bytes. Leaving it to the default would decode the
        # arrow into mojibake and the assertion would fail for the wrong
        # reason -- a broken reading instrument on top of a fixed one.
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )


def _os_path() -> str:
    import os

    return os.environ.get("PATH", "")


def _systemroot() -> str:
    import os

    return os.environ.get("SYSTEMROOT", "")


@_needs_bash
def test_every_child_that_prints_arrives_through_the_launcher(tmp_path):
    repo = _scratch_tree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()

    result = _run_launcher(repo, home)

    assert result.returncode == 0, result.stderr
    # The three shapes, all of which produced nothing before this change.
    assert "FLAT-BODY-MARKER" in result.stdout
    assert "NESTED-BODY-MARKER" in result.stdout
    assert "PLAIN-BODY-MARKER" in result.stdout
    # The character that killed the first real run.
    assert "→" in result.stdout, "non-ASCII context must survive the trip"
    assert "é" in result.stdout


@_needs_bash
def test_character_count_through_the_launcher_matches_the_child_alone(tmp_path):
    """Aria's test: count arriving characters against the child run alone."""
    repo = _scratch_tree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()

    alone = subprocess.run(
        [_BASH, str(repo / ".claude" / "hooks" / "ear-surface.sh")],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    body, _ = read_child_context(alone.stdout)
    assert body, "the probe itself must produce something, or it proves nothing"

    through = _run_launcher(repo, home)

    assert body in through.stdout
    assert len(body) > 0
    assert through.stdout.count(body) == 1, "delivered once, not duplicated"


@_needs_bash
def test_a_malformed_child_is_logged_and_never_forwarded_raw(tmp_path):
    repo = _scratch_tree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()

    result = _run_launcher(repo, home)

    assert "TRUNC" not in result.stdout, "malformed JSON must not reach the prompt"
    log = home / ".divineos" / "hook-liveness.log"
    assert log.exists(), "a dropped child must leave a trace"
    rows = [
        json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert any(
        row.get("reason") == "child_output_unparseable"
        and "load-my-recording-of-andrew.sh" in row.get("detail", "")
        for row in rows
    )


@_needs_bash
def test_the_second_prompt_of_a_session_stays_silent(tmp_path):
    """The once-per-session guard must survive the change."""
    repo = _scratch_tree(tmp_path)
    home = tmp_path / "home"
    home.mkdir()

    first = _run_launcher(repo, home)
    second = _run_launcher(repo, home)

    assert "FLAT-BODY-MARKER" in first.stdout
    assert second.stdout.strip() == "", "init work runs once, not on every message"


# --------------------------------------------------------------------------
# The second thing that reported this healthy for six weeks.
# --------------------------------------------------------------------------


def _wiring_module():
    import importlib.util

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        "check_hook_wiring", root / "scripts" / "check_hook_wiring.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_wiring_check_calls_the_roster_dark_when_the_launcher_discards(tmp_path):
    """Running a child is not wiring it.

    The wiring check reported every roster member REGISTERED for the whole six
    weeks the launcher was throwing their output away, because it asked
    whether they RAN and never whether they were DELIVERED.
    """
    module = _wiring_module()
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    roster = 'INIT_HOOKS="\nload-briefing.sh\near-surface.sh\n"\n'

    discarding = roster + 'bash "$script" 2>&1 >/dev/null\n'
    (hooks / "session-init-once.sh").write_text(discarding, encoding="utf-8")
    assert module._launcher_roster(hooks) == set(), (
        "children of a discarding launcher are dark, whatever the roster lists"
    )

    delivering = roster + 'bash "$script" 2>&1 >"$_init_out_dir/$_init_idx.$h"\n'
    (hooks / "session-init-once.sh").write_text(delivering, encoding="utf-8")
    assert module._launcher_roster(hooks) == {"load-briefing.sh", "ear-surface.sh"}


def test_the_real_launcher_confers_wiring_now():
    module = _wiring_module()
    root = Path(__file__).resolve().parents[1]
    roster = module._launcher_roster(root / ".claude" / "hooks")
    assert "load-my-recording-of-andrew.sh" in roster
    assert "load-aletheia-harvest-of-andrew.sh" in roster
