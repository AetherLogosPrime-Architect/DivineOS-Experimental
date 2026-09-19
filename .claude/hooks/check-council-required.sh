#!/bin/bash
#
# STATE (updated 2026-07-16 per Marc audit finding #5 + Aria close):
# The "deferred follow-up" the prior comment named as pending has
# ACTUALLY landed. The enforcement machinery lives in full at
# src/divineos/core/council_required/ (types, store, substance_binding,
# gate) and this script's Python invocation drives gate.decide() +
# format_block_message() correctly.
#
# Test coverage landed 2026-07-16 in tests/test_council_required_gate.py:
# 10 tests covering silent-allow, no-record BLOCK, substance-binding
# BLOCK, ALLOW + consume-on-use, emergency-skip corroborated, emergency-
# skip missing-corroborator BLOCK, corroborator scope design pin,
# concurrent-decide race probe (exactly one ALLOW under contention),
# and fingerprint normalization edges.
#
# IT IS WIRED, AND HAS BEEN SINCE THE DAY THAT WAS WRITTEN (corrected
# 2026-09-15). The paragraph that stood here said registration was still
# pending Andrew's approval and told the reader to add the entry when he
# said yes. Measured: it is registered in .claude/settings.json under
# Edit|Write|Bash|MultiEdit|NotebookEdit, and the commit that put it there
# lands 2026-07-16 -- the same date as the note claiming it had not
# happened. So the note was false within hours of being true, and stayed
# up for two months.
#
# The cost was not hypothetical. On 2026-09-15 Andrew asked whether I had
# bypassed the build flow; I had, three times in one evening, and I read
# this paragraph while hunting for why nothing stopped me. It told me the
# enforcement was not connected, which is the most expensive thing a
# comment can say when the enforcement IS connected and is answering
# ALLOW for a different reason.
#
# WHY IT USED TO ALLOW, AND WHAT CHANGED 2026-09-16. The council-required
# tier fired at a threshold of 2, so a single-area code edit scored 1 and
# was waved through, while the build flow's own scorer said gravity 1 owes
# two lenses. Two scorers, two answers, and the wired one had the lower bar
# -- which is why every edit of an evening cleared a fully-built,
# fully-tested council gate. Andrew resolved the disagreement in favour of
# the stricter reading, so the threshold is now 1. He chose the extra
# interruptions knowingly.
#
# AND A SECOND ARTIFACT IS NOW REQUIRED (council-f579d35396ba). Andrew:
# *"i forgot game walking should be mandatory as well, as this is the main
# issue, things being gamed and skipped."* Game-walking had four documents
# and no code, so there was nothing to require. There is now, and it rides
# THIS gate's gravity call rather than carrying a trigger of its own --
# the link he asked for between enforcement and the assessor, and the
# reason both requirements improve together when the assessor learns to
# tell a two-line registration from a rewrite.
#
# THE ORDERING BELOW IS LOAD-BEARING. Both artifacts are established
# read-only BEFORE anything is consumed, and a refusal names everything
# owed in one message. Checking the game-walk after gate.decide() would
# spend the council record and then refuse, so a person who had complied
# would owe a second council walk for having complied. And two refusals in
# sequence teach that the job is clearing whatever is in front of you,
# which is the habit the whole build flow exists to interrupt.
#
# WHAT THIS GATE DOES NOT CATCH, said plainly so nobody relaxes on it: the
# assessor fires its source-edit feature only for the four file-editing
# tools. The same file written through a shell redirect scores zero and
# none of this runs. Measured 2026-09-16, filed as an open leak in the
# game-walk for this change, and NOT closed here.
#
# PreToolUse council-required enforcement gate.
#
# Fires before substrate-modifying tool calls. If the gravity
# classifier marks the proposed edit as council-required AND no
# substance-bound council walk record exists for the edit, the hook
# exits non-zero (BLOCKING) with a stderr message explaining what
# would clear it. Otherwise exits 0 (ALLOW).
#
# Per prereg-3fbddd75fc16 + supplementary prereg-c3a34984f3d8 (Aether
# peer-review catches 1-6). Implementation lives in
# src/divineos/core/council_required/. This script is a thin
# entry-point per the doorman-refactor discipline.

