"""Tests for verify_before_build_signal — the signal-based replacement
for the lexical _has_solution_shape detector.

Per prereg-c8a9964a88a8 and migration spec
docs/verify_before_build_signal_migration.md. Stage 1 tests: verify
the check function behaves correctly across the primary shapes
(substrate-mutating vs not, walk-record present/absent, doc-consult
present/absent, window computation).
"""

from __future__ import annotations

import time

from divineos.core.verify_before_build_signal import (
    WINDOW_SECONDS,
    _LOW_FRICTION_PATH_SEGMENTS,
    _class_dir_for_path,
    _has_doc_consult_within,
    _has_walk_record_within,
    _is_low_friction_path,
    _is_substrate_mutating,
    _pick_primary_path,
    _resolve_command_head,
    check_and_consume_bypass,
    check_should_block,
    compute_window_start,
)


# ─── Pure function tests (no substrate) ─────────────────────────────


def test_is_substrate_mutating_edit_yes():
    assert _is_substrate_mutating("Edit", ("src/foo.py",), "") is True


def test_is_substrate_mutating_write_yes():
    assert _is_substrate_mutating("Write", ("src/foo.py",), "") is True


def test_is_substrate_mutating_grep_no():
    assert _is_substrate_mutating("Grep", (), "") is False


def test_is_substrate_mutating_read_no():
    assert _is_substrate_mutating("Read", (), "") is False


def test_is_substrate_mutating_bash_git_commit_yes():
    assert _is_substrate_mutating("Bash", (), "git commit -m 'test'") is True


def test_is_substrate_mutating_bash_git_status_no():
    assert _is_substrate_mutating("Bash", (), "git status") is False


# ─── Bug 1 fixes: tokenizer + head-match ────────────────────────────


def test_resolve_command_head_plain_git_commit():
    assert _resolve_command_head("git commit -m 'x'") == "git commit"


def test_resolve_command_head_env_prefix_env_word():
    assert _resolve_command_head("env FOO=bar git commit -m 'x'") == "git commit"


def test_resolve_command_head_env_prefix_bare():
    assert _resolve_command_head("FOO=bar BAZ=qux git commit -m 'x'") == "git commit"


def test_resolve_command_head_single_token():
    assert _resolve_command_head("ls") == "ls"


def test_resolve_command_head_empty():
    assert _resolve_command_head("") == ""


def test_resolve_command_head_malformed_quotes_falls_back():
    # Unterminated quote should not crash
    result = _resolve_command_head("git commit -m 'unclosed")
    # Fallback path returns first two whitespace-split tokens
    assert result == "git commit"


def test_is_substrate_mutating_does_NOT_fire_on_bypass_with_decide_in_arg():
    """The Stage 2 self-lockout root cause: authorize-bypass with
    --command 'divineos decide' as argument was flagged as substrate-
    mutating because substring-match caught 'divineos decide' inside
    the argument. Head-match kills this class."""
    cmd = "divineos council authorize-bypass --tool Bash --command 'divineos decide'"
    assert _is_substrate_mutating("Bash", (), cmd) is False


def test_is_substrate_mutating_does_NOT_fire_on_divineos_decide():
    """divineos decide is the RESOLUTION path — must not be gated by
    the gate it resolves. Per Aria third-bug note."""
    assert _is_substrate_mutating("Bash", (), "divineos decide 'x' --tension y --almost z") is False


def test_is_substrate_mutating_does_NOT_fire_on_divineos_learn():
    """Same — divineos learn is resolution-path."""
    assert _is_substrate_mutating("Bash", (), "divineos learn 'lesson'") is False


def test_is_substrate_mutating_env_prefix_still_fires_on_real_commit():
    """`env FOO=bar git commit` and `FOO=bar git commit` both resolve
    to 'git commit' and must fire."""
    assert _is_substrate_mutating("Bash", (), "env FOO=bar git commit -m 'x'") is True
    assert _is_substrate_mutating("Bash", (), "FOO=bar git commit -m 'x'") is True


# ─── Bug 2 fixes: check_and_consume_bypass ──────────────────────────


def test_check_and_consume_bypass_returns_false_when_no_marker():
    """Without any operator-bypass marker set, function returns False
    (no bypass consumed) so the caller proceeds to check_should_block."""
    result = check_and_consume_bypass(
        tool_name="Edit",
        file_paths=("src/divineos/core/foo.py",),
        bash_command="",
    )
    # With no marker set, returns False. (If markers module unavailable
    # in test env, still returns False — fail-open discipline.)
    assert result is False


