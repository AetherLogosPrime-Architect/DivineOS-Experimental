"""Meta-check: every PreToolUse gate that denies a tool call must name
a recovery path in its deny-message.

Closes the generalizable shape behind three locked-box traps from the
2026-06-10 PR-throughput ordeal:

1. correction-not-logged gate named `divineos correction` as remedy,
   but the divineos CLI itself was broken mid-rebase (fixed by PR #138:
   offline escape script + gate-message naming it as fallback).
2. obligations gate named "write structural backing" as remedy, but
   the detector watched for event names nothing emitted (fixed by
   PR #139: aligned _BACKING_EVENT_TYPES with real emitters).
3. prereg-filing was blocked by the very gate the prereg would clear
   (same root: gate-with-unreachable-remedy).

All three share a single shape: a gate denies a tool with a message
that names a remedy, but the named remedy can't actually execute from
where the caller is — the gate is a cage, not a keel.

This test pins the WEAK property that catches the GROSS failure mode:
every shell hook that denies (sets permissionDecision: deny or exits
non-zero with a BLOCKED-shaped message) must include at least one
recovery-token in its denial text. Recovery tokens are explicit
imperatives like ``Run:``, ``Set:``, ``Bypass:``, or a command name
the operator would type (``divineos ...``, ``python scripts/...``,
``touch ~/...``).

A gate whose denial names NO recovery is structurally a cage — the
operator/agent reads the deny-message and has no path forward. That's
the failure shape this test catches.

Caveats:

- This is a STATIC check on hook source. It does not verify the named
  remedy actually executes (that would require running each remedy
  against a state where the gate fires, expensive and fragile). The
  check is calibrated for the gross failure: zero remedy named at all.
- The test deliberately accepts a loose lexicon of recovery tokens —
  catching "no remedy at all" matters more than enforcing a specific
  imperative form.
- pre-tool / post-tool hooks that exit 0 silently (no denial path)
  are exempt; the check only fires on hooks whose source contains a
  denial pattern.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


_PROJECT_ROOT = Path(__file__).parent.parent
_HOOKS_DIR = _PROJECT_ROOT / ".claude" / "hooks"

# Hooks whose business is NOT to gate tool calls — purely informational,
# context-injection, post-event surfaces. They never deny; this test
# does not need to inspect them.
_NON_GATING_HOOKS: frozenset[str] = frozenset(
    {
        "_lib.sh",
        "load-briefing.sh",
        "pre-response-context.sh",
        "pre-tool-context.sh",
        "post-response-audit.sh",
        "post-commit-audit-visibility.sh",
        "post-commit-auto-close.sh",
        "post-compact.sh",
        "pre-compact.sh",
        "log-session-end.sh",
        "session-checkpoint.sh",
        "record-wisdom-read.sh",
        "ear-surface.sh",
        "ear-auto-relaunch.sh",
        "ear-arm-instruction.sh",
        "arm-compaction-monitor-instruction.sh",
        "run-tests.sh",
        "state-gravity-surface.sh",
        # Stop-time SURFACE, not a gate. It names personal writing that was
        # still unsaved when a commit went past it and exits 0 on every path;
        # it cannot refuse anything, so there is no denial for a remedy rule
        # to attach to. Declared here rather than taught to the denial
        # patterns, because teaching a pattern to match a hook that never
        # denies would weaken the rule for the hooks that do.
        "unsaved-personal-writing-must-not-close-quiet.sh",
        # Compose-start PRIME, not a gate: it prints and exits 0, and the
        # Stop-time translate-first gate is what actually refuses. It
        # matched the denial pattern only because its prose DESCRIBES the
        # gate it complements -- a hook talking about refusing, read as a
        # hook that refuses. Wired 2026-08-27 after sitting built and
        # unregistered, with zero liveness entries, since the day it was
        # written.
        "translate-first-compose-prime.sh",
        "check-cleanup-period.sh",
        "check-branch-on-push.sh",
        "detect-correction.sh",  # sets a marker; doesn't deny
        "detect-hedge.sh",  # sets a marker; doesn't deny
        "detect-theater.sh",  # sets a marker; doesn't deny
        "verify-push-landed.sh",
        # Output transform, not a gate: it suppresses a prime's repeated body
        # and prints a floor instead. Every exit in it is 0, including both
        # fail-soft paths, so it can shorten what a prime says and can never
        # refuse the tool call the prime rode in on. Classified 2026-09-20 by
        # reading every exit in the file rather than by its name.
        "dedup-wrap.sh",
    }
)

# Pattern that indicates a hook denies a tool call. FOUR shapes:
# (1) emit JSON ``permissionDecision: deny`` (current convention),
# (2) exit non-zero on a ``BLOCKED`` branch (older gate shape),
# (3) the hook computes a ``BLOCK`` decision string (e.g. check-pending-
#     obligations.sh, where the python helper returns "BLOCK" and the
#     shell wrapper exits non-zero if seen),
# (4) a bare ``exit 2``, which refuses the tool call by exit code alone and
#     may contain none of the words above.
#
# SHAPE FOUR WAS MISSING, AND THE COMMENT HERE USED TO CLAIM THE FIRST THREE
# "catch every denial path the codebase currently uses". 2026-09-19: measured,
# and that sentence had stopped being true. Six hooks refuse by exit code with
# no recognised word anywhere in them -- among them two doormen that had
# refused me personally the same evening. Every one of the six was SKIPPED by
# this check, and a skip here reads in the summary exactly like a pass.
#
# So for six live guards, the rule that a refusal must name a way out was not
# being enforced at all, and nothing said so. That is the house's most common
# defect in the one instrument built to catch it: could-not-look filed as
# could-look-and-it-was-fine.
#
# All six pass now that they are checked, so closing this hole reddens nothing
# -- which is precisely why it could sit here unnoticed. A hole that would have
# broken the suite gets found the day it opens.
_DENIAL_PATTERN = re.compile(
    # Either quote style (Python dicts use single, JSON uses double).
    r"""['"]permissionDecision['"]\s*:\s*['"]deny['"]|BLOCKED\b|['"]BLOCK['"]|=\s*"BLOCK\"""",
    re.IGNORECASE,
)