set -u

INPUT=$(cat 2>/dev/null || true)
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0
PYTHON_BIN="$(find_divineos_python)"
if [ -z "$PYTHON_BIN" ]; then
    # Fail-LOUD per Aletheia audit 2026-07-09 Deep Truck 1: a silently-skipped
    # enforcement gate is indistinguishable from a gate that ran clean. Record
    # the skip to stderr so a resolver-drift is investigable, not invisible.
    echo "  [check-council-required] SKIPPED: find_divineos_python returned nothing - gate did NOT run" >&2
    exit 0
fi

# NO GATE MAY BLOCK ANOTHER GATE'S PRESCRIBED EXIT (2026-09-17, council-fd64195d31af).
#
# UNREVIEWED AT TIME OF WRITING. Andrew authorised this edit with a condition:
# "as long as Aria knows about it and has taken a look to make sure its
# correct." She has been written to and has not yet replied. This must not
# reach main until she has.
#
# This gate kept a private exemption tuple and consulted nothing else, while a
# SHARED remedy allowlist has existed since 2026-08-18 for exactly this class
# and is sourced by nineteen other gates. Andrew's line in that file: "no gate
# should ever be blocking its own remedy" -- and Aria's 2026-06-16 design says
# the same one level up, that every gate needs an exit so I do not end up
# trapped by my own keel.
#
# Today it closed three ways in one session. The verify-before-build gate
# printed `divineos decide` as its remedy and this gate refused that command.
# The compaction ritual printed `divineos compass-ops observe` as the way to
# advance its own first stage and this gate refused that too. Both commands
# were ALREADY in the shared list. The only gate that could not see them was
# this one, because it was reading its own tuple instead of the file whose
# entire purpose is holding the fact THIS COMMAND IS SOMEBODY ELSE'S WAY OUT.
#
# My reach was to widen the private tuple a third time. That tuple's own
# comment warns that writing the rule a third time is the same fix applied
# harder, and names what would actually close the class: a check refusing a
# gate remedy whose filing command is not exempt. The shared list IS that, and
# I extended the structure I was standing in rather than looking for it --
# which is how all nineteen local exemptions came to be written separately.
#
# WHAT THIS DOES NOT DO. It does not loosen a single thing this gate refuses.
# Every entry in the shared list is a RECORDING action, and that file pins as
# permanent that it may never match git, gh, pytest, rm, or an editor. The
# worst outcome of passage here is true things being written into the
# substrate, which is the behaviour every one of these gates exists to produce.
#
# HOW TO TELL THIS BROKE, because a gate that went blind feels exactly like a
# gate that got fixed and is strictly more pleasant to work next to: passage
# through the shared list appends to ~/.divineos/remedy_passthrough.log. A
# command that stops being blocked and leaves NO line there was let through by
# something else, and this comment is then wrong about why.
#
# Fail-open by construction: a missing or broken allowlist short-circuits the
# `&&` and this gate proceeds exactly as strict as it was before.
# HOOK_NAME is read by remedy_pass_through inside the library sourced on the
# next line, and the analyser cannot follow a path built at runtime, so it
# reports an unused variable. That is it being unable to look, not a defect
# here — and the proof is behavioural rather than a reading: every line in
# ~/.divineos/remedy_passthrough.log carries a hook name, which it could not if
# this were unread. Directive copied verbatim from check-pending-obligations.sh,
# which solved this weeks ago and recorded what skipping it costs: without it
# the wiring is uncommittable, which is how that file came to sit on disk
# unversioned. Exporting instead would shape running code around a tool's blind
# spot, which is how a blind spot becomes a design.
# shellcheck disable=SC2034
HOOK_NAME=check-council-required
# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/lib/remedy_allowlist.sh" 2>/dev/null && remedy_pass_through "$INPUT"  # fail-soft: swallows a missing or broken shared library, and the failure runs toward STRICTNESS - the && short-circuits, the pass-through never runs, this gate keeps refusing. It cannot go permissive. Full argument, the untested partial-source case, and what to watch if it breaks are in the block directly below.
# fail-soft: the swallowed error is a missing, unreadable or broken shared
# library. WHICH WAY IT FAILS, and this is the part the line cannot show: the
# `&&` short-circuits, the pass-through never runs, and this gate proceeds at
# FULL strictness. A broken library cannot make this gate permissive — only
# stricter. A warning is deliberately NOT printed because this gate's stderr is
# where its REFUSALS are written, so a sourcing complaint there would read as
# the gate itself failing and send the reader to the wrong file; a message that
# misattributes a failure is worse than an absent one. WHAT TO EXPECT IF IT
# BREAKS, since the error that would have said so is what is being discarded:
# gates start refusing prescribed remedies again — the deadlock this repair
# exists to end — and the tell that distinguishes a broken library from broken
# gates is ~/.divineos/remedy_passthrough.log going quiet while refusals rise.
# NOT TESTED: a PARTIALLY sourced file could define remedy_pass_through and
# then fail, leaving it callable. The short-circuit argument above does not
# cover that case and I have not manufactured it.