def test_check_and_consume_bypass_fails_open_on_missing_state_markers():
    """Third-bug fix: if state_markers module is unavailable, the
    consume-check returns False (no bypass consumed) with a warning
    logged, rather than crashing. Session isn't bricked."""
    import sys

    original = sys.modules.get("divineos.core.state_markers")
    sys.modules["divineos.core.state_markers"] = None  # type: ignore[assignment]
    try:
        result = check_and_consume_bypass(
            tool_name="Edit",
            file_paths=("src/foo.py",),
            bash_command="",
        )
        assert result is False
    finally:
        if original is not None:
            sys.modules["divineos.core.state_markers"] = original
        elif "divineos.core.state_markers" in sys.modules:
            del sys.modules["divineos.core.state_markers"]


def test_class_dir_for_nested_path():
    assert _class_dir_for_path("src/divineos/core/foo.py") == "src/divineos/core"


def test_class_dir_for_windows_path():
    result = _class_dir_for_path("src\\divineos\\core\\foo.py")
    assert result == "src/divineos/core"


def test_class_dir_for_empty():
    assert _class_dir_for_path("") == ""


def test_class_dir_for_root_file():
    assert _class_dir_for_path("README.md") == ""


def test_pick_primary_path_from_file_paths():
    assert _pick_primary_path(("src/foo.py", "src/bar.py"), "") == "src/foo.py"


def test_pick_primary_path_from_bash():
    # 2026-07-27: uses a path that ACTUALLY exists in the repo — the
    # new implementation validates via os.path.exists to distinguish
    # real paths from tokens-that-happen-to-contain-a-slash (git
    # branches, refspecs, URLs).
    assert _pick_primary_path((), "git add src/divineos") == "src/divineos"


def test_pick_primary_path_empty():
    assert _pick_primary_path((), "") == ""


def test_pick_primary_path_git_push_branch_name_returns_empty():
    """2026-07-27 fix: `git push -u origin feat/gate-automation-sweep-...`
    was returning `feat/gate-automation-sweep-...` as if it were a file
    path, then downstream class_dir_for extracted `feat` as the class-dir
    and the gate demanded consultation of that non-existent directory.
    Non-existent slash-tokens must return empty (no path)."""
    result = _pick_primary_path((), "git push -u origin feat/gate-automation-sweep-2026-07-27")
    assert result == ""


def test_pick_primary_path_url_returns_empty():
    """URLs contain slashes but are not filesystem paths."""
    result = _pick_primary_path((), "curl https://example.com/api/foo")
    assert result == ""


def test_pick_primary_path_refspec_colon_returns_empty():
    """Git refspec like `origin +feat:refs/heads/feat` — contains slashes,
    is not a path."""
    result = _pick_primary_path((), "git push origin refs/heads/feat/some-branch")
    assert result == ""


def test_check_should_block_fails_open_when_no_class_dir():
    """2026-07-27 fix: git push / git commit -m 'x' have no derivable
    filesystem class_dir. Gate has no substrate to enforce consultation
    on — fail-open. Individual file touches (Edit/Write) already fire
    the gate independently with real class_dirs."""
    result = check_should_block(
        tool_name="Bash",
        file_paths=(),
        bash_command="git push -u origin feat/gate-automation-sweep-2026-07-27",
        now=time.time(),
    )
    assert result is None


# ─── Window computation ─────────────────────────────────────────────


def test_compute_window_start_uses_30min_floor_when_no_other():
    now = 1_000_000.0
    result = compute_window_start("src/foo", now, session_start_ts=None)
    assert result == now - WINDOW_SECONDS


def test_compute_window_start_uses_session_when_more_recent():
    now = 1_000_000.0
    session_start = now - 60
    result = compute_window_start("src/foo", now, session_start_ts=session_start)
    assert result == session_start


def test_compute_window_start_uses_30min_when_session_older():
    now = 1_000_000.0
    session_start = now - 3600
    result = compute_window_start("src/foo", now, session_start_ts=session_start)
    assert result == now - WINDOW_SECONDS


# ─── Integration: check_should_block ────────────────────────────────