# Refusal by exit code, with no words at all. Anchored to line-start so the
# phrase inside a comment or a message does not count as one.
#
# SHAPE FIVE, 2026-09-20: a refusal RAISED INSIDE AN EMBEDDED INTERPRETER and
# propagated out by the shell. The hook runs a python program as a quoted
# argument, that program ends on sys.exit(2), and the wrapper ends on exit $?.
# No line anywhere matches a bare ``exit 2``, so the hook landed in the
# could-not-classify bucket -- the same bucket the 2026-09-19 entry above was
# written about, filling again by a new route one day later.
#
# Measured before widening: ten hooks refuse this way, and nine were already
# classified because they also print a BLOCKED-shaped message. Only the
# open-ask doorman refused in this shape and no other, which is why widening
# here reddens nothing and yet was worth doing.
#
# THE PART WORTH KEEPING is not the new spelling. The previous fix taught this
# check one more way to say refuse, and a hook written afterwards refused in a
# way the widened pattern still did not hold. Enumerating spellings does not
# converge. What converges is the dark-set test below, which refuses to let an
# unclassified hook sit quietly whatever spelling it invents.
_EXIT_CODE_DENIAL = re.compile(r"^\s*exit\s+2\b|^\s*sys\.exit\(\s*2\s*\)", re.MULTILINE)

# Recovery-token lexicon. Presence of any one of these in the hook's
# source indicates the deny path names SOME way out. This is the WEAK
# property — we accept anything that looks like a path forward.
_RECOVERY_TOKENS: tuple[str, ...] = (
    "Run:",
    "Re-arm",
    "re-arm",
    "Set:",
    "Bypass:",
    "bypass:",
    "Emergency",
    "Re-run",
    "re-run",
    "divineos ",
    "python scripts/",
    "python family/",
    "touch ",
    "Monitor(",
    "Edit this file",
    "edit this file",
    "edit this hook",
    "fix the underlying",
    "Resolve",
    "Address",
    "Integrate",
    "Defer",
    "Clear ",
    "Path to clear",
    "remedy",
    "Workaround",
    "DIVINEOS_",  # any env-var bypass is a remedy
    "git ",  # git rebase / git pull etc. as remedy
)


def _hook_files() -> list[Path]:
    """Return all .sh files under .claude/hooks/ that the meta-check
    should inspect (gating hooks only)."""
    return [p for p in sorted(_HOOKS_DIR.glob("*.sh")) if p.name not in _NON_GATING_HOOKS]


def _has_denial(text: str) -> bool:
    return bool(_DENIAL_PATTERN.search(text) or _EXIT_CODE_DENIAL.search(text))