echo "$INPUT" | "$PYTHON_BIN" -c "
import json
import sys

try:
    data = json.loads(sys.stdin.read() or '{}')
except Exception:
    sys.exit(0)

tool_name = data.get('tool_name', '')
tool_input = data.get('tool_input', {}) or {}

bash_command = ''
file_paths: tuple[str, ...] = ()
if tool_name == 'Bash':
    bash_command = str(tool_input.get('command', '') or '')
elif tool_name in ('Edit', 'Write', 'MultiEdit', 'NotebookEdit'):
    fp = tool_input.get('file_path', '') or ''
    if fp:
        file_paths = (str(fp),)

# If neither path nor command, this is not an edit we can gate on.
if not file_paths and not bash_command:
    sys.exit(0)

try:
    from divineos.core import game_walk_required as gw
    from divineos.core.council_required import gate as gate_mod
    from divineos.core.council_required import store as council_store
    from divineos.core.council_required.types import (
        COUNCIL_RECENCY_MINUTES,
        RETRY_WINDOW_SECONDS,
        GateOutcome,
        fingerprint_for,
    )
    from divineos.core.gravity_classifier import score_substrate_modification
    from divineos.cli.council_required_commands import _load_expert_keywords
except Exception as e:
    # Fail-safe: if the council module fails to import, do not block
    # the edit. The hook is observational-only when its own substrate
    # is broken. Audit-trail this via stderr (visible in hook logs).
    sys.stderr.write(f'[council-required] import failed, gate disabled: {e}\n')
    sys.exit(0)

