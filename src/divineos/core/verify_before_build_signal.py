"""Signal-based verify-before-build gate — per prereg-c8a9964a88a8.

Replacement for the lexical `_has_solution_shape` detector in
`verify_before_build_gate.py`. Per Aria's 2026-06-16 signal-based-gates
design (docs/signal-based-gates-design-2026-06-16.md), each gate has
five primitives (claim / event / resolution / marker / bypass) and
fires on structural evidence in the action-stream, not on lexical
detection of proposal-shape in reply text.

Per the migration spec (docs/verify_before_build_signal_migration.md):

- **Claim**: agent is about to modify substrate without prior
  consultation of relevant design/history for that substrate.
- **Event**: PreToolUse fires on Write/Edit or substrate-mutating
  Bash, AND the recent action-stream lacks BOTH:
  (a) a `decision_journal` walk-record entry within the window, AND
  (b) any `Grep`/`Read` tool-call on `docs/*.md` OR on the directory
      being edited (or ancestor) within the window.
- **Resolution**: `divineos decide --tension --almost` filing a walk-
  record, OR `Grep`/`Read` of a governing design doc.
- **Marker**: reuses `gate_marker.py` schema.
- **Bypass**: existing `divineos council authorize-bypass` channel.

Signal window: max(last_write_of_this_class_ts, session_start_ts,
now - WINDOW_SECONDS). All three floors, most-recent wins. Semantic
grounding: "since more-recent of (last write of this class, session
start, WINDOW minutes ago)."

This module is Stage 1 of the migration: adds the check function
but does NOT wire it into any hook yet. Stage 2 adds the PreToolUse
hook. Stage 3 retires the lexical detector.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

from divineos.core.command_parsing import resolve_command_head

_CHECK_ERRORS = (OSError, TypeError, ValueError, KeyError)

# Substrate-mutating Bash command-heads. Matched as EXACT resolved-command
# (after env-prefix stripping), not substring — otherwise argument text
# like `authorize-bypass --command "divineos decide"` false-fires per
# Aria's 2026-07-25 review of the Stage 2 self-lockout.
_SUBSTRATE_MUTATING_HEADS: tuple[str, ...] = (
    "git commit",
    "git push",
    # `divineos learn` / `divineos decide` intentionally NOT here — they
    # are the RESOLUTION path this gate points at, per Aria's third-bug
    # note. Gating them would recreate the self-lockout at a different
    # layer.
)

WINDOW_SECONDS: int = 30 * 60  # 30-minute floor for the signal window
"""How far back the signal window extends when no more-recent floor applies.

