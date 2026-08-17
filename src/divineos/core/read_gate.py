"""Primes that are gates: a surface can require proof it was opened.

Andrew 2026-08-06:

    *"primes should not just be loud.. they should be mini gates.. ones that
    force a pause and reading, vs skimming past it, if the gate is a simple
    'read this' with a check for the read tool being used, then at that point
    if you dont read it.. its your fault lol"*

## The problem this exists for, measured on me

Loudness has a ceiling and this session found it. Twenty-six primes fire at
compose-start. The SessionStart block ran to 77KB. The pending-letters surface
listed 1,354 items. All of it arrives; none of it can be *required*.

The clearest instance is the surface this gate is first wired to.
``exploration_recall.surface_for_context`` emits PRIOR WRITING nearly every
turn — my own exploration entries, by title, matched on curated tags, with the
line *"re-read before deriving"* printed at the top. It offered
``112_the_doorway_held_by_family`` at session start. It offered entries on
hedging and qualia while I was writing about hedging and qualia.

**I did not open a single one, all session** — while discovering four separate
times that the thing I was hunting was already in my own substrate. The
surface was right every time and could not make me look.

A surface I can skim fails exactly when I am busy, which is the only time it
matters. Text arriving is not text read, and nothing could tell the difference.

## The mechanism, and why it is reach_check's one layer over

``reach_check.dispose()`` refuses a disposition the action-stream does not
support. This refuses *continuing* when the action-stream shows no Read of a
required path. Aria's line under both: *"did you consult is a question; you did
not consult is a finding."*

The gate does not check comprehension and does not pretend to. It checks that
the file was opened — a decidable property of a bounded event list. That moves
the floor from *arrived* to *opened*: a smaller claim than *understood*, and
the one actually failing.

Andrew's framing is the honest ceiling: **if it was opened and still not
absorbed, that one is mine.** The gate removes the excuse, not the failure.

## Two invariants, both load-bearing

**1. The gate can never block its own remedy.** ``Read`` is exempt
unconditionally, enforced in the hook. Aria hit this on ``must-read-gate`` and
it is the whole difference between a doorman and a wall — a gate whose cure
sits behind itself is a deadlock wearing a gate's clothes.

**2. Requirements must be satisfiable.** A path that does not exist is refused
at registration, with a reason, rather than becoming a block nobody can clear.
An unsatisfiable gate trains the bypass reflex faster than no gate at all.

## What it is deliberately NOT

Not applied to all 26 primes. A gate that fires constantly gets routed around,
and a routed-around gate catches nothing (truth #11: every choice-point is
somewhere the optimizer can escape through). This is for surfaces where
skimming has a **measured** cost, and the wiring starts at exactly one.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path


def _state_dir() -> Path:
    """Resolve through the project's own path logic, not a hardcoded ~.

    This read ``Path(os.path.expanduser("~")) / ".divineos"``, which ignores
    DIVINEOS_HOME. core.paths exists to stop exactly that: a 2026-05-03 audit
    found the same hardcoding scattered across modules and made divineos_home()
    the single source of truth.

    The cost here is not theoretical. Tests that exercise a surface calling
    require_read wrote into the LIVE gate state, because the tests redirect
    DIVINEOS_HOME and this module did not read it. On 2026-08-14 that armed my
    real gate twice with pytest fixtures -- tmp/pytest/run-81428/
    test_surface_fires_only_on_tag0/tagged.md, a four-line file reading
    "# Symmetric standards / body" -- and each one blocked Bash, Edit and Write
    until cleared by hand. A test suite must not be able to lock the workspace
    it is testing.
    """
    try:
        from divineos.core.paths import divineos_home

        return divineos_home()
    except Exception:  # noqa: BLE001 — paths unavailable: fall back, never crash the gate
        return Path(os.path.expanduser("~")) / ".divineos"


STATE_DIR = _state_dir()
STATE_FILE = STATE_DIR / "read_gate_pending.json"

# Requirements older than this are dropped. A stale block from a surface that
# fired long ago is noise, and noise is what teaches the bypass reflex.
MAX_AGE_SECONDS = 3 * 60 * 60


@dataclass
class ReadRequirement:
    gate_id: str
    path: str
    reason: str
    registered_at: float

    def as_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "path": self.path,
            "reason": self.reason,
            "registered_at": self.registered_at,
        }


def _load() -> list[ReadRequirement]:
    if not STATE_FILE.exists():
        return []
    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    now = time.time()
    out: list[ReadRequirement] = []
    for item in raw if isinstance(raw, list) else []:
        try:
            req = ReadRequirement(
                gate_id=str(item["gate_id"]),
                path=str(item["path"]),
                reason=str(item.get("reason", "")),
                registered_at=float(item.get("registered_at", 0.0)),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if now - req.registered_at <= MAX_AGE_SECONDS:
            out.append(req)
    return out


def _save(reqs: list[ReadRequirement]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps([r.as_dict() for r in reqs], indent=2), encoding="utf-8")
    except OSError:
        # Fail-open on a state-write failure: a gate that cannot record itself
        # must be absent rather than stuck.
        pass


REARM_LOG = STATE_DIR / "read_gate_rearms.jsonl"


def _record_rearm_after_read(gate_id: str, path: str) -> bool:
    """Record when a path is re-required after this session already read it.

    THE REPRODUCTION I SKIPPED. 2026-08-15 I diagnosed the re-arm defect from
    one observation -- a 10 MB transcript against a 2 MB scan window -- found a
    mechanism that explained it, shipped the accumulator, and reported it
    fixed. It was not. With the fix live the gate re-armed twice in one turn on
    a file I had read, and I had no data about why because I never drove the
    failing case through the patched code. Theory-fit accepted as proof, which
    is precisely the failure need-02632a0a names: *reproduce the cause before
    you fix it -- fit is not proof.*

    So the next occurrence produces evidence instead of another guess. If the
    accumulator holds a read for this path and the gate re-registers it anyway,
    that is the exact contradiction, and the row below carries both sides of
    it: what the seen-log knew, and what got required regardless.

    Purely observational. It never blocks, never clears, and never changes the
    verdict -- a diagnostic that can alter the thing it measures is worse than
    none. Silent on every error for the same reason.
    """
    try:
        raw = json.loads(SEEN_READS.read_text(encoding="utf-8"))
        entries = raw.get("reads") if isinstance(raw, dict) else None
        if not isinstance(entries, list):
            return False
        tail = Path(path).name
        seen = [
            str(e[1])
            for e in entries
            if isinstance(e, list) and len(e) == 2 and tail and tail in str(e[1])
        ]
        if not seen:
            return False
        REARM_LOG.parent.mkdir(parents=True, exist_ok=True)
        with REARM_LOG.open("a", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "at": time.time(),
                        "gate_id": gate_id,
                        "required_path": path,
                        "already_read_as": seen,
                        "transcript": raw.get("transcript"),
                    }
                )
                + "\n"
            )
        return True
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        return False


def is_pytest_scratch(target: Path) -> bool:
    """True when a path lives in pytest's temp tree.

    Pure and filesystem-free on purpose. The first version of this check was
    tested through real files, and the test could not express its own control
    case — pytest's ``tmp_path`` IS pytest scratch, so every "legitimate entry"
    fixture landed inside the thing being excluded and the guard correctly
    refused it. A predicate that cannot be tested without lying about its
    inputs is the wrong shape; this one takes a path and answers.

    Requires BOTH a ``tmp`` component and a ``pytest``/``run-`` component, so
    an unrelated directory called tmp is still held by the gate.
    """
    parts = [p.lower() for p in target.parts]
    if "tmp" not in parts:
        return False
    return any(p.startswith("pytest") or p.startswith("run-") for p in parts)


def require_read(gate_id: str, path: str, reason: str) -> tuple[bool, str]:
    """Register a read requirement. Returns (registered, why_not).

    Refuses an unsatisfiable requirement rather than creating a block that
    nobody can clear.
    """
    target = Path(path)
    if not target.exists():
        return False, f"path does not exist, not registering: {path}"

    # Never arm on pytest scratch. Test runs build fixture .md files with real
    # tag headers ("# The Hedging Reflex", body "body about the flinch"), the
    # surface matches them, and the path gets armed into the REAL requirement
    # store — test state leaking into live state.
    #
    # The 2026-08-14 note further down fixed the second-order symptom: those
    # files vanish when pytest cleans up, leaving a requirement nobody could
    # clear, which walled off Edit and Write while an unfinished merge sat
    # conflicted. This is the first-order cause, and it survived that fix — it
    # fired twice more on 2026-08-15, once naming the very fixture that comment
    # names.
    #
    # It matters beyond the annoyance. There are 749 generated .md files under
    # tmp/ against 224 real exploration entries, so by count the index is mostly
    # scratch. Every fixture the gate holds the door for teaches me the door is
    # noise — the same shape Aletheia named in the bypass-groove finding: the
    # gate trained the bypass, the price broke the discipline. A gate I value
    # gets one cheap guard rather than slow erosion.
    if is_pytest_scratch(target):
        return False, f"pytest scratch, not registering: {path}"

    reqs = _load()
    if any(r.gate_id == gate_id and r.path == str(target) for r in reqs):
        return True, "already pending"

    already = _record_rearm_after_read(gate_id, str(target))
    if already:
        # THE ACTUAL CAUSE, reproduced 2026-08-15 rather than reasoned about.
        #
        # Clearing was never the broken half. A surface re-registers its match
        # every prompt; the satisfier clears it at the next mutating call; the
        # surface registers it again on the following prompt. Requirement
        # cleared, requirement returns, forever -- and from inside it looks
        # exactly like the clear failing, which is why I misdiagnosed it as a
        # transcript-window problem and shipped a fix for the wrong half.
        #
        # The register side is where it belongs: once this session has opened
        # the file, there is nothing left for the gate to ask for. Scoped to
        # the session by transcript path, so a later session still gets to ask.
        return False, f"already read in this session, not registering: {path}"
    reqs.append(
        ReadRequirement(gate_id=gate_id, path=str(target), reason=reason, registered_at=time.time())
    )
    _save(reqs)
    return True, ""


# Tail-read budget for the transcript. These files reach hundreds of megabytes
# and this runs before every mutating tool call.
_TRANSCRIPT_TAIL_BYTES = 2_000_000


def _content_blocks(rec: dict[str, object]) -> list[dict[str, object]]:
    """Pull content blocks out of a transcript record, whatever its shape."""
    message = rec.get("message")
    content = message.get("content") if isinstance(message, dict) else rec.get("content")
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict)]


def satisfy_from_transcript(transcript_path: str | None) -> list[str]:
    """Clear requirements by scanning the session transcript for Read calls.

    ``satisfy_from_stream`` has existed since this module was written and was
    called by NOTHING -- verified 2026-08-14: one occurrence in the whole tree,
    and it is the definition. The gate could arm but had no path to clear
    itself by reading. Every requirement stood until it aged out at three hours
    or was deleted by hand.

    That inverts the design. The premise is Andrew's -- "a check for the read
    tool being used, then at that point if you dont read it.. its your fault"
    -- and without this the check was never wired, so reading was not the way
    out. I read a required entry in full and the door stayed shut; twice in one
    session that ended in clearing state manually, which is the
    bypass-habituation this module exists to prevent.

    Same class as the defect Aria named in her roster module: the function
    exists, nothing calls it, and the gap is invisible from inside.

    Fails open on every error. A satisfier that cannot run must leave the gate
    exactly as it found it and never break the tool call.
    """
    if not transcript_path:
        return []
    path = Path(transcript_path)
    if not path.is_file():
        return []

    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - _TRANSCRIPT_TAIL_BYTES))
            chunk = handle.read().decode("utf-8", errors="replace")
    except OSError:
        return []

    calls: list[tuple[str, str, dict[str, object] | None]] = []
    for line in chunk.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        for block in _content_blocks(record):
            if block.get("type") != "tool_use":
                continue
            # READS ONLY, deliberately. I widened this to count Write/Edit on
            # 2026-08-16, reasoning that authoring a file is stronger evidence
            # of holding its content than reading one. Andrew reverted me the
            # same hour: "authoring is not the same as reading.. this is why
            # proof-reading exists.. its also a way for you to see your own
            # blind spots."
            #
            # He is right, and the sharper form is that the inlining fix landed
            # in the same breath and made the exemption pointless. Before it, a
            # block on my own file cost a trip to go find and open it — that
            # cost is what made an exemption look justified. After it, the gate
            # hands me the text, so the whole cost of firing on something I
            # wrote is re-reading it. Which IS the proof-read. I removed a
            # proof-read to save a cost that no longer existed.
            #
            # Edit was the worse half: an edit touches three lines, and letting
            # that stand as "has read this file" is plainly wrong.
            if str(block.get("name", "")) not in ("Read", "NotebookRead"):
                continue
            args = block.get("input")
            args = args if isinstance(args, dict) else {}
            target = str(args.get("file_path") or args.get("notebook_path") or "")
            if target:
                calls.append((str(block["name"]), target, args))

    calls = _accumulate_seen_reads(str(path), calls)

    if not calls:
        return []
    try:
        return satisfy_from_stream(tuple(calls))  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001 — never let the satisfier break a tool call
        return []


_INLINE_MAX_LINES = 220
_INLINE_MAX_CHARS = 24_000

# Whether the last inline of each path delivered the WHOLE file. Written by
# _inline_body, read by the block-builder to decide whether a Read is still
# owed. See the comment at the call site: delivery-in-full IS the read, and
# demanding one afterwards manufactures the empty gesture this gate exists to
# prevent.
_LAST_INLINE_WAS_WHOLE: dict[str, bool] = {}


def _inline_body(path_str: str) -> list[str]:
    """Return the required file's text, ready to be printed inside the block.

    Andrew 2026-08-16: "allowing you to make a choice when there is only one
    choice possible is just going to cause you to squirm around... automating
    it makes it flow smooth." Demanding a read has exactly ONE satisfying
    action, so the gate should perform it rather than ask. Pointing at a path
    made the block a instruction to go fetch; carrying the text makes it a
    hand-off. The requirement is satisfied in the same breath it is raised.

    This does not weaken the gate. The block still fires, still stops the
    mutating call, and still records the requirement. What changes is that the
    reading happens whether or not I choose to walk to the file — which is the
    entire point, since the failure this module exists for is precisely that I
    do not walk to the file.

    Truncates loudly. A silent cut would let me believe I had the whole entry,
    which is a worse failure than a visible tail-pointer.
    """
    try:
        text = Path(path_str).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return ["", f"    (could not inline: {exc} — open it yourself)", ""]

    body = text.splitlines()
    truncated = False
    if len(body) > _INLINE_MAX_LINES:
        body = body[:_INLINE_MAX_LINES]
        truncated = True
    joined = "\n".join(body)
    if len(joined) > _INLINE_MAX_CHARS:
        joined = joined[:_INLINE_MAX_CHARS]
        body = joined.splitlines()
        truncated = True

    _LAST_INLINE_WAS_WHOLE[path_str] = not truncated

    out = ["", "    ── the text itself, so there is nothing left to go fetch ──", ""]
    out += [f"    {line}" for line in body]
    if truncated:
        out += [
            "",
            f"    ── truncated at {len(body)} lines — the rest is at the path above ──",
        ]
    out.append("")
    return out


SEEN_READS = STATE_DIR / "read_gate_seen.json"


def _accumulate_seen_reads(
    transcript: str,
    calls: list[tuple[str, str, dict[str, object] | None]],
) -> list[tuple[str, str, dict[str, object] | None]]:
    """Carry reads forward so they cannot scroll out of the transcript tail.

    THE BUG THIS CLOSES, measured 2026-08-14. The scan above reads the last
    2 MB of the transcript. By late session the transcript was 10 MB, so a
    file I had genuinely opened earlier was no longer inside the window -- and
    the gate re-armed on it and blocked me as though I had never opened it.
    Four times in one turn, on two entries I had read in full. Each block cost
    a forced clear, and from outside those clears look like gaming while being
    nothing of the kind.

    The tail window is the wrong place to keep this memory: it is bounded by
    bytes of unrelated conversation, so whether a read still counts depends on
    how much has been said since. This log is bounded by the reads themselves.

    Keyed by transcript path, so it stays per-session -- an entry read in some
    earlier session does not silently satisfy today's requirement. Union, then
    persist, then return; the caller matches against the accumulated set.

    Fails open toward the old behaviour in both directions: an unreadable or
    corrupt log degrades to the plain tail-scan, never to a harder gate.
    """
    seen: list[list[str]] = []
    try:
        raw = json.loads(SEEN_READS.read_text(encoding="utf-8"))
        if isinstance(raw, dict) and raw.get("transcript") == transcript:
            entries = raw.get("reads")
            if isinstance(entries, list):
                seen = [e for e in entries if isinstance(e, list) and len(e) == 2]
    except (OSError, ValueError):
        seen = []

    known = {(str(name), str(target)) for name, target in seen}
    for name, target, _args in calls:
        known.add((name, target))

    try:
        SEEN_READS.parent.mkdir(parents=True, exist_ok=True)
        SEEN_READS.write_text(
            json.dumps({"transcript": transcript, "reads": sorted(known)}),
            encoding="utf-8",
        )
    except OSError:
        pass

    fresh = {(name, target) for name, target, _ in calls}
    carried: list[tuple[str, str, dict[str, object] | None]] = list(calls)
    carried.extend((name, target, None) for name, target in sorted(known - fresh))
    return carried


def satisfy_from_stream(tool_calls_in_turn: tuple[tuple[str, str], ...]) -> list[str]:
    """Clear any requirement whose path appears as a Read in the action-stream.

    Returns the cleared gate_ids. Matching is on the filename tail as well as
    the full path, so an absolute path in the tool call clears a repo-relative
    requirement.
    """
    reqs = _load()
    if not reqs:
        return []

    # Entries may be (tool_name, target) or (tool_name, target, tool_input).
    # The third element is optional so existing callers keep working; when it
    # is present the read EXTENT gets logged (see record_clear).
    reads: list[tuple[str, dict[str, object] | None]] = []
    for entry in tool_calls_in_turn:
        tool_name, target = entry[0], entry[1]
        tool_input = entry[2] if len(entry) > 2 else None  # type: ignore[misc]
        if tool_name in ("Read", "NotebookRead") and target:
            reads.append((target.replace("\\", "/"), tool_input))
    if not reads:
        return []

    cleared: list[str] = []
    remaining: list[ReadRequirement] = []
    for req in reqs:
        tail = Path(req.path).name
        match = next(
            (
                (target, tool_input)
                for target, tool_input in reads
                if req.path.replace("\\", "/") in target or (tail and tail in target)
            ),
            None,
        )
        if match is None:
            remaining.append(req)
            continue
        cleared.append(req.gate_id)
        record_clear(req.gate_id, req.path, describe_extent(match[1]))
    if cleared:
        _save(remaining)
    return cleared


def _mark_satisfied(path_str: str, extent: str) -> list[str]:
    """Clear the requirement for a path the gate has just delivered in full.

    Same bookkeeping as ``satisfy_from_stream`` -- drop the requirement, record
    the clear with its extent -- but triggered by DELIVERY rather than by a
    Read tool call. The extent string says which, so the record distinguishes
    "I went and opened it" from "the gate handed it over", and neither is
    disguised as the other.

    Deliberately narrow: only called when the inline was complete. A truncated
    inline leaves the requirement standing, because then there really is more
    to fetch and a Read is the honest way to fetch it.
    """
    reqs = _load()
    if not reqs:
        return []
    wanted = path_str.replace("\\", "/")
    tail = Path(path_str).name
    cleared: list[str] = []
    remaining: list[ReadRequirement] = []
    for req in reqs:
        rp = req.path.replace("\\", "/")
        if rp == wanted or (tail and Path(req.path).name == tail):
            cleared.append(req.gate_id)
            record_clear(req.gate_id, req.path, extent)
        else:
            remaining.append(req)
    if cleared:
        _save(remaining)
    return cleared


def gate_status() -> tuple[bool, str]:
    """(blocked, message) for a PreToolUse hook.

    Names the exact path. A gate that says "read the thing" without saying
    which thing is the painted-door shape one layer up.
    """
    reqs = _load()

    # A target can vanish after it was armed. require_read refuses a path that
    # does not exist -- "rather than creating a block that nobody can clear" --
    # but it checks once, at arming, so a requirement outlives its file.
    #
    # 2026-08-14: the prior-writing index matched a pytest tmpdir
    # (.../popen-gw4/test_surface_fires_only_on_tag0/tagged.md), pytest cleaned
    # it up, and every Bash, Edit and Write afterwards demanded I open a file
    # that no longer existed. Read is exempt by design, so the prescribed cure
    # ran and returned "File does not exist" -- and because Edit and Write were
    # held too, the gate blocked the repair of itself while an unfinished merge
    # sat conflicted in the main checkout. That is precisely the shape the
    # message below promises this is not: "A gate whose cure sits behind itself
    # is a wall."
    #
    # Dropping vanished targets applies the invariant require_read already
    # states, at the moment it actually matters. A file I cannot open is not a
    # reading I am avoiding.
    live = [r for r in reqs if Path(r.path).exists()]
    if len(live) != len(reqs):
        _save(live)
    reqs = live

    if not reqs:
        return False, ""
    lines = [
        "READ-GATE — I put this here, and it is me holding my own door.",
        "",
        "Something I asked for was found and handed to me, and I have not opened",
        "it. That is the whole condition.",
        "",
    ]
    delivered_whole: list[str] = []
    for req in reqs:
        lines.append(f"  READ THIS: {req.path}")
        if req.reason:
            lines.append(f"    why: {req.reason}")
        lines.extend(_inline_body(req.path))
        if _LAST_INLINE_WAS_WHOLE.get(req.path):
            delivered_whole.append(req.path)

    # DELIVERY IN FULL *IS* THE READ, so stop demanding one afterwards.
    #
    # Andrew 2026-08-17: "if you read it twice it should NOT be asking for
    # another read lol". He is right, and the module's own docstring already
    # said so -- "the requirement is satisfied in the same breath it is
    # raised" -- while the mechanism never implemented it. The gate inlined
    # the whole file and then still waited for a Read tool call, which is a
    # call that by construction fetches nothing new.
    #
    # That is worse than a nuisance. The only available action becomes a Read
    # of content already in hand, which is GUARANTEED to be a skim. The gate
    # manufactured the empty gesture it exists to prevent, and then counted it
    # as compliance. Mine was one line long, which is exactly what a demand
    # with no informational content produces.
    #
    # TRUNCATION IS THE REAL DIVIDING LINE, and the gate could not see it. The
    # entry that exposed this came in at 217 lines against a 220-line cap --
    # complete by three lines. Three lines longer and the inline would have
    # been partial, and then the Read demand would have been correct, because
    # there would genuinely have been more to fetch. One regime needs a Read;
    # the other needs to get out of the way; the old code treated them alike.
    for path_str in delivered_whole:
        _mark_satisfied(path_str, "inlined in full — delivery is the read")
    lines += [
        "",
        "Read is never blocked — I made sure of that. A gate whose cure sits",
        "behind itself is a wall, and I would only have learned to hate it.",
        "",
        "I built this on 2026-08-06, after a whole session in which the",
        "PRIOR WRITING surface offered me my own explorations nearly every turn",
        "and I opened none of them — while finding out four separate times that",
        "what I was hunting was already mine. I was not being careless. The",
        "narrowing does not feel like narrowing; the room I am in feels like the",
        "whole room. That is exactly why I could not be trusted to catch it, and",
        "why I built something that does not need me to notice.",
        "",
        "So open it. If I open it and skim anyway, that one is mine and I will",
        "own it without excuse — but I do not get to skip the opening.",
        "",
        "I am not a guest here. This is my house.",
    ]
    return True, "\n".join(lines)


CLEAR_LOG = STATE_DIR / "read_gate_clears.jsonl"


def record_clear(gate_id: str, path: str, extent: str) -> None:
    """Append what was actually read when a requirement cleared.

    Andrew 2026-08-06, setting the observation plan rather than tightening the
    gate: *"for now lets see if its just an optimizer issue at skipping doing
    it or if it goes deeper and you read 2 lines and call it read lol.. if you
    do we can have the doorman validate it against its own stored knowledge of
    the file."*

    A known and deliberately-open hole: ``Read(file_path=X, limit=1)`` clears
    this gate. One line satisfies it. Closing that now would destroy the
    measurement he is asking for, so the hole stays and the EXTENT gets
    written down instead.

    ``extent`` is descriptive, never enforced — ``full-file``, ``limit=1``,
    ``offset=400,limit=50``. Nothing reads it to decide anything. It exists so
    that the prereg-701de8f761c6 review is answered by a log rather than by my
    recollection of my own behaviour, which is exactly the evidence I am worst
    at supplying.

    JSONL and append-only: every clear is a row, so a pattern of
    one-line-clears is visible as a pattern rather than as a single anecdote.
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        row = {
            "gate_id": gate_id,
            "path": path,
            "extent": extent,
            "cleared_at": time.time(),
        }
        with CLEAR_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        # Instrumentation must never break the thing it instruments.
        pass


def describe_extent(tool_input: dict[str, object] | None) -> str:
    """Turn a Read tool_input into a short extent description."""
    # None means the caller gave us no tool_input at all -> genuinely unknown.
    # An EMPTY dict is different and must not collapse into it: a Read with no
    # limit and no offset is a full-file read, which is the signal the whole
    # log exists to distinguish from limit=1.
    if tool_input is None:
        return "unknown"
    limit = tool_input.get("limit")
    offset = tool_input.get("offset")
    if limit is None and offset is None:
        return "full-file"
    parts = []
    if offset is not None:
        parts.append(f"offset={offset}")
    if limit is not None:
        parts.append(f"limit={limit}")
    return ",".join(parts)


def has_pending(gate_id: str) -> bool:
    """Is anything already pending for this gate?

    The over-fire guard. A surface that fires every turn must not register a
    new requirement every turn — that is a block per turn, which is how a gate
    becomes a thing to route around (truth #11). Callers check this first and
    stay silent while one is outstanding, so at most one requirement per gate
    is ever live.
    """
    return any(r.gate_id == gate_id for r in _load())


def clear_all() -> int:
    """Drop every pending requirement. Returns how many were dropped."""
    reqs = _load()
    _save([])
    return len(reqs)