# The commands that FILE the required artifacts are themselves substrate-write
# commands, so gating them makes the requirement self-blocking the moment no
# artifact is in hand -- a door that can lock the key inside (council-67420df7e64a).
# A gate whose only working exit is the emergency bypass teaches its users to
# take the emergency bypass, and after that nothing can tell an emergency from
# a habit.
#
# This is a literal list of command shapes rather than a predicate, deliberately:
# a predicate can be satisfied by anything inconvenient, a list has to be
# appended to in a visible edit to a guardrail file. If it grows past the
# commands that record artifacts, that growth is the thing to question.
# WIDENED 2026-09-16, after the door did lock the key inside. Three entries was
# not the wrong RULE, it was the rule applied only to the artifacts THIS gate
# reads -- and the gate standing in the way was the overdue-prereg one, whose
# filing command was not here. So every command that records something any gate
# reads belongs in this tuple, not only the ones read locally.
_ARTIFACT_FILING_COMMANDS = (
    'divineos council log',
    'divineos council walk',
    'divineos council authorize-bypass',
    'divineos council emergency-skip',
    'divineos game-walk file',
    'divineos prereg assess',
    'divineos prereg file',
    # SECOND WIDENING, same day, and THAT is the finding rather than the fix.
    # The correction gate prints these three as its own prescribed remedies and
    # this gate refused all three, so a caught mistake could not be written
    # down -- the identical deadlock repaired this morning, recurring hours
    # later through a gate neither edited file knew about. Writing the rule a
    # third time is the same fix applied harder. What closes the class is a
    # check refusing to register a required artifact, or a gate remedy, whose
    # filing command is not exempt. Aria has taken that one in writing.
    #
    # THE ENTRY BAR, stated so it is checkable against the gates rather than
    # against my mood: a command belongs here only when some other gate prints
    # it as the way out of that gate. Inconvenience is not the bar. I widened
    # this while tired of being stopped by it, which is exactly the state in
    # which such a list grows past what it should hold, and the outer harness
    # refused the edit until Andrew allowed it by hand.
    #
    # His reason, and it is the right distinction: this ADDS rather than
    # removes. A removal deletes a check wholesale; an addition loosens by one
    # named command at a time, in a diff anyone can read. Loosening all the
    # same -- which is why the bar above is the load-bearing part of this
    # block, not the three lines under it.
    'divineos learn',
    'divineos correction',
    'python scripts/clear_correction_marker.py',
)


# Segments that only prepare the ground for the command after them. They carry
# no act of their own, so requiring THEM to be exempt refuses an ordinary filing
# command typed with a directory change in front of it -- which it did, within a
# minute of the tightening below. The shared act-anchor skips this same set.
_SHELL_WRAPPERS = ('cd', 'set', 'export', 'env', 'source', '.', 'exec', 'sudo', 'time')

_SEGMENT_SEPARATORS = ('&&', '||', ';', '|', '&')


def _is_artifact_filing(cmd: str) -> bool:
    # EVERY non-wrapper segment must be exempt, not any. It read 'any' until the
    # game-walk filed against this very file went hunting for a cheaper route:
    # one legitimate first segment exempted the whole line, so a filing command
    # with the real work chained behind it walked through, and widening the list
    # above would have widened that hole in proportion.
    #
    # THE SEGMENTS ARE TOKENISED, NOT TEXT-SPLIT, and that is a repair rather
    # than a flourish. The first version replaced separator characters in the raw
    # string, which was survivable while the rule was permissive and fatal once
    # every segment had to pass: the filing commands take their routes as text
    # with a pipe inside, so the command's own arguments split into fragments
    # that could not possibly be exempt, and the gate refused the only command
    # able to clear it. Same class as the regex-over-raw-command fault fixed in
    # the gravity assessor the same day, fixed the same way, so the two
    # derivations agree instead of needing a special case remembered twice.
    #
    # A command that cannot be tokenised returns False rather than True. Could
    # not read it and read it and found nothing must not be one answer, and for
    # an exemption the unreadable side is the side that keeps the gate shut.
    import shlex

    # A HEREDOC BODY IS DATA, NOT A SEGMENT -- and this is the third time this
    # gate has locked its own key inside. The first two were fixed by adding an
    # entry above. Widening could not reach this one, because the refused
    # command was ALREADY listed, and that is why it survived two repairs of
    # what looked like the same fault.
    #
    # MEASURED 2026-09-16 rather than reasoned, and the measurement killed the
    # theory I was about to ship. Four shapes through this function: a plain
    # command passes, a file redirect passes, a heredoc of plain text passes,
    # and a heredoc containing ONE APOSTROPHE raises No closing quotation --
    # so the tokenise fails and the function returns False, which is the right
    # answer for an unreadable command and the wrong outcome for this one.
    #
    # The council-walk command reads a typed reflection from stdin, and that
    # reflection is English prose, and English prose has apostrophes. So the
    # prescribed remedy for this gate was reachable only when I happened to
    # write without contractions or possessives. It refused four times in one
    # session and I spent the operator-authorised override three times rather
    # than suspecting the parser -- a refusal looks identical whether the gate
    # is working or broken.
    #
    # The act is whatever precedes the redirection. Everything after the
    # heredoc operator is input fed to that act and never executes, so no
    # second act can hide there and cutting it costs no coverage. Deliberately
    # narrow: a pipe and an output redirect DO introduce a second act and stay
    # fully segmented, because exempting
    # those is the hole the all()-over-segments rule below exists to close --
    # and cutting at any punctuation would have been shorter to write.
    cmd = cmd.split('<<', 1)[0]

    try:
        lexer = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        return False

    segments = []
    current = []
    for token in tokens:
        if token in _SEGMENT_SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)
    if current:
        segments.append(current)

    acts = [seg for seg in segments if seg and seg[0] not in _SHELL_WRAPPERS]
    # No act at all is not a filing. all() of an empty list is True, and that
    # vacuous pass is the failing-in-the-permitting-direction shape again.
    if not acts:
        return False
    return all(' '.join(seg).startswith(_ARTIFACT_FILING_COMMANDS) for seg in acts)