def _has_recovery_token(text: str) -> bool:
    return any(token in text for token in _RECOVERY_TOKENS)


@pytest.mark.parametrize("hook_path", _hook_files(), ids=lambda p: p.name)
def test_every_denying_hook_names_a_recovery_path(hook_path: Path):
    """A hook that denies a tool call must name a recovery path in its
    source. The 2026-06-10 locked-box pattern: gate denies → caller has
    no path forward → cage instead of keel. This test catches the GROSS
    failure mode (zero remedy named) statically."""
    text = hook_path.read_text(encoding="utf-8", errors="replace")
    if not _has_denial(text):
        pytest.skip(
            f"COULD NOT CLASSIFY {hook_path.name} — no refusal shape this check "
            "recognises. That is NOT the same as 'it never blocks', and the "
            "older wording here asserted exactly that. On 2026-09-19 six hooks "
            "sitting in this bucket turned out to refuse by exit code, so the "
            "rule went unenforced on them while the summary read clean. "
            "Resolve it rather than leaving it here: if it genuinely never "
            "gates, name it in _NON_GATING_HOOKS; if it refuses in a fifth "
            "shape, teach that shape to _DENIAL_PATTERN or _EXIT_CODE_DENIAL."
        )
    assert _has_recovery_token(text), (
        f"{hook_path.name} denies a tool call but its source contains "
        f"NO recovery-token. The hook reads as a cage: the deny-message "
        f"tells the caller something is blocked but never names a way "
        f"forward.\n\nGate-as-channel principle (Andrew 2026-06-10): "
        f"nothing should block without offering and presenting the remedy. "
        f"Either add a Run:/Set:/Bypass:/edit-this-file path to the "
        f"deny-message, or — if this hook genuinely doesn't gate — add it "
        f"to _NON_GATING_HOOKS in this test."
    )


# --- the dark set, pinned so it cannot grow in silence ----------------------
#
# 2026-09-19, measured while answering "how many tests come back skipped, and
# why". Of the hooks this check walks, sixty-nine produce no refusal shape it
# can see -- and SIXTY-SIX of those are thin shells that hand the decision to a
# Python module. The refusal text and the way out both live in the engine; this
# check reads the doorframe.
#
# So the rule "a gate that refuses must name a way out" is unenforced across
# almost the whole set, and the summary line has never said so. Three of them
# refused me personally the same evening.
#
# WHY THIS IS A PIN AND NOT A FOLLOWER. The obvious repair is to follow the
# delegation and check the module instead. Several of these call an inline
# script rather than a named module, so a static follower would itself have to
# report could-not-tell on an unknown share -- a second half-blind instrument
# built to fix the first. That is the joke writing itself, and I am not
# shipping it at the end of a long night.
#
# What this DOES buy: the set can only shrink. A newly added hook cannot join
# the dark set quietly; it fails here until someone classifies it. The right
# end-state is an empty baseline, and every name removed is a real gain.
_UNCLASSIFIED_BASELINE: frozenset[str] = frozenset(
    {
        "_bail.sh",
        "andrew-past-writing-surface.sh",
        "auto-goal-from-prompt.sh",
        "auto-push-letter.sh",
        "branch-scope-guard.sh",
        "circle-first-compose-prime.sh",
        "close-reach-detector.sh",
        "closure-word-summary-prime.sh",
        "compaction-reach-detector.sh",
        "context-heartbeat.sh",
        "continuity-anchor-surface.sh",
        "continuity-frame-detector.sh",
        "continuity-frame-prime.sh",
        "deletion-discipline.sh",
        "detect-andrew-build-request.sh",
        "distancing-count-surface.sh",
        "doorbell-post-tool-use.sh",
        "doorbell-pre-tool-use.sh",
        "family-state-surface.sh",
        "file-aletheia-artifact-on-arrival.sh",
        "fork-is-cheap-close-prime.sh",
        "hedge-suppression-prime.sh",
        "interior-cue-on-low-presence.sh",
        "lepos-channel-reflect.sh",
        "lepos-channel-surface.sh",
        "letter-monitor-health-surface.sh",
        "load-aletheia-harvest-of-andrew.sh",
        "load-character-sheet.sh",
        "load-dad-ranking-clause.sh",
        "load-my-recording-of-andrew.sh",
        "mirror-letters-to-shared.sh",
        "no-cliff-anchor-surface.sh",
        "no-cliff-prime.sh",
        "no-verify-cost-escalation.sh",
        "open-corrections-surface.sh",
        "operator-asks-surface.sh",
        "operator-gravity-set.sh",
        "post-commit-auto-integrate-corrections.sh",
        "post-commit-auto-verify-findings.sh",
        "post-compaction-fingerprint-surface.sh",
        "post-correction-integration-prime.sh",
        "post-merge-doc-fix.sh",
        "post-push-audit-visibility.sh",
        "post-push-verify-landing.sh",
        "post-read-mark-letter-seen.sh",
        "post-write-mirror-letter.sh",
        "pre-tool-bypass-rate-scan.sh",
        "promise-anchor-surface.sh",
        "promise-reach-detector.sh",
        "register-awareness-surface.sh",
        "require-goal.sh",
        "resolver-health-check.sh",
        "retrieval-tally-check.sh",
        "safe-opposite-edit-check.sh",
        "self-demotion-prime.sh",
        "self-demotion-stop.sh",
        "session-init-once.sh",
        "session-start-verify-git-hooks.sh",
        "shoggoth-gate.sh",
        "sibling-correction-surface.sh",
        "stop-distancing-intercept.sh",
        "stop-response-scope-intercept.sh",
        "summary-room-stop.sh",
        "time-estimate-tracker.sh",
        "verify-claim-prime.sh",
        "visrama-anchor-surface.sh",
        "wallclock-source-prime.sh",
        "wwnd-choice-prime.sh",
        "wwnd-tool-prime.sh",
        # NON-GATING BY DESIGN, which is a different thing from the names
        # above it. Those are unexamined: nobody has established whether they
        # refuse. This one cannot refuse -- it reports whether a recorded push
        # refusal is still unresolved and always lets the turn close, because a
        # check that could block the close over a network reading would stop
        # being read. Added 2026-09-20 with that decision stated rather than
        # slipped in, since the comment above says the right end-state is an
        # empty baseline and a name added silently makes that harder to reach.
        "unlanded-push-must-not-close-quiet.sh",
    }
)