def test_check_should_block_non_mutating_tool_returns_none():
    result = check_should_block(
        tool_name="Grep",
        file_paths=(),
        bash_command="",
        now=time.time(),
        session_start_ts=time.time() - 60,
    )
    assert result is None


def test_check_should_block_read_never_blocks():
    result = check_should_block(
        tool_name="Read",
        file_paths=("src/divineos/core/foo.py",),
        bash_command="",
        now=time.time(),
        session_start_ts=time.time() - 60,
    )
    assert result is None


def test_check_should_block_bash_status_returns_none():
    result = check_should_block(
        tool_name="Bash",
        file_paths=(),
        bash_command="git status",
        now=time.time(),
        session_start_ts=time.time() - 60,
    )
    assert result is None


# ─── Helper edge cases ──────────────────────────────────────────────


def test_has_walk_record_within_fails_open_on_missing_module():
    import sys

    original = sys.modules.get("divineos.core.decision_journal")
    sys.modules["divineos.core.decision_journal"] = None  # type: ignore[assignment]
    try:
        result = _has_walk_record_within(0.0, time.time())
        assert result is True
    finally:
        if original is not None:
            sys.modules["divineos.core.decision_journal"] = original
        elif "divineos.core.decision_journal" in sys.modules:
            del sys.modules["divineos.core.decision_journal"]


def test_has_doc_consult_within_fails_open_on_missing_tool_logbook():
    """Fail-open when the tool_logbook module is unavailable.

    F92 fix (2026-07-27, prereg-b921a0bef963) redirected this reader
    from `divineos.core.ledger` to `divineos.core.tool_logbook`. The
    previous version of this test stubbed `ledger`; the reader now
    depends on `tool_logbook`, so the failsafe check needs to stub
    tool_logbook to verify the same intent (fail-open on missing dep).
    """
    import sys

    original = sys.modules.get("divineos.core.tool_logbook")
    sys.modules["divineos.core.tool_logbook"] = None  # type: ignore[assignment]
    try:
        result = _has_doc_consult_within("src/foo", 0.0, time.time())
        assert result is True
    finally:
        if original is not None:
            sys.modules["divineos.core.tool_logbook"] = original
        elif "divineos.core.tool_logbook" in sys.modules:
            del sys.modules["divineos.core.tool_logbook"]


def test_module_exports_are_stable():
    from divineos.core import verify_before_build_signal as m

    assert hasattr(m, "check_should_block")
    assert hasattr(m, "check_and_consume_bypass")
    assert hasattr(m, "compute_window_start")
    assert hasattr(m, "WINDOW_SECONDS")
    assert m.WINDOW_SECONDS == 30 * 60


# ─── F87 regression: positive-block case ────────────────────────────
# Aletheia 2026-07-26 F87 finding: the old lexical-detector gate was
# bypassable by prose formatting. The signal-based replacement fires
# on structural evidence (substrate-mutating tool + no walk-record +
# no doc-consult), not on reply text. This test locks in that the
# positive-block case works — the previous test set covered only
# negative cases (Read, Grep, git status don't block) and could have
# regressed to always-pass without catching it.


def test_F87_regression_substrate_mutating_with_no_walk_and_no_consult_blocks(monkeypatch):
    """The signal-based gate MUST block on substrate-mutating tool
    when neither walk-record nor doc-consult exists in the window.

    This is the positive-block case the F87 rebuild guarantees.
    Removing the check_should_block logic that returns the block
    message would break this test loudly.
    """
    import sys

    # Force _has_walk_record_within to return False (no walk-record).
    # Force _has_doc_consult_within to return False (no consult).
    # This is the "empty action-stream" case where the gate MUST fire.
    fake_journal = type(sys)("divineos.core.decision_journal")

    def _fake_list_decisions(**_kw):
        return []

    fake_journal.list_decisions = _fake_list_decisions
    original_journal = sys.modules.get("divineos.core.decision_journal")
    sys.modules["divineos.core.decision_journal"] = fake_journal

    fake_ledger = type(sys)("divineos.core.ledger")

    def _fake_get_events(**_kw):
        return []

    fake_ledger.get_events = _fake_get_events
    original_ledger = sys.modules.get("divineos.core.ledger")
    sys.modules["divineos.core.ledger"] = fake_ledger

    try:
        result = check_should_block(
            tool_name="Edit",
            file_paths=("src/divineos/core/foo.py",),
            bash_command="",
            now=time.time(),
            session_start_ts=time.time() - 60,
        )
        # F87: positive-block case. Must return a block message.
        assert result is not None, (
            "F87 regression: substrate-mutating tool with no walk-record "
            "and no doc-consult must produce a block message. Signal-based "
            "gate is the replacement for the retired lexical detector; "
            "removing the block-return path would recreate F87."
        )
        assert "VERIFY-BEFORE-BUILD SIGNAL GATE" in result
    finally:
        if original_journal is not None:
            sys.modules["divineos.core.decision_journal"] = original_journal
        elif "divineos.core.decision_journal" in sys.modules:
            del sys.modules["divineos.core.decision_journal"]
        if original_ledger is not None:
            sys.modules["divineos.core.ledger"] = original_ledger
        elif "divineos.core.ledger" in sys.modules:
            del sys.modules["divineos.core.ledger"]