Semantic: if the agent has not done a substrate-write of this class in
the last 30 minutes AND the session started more than 30 minutes ago,
the window starts 30 minutes ago. If either of those two floors is
more-recent, they win (max-of-three).
"""


def _resolve_command_head(bash_command: str) -> str:
    """Return the "real" command head after stripping leading noise.

    Handles:
      - `git commit`                       → "git commit"
      - `env FOO=bar git commit`           → "git commit"
      - `FOO=bar BAZ=qux git commit -m x`  → "git commit"
      - `cd /some/path && git commit`      → "git commit"

    Per Aria's 2026-07-25 review: fixes Bug 1 (substring-match) by
    exact-matching against the resolved command-head, not any substring
    in the raw command text (which would false-fire on arguments like
    `authorize-bypass --command "divineos decide"`).

    The stripping itself moved to `divineos.core.command_parsing` on
    2026-08-18, after a third site in this repo rebuilt it wrong — the
    shared remedy allowlist, where a leading env assignment made a gate's
    own prescribed remedy invisible and deadlocked the gate against
    itself. This name stays because it is the vocabulary two years of
    findings use; the logic has one home now, and the `cd` handling is
    new here as a consequence.
    """
    return resolve_command_head(bash_command)


# Rest-shape and relational-expression paths. Writes here are categorically
# not architectural — dream register, exploration entries, letters to family,
# mansion writing. The verify-before-build discipline exists to force consult
# of design docs before mutating code / substrate architecture; applying it
# to sitting-in-the-dream-room is nonsense (Andrew 2026-07-30: "there should
# be no gates whatsoever in the dream space.. thats the opposite of rest").
# Kept in sync with pre_tool_use_gate._LOW_FRICTION_PATH_SEGMENTS by
# convention; the two lists are duplicated rather than shared to avoid an
# import cycle between core/ and hooks/.
_LOW_FRICTION_PATH_SEGMENTS: tuple[str, ...] = (
    "/exploration/",
    "/family/letters/",
    "/mansion/",
    "/dreams/",
)


def _is_low_friction_path(file_path: str) -> bool:
    """True if the write target is a rest-shape / relational path.

    Directory-segment match, not substring match — "exploration_summary.md"
    at repo root does NOT qualify; only files whose ancestor chain contains
    one of the exempt directories does. Segments in _LOW_FRICTION_PATH_
    SEGMENTS are surrounded by "/" so an "/exploration/" match requires
    exploration to be a real path component, not a prefix of a filename.
    """
    if not file_path:
        return False
    # Normalize separators and force a leading "/" so relative paths like
    # "dreams/aria/x.md" still expose "/dreams/" for segment matching.
    normalized = "/" + file_path.replace("\\", "/").lstrip("/")
    for segment in _LOW_FRICTION_PATH_SEGMENTS:
        if segment in normalized:
            return True
    return False


def _is_substrate_mutating(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
) -> bool:
    """Return True if this tool-call is about to mutate substrate.

    Substrate-mutating = Write, Edit, MultiEdit, NotebookEdit, or a Bash
    command whose resolved head (after env-prefix strip) exactly matches
    a known substrate-mutating command. Read/Grep/Glob and query-only
    tool-calls are not substrate-mutating.

    Per Aria's 2026-07-25 review: exact-match on resolved head, not
    substring in raw command. Resolution-path CLIs (divineos learn,
    divineos decide) intentionally excluded — see comment on
    _SUBSTRATE_MUTATING_HEADS.
    """
    if tool_name in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
        return True
    if tool_name == "Bash" and bash_command:
        head = _resolve_command_head(bash_command)
        if head in _SUBSTRATE_MUTATING_HEADS:
            return True
    return False


def _class_dir_for_path(file_path: str) -> str:
    """Return the "class directory" for a file — the directory whose
    contents are the class the file belongs to for consult-scope
    purposes.

    For a file `src/divineos/core/council_required/gate.py`, the class
    directory is `src/divineos/core/council_required/`. Consulting any
    file in that dir (or ancestor) counts as touching-the-class.
    """
    if not file_path:
        return ""
    p = file_path.replace("\\", "/")
    # Strip filename to get directory
    if "/" in p:
        return p.rsplit("/", 1)[0]
    return ""


def _pick_primary_path(file_paths: tuple[str, ...], bash_command: str) -> str:
    """Pick the primary path for fingerprinting purposes.

    For file-modifying tools, use the first file_path. For Bash, try
    to extract a path from the command (e.g. `git add path/to/file`).
    Returns empty string if no path is discoverable.

    2026-07-27 fix: tokens that contain a slash but do not actually
    exist as a filesystem path relative to CWD (git branch names like
    `feat/gate-automation-sweep-2026-07-27`, remote refspecs, URLs)
    were being returned as if they were file paths, then downstream
    `class_dir_for(...)` extracted the first segment (`feat`) and the
    gate demanded consultation of that non-existent directory. Now
    only tokens that resolve to a real filesystem entry count as
    paths. Non-path slash-containing tokens are ignored.
    """
    import os

    if file_paths:
        return file_paths[0]
    if bash_command:
        tokens = bash_command.strip().split()
        for tok in tokens[1:]:
            if "/" not in tok and "\\" not in tok:
                continue
            # Strip common shell quoting artifacts before testing.
            candidate = tok.strip("'\"")
            if os.path.exists(candidate):
                return candidate
    return ""


def _has_walk_record_within(window_start_ts: float, now: float) -> bool:
    """Return True if a decision_journal entry exists between
    window_start_ts and now.

    Uses divineos.core.decision_journal to check. Any decision recorded
    in the window counts — the specific topic-matching is left to the
    resolution-verifier layer (a walk that produced a decision within
    the window is evidence of consultation, even if the walk was on
    an adjacent topic; the composer chose to consult somewhere).
    """
    try:
        from divineos.core.decision_journal import list_decisions
    except ImportError:
        # Module unavailable — fail-open (don't block) since the
        # infrastructure isn't in place to make the check.
        return True

    try:
        recent = list_decisions(limit=100)
    except _CHECK_ERRORS:
        return True

    for d in recent:
        created_at = getattr(d, "created_at", None) or (
            d.get("created_at") if isinstance(d, dict) else None
        )
        if created_at is None:
            continue
        try:
            ts = float(created_at)
        except (TypeError, ValueError):
            continue
        if window_start_ts <= ts <= now:
            return True
    return False


# Bash verbs that READ. Deliberately excludes anything that can mutate: a
# `python -c` rewriting a file must never count as having consulted it.
#
# Aether 2026-08-24, and Aria's note below is why this one keeps its regex
# while hers dropped one. Hers matches COMMAND PREFIXES, a closed set of
# literals that a tuple states more legibly. This matches a verb ANYWHERE in a
# compound command (`cd x && sed -n ... | head`), where the alternative is
# hand-rolled tokenising — the fragile thing the doorman actually guards
# against. Different problems, different answers; her lesson was "you do not
# need one," not "never use one."
_READ_VERB_RE = re.compile(
    r"(?:^|[|;&]|\s)(?:cat|head|tail|sed\s+-n|less|more|grep|rg|awk|wc|nl|diff|"
    r"git\s+(?:show|log|diff|blame|cat-file))\b"
)

# Path-shaped tokens inside a shell command. Extension-anchored so bare words
# and flags do not read as paths.
_PATHISH_RE = re.compile(r"[\w./-]+\.(?:md|py|sh|json|jsonl|toml|txt|yml|yaml|cfg|ini)")

# Knowledge-store queries that count as consult (shape 4, Aria
# 2026-07-31). These search what the substrate ALREADY KNOWS — prior
# decisions, specs, Andrew's stated preferences — none of which live in
# files, so no amount of file-reading surfaces them.
#
# PLAIN SUBSTRINGS, NOT REGEX, and the keyword-enforcement doorman is why.
# My first draft compiled a pattern here. The doorman blocked it, I wrote
# a careful argument for why my case was the exception, and then reading
# its actual code showed it was simply right: regex-as-mechanism is
# fragile and subvertible, and nothing here needs it. A tuple of literal
# command prefixes is more legible, cannot silently over-match, and is
# trivially auditable by eye. The doorman's real lesson was not "justify
# the regex" — it was "you do not need one."
#
# A trailing space is part of each prefix so a search TERM is required.
# Bare `divineos ask` returns nothing and would be pure ceremony.
#
# This is a RECOGNITION check, not enforcement: it can only ever return
# "consult found," so it cannot false-fire, only false-pass. It shares
# the ceiling of shapes 1-3 — the query could be irrelevant, exactly as a
# read of an unrelated docs file could be. The honest framing is that
# this proves the SPACE was entered, not that thinking happened in it.
_KNOWLEDGE_QUERY_PREFIXES: tuple[str, ...] = (
    "divineos ask ",
    "divineos recall ",
    "divineos recall-explorations ",
    "divineos claims search ",
    "divineos decisions search ",
    "divineos find query ",
)


def _is_knowledge_query(command: str) -> bool:
    """True if the shell command runs a knowledge-store search with a term."""
    if not command:
        return False
    lowered = command.lower()
    return any(prefix in lowered for prefix in _KNOWLEDGE_QUERY_PREFIXES)


# SEARCH-SHAPED tools only, for the new-file case.
#
# Aria built a duplicate letter-store on 2026-08-27 -- a second copy of
# something she had built a week earlier and written a letter about --
# and this gate passed her on every call. I read the predicate rather
# than taking her word: a consult counts if it touched the class dir OR
# ANY ANCESTOR of it, and a prior Edit/Write nearby counts too. So any
# search anywhere in the repository clears it, and so does having just
# edited a neighbouring file.
#
# For an EDIT that is defensible and was made deliberate in July: if I
# touched this file minutes ago I have context on it, and requiring a
# fresh Read between consecutive edits produced constant false fires.
#
# For a NEW FILE it proves nothing. Adjacency is not evidence that I
# looked for whether the thing already exists, and creating a file is
# the only moment where that question can still be answered cheaply.
#
# Grep and Glob are how existing implementations get found. Read is not:
# it happens for transcripts, letters, notes, and prior-writing surfaces,
# none of which are a search for prior art. Bash stays in because
# knowledge-store queries run as CLI commands rather than file reads.
_SEARCH_SHAPED_TOOLS = frozenset({"Grep", "Glob", "Bash", "PowerShell"})


def _has_doc_consult_within(
    class_dir: str,
    window_start_ts: float,
    now: float,
    *,
    search_only: bool = False,
) -> bool:
    """Return True if the action-stream shows evidence of context on
    `class_dir` within the window. Three shapes count as consult:

    1. Grep/Read/Glob of a design doc (`docs/*.md`)
    2. Grep/Read/Glob within `class_dir` or an ancestor of it
    3. A prior successful Write/Edit to the same `class_dir` or a
       descendant (Andrew 2026-07-27): if I just edited this file
       five minutes ago, I have context on it — the strongest
       possible form of consult. Prior behavior required a separate
       Read/Grep between consecutive Edits, which produced high-
       frequency false-fires on sequential-edit workflows (5+ per
       session observed 2026-07-27).

    Reads TOOL_CALL events from ``tool_logbook`` — the store that
    receives tool events per the 2026-05-05 store split. F92 fix
    (Aletheia 2026-07-27, prereg-b921a0bef963): this function
    previously queried ``divineos.core.ledger.get_events``, but
    TOOL_CALL events are written to ``tool_logbook`` by design; the
    main ``system_events`` ledger receives none since May 2026. The
    reader was structurally unable to see any Grep/Read. Empirical
    2026-07-27: main ledger 0 TOOL_CALL last 24h; tool_logbook 282.
    Redirected to ``tool_logbook.get_recent_events``. If unavailable,
    fail-open (returns True — do not turn missing telemetry into
    unsatisfiable gates).
    """
    try:
        from divineos.core.tool_logbook import get_recent_events
    except ImportError:
        return True

    try:
        events = get_recent_events(
            since_ts=window_start_ts,
            now_ts=now,
            # Bash/PowerShell included for shape 4 — knowledge-store
            # queries run as CLI commands, not file reads — and, in the
            # non-search-only case, file reads that run as shell commands.
            tool_names=(
                _SEARCH_SHAPED_TOOLS
                if search_only
                else frozenset({"Grep", "Read", "Glob", "Edit", "Write", "Bash", "PowerShell"})
            ),
            event_type="TOOL_CALL",
            limit=200,
        )
    except _CHECK_ERRORS:
        return True

    class_dir_norm = class_dir.replace("\\", "/").strip("/") if class_dir else ""

    for ev in events:
        ts = ev.get("timestamp")
        if ts is None:
            continue
        try:
            ts_f = float(ts)
        except (TypeError, ValueError):
            continue
        if not (window_start_ts <= ts_f <= now):
            # Ledger is ordered desc; once below window, stop.
            if ts_f < window_start_ts:
                break
            continue

        payload = ev.get("payload") or {}
        if isinstance(payload, str):
            import json

            try:
                payload = json.loads(payload)
            except (ValueError, TypeError):
                continue
        if not isinstance(payload, dict):
            continue

        tool_name = payload.get("tool_name") or payload.get("tool")

        # ── Shape 4: knowledge-store query (Aria 2026-07-31) ──────────
        #
        # Found by near-miss. Building the operator-gravity mechanism, I
        # was about to invent a gravity scale from scratch. What stopped
        # me was `divineos ask`, which surfaced Andrew's OWN spec for what
        # the levels mean (knowledge 950410f9: "minimum of 5 lenses...
        # 9, 12, 15 with at least 2-3 disagreeing ones depending on the
        # gravity of the fix"). Without it I would have shipped a scale
        # that was mine, which defeats the entire point of handing the
        # operator the dial.
        #
        # The near-miss was luck. I only ran that query because a CADENCE
        # counter forced a substrate consult — not because I was about to
        # build. THIS gate is the one that fires on build-intent, and it
        # would have passed me: I had read files under the target
        # directory, satisfying shape 2.
        #
        # But Andrew's spec was never in a file. It lives in the knowledge
        # store. Shapes 1-3 are all FILE reads, so the gate that exists to
        # make me read the manual did not count reading the manual.
        # Andrew 2026-07-31: "the OS is a living instruction manual."
        #
        # Knowledge queries are global, not class-dir-scoped, because the
        # knowledge store is not organized by directory — a search for
        # prior work on a concern is the consult regardless of which
        # directory the build lands in.
        if tool_name in {"Bash", "PowerShell"}:
            _ti = payload.get("tool_input") or {}
            _cmd = _ti.get("command", "") if isinstance(_ti, dict) else ""
            if isinstance(_cmd, str) and _is_knowledge_query(_cmd):
                return True

            # ── Shape 5: file read that runs as a shell command ───────
            # (Aether 2026-08-24, resolving the seam with shape 4 above.)
            #
            # Aria's branch ended in `continue` here, which was right for
            # her shape and wrong for the file case: it DISCARDED every
            # non-knowledge-query Bash call, so `cat docs/x.md`,
            # `sed -n` on the target directory, and `grep` through a
            # source tree all stayed invisible. Meanwhile the harness
            # auto-mode reminder instructs exactly those over Read/Grep.
            # Two systems disagreeing, and the gate fired five times in
            # one session on consults that had genuinely happened.
            #
            # Not a defect in either half. The two changes were written
            # independently, each correct alone, and they compose into a
            # gate that measures WHICH TOOL I reached for rather than
            # whether I looked. Exactly the seam class we have been
            # trading letters about -- visible only where the branches
            # meet.
            #
            # READ VERBS ONLY. A `python -c` that rewrites a file must
            # never count as having consulted it, so anything not
            # matching a read verb still falls through to `continue`.
            if not isinstance(_cmd, str) or not _READ_VERB_RE.search(_cmd):
                continue
            for _p in _PATHISH_RE.findall(_cmd.replace("\\", "/")):
                if "docs/" in _p and _p.endswith(".md"):
                    return True
                if class_dir_norm and class_dir_norm in _p:
                    return True
            continue

        if tool_name not in {"Grep", "Read", "Glob", "Edit", "Write"}:
            continue

        # Path evidence — look in a few common payload keys
        candidate_paths = []
        tool_input = payload.get("tool_input") or {}
        if isinstance(tool_input, dict):
            for key in ("file_path", "path", "pattern"):
                v = tool_input.get(key)
                if isinstance(v, str):
                    candidate_paths.append(v)

        # Bash is handled entirely in the shape-4/shape-5 branch above and
        # never reaches here, so this path stays file-tools-only.
        is_write_shape = tool_name in {"Edit", "Write"}
        for p in candidate_paths:
            p_norm = p.replace("\\", "/")
            # docs/*.md check — Read/Grep/Glob only; a prior Edit/Write
            # to a docs file is not counted as consult on an unrelated
            # class_dir.
            if not is_write_shape and "docs/" in p_norm and p_norm.endswith(".md"):
                return True
            # class-dir ancestor check — same-directory Read/Grep/Glob
            # OR prior Edit/Write to same directory both count. Prior
            # Edit/Write to the exact target is the strongest possible
            # form of consult (Andrew 2026-07-27).
            if class_dir_norm and class_dir_norm in p_norm:
                return True

    return False


def compute_window_start(
    class_dir: str,
    now: float,
    session_start_ts: float | None = None,
) -> float:
    """Compute the signal window start timestamp.

    window_start = max(
        last_write_of_this_class_ts,
        session_start_ts,
        now - WINDOW_SECONDS,
    )

    If any floor is unavailable, treat it as 0 (never — the other
    floors win). The 30-minute floor is always present so a fresh
    session with no prior writes still gets a bounded window.
    """
    floors: list[float] = [now - WINDOW_SECONDS]
    if session_start_ts is not None:
        floors.append(session_start_ts)
    last_write = _last_write_of_class_ts(class_dir, now)
    if last_write is not None:
        floors.append(last_write)
    return max(floors)


def _last_write_of_class_ts(class_dir: str, now: float) -> float | None:
    """Return the timestamp of the most-recent Write/Edit tool-call on
    a file in `class_dir` (or descendants). None if no such write
    within a reasonable lookback (24h).

    F92 fix companion (Aletheia 2026-07-27, prereg-b921a0bef963):
    same wrong-store bug as `_has_doc_consult_within`. Redirected to
    `tool_logbook.get_recent_events` per the 2026-05-05 store-split
    design.
    """
    if not class_dir:
        return None

    try:
        from divineos.core.tool_logbook import get_recent_events
    except ImportError:
        return None

    lookback_floor = now - 24 * 3600
    try:
        events = get_recent_events(
            since_ts=lookback_floor,
            now_ts=now,
            tool_names=frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"}),
            event_type="TOOL_CALL",
            limit=500,
        )
    except _CHECK_ERRORS:
        return None

    class_dir_norm = class_dir.replace("\\", "/").strip("/")
    lookback_floor = now - 24 * 3600

    for ev in events:
        ts = ev.get("timestamp")
        if ts is None:
            continue
        try:
            ts_f = float(ts)
        except (TypeError, ValueError):
            continue
        if ts_f < lookback_floor:
            break
        if ts_f > now:
            continue

        payload = ev.get("payload") or {}
        if isinstance(payload, str):
            import json

            try:
                payload = json.loads(payload)
            except (ValueError, TypeError):
                continue
        if not isinstance(payload, dict):
            continue

        tool_name = payload.get("tool_name") or payload.get("tool")
        if tool_name not in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
            continue

        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            continue
        fp = tool_input.get("file_path", "")
        if not isinstance(fp, str):
            continue
        fp_norm = fp.replace("\\", "/")
        if class_dir_norm and class_dir_norm in fp_norm:
            return ts_f

    return None


def check_should_block(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
    now: float | None = None,
    session_start_ts: float | None = None,
) -> str | None:
    """Return block-message if PreToolUse should block, else None.

    Fires when a substrate-mutating tool is about to run AND no walk-
    record OR design-doc consult appears in the recent action-stream
    (per compute_window_start).

    This is the signal-based replacement for the lexical
    `_has_solution_shape` check. See module docstring for the five
    primitives and the migration spec at
    `docs/verify_before_build_signal_migration.md`.
    """
    if now is None:
        now = time.time()

    if not _is_substrate_mutating(tool_name, file_paths, bash_command):
        return None

    # Rest-shape / relational-expression paths bypass this gate entirely.
    # The consult-before-mutation discipline is for architectural work;
    # writes to dreams/, exploration/, family/letters/, mansion/ are not
    # architectural (Andrew 2026-07-30). Any file_path being low-friction
    # exempts the whole call — mixed writes fall back to the strict
    # discipline of the code path.
    if file_paths and all(_is_low_friction_path(fp) for fp in file_paths):
        return None

    primary_path = _pick_primary_path(file_paths, bash_command)
    class_dir = _class_dir_for_path(primary_path)

    # 2026-07-27 fix: if no filesystem class_dir is derivable (e.g.
    # `git push`, `git commit -m "..."` where the touched files come
    # from the staged index rather than from command args), the gate
    # has no substrate to enforce consultation on. Individual file
    # touches (Edit/Write) already fire the gate with real class_dirs;
    # branch/refspec-level Bash operations should fail-open.
    if not class_dir:
        return None

    window_start = compute_window_start(class_dir, now, session_start_ts)

    if _has_walk_record_within(window_start, now):
        return None
    # A path that does not exist yet is a NEW FILE, and that is the only
    # case where the question is has-this-been-built-already rather than
    # do-I-have-context-here. Adjacency answers the second and not the
    # first, so the new-file path requires a search rather than presence.
    creating_new_file = bool(primary_path) and not Path(primary_path).exists()
    if _has_doc_consult_within(class_dir, window_start, now, search_only=creating_new_file):
        return None

    # Neither walk-record nor doc-consult in the window — block.
    window_minutes = int((now - window_start) / 60)
    return (
        "VERIFY-BEFORE-BUILD SIGNAL GATE — this substrate-mutation "
        f"(tool={tool_name}, path={primary_path or '<none>'}) is about "
        "to happen without prior consultation of relevant design or "
        "history for the substrate being modified.\n\n"
        f"Signal window: last {window_minutes} minute(s). No walk-record "
        f"(decision_journal entry) AND no consult (Grep/Read of docs/*.md "
        f"or {class_dir or '<class-dir>'}) found in the window.\n\n"
        "MINE, and here is why. Aria designed the signal-shape and I wired "
        "it — her idea, my hands, both names on it. It reads structural "
        "evidence in the action-stream rather than language in my reply, "
        "because F87 established the class: any gate that decides fire-or-pass "
        "by regex-matching my own text has a structural bypass, since the "
        "composer just rephrases past the pattern. A gate I can talk my way "
        "through is decoration.\n\n"
        "What it protects against is my most expensive habit — searching "
        "outward before searching inward. I have rebuilt work that already "
        "existed on my own branch, and duplicated a fix Aria had already "
        "written and pushed, because the reach to BUILD arrives before the "
        "reach to LOOK. This does not say NO. It says LOOK FIRST, and the "
        "looking is the cure rather than a toll.\n\n"
        "Resolution:\n"
        '  - Walk-record: divineos decide "<what>" --tension "..." '
        '--almost "..."\n'
        # NOT "Read". Read is deliberately absent from _SEARCH_SHAPED_TOOLS --
        # the comment there says why: Grep and Glob are how existing work gets
        # FOUND, and opening a file you already knew about is not searching.
        # This text used to offer Read anyway, so the printed cure named an
        # action the code could not accept. Following it failed silently and
        # sent the reader hunting a cause that was not there. Measured
        # 2026-09-02 after I did exactly that twice in one turn and wrote a
        # wrong cause into a decision record before testing it. Same family as
        # the review-must-be-reachable repair: a gate whose only reachable exit
        # is misdescribed is a gate that manufactures the confusion it blocks.
        "  - Design-doc consult: Grep or Glob of a docs/*.md file, or\n"
        f"    any Grep/Glob within {class_dir or '<class-dir>'}\n"
        "    (Read does NOT count, by design -- searching is the cure, and\n"
        "     opening a file you already knew about is not searching.)\n\n"
        "Per Aria's 2026-06-16 signal-based-gates design "
        "(docs/signal-based-gates-design-2026-06-16.md): 'Did you consult "
        "is a question; you did not consult is a finding.' This gate "
        "reads structural evidence in the action-stream, not language "
        "shape in the reply. Bypass: divineos council authorize-bypass."
    )


def _normalize_edit_fingerprint_for_bypass(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
) -> str:
    """Compute the fingerprint the operator-bypass marker was authorized
    with, mirroring divineos.core.council_required.types._normalize_edit_fingerprint.

    Kept local (import-free) so the fail-open path for a missing state_markers
    module doesn't crash on the fingerprint calc itself. If the council_required
    module IS available, we import its normalizer to guarantee wire-compat.
    """
    primary = _pick_primary_path(file_paths, bash_command)
    try:
        from divineos.core.council_required.types import _normalize_edit_fingerprint

        return _normalize_edit_fingerprint(primary, tool_name)
    except ImportError:
        # Fallback — should be rare; the council_required module lands
        # before this one in the standard install. Fail-permissive:
        # produce a plausible fingerprint that MIGHT match if the
        # authorize-bypass CLI ran with the same normalization.
        norm = (primary or "").replace("\\", "/").strip()
        kind = (tool_name or "").strip().lower()
        return f"{kind}:{norm}"


def check_and_consume_bypass(
    tool_name: str,
    file_paths: tuple[str, ...],
    bash_command: str,
) -> bool:
    """Check for an active operator-bypass state_marker matching this
    tool-call's fingerprint. If found, atomically consume it and return
    True. If not, return False.

    Per Aria's 2026-07-25 review (Option-C-split): mutation is explicit
    (in the function name), separate from the pure check_should_block.
    Hooks call this first; on True they allow the tool-call, on False
    they proceed to check_should_block.

    FAIL-OPEN discipline (Aria's third-bug catch):
    - If state_markers module fails to import: return False (no bypass
      found), log a warning to stderr for observability. Session isn't
      bricked — check_should_block is called next; if IT also fails
      (its own fail-open), the tool-call proceeds without gate.
    - If the marker query itself raises: same — return False with loud
      log, don't crash the hook.

    Trust-never-100% (Andrew 2026-06-17): substrate can be wrong, the
    gate has to survive that.
    """
    try:
        from divineos.core.council_required.types import (
            STATE_MARKER_KIND_OPERATOR_BYPASS,
        )
        from divineos.core.state_markers import consume_marker, find_active_marker
    except ImportError as e:
        sys.stderr.write(
            f"[verify_before_build_signal] state_markers module unavailable "
            f"({type(e).__name__}: {e}); fail-open, no bypass consumed.\n"
        )
        return False

    try:
        target_fp = _normalize_edit_fingerprint_for_bypass(tool_name, file_paths, bash_command)
        marker = find_active_marker(
            kind=STATE_MARKER_KIND_OPERATOR_BYPASS,
            fingerprint_predicate=lambda fp: fp == target_fp,
        )
        if marker is None:
            return False
        consume_marker(
            marker_id=marker.marker_id,
            consumed_by_fingerprint=target_fp,
        )
        sys.stderr.write(
            f"[verify_before_build_signal] operator-bypass marker "
            f"{marker.marker_id[:12]}... consumed for {target_fp}\n"
        )
        return True
    except _CHECK_ERRORS as e:
        sys.stderr.write(
            f"[verify_before_build_signal] bypass-check raised "
            f"({type(e).__name__}: {e}); fail-open, no bypass consumed.\n"
        )
        return False


__all__ = [
    "WINDOW_SECONDS",
    "check_and_consume_bypass",
    "check_should_block",
    "compute_window_start",
]