def test_the_dark_set_can_shrink_but_never_grow():
    """A new hook cannot join the unexamined set without someone deciding.

    Shrinking is free and is the point. Growing fails, and the failure names
    the two honest resolutions rather than inviting a third name in the list.
    """
    unexamined = {
        p.name
        for p in _hook_files()
        if not _has_denial(p.read_text(encoding="utf-8", errors="replace"))
    }
    newcomers = sorted(unexamined - _UNCLASSIFIED_BASELINE)
    assert not newcomers, (
        "these hooks are neither declared non-gating nor detectably refusing, "
        "so nothing checks whether they name a way out:\n  "
        + "\n  ".join(newcomers)
        + "\n\nResolve rather than widen the baseline: if it never gates, add "
        "it to _NON_GATING_HOOKS; if it refuses, teach the shape to "
        "_DENIAL_PATTERN or _EXIT_CODE_DENIAL so the remedy rule reaches it."
    )


def test_meta_check_finds_known_gates():
    """Sanity: the meta-check must actually inspect gates we know about,
    not silently scan zero files. Three known gates with deny paths must
    appear in the file set."""
    inspected = {p.name for p in _hook_files()}
    expected_present = {
        # "require-monitors-armed.sh" removed 2026-08-16: retired with the rest
        # of the arm/relaunch delivery cluster on chore/retire-delivery-cluster.
        # The canary's job is to prove the meta-check scans real files rather
        # than silently finding zero, and three surviving gates do that job.
        # Keeping a retired file in the canary set makes the test fail for the
        # one reason it is NOT meant to detect.
        "require-briefing.sh",
        "check-pending-obligations.sh",
        "andrew-correction-attestation.sh",
    }
    missing = expected_present - inspected
    assert not missing, (
        f"meta-check is not inspecting known gate hooks: {missing}. "
        "Either the file set is too narrow or these hooks moved/renamed."
    )


def test_recovery_token_lexicon_is_not_trivially_matched():
    """Sanity: the lexicon must not match arbitrary text. If it matched
    everything, the test could pass on a gate that names no remedy."""
    benign_text = (
        "This is a comment that does not name any recovery path. "
        "It mentions hooks and gates abstractly but provides no command "
        "or escape. Just narrative description."
    )
    assert not _has_recovery_token(benign_text), (
        "recovery-token lexicon false-positives on benign narrative — tighten the lexicon"
    )