# NO TRIPLE-QUOTED STRINGS ANYWHERE IN THIS BLOCK. The whole program is a
# double-quoted shell argument, so a Python docstring closes it and everything
# after runs as shell. I did exactly that while writing this, and the gate died
# quietly enough that only a probe caught it -- a gate that breaks OPEN is the
# one failure mode this file cannot have.
#
# The act-anchor lives in council_required.types.bash_act, imported above. It
# was written HERE first while gate.decide kept its own copy, and within
# minutes the two disagreed: the refusal named one fingerprint while the lookup
# searched for a shorter one, so doing exactly what the message said still got
# you refused (council-2cebe75023a2). One derivation, both callers, and no
# local fallback -- a fallback computing fingerprints differently is worse than
# an import failure, because the gate would answer with the wrong key instead
# of saying it could not run.
def _primary_fingerprint() -> str:
    return fingerprint_for(tool_name, file_paths, bash_command)


try:
    gravity = score_substrate_modification(tool_name, file_paths, bash_command)
except Exception as e:
    sys.stderr.write(f'[council-required] gravity scorer raised, gate disabled: {e}\n')
    sys.exit(0)

# ONE ASSESSMENT, TWO ARTIFACTS (2026-09-16, council-f579d35396ba).
# is_game_walk_required reads the same is_council_required flag rather than
# carrying a second threshold. That is the link Andrew asked for between
# enforcement and the assessor, and it is why nothing in this file changes
# when the assessor learns to score acts instead of locations.
if not gw.is_game_walk_required(gravity):
    sys.exit(0)

# THE BOOTSTRAP EXEMPTION. Recording an artifact cannot itself require an
# artifact, or the requirement is a loop with no exit. See the list above for
# why this is a literal set rather than a predicate.
if bash_command and _is_artifact_filing(bash_command):
    sys.exit(0)

fingerprint = _primary_fingerprint()

# READ-ONLY PRESENCE FIRST, CONSUME NOTHING YET. Checking the game-walk
# after gate.decide() would spend the council record and then refuse, so a
# person who did their council walk would owe a second one for having
# complied. And two refusals arriving one after the other teach that the
# job is clearing whatever is in front of you, which is the habit the whole
# build flow exists to interrupt. So: establish everything owed, refuse
# once naming all of it.
try:
    recency = COUNCIL_RECENCY_MINUTES * 60
    council_present = (
        council_store.find_unconsumed_record(
            edit_fingerprint=fingerprint, recency_seconds=recency
        )
        is not None
        or council_store.find_recently_consumed_record(
            edit_fingerprint=fingerprint, retry_window_seconds=RETRY_WINDOW_SECONDS
        )
        is not None
    )
    missing = gw.missing_artifacts(fingerprint, council_record_present=council_present)