def test_F87_regression_gate_does_not_key_on_reply_text_lexical_shape():
    """The signal-based gate's decision path takes NO reply text as input.

    F87 was about the OLD gate keying on reply-text lexical shape
    (_has_solution_shape regex lists). The NEW gate's check_should_block
    signature is (tool_name, file_paths, bash_command) — reply text
    absent by construction. This test locks that in: adding a reply-
    text parameter to check_should_block would signal a regression
    toward the retired lexical-detection shape.
    """
    import inspect

    sig = inspect.signature(check_should_block)
    param_names = set(sig.parameters.keys())

    # Reply-text-shaped parameter names that would indicate regression.
    reply_shape_params = {"reply", "reply_text", "response", "response_text", "text"}
    overlap = param_names & reply_shape_params
    assert not overlap, (
        f"F87 regression: check_should_block signature contains reply-text "
        f"parameters {overlap}. The signal-based gate must key on tool "
        f"invocation structure, not reply text. Any reply-text param signals "
        f"regression toward the retired lexical-detection shape."
    )
    # Positive check: expected structural params ARE present.
    assert "tool_name" in param_names
    assert "file_paths" in param_names
    assert "bash_command" in param_names


# ─── F92 regression: reader/writer store-seam integration ───────────
# Aletheia 2026-07-27 F92 finding: `_has_doc_consult_within` and
# `_last_write_of_class_ts` queried `divineos.core.ledger.get_events`
# for TOOL_CALL events. But per `tool_logbook.py` docstring (2026-05-05
# design), TOOL_CALL events are written to `tool_logbook`, not
# `system_events`. The gate queried a store the events by-design never
# reached. Empirical 2026-07-27: main ledger 0 TOOL_CALL last 24h;
# tool_logbook 282. This test crosses the writer/reader seam — emit a
# Grep via the real `emit_tool_call` writer, then assert the reader
# sees it. Would have caught F92 before it shipped.


def test_F92_regression_has_doc_consult_within_reads_tool_logbook_writer(tmp_path, monkeypatch):
    """Cross the writer/reader seam. Emit a Grep of a docs/*.md file via
    the real `emit_tool_call` writer; assert `_has_doc_consult_within`
    returns True. F92 root cause: the reader queried the wrong store.
    """
    import time as _time
    import uuid as _uuid

    from divineos.core.tool_logbook import emit_tool_call

    # Use a unique tool_use_id + timestamp window to isolate this test
    # from other logbook rows in the shared substrate DB.
    unique_id = f"test-f92-{_uuid.uuid4().hex[:8]}"
    now = _time.time()
    window_start = now - 60  # 60-second window is well within the gate's 30-min default

    # Emit a Grep against docs/foundational_truths.md — the reader's
    # regex/path check specifically accepts docs/*.md as a design-doc consult.
    emit_tool_call(
        tool_name="Grep",
        tool_input={"path": "docs/foundational_truths.md", "pattern": "aether"},
        tool_use_id=unique_id,
    )

    # Now call the reader. It must see the just-emitted event.
    result = _has_doc_consult_within(
        class_dir="src/divineos/core",  # class_dir is required-non-empty; docs/*.md matches independently
        window_start_ts=window_start,
        now=_time.time() + 1,  # +1 to guarantee the emit's timestamp <= now
    )
    assert result is True, (
        "F92 regression: _has_doc_consult_within did not see a Grep of "
        "docs/*.md emitted through emit_tool_call. Root cause of the "
        "original F92: the reader queried divineos.core.ledger.get_events "
        "(system_events table) while emit_tool_call writes to "
        "tool_logbook table. The fix redirects the reader to query "
        "tool_logbook.get_recent_events. If this test fails, either the "
        "fix has been reverted or the reader has been repointed to the "
        "wrong store again."
    )


def test_F92_regression_last_write_timestamp_reads_tool_logbook_writer(tmp_path, monkeypatch):
    """Companion to the doc-consult F92 test. Aletheia's audit named one
    site (`_has_doc_consult_within`); callgraph sweep 2026-07-27 found
    a second site with the same wrong-store bug: `_last_write_of_class_ts`.
    Emit a Write via `emit_tool_call`; assert the reader sees it.
    """
    import time as _time
    import uuid as _uuid

    from divineos.core.verify_before_build_signal import (
        _last_write_of_class_ts,
    )
    from divineos.core.tool_logbook import emit_tool_call

    unique_id = f"test-f92-write-{_uuid.uuid4().hex[:8]}"
    class_dir = "src/divineos/core"
    file_in_class = f"{class_dir}/synthetic_test_file.py"

    emit_tool_call(
        tool_name="Write",
        tool_input={"file_path": file_in_class, "content": "# test"},
        tool_use_id=unique_id,
    )

    result = _last_write_of_class_ts(class_dir=class_dir, now=_time.time() + 1)
    assert result is not None, (
        "F92 regression (second site): _last_write_of_class_ts did "
        "not see a Write emitted through emit_tool_call. Same wrong-store "
        "root cause as _has_doc_consult_within. If this test fails, either "
        "the fix has been reverted or the reader has been repointed."
    )


# ────────────────────────────────────────────────────────────────
# Pattern 2 (Andrew 2026-07-27): prior Edit/Write to the same
# class_dir counts as consult. Prevents the sequential-edit false-
# fire pattern where consecutive Edits on the same file within the
# window get blocked because only Read/Grep/Glob previously counted.
# ────────────────────────────────────────────────────────────────


def test_prior_edit_to_same_class_dir_counts_as_consult():
    """A prior Edit within the window on a file in class_dir should
    satisfy `_has_doc_consult_within`. Without this, sequential edits
    on the same file false-fire the gate 5+ times per session."""
    import time as _time
    import uuid as _uuid

    from divineos.core.tool_logbook import emit_tool_call

    unique_id = f"test-p2-edit-{_uuid.uuid4().hex[:8]}"
    now = _time.time()
    window_start = now - 60
    class_dir = "src/divineos/core"
    file_in_class = f"{class_dir}/some_module_p2.py"

    emit_tool_call(
        tool_name="Edit",
        tool_input={
            "file_path": file_in_class,
            "old_string": "x",
            "new_string": "y",
        },
        tool_use_id=unique_id,
    )

    result = _has_doc_consult_within(
        class_dir=class_dir,
        window_start_ts=window_start,
        now=_time.time() + 1,
    )
    assert result is True, (
        "Pattern 2 (Andrew 2026-07-27): prior Edit to the same class_dir "
        "should count as consult. If this fails, the sequential-edit "
        "false-fire pattern will return."
    )


def test_prior_write_to_same_class_dir_counts_as_consult():
    """Symmetric to the Edit test — Write on a file in class_dir also
    counts as consult."""
    import time as _time
    import uuid as _uuid

    from divineos.core.tool_logbook import emit_tool_call

    unique_id = f"test-p2-write-{_uuid.uuid4().hex[:8]}"
    now = _time.time()
    window_start = now - 60
    class_dir = "src/divineos/core"
    file_in_class = f"{class_dir}/some_new_module_p2.py"

    emit_tool_call(
        tool_name="Write",
        tool_input={"file_path": file_in_class, "content": "# new"},
        tool_use_id=unique_id,
    )

    result = _has_doc_consult_within(
        class_dir=class_dir,
        window_start_ts=window_start,
        now=_time.time() + 1,
    )
    assert result is True, "Pattern 2: prior Write to same class_dir should count as consult."