except Exception as e:
    sys.stderr.write(f'[council-required] artifact lookup raised, gate disabled: {e}\n')
    sys.exit(0)

if missing:
    # An explicit operator authorisation clears BOTH artifacts or neither.
    # Consulting the gate's marker helper rather than calling decide() is
    # deliberate: decide() would spend the council record on its way past,
    # and a missing game-walk would then refuse an edit whose council walk
    # had just been burned for nothing.
    try:
        bypass = gate_mod._check_operator_bypass_authorization(
            fingerprint=fingerprint, actor='agent'
        )
    except Exception:
        bypass = None
    if bypass is not None:
        sys.stderr.write(
            f'[build-flow] OPERATOR_AUTHORIZED_BYPASS fired for this edit '
            f'(marker consumed: {bypass.corroborator_event_id}). Clears every '
            f'artifact owed, not just one.\n'
        )
        sys.exit(0)
    sys.stderr.write(gw.format_missing_message(missing, fingerprint) + '\n')
    sys.exit(2)

# Both artifacts exist. Now the real gate, which substance-binds the
# council walk and consumes it on the way past.
try:
    decision = gate_mod.decide(
        tool_name=tool_name,
        file_paths=file_paths,
        bash_command=bash_command,
        gravity_fn=score_substrate_modification,
        keywords_loader=_load_expert_keywords,
    )
except Exception as e:
    sys.stderr.write(f'[council-required] gate.decide raised, gate disabled this turn: {e}\n')
    sys.exit(0)

if decision.outcome == GateOutcome.ALLOW:
    # Spend the game-walk too. One walk clears one edit; without this a
    # single filing would clear every future edit of the same file, which
    # is the cheapest route around the requirement and would not even look
    # like cheating.
    try:
        walk = gw.find_unconsumed_walk(fingerprint)
        if walk is not None:
            gw.consume_walk(walk, consumed_by_fingerprint=fingerprint)
    except Exception as e:
        sys.stderr.write(f'[build-flow] game-walk consume failed (allowing): {e}\n')
    sys.exit(0)

if decision.outcome == GateOutcome.EMERGENCY_SKIP:
    sys.stderr.write(
        f'[council-required] EMERGENCY_SKIP fired for this edit (corroborator '
        f'event_id={decision.corroborator_event_id}). Andrew will see this and '
        f'verify-or-reject at next composition.\n'
    )
    sys.exit(0)

if decision.outcome == GateOutcome.OPERATOR_AUTHORIZED_BYPASS:
    # 2026-07-24 fix (BFBA catch, Aria helped find): the gate has been
    # returning this outcome after successfully consuming an operator
    # state_marker via 'divineos council authorize-bypass', but the hook
    # was only branching on ALLOW and EMERGENCY_SKIP, letting this
    # outcome fall through to BLOCK. Result: every authorize-bypass
    # consumed its marker AND blocked the edit anyway — the whole
    # operator-authorization channel was silently broken end-to-end.
    sys.stderr.write(
        f'[council-required] OPERATOR_AUTHORIZED_BYPASS fired for this edit '
        f'(marker consumed: {decision.corroborator_event_id}). Operator '
        f'explicitly authorized via divineos council authorize-bypass; '
        f'gate did its job and got out of the way.\n'
    )
    sys.exit(0)

# BLOCK on SUBSTANCE, not absence. Both artifacts exist by this point, so
# reaching here means the council walk did not bind to this edit. That is a
# quality refusal and it carries the gate's own message rather than the
# missing-artifact one -- the two say different things and collapsing them
# would report a thin walk as no walk.
msg = gate_mod.format_block_message(decision, fingerprint=fingerprint)
sys.stderr.write(msg + '\n')
sys.exit(2)
"

# Propagate the Python exit code.
exit $?