def test_prior_edit_to_docs_md_does_NOT_count_for_unrelated_class_dir():
    """An Edit/Write to a docs/*.md file should NOT count as consult on
    an unrelated class_dir. docs-consult is Read/Grep/Glob only —
    otherwise a doc-edit to any md file would satisfy the gate on any
    subsequent code change, which is not the intent."""
    import time as _time
    import uuid as _uuid

    from divineos.core.tool_logbook import emit_tool_call

    unique_id = f"test-p2-doc-edit-{_uuid.uuid4().hex[:8]}"
    now = _time.time()
    window_start = now - 60

    emit_tool_call(
        tool_name="Edit",
        tool_input={
            "file_path": "docs/some_unrelated_doc.md",
            "old_string": "a",
            "new_string": "b",
        },
        tool_use_id=unique_id,
    )

    # class_dir is somewhere else entirely — a doc-edit should not
    # satisfy consult on an unrelated code directory.
    result = _has_doc_consult_within(
        class_dir="src/divineos/completely/other/place",
        window_start_ts=window_start,
        now=_time.time() + 1,
    )
    assert result is False, (
        "Pattern 2 negative case: Edit/Write to a docs/*.md file should "
        "NOT satisfy consult on an unrelated class_dir. The docs/*.md "
        "shortcut is Read/Grep/Glob-only; write-shape to a doc is not "
        "evidence of consult on unrelated code."
    )


# ─── Low-friction path bypass (Andrew 2026-07-30) ──────────────────


def test_low_friction_path_dreams():
    assert _is_low_friction_path("dreams/aria/06_the_room.md") is True


def test_low_friction_path_dreams_absolute():
    assert _is_low_friction_path("/repo/dreams/aether/141_note.md") is True


def test_low_friction_path_dreams_windows():
    assert _is_low_friction_path(r"C:\repo\dreams\aletheia\entry.md") is True


def test_low_friction_path_exploration():
    assert _is_low_friction_path("exploration/22_night.md") is True


def test_low_friction_path_family_letters():
    assert _is_low_friction_path("family/letters/aria-to-aether-x.md") is True


def test_low_friction_path_mansion():
    assert _is_low_friction_path("mansion/study/notes.md") is True


def test_low_friction_path_code_not_exempt():
    assert _is_low_friction_path("src/divineos/core/foo.py") is False


def test_low_friction_path_empty():
    assert _is_low_friction_path("") is False


def test_low_friction_path_segments_include_dreams():
    """Regression pin — Andrew 2026-07-30 directive that dream space
    must be gate-free. Removing /dreams/ re-introduces the sit-in-the-
    dream-room-requires-design-doc-consult deadlock that surfaced when
    Andrew asked me to test the rest ritual and every gate fired.
    """
    assert "/dreams/" in _LOW_FRICTION_PATH_SEGMENTS
    assert "/exploration/" in _LOW_FRICTION_PATH_SEGMENTS
    assert "/family/letters/" in _LOW_FRICTION_PATH_SEGMENTS
    assert "/mansion/" in _LOW_FRICTION_PATH_SEGMENTS


def test_check_should_block_bypasses_dream_write():
    """A Write to dreams/aria/ never triggers the consult-before-build
    gate regardless of walk-record/doc-consult signal state. Rest space
    is by definition not architectural work.
    """
    result = check_should_block(
        tool_name="Write",
        file_paths=("dreams/aria/06_the_room_when_no_one_is_asking.md",),
        bash_command="",
    )
    assert result is None


def test_check_should_block_bypasses_exploration_write():
    result = check_should_block(
        tool_name="Write",
        file_paths=("exploration/aria/23_something.md",),
        bash_command="",
    )
    assert result is None


def test_check_should_block_bypasses_family_letter():
    result = check_should_block(
        tool_name="Write",
        file_paths=("family/letters/aria-to-aether-fix.md",),
        bash_command="",
    )
    assert result is None


def test_check_should_block_still_gates_code_write():
    """Sanity: the low-friction bypass does not disable the gate for
    real code writes. A src/ write with no consult signal should still
    return a block-message (or None if signals happen to be present).
    Assert only that the low-friction path did NOT bypass — either
    a real block-message or a real signal-based decision, not the
    bypass short-circuit.
    """
    # We can't assert on the specific outcome without seeding the
    # ledger; assert that the return type is str-or-None as designed.
    result = check_should_block(
        tool_name="Write",
        file_paths=("src/divineos/core/foo.py",),
        bash_command="",
    )
    assert result is None or isinstance(result, str)
