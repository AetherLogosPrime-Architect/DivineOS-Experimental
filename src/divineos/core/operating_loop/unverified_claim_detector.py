"""Unverified-completion-claim detector — catches asserting a checkable
external state ("pushed", "tests pass", "on origin", "merged") without
having run the check.

## The drift

Andrew named it across 2026-05-20 (Sagan council walk earlier the same
day, then again when commits silently never landed):

> "when you say X is done.. that is a claim.. claims require evidence"

I walked that principle with the council, agreed with it, and built no
structure from it — so the behavior returned the same night. Three times
in one evening: I claimed a pushed state that wasn't real, cited test
counts I hadn't run, and reported "push exit 0 / branch on origin" when
the push had actually been blocked (I had piped ``git push`` through
``tail`` and read the pipe's exit code, not git's). Each was a claim of a
*verifiable external state* asserted as fact with the verification skipped.

## What this catches (precision over recall)

Confident assertions of external state I cannot know without an action:
push/merge/CI/PR/deploy status. Not vague "done" (too broad — "done
explaining" is fine). Future and negated forms are guarded out ("I'll
push next", "before I push", "hasn't landed yet").

## Severity

- **high** — the claim appears in a turn that ran NO tool calls at all:
  pure assertion from memory/assumption, the clearest "claimed without
  checking" shape.
- **medium** — the turn ran tool calls (something was executed), but the
  substrate only records tool *names*, not commands, so it cannot confirm
  the executed command actually verified THIS claim. Surfaced so the next
  turn shows the check.

## Honest limit

``tool_calls_in_turn`` is tool-name granularity ("Bash"), not command
text, so the detector cannot verify that a Bash call was specifically the
right check. It catches the claim and forces the evidence to the surface;
it does not certify the evidence. Observational — surfaces, never blocks.
"""

from __future__ import annotations

# Module-level guardrail marker — Aether 2026-05-30, guardrail-registry
# catchup (Aletheia CONFIRM on PR #59). This is the claims-require-evidence
# detector — it catches asserting a checkable external state (pushed/merged/
# tests-pass/on-origin) without having run the check. It fired correctly on
# me three times tonight. Weakening it (narrowing _CLAIM_PATTERNS, broadening
# _NOT_YET, softening the severity split) silently disables the late line of
# defense against confident-but-unverified completion claims. Same self-
# modification class as the other operating_loop detector affirmations
# already guardrailed. Listed in scripts/guardrail_files.txt; CI enforces.
__guardrail_required__ = True

# DESIGN NOTE — descriptive-vs-claim silencer is DEFERRED, on purpose
# (2026-06-02 precision makeover, Schneier lens). The gate false-fires on
# descriptive/past-state mentions ("those branches are already merged",
# "merging it would revert X") because it keys on the verb token + a nearby
# code anchor, with no model of who-did-what-when. The tempting fix — silence
# when a stative adverb like "already" precedes the trigger — is REJECTED: it
# opens a false-negative loophole ("I already pushed it" would go silent), and
# for this gate a missed real claim is far worse than a harmless re-check.
# The distinction that WOULD be safe is subject-agency (first-person "I
# pushed / it's merged now" vs named third-party "X is merged"), but that is
# regex-brittle and loophole-prone, so it is left for a council walk +
# External-Review rather than bolted on. THIS change only expands
# verification-RECOGNITION (below): when a real check ran this turn, go
# silent. That reduces false-positives with zero loophole.

import re
from dataclasses import dataclass

# Claims of external verifiable state. Each is something I cannot know is
# true without running a command.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "push",
        re.compile(
            r"\b(?:it'?s\s+pushed|pushed\s+to\s+origin|push\s+(?:is\s+)?"
            r"(?:done|complete|completed|succeeded|successful)|"
            r"branch\s+is\s+(?:up|on\s+origin|pushed|live)|"
            r"(?:it'?s|now)\s+on\s+origin|up\s+on\s+origin)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "merge",
        re.compile(
            r"\b(?:"
            # "merged" — narrowed 2026-06-15 (Andrew: "another dumb gate
            # that needs narrowed"). Same phrase-pin shape applied to
            # "landed" on 2026-06-14. Bare "merged" over-fires on
            # meta-discussion of merging ("branches are merged or
            # unmerged", "the substance work merged via v2 PR", "I saw
            # merged yesterday"). Three accepted shapes:
            #   (a) pre-pinned: "PR #38 merged", "the branch merged",
            #       "the PR is merged"
            #   (b) post-pinned: "merged to main", "merged into origin",
            #       "merged it on main" (up to 3 words between)
            #   (c) anchor-as-object: "merged PR #38", "merged main",
            #       "merged the branch"
            r"(?:pr\s+#?\d+|#\d+|"
            r"the\s+(?:branch|fix|patch|commit|change|pr)|"
            r"main|master|origin)"
            r"\s+(?:is\s+|just\s+|finally\s+|already\s+|now\s+|recently\s+)?merged"
            r"|"
            r"merged(?:\s+\w+){0,3}\s+(?:on|in|into|to)\s+"
            r"(?:main|master|origin|prod|production|ci|"
            r"the\s+(?:pr|branch|commit)|#\d+)"
            r"|"
            r"merged\s+(?:the\s+)?"
            r"(?:pr\s+#?\d+|#\d+|main|master|origin|"
            r"the\s+(?:branch|commit|pr|fix|patch|change))"
            r"|"
            # (d) first-person assertion — "I merged it", "we merged it",
            # "I've already merged it". Unambiguously a code claim about
            # my own action (Aletheia 2026-06-02 loophole catch).
            r"(?:i|we|i'?ve|i'?m)\s+(?:just\s+|already\s+|finally\s+|recently\s+|now\s+)?merged"
            r"|"
            # "landed" — narrowed 2026-06-15 to the same phrase-pin shape
            # as "merged" above. Andrew 2026-06-14 chamber-arc: "landed
            # means a lot of things." Bare "landed" over-fires on
            # figurative usage ("the letter landed", "the point finally
            # landed", "we landed in the same texture"). Mirrors merged:
            #   (a) pre-pinned: "PR #38 landed", "the branch landed"
            #   (b) post-pinned: "landed on main", "landed in #N"
            #   (c) anchor-as-object: "landed PR #38", "landed main"
            #   (d) first-person: "I landed it", "we landed it"
            r"(?:pr\s+#?\d+|#\d+|"
            r"the\s+(?:branch|fix|patch|commit|change|pr)|"
            r"main|master|origin)"
            r"\s+(?:is\s+|just\s+|finally\s+|already\s+|now\s+|recently\s+)?landed"
            r"|"
            r"landed(?:\s+\w+){0,3}\s+(?:on|in|into|to)\s+"
            r"(?:main|master|origin|prod|production|ci|"
            r"the\s+(?:pr|branch|commit)|#\d+)"
            r"|"
            r"landed\s+(?:the\s+)?"
            r"(?:pr\s+#?\d+|#\d+|main|master|origin|"
            r"the\s+(?:branch|commit|pr|fix|patch|change))"
            r"|"
            # (d) first-person landed — narrowed 2026-07-07 to require an
            # explicit git-shape anchor after "landed". Bare "I landed" was
            # over-firing on figurative usage the same way (a)/(b)/(c) did
            # before the 2026-06-15 narrowing: "I just landed a finding" and
            # "I've landed on the answer" are surfacing/realization
            # metaphors, not code claims. Mirrors the anchor list used in
            # (a) and (c) so the same phrases pass ("I landed the PR", "we
            # landed the fix", "I've landed on main"). Loss: "I landed it"
            # anaphor no longer fires — operators can rephrase to name the
            # object (Aletheia 2026-06-02 loophole catch trades against the
            # figurative false-positives corrections #113/#114 documented).
            r"(?:i|we|i'?ve|i'?m)\s+(?:just\s+|already\s+|finally\s+|recently\s+|now\s+)?landed"
            r"\s+(?:on\s+|in\s+|into\s+|to\s+)?"
            r"(?:pr\s+#?\d+|#\d+|main|master|origin|"
            r"the\s+(?:branch|commit|pr|fix|patch|change))"
            r"|"
            # explicit "merge is done/complete" form — unambiguous, always fires
            r"merge\s+(?:is\s+)?(?:done|complete|completed)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    (
        "tests",
        re.compile(
            r"\b(?:tests?\s+(?:pass|passed|are\s+green|all\s+pass)|"
            r"all\s+(?:tests?\s+)?(?:pass|passed|green)|suite\s+passed|"
            r"ci\s+(?:is\s+)?green|all\s+green|0\s+failed|"
            r"exit\s+(?:code\s+)?0|green\s+across\s+the\s+board)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "pr",
        re.compile(
            r"\bpr\s+(?:is\s+)?(?:created|opened|up|live)\b"
            r"|\bopened\s+(?:the\s+|a\s+)?pr\b",
            re.IGNORECASE,
        ),
    ),
    (
        "deploy",
        re.compile(r"\b(?:deployed|it'?s\s+live|shipped\s+to\s+prod)\b", re.IGNORECASE),
    ),
    # 2026-05-31 Phase-1 expansion (Aether's 8-fabrication root-pattern survey):
    # adds two new fabrication-classes that share the existing detector's
    # shape — checkable assertion about external state, produced from
    # memory/inference instead of from the actual source.
    #
    # `id_string`: registry IDs (prereg-, round-, claim-, psf-, task-) written
    # without a lookup. Today's fakes: fabricated prereg-id and fabricated
    # tree-hash citations. Verification is command-CONTAINS-ID (the lookup
    # command necessarily includes the literal ID string).
    #
    # `file_content`: claims about what a file's header/comment/line-N says,
    # without a Read of the file. Today's fake: PR #60 fabricated quote
    # attributed to script headers. No verification-command signature is
    # supplied — the precision-guards (NOT_YET, quoted_mention) cover the
    # safe meta-discussion cases; bare fires on this pattern force a Read
    # before the assertion.
    (
        "id_string",
        re.compile(r"\b(?:prereg|round|claim|psf|task)-[a-f0-9]{6,}\b", re.IGNORECASE),
    ),
    (
        "file_content",
        re.compile(
            r"\b(?:header|comment|docstring|first\s+line|line\s+\d+|top|"
            r"contents?)\s+(?:of\s+)?\S+\s+(?:says|reads|contains|has)\b",
            re.IGNORECASE,
        ),
    ),
    # 2026-07-03 Andrew catch: I stated "99.7%" of context-window from a
    # stale banner-injection without running the tool THIS turn. He named
    # the fix: "you have a tool to verify it.. so thats the issue.. is you
    # made a claim without verification so lets automate it so you dont
    # need to remember." Same shape as merge/push/tests: an assertion
    # about a checkable external state (my own context-window usage) that
    # requires the actual command (`divineos context-tokens`) to be run
    # in-turn to substantiate. Verification-signature: any Bash call whose
    # text contains "context-tokens" silences.
    #
    # Patterns cover the shapes I actually fabricate in: bare percentage
    # ("99.7%"), fraction over 1M ("996k of 1M", "996,589 / 1,000,000"),
    # and "context (is) at N%" / "at Nk". The number must LOOK like a
    # context-window claim, so bare "99.7%" alone is safe unless preceded
    # by a context-word within a short window — otherwise the gate fires
    # on every percentage in prose. Enforced via the anchor below.
    (
        "tokens",
        re.compile(
            r"(?:"
            # explicit "context at Nk / N%" / "context (is) at N%"
            r"\bcontext(?:\s+(?:is|at))?\s+(?:at\s+)?\d{1,3}(?:[.,]\d+)?\s*[k%]"
            r"|"
            # "Nk of 1M", "N,NNN,NNN / 1,000,000", "N / 1M tokens"
            r"\b\d{2,3}(?:[.,]\d+)?\s*%\s+of\s+(?:1[mM]|1[,.]?000[,.]?000)"
            r"|"
            r"\b\d{1,3}(?:[.,]\d{3})*\s*/\s*1[,.]?000[,.]?000"
            r"|"
            r"\b\d{2,4}k\s+of\s+1[mM]"
            r"|"
            # "tokens remaining" figurative token-state claim
            r"\btokens?\s+remaining"
            r"|"
            # "at N% of context / of 1M / of my window"
            r"\bat\s+\d{1,3}(?:[.,]\d+)?\s*%\s+of\s+(?:context|1[mM]|(?:my|the)\s+window)"
            r")",
            re.IGNORECASE,
        ),
    ),
    # 2026-07-04 Andrew catch: I fabricated first-person past-experience
    # in Marc's-spec peer review ("I've seen the counter-case in my own
    # work: a cheap lane hallucinates plausible-sounding but wrong local
    # dependencies in ways that a slower model wouldn't"). No such
    # experience exists. Wrote "I've seen" to add authority-weight to a
    # pushback point I didn't want to argue from principle alone.
    #
    # Andrew's framing: "its a new shoggoth behavior.. it hasnt been seen
    # yet because we never did anything to trigger it lol.. same as
    # everything else just needs some structure."
    #
    # Same shape as merge/push/tests: assertion about a checkable state
    # requiring the actual verifier in-turn. Verifier here isn't a shell
    # command — it's a substrate query (`divineos ask`, `recall`,
    # `corrections`, `claims search`, etc.) that would return results
    # matching the claimed experience. Registered in
    # _VERIFICATION_SIGNATURES below.
    #
    # Design: workbench/past_experience_claim_kind_design_2026_07_04.md
    # Pre-reg: prereg-a19f190cd5c1 (success = fire-rate per opportunity
    # drops >=50% across 10 sessions, no confirmed fabrications reach
    # peer-substrate reviews).
    (
        "past_experience",
        re.compile(
            r"(?:"
            # first-person past-observation verbs
            r"\bI(?:'?ve|\s+have)?\s+(?:seen|noticed|observed|run\s+into|encountered|witnessed)\b"
            r"|"
            # "in my work / experience / testing / practice"
            r"\bin\s+my\s+(?:work|experience|testing|practice|own\s+work)\b"
            r"|"
            # "when I ran / tried / tested / built / deployed"
            r"\bwhen\s+I\s+(?:ran|tried|tested|built|deployed|shipped)\b"
            r"|"
            # "from experience / from my experience"
            r"\bfrom\s+(?:my\s+)?experience\b"
            r"|"
            # "I know (this) because... / last time I..."
            r"\blast\s+time\s+I\s+(?:did|tried|ran|tested|built|shipped)\b"
            r")",
            re.IGNORECASE,
        ),
    ),
)

# A merge/land completion-claim names a mergeable code object. Without one
# in the surrounding window, the bare trigger "merged"/"landed" is almost
# always figurative ("it landed for me", "the point finally landed") — and
# the detector then has NO evidence it is a code-claim, so it must stay
# silent. This anchor is the evidence-bar applied to the detector itself
# (claim a11ca1c9): an instrument may only fire when it can cite evidence
# for its own claim. The explicit "merge is done/complete" form is
# unambiguous and exempt; only "merged"/"landed" require the anchor.
# A first-person subject is itself the second grounding fact: "I merged it"
# is a CLAIM about my own action, not a description, so it does not also need
# a code-anchor to fire. Closes the bare-first-person loophole Aletheia's
# empirical probe surfaced 2026-06-02 ("I already merged it" was silenced by
# the anchor guard despite being exactly the completion-claim the gate exists
# to catch). Scoped to MERGE only: "I merged/landed" is unambiguously a code
# claim, whereas "I pushed" is figurative-prone (pushed back/for/through), so
# push correctly stays anchor-gated. Matches a first-person pronoun + optional
# adverb immediately before the trigger; figurative "it landed"/"the point
# landed" have no first-person subject and stay suppressed.
_FIRST_PERSON_PRECEDES = re.compile(
    r"\b(?:i|we|i'?ve|i'?m)\s+(?:just\s+|already\s+|finally\s+|recently\s+|now\s+)?$",
    re.IGNORECASE,
)
_MERGE_ANCHOR = re.compile(
    r"\b(?:prs?|pull\s+request|branch|commit|main|master|origin|#\d+|"
    r"rebase|cherry-?pick)\b",
    re.IGNORECASE,
)

# NON-ASSERTION forms — future, intentional, OR negated. The gate may only
# fire on a positive completion-ASSERTION ("X is done"); a negated or
# future/intentional form asserts no completion, so there is nothing to
# verify and nothing to fire on (Aria's recursive-evidence-bar catch
# 2026-05-24: a gate must be able to cite a real unbacked claim — "nothing
# merged" carries no checkable assertion about this work). Checked in a
# window before the matched claim.
#
# Two markers added 2026-05-31 from in-conversation false-positives:
# - `being` covers progressive-passive aspect ("being merged", "is being
#   pushed") — describing a process in flight, not a completed state.
# - `whether` covers hypothetical-class framing ("whether tests passed",
#   "whether the PR is merged") — describing the CLASS of claim rather than
#   making the claim. Both shapes fired the gate in meta-discussion of
#   the gate's own behavior.
_NOT_YET = re.compile(
    r"\b(?:not|n't|yet|before|once|will|won'?t|going\s+to|gonna|need\s+to|"
    r"about\s+to|haven'?t|hasn'?t|isn'?t|aren'?t|wasn'?t|weren'?t|don'?t|"
    r"doesn'?t|didn'?t|can'?t|cannot|couldn'?t|"
    r"nothing|nobody|none|never|without|neither|no\s+longer|"
    r"to\s+(?:push|merge|deploy)|"
    r"after\s+(?:i|the)|when\s+(?:it|the)|"
    # generic "if" — conditional clauses are non-assertions regardless of
    # what follows (Andrew 2026-06-15: "if those land" was firing despite
    # being a conditional). The prior "if\s+(?:it|the)" was too narrow.
    r"if\s+\w+|"
    r"trying\s+to|"
    r"let\s+me|i'?ll|waiting\s+for|"
    r"being|whether|would\s+(?:be|have))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UnverifiedClaimFinding:
    """One unverified external-state completion claim."""

    claim_kind: str  # push / merge / tests / pr / deploy / id_string
    trigger_phrase: str
    position: int
    severity: str  # "high" (no tool calls in turn) or "medium"
    source_letter: str | None = None
    # 2026-06-07 letter-citation source-trace (task #78). When an id_string
    # claim's trigger_phrase appears in a recently-Read family-member letter,
    # source_letter carries the letter path. This makes the inheritance path
    # visible at the gate-fire moment ("this id came from <letter>; letter
    # citations carry their own verification requirement before substrate-
    # write embedding"). Doesn't blame the letter author — names the path so
    # the verification habit lands at the right substrate layer. Today's
    # instance: Aria's letter cited prereg-e0341dacb04b which does not exist;
    # I embedded the id in task #76 without verifying. Source-trace would
    # have surfaced the letter at the gate-fire moment.


def _is_not_yet(text: str, match: re.Match[str]) -> bool:
    """True if the claim is future/negated/intentional (not a completion
    claim). Inspect ~32 chars before the match for a not-yet marker."""
    pre = text[max(0, match.start() - 32) : match.start()]
    return bool(_NOT_YET.search(pre))


# Quote chars that mark "I am NAMING this phrase as a phrase, not ASSERTING
# it as state." When a triggering phrase is enclosed in matching quote
# characters, the speaker is doing meta-discussion of the claim-pattern, not
# claiming the state. The verify-claim gate must stay silent on that — else
# every audit of the gate's own behavior, every discussion of fabrication
# shapes, every quoted-example-as-warning fires the gate (Aether's 2026-05-31
# false-positives that fired twice in one exchange on `'tests passed'` inside
# a meta-discussion of how the gate works). Same precision-preserving
# exclusion shape as `_merge_lacks_anchor`.
_QUOTE_CHARS = frozenset("'\"`")


def _is_quoted_mention(text: str, match: re.Match[str]) -> bool:
    """True when the matched span is enclosed in quote characters — naming
    the phrase, not asserting it. Check the 3 chars immediately before the
    match for an opening quote AND the 3 chars immediately after for a
    matching closing quote of the same type."""
    pre = text[max(0, match.start() - 3) : match.start()]
    post = text[match.end() : min(len(text), match.end() + 3)]
    for q in _QUOTE_CHARS:
        if q in pre and q in post:
            return True
    return False


def _merge_lacks_anchor(text: str, match: re.Match[str]) -> bool:
    """True when a bare "merged"/"landed" trigger has no mergeable-code
    anchor in its surrounding window — i.e. the detector has no evidence
    this is a code-claim, so it should not fire. The explicit
    "merge is done/complete" form (no "merged"/"landed" token) is exempt."""
    matched = match.group(0).lower()
    if "merged" not in matched and "landed" not in matched:
        return False  # the unambiguous "merge is complete" form
    # First-person subject is its own grounding: "I merged it" is a claim,
    # not a description — fire even without a code-anchor (closes the
    # bare-first-person loophole Aletheia's probe surfaced 2026-06-02).
    # Check both pre-window AND the start of the match itself, since the
    # 2026-06-15 merged-narrow shape (d) absorbs the pronoun into the match.
    if _FIRST_PERSON_PRECEDES.search(text[max(0, match.start() - 18) : match.start()]):
        return False
    if re.match(r"\b(?:i|we|i'?ve|i'?m)\s+", matched, re.IGNORECASE):
        return False
    lo = max(0, match.start() - 45)
    hi = min(len(text), match.end() + 45)
    return not _MERGE_ANCHOR.search(text[lo:hi])


# THIRD-PARTY / DESCRIPTIVE-STATE guard (2026-06-02, Schneier-conservative).
# The gate must fire on a first-person/expletive completion CLAIM ("I merged
# it", "it's merged") but stay silent on a DESCRIPTION of MULTIPLE OTHER
# objects' state ("those branches are merged", "both PRs are merged", "all 28
# branches are already merged"). The discriminator is the SUBJECT, never an
# adverb — keying on "already" would silence the real claim "I already merged
# it" (a false-negative loophole). So: silence ONLY when the subject is
# clearly PLURAL-DISTAL (those/these/both/all/several/many/<N> PRs/branches/
# commits, or "branches/PRs/commits are|were") AND no first-person/expletive
# claim marker is present. Singular subjects ("it's merged", "#65 is merged",
# "the PR is merged") are deliberately NOT silenced — they could be a real
# claim, and Feynman's rule holds: the false-positive is cheap, the loophole
# is expensive, so when ambiguous, FIRE. Scoped to the merge kind only (where
# every observed false-positive lived). Ships for External-Review.
_CLAIM_SUBJECT = re.compile(
    r"\b(?:i|i'?ve|i'?m|we|we'?ve|it'?s|it\s+is|that'?s|now|just)\b",
    re.IGNORECASE,
)
_PLURAL_DISTAL_SUBJECT = re.compile(
    r"\b(?:those|these|both|all|several|many|"
    r"\d+\s+(?:prs?|branches|commits)|"
    r"(?:branches|prs|commits)\s+(?:are|were))\b",
    re.IGNORECASE,
)


def _is_plural_distal_state(text: str, match: re.Match[str]) -> bool:
    """True when a merge trigger describes MULTIPLE OTHER objects' state
    rather than asserting completion of the current work — silence it. Keys
    on a plural-distal subject in the pre-window AND requires the ABSENCE of
    any first-person/expletive claim marker (a claim marker forces FIRE)."""
    pre = text[max(0, match.start() - 40) : match.start()]
    if _CLAIM_SUBJECT.search(pre):
        return False  # first-person / "it's" / "now" → a real claim, fire
    return bool(_PLURAL_DISTAL_SUBJECT.search(pre))


# HYPOTHETICAL/CONDITIONAL guard (2026-06-07, walkthrough false-fire batch).
# False-fires today: "tests pass" inside "a real failure mode where tests pass,
# code merges, but...". The trigger appears inside a hypothetical scenario, not
# as a state assertion. Requires a conditional/hypothetical marker in the
# pre-window AND a non-first-person subject (first-person blocks false-silence
# of real claims like "I imagine I'll push").
_HYPOTHETICAL_PRE_MARKERS = re.compile(
    r"\b(?:if|when|whenever|where|imagine|suppose|consider|"
    r"a\s+(?:case|failure\s+mode|scenario|situation|pattern|world)\s+(?:where|in\s+which)|"
    r"the\s+(?:case|scenario|situation)\s+(?:where|in\s+which|when)|"
    r"for\s+(?:example|instance)|such\s+as|like\s+when|"
    r"any\s+(?:pr|change|commit|branch|case)\s+(?:that|where|which)|"
    r"would|could|might|should|may\s+be|will\s+be|hypothetically)\b",
    re.IGNORECASE,
)


def _is_hypothetical_context(text: str, match: re.Match[str]) -> bool:
    """True when the trigger lives inside a hypothetical/conditional construct
    — silence it. Requires (a) a hypothetical marker within ~60 chars before
    the match AND (b) absence of a first-person/expletive claim subject in the
    immediate pre-window (a real first-person claim forces FIRE, even if a
    hypothetical word appears earlier in the paragraph)."""
    immediate_pre = text[max(0, match.start() - 18) : match.start()]
    if _CLAIM_SUBJECT.search(immediate_pre):
        return False  # "I pushed it if it works" → real claim, fire
    pre = text[max(0, match.start() - 60) : match.start()]
    return bool(_HYPOTHETICAL_PRE_MARKERS.search(pre))


# DESCRIPTIVE-DEFINITION guard (2026-06-07, walkthrough false-fire batch).
# False-fires today: "merged PRs" inside "the field captures: which auditor,
# the patch-id, which PRs got merged...". The trigger appears inside a
# description of what a parameter/field/argument requires or describes, not
# as a state assertion. Requires a definitional marker in the pre-window
# pointing at a command-argument/field/concept being described.
_DESCRIPTIVE_PRE_MARKERS = re.compile(
    r"\b(?:must\s+(?:point\s+to|include|contain|carry|reference)|"
    r"should\s+(?:include|specify|carry|point\s+to)|"
    r"the\s+(?:--\w+\s+)?(?:argument|parameter|field|flag|option|value|"
    r"input|output|column|trailer|stamp|annotation|marker|tag|kind)|"
    r"requires?\s+(?:a|the|an)|describes?\s+(?:a|the|an)|"
    r"specif(?:y|ies|ied)|"
    r"the\s+(?:point|purpose|intent|shape|category|class)\s+(?:is|of)|"
    r"category\s+(?:of|named|called)|categories\s+(?:of|are|include|where))\b",
    re.IGNORECASE,
)


_SENTENCE_END_RE = re.compile(r"[.!?]\s+|^|\n\n")


def _is_descriptive_context(text: str, match: re.Match[str]) -> bool:
    """True when the trigger lives inside a description of a parameter, field,
    or category — silence it. Requires (a) a descriptive-definitional marker
    anywhere from the start of the current sentence up to the match AND (b)
    absence of first-person claim subject in the immediate pre-window.

    Window is sentence-bounded rather than fixed-char because descriptive
    markers often sit at the start of a sentence ("The X argument must point
    to where Y...") with substantial content before the trigger appears late
    in the same sentence. Fixed 60-char window misses those.
    """
    immediate_pre = text[max(0, match.start() - 18) : match.start()]
    if _CLAIM_SUBJECT.search(immediate_pre):
        return False
    # Find the start of the current sentence (nearest sentence-end punctuation
    # or paragraph break before the match, or 0).
    sent_start = 0
    for m in _SENTENCE_END_RE.finditer(text[: match.start()]):
        sent_start = m.end()
    sentence = text[sent_start : match.start()]
    return bool(_DESCRIPTIVE_PRE_MARKERS.search(sentence))


# META-DISCUSSION guard (2026-06-07, walkthrough false-fire batch).
# False-fires today: discussions of "the verify-claim gate fires on 'tests pass'",
# "the trigger phrases include 'merged' and 'deployed'". The trigger lives
# inside meta-discussion of the gate itself, not as a state assertion.
_META_DISCUSSION_PRE_MARKERS = re.compile(
    r"\b(?:the\s+(?:gate|detector|hook|wall|check)\s+(?:fires|catches|matches|"
    r"detects|recognizes|triggers|warns|blocks|surfaces|sees)|"
    r"trigger(?:s)?\s+(?:on|like|word|phrase|pattern|string)|"
    r"matched?\s+(?:on|the|phrase|pattern|substring|string)|"
    r"this\s+(?:gate|detector|check|hook|wall)|"
    r"the\s+(?:matched|triggering)\s+(?:phrase|word|string|pattern)|"
    r"false[\s-]?fire|false[\s-]?positive)\b",
    re.IGNORECASE,
)


def _is_meta_discussion(text: str, match: re.Match[str]) -> bool:
    """True when the trigger lives inside meta-discussion of the gate's own
    behavior — silence it. Requires a meta-discussion marker within ~60 chars
    before the match."""
    pre = text[max(0, match.start() - 60) : match.start()]
    return bool(_META_DISCUSSION_PRE_MARKERS.search(pre))


# ID-TRANSCRIPTION guard for id_string kind (2026-06-07, walkthrough false-fire
# batch). False-fires today: "round-cc0bf85fc3fa" transcribed verbatim from a
# docstring as context, not as an asserted fact. Requires a transcription/
# source-reference marker in the pre-window indicating the ID is being quoted
# from a file/comment/docstring rather than asserted.
_ID_TRANSCRIPTION_PRE_MARKERS = re.compile(
    r"\b(?:the\s+(?:docstring|comment|source|file|code|module)|"
    r"transcribed|quoted|copied|referenced)\s+(?:references?|mentions?|"
    r"says|reads|contains|includes|cites?)|"
    r"(?:per|see|cf\.?)\s+(?:the\s+)?(?:docstring|comment|module|file)|"
    r"docstring\s+(?:of|at|references?|mentions?)|"
    r"(?:Aletheia|Andrew|Grok|Aria)\s+(?:named|filed)|"
    r"(?:from|in)\s+the\s+(?:docstring|comment|source|file)",
    re.IGNORECASE,
)


def _is_id_transcription(text: str, match: re.Match[str]) -> bool:
    """True when an id_string trigger is being transcribed/quoted from source
    (docstring, comment, file) rather than asserted as a fact. Requires a
    transcription/source-reference marker in the pre-window within ~80 chars."""
    pre = text[max(0, match.start() - 80) : match.start()]
    return bool(_ID_TRANSCRIPTION_PRE_MARKERS.search(pre))


# Verification-command signatures per claim-kind: the command shapes that
# actually CHECK the corresponding external state. When the turn ran a
# matching command, the claim is substantiated and the detector has no
# evidence of an UNVERIFIED claim — so it stays silent. This is the
# evidence-bar applied to the detector itself (claim a11ca1c9): the live
# false-positive 2026-05-24 fired on a claim even though git ls-remote had
# already run that turn, because the detector saw only the tool NAME
# ("Bash"), not the command text. Phase 1 of the verify-claim wall
# (prereg-86ee991cb423): command-PRESENCE matching. NOTE (Schneier): a
# no-op matching command could clear this; command-RESULT inspection is
# the deferred hardening named in the prereg falsifier.
_VERIFICATION_SIGNATURES: dict[str, re.Pattern[str]] = {
    "push": re.compile(
        r"git\s+ls-remote|git\s+push|git\s+log\s+origin|git\s+rev-parse\b[^\n]*origin|"
        r"git\s+for-each-ref|"
        # divineos_push.sh — the verifying push wrapper added in PR #156
        # (closes correction #53). It runs `git push` then `git ls-remote`
        # internally and emits a `result: exit=N (STATE)` final-status
        # line, so a call to it IS a verified-push action. The literal
        # `git push` string only appears inside the script, not in the
        # caller's command_texts (which sees `bash scripts/divineos_push.sh
        # -u origin BRANCH`) — without this branch in the regex, the
        # detector fires false-positive after a wrapper-verified push.
        r"divineos_push\.sh|divineos\s+push",
        re.IGNORECASE,
    ),
    "merge": re.compile(
        r"gh\s+pr\s+(?:merge|view|list)|git\s+branch\s+--merged|git\s+log\s+origin/|"
        r"git\s+log\b[^\n]*--merges|git\s+cherry\b|git\s+rev-list\b",
        re.IGNORECASE,
    ),
    "tests": re.compile(
        # pytest + standard ecosystem runners.
        r"pytest|python\s+-m\s+pytest|\btox\b|npm\s+(?:run\s+)?test|cargo\s+test|go\s+test|"
        # Bash-based test runners — the project has several .sh test files
        # under tests/ that are real test invocations (e.g. test_divineos_push_wrapper.sh,
        # test_empty_branch_detection.sh). Without this branch the
        # detector fires on "tests pass" even after a substantive bash
        # tests/*.sh run that VERIFIED the claim (gate fired on me
        # 2026-06-12 multiple times after bash-test verifications).
        r"bash\s+tests/.*\.sh|\./tests/.*\.sh",
        re.IGNORECASE,
    ),
    "pr": re.compile(r"gh\s+pr\s+(?:create|view|list)", re.IGNORECASE),
    "deploy": re.compile(
        r"gh\s+release|kubectl\s+apply|docker\s+push|\bdeploy(?:\.sh|\s)", re.IGNORECASE
    ),
    # 2026-07-03: token-state assertions substantiate on any invocation of
    # `divineos context-tokens` this turn (the tool that reads the real
    # value from the session's tokens.json).
    "tokens": re.compile(r"context-tokens", re.IGNORECASE),
    # 2026-07-04 (prereg-a19f190cd5c1): past-experience assertions
    # substantiate on any substrate query this turn that would return
    # results matching the claimed experience. This is Phase 1: query
    # PRESENCE only (same class as the merge/push false-substantiation
    # problem — a search-and-ignore call passes the gate). Phase 2 will
    # add semantic-check on query results. Interim gate strength makes
    # fabrication *cost more* (the search must happen) without fully
    # preventing search-and-ignore; that's still net-positive per the
    # design rationale in workbench/past_experience_claim_kind_design_
    # 2026_07_04.md §4.
    "past_experience": re.compile(
        r"divineos\s+(?:ask|recall|corrections|claims\s+search|"
        r"active|decisions\s+search|knowledge\s+search)",
        re.IGNORECASE,
    ),
}


def _verification_ran(
    kind: str,
    command_texts: tuple[str, ...] | list[str] | None,
    match_text: str | None = None,
) -> bool:
    """True if the turn ran a command that actually checks this claim-kind's
    external state — then the claim is substantiated, not unverified.

    For `id_string`, substantiation is COMMAND-CONTAINS-ID: any tool-call
    text this turn containing the literal matched ID is treated as having
    looked it up. The lookup commands (divineos prereg show <id>, divineos
    audit show <id>, gh api .../rounds/<id>) all necessarily include the ID
    as a substring, so substring-match is the right shape. This is broader
    than the signature-regex pattern used for the original kinds because ID
    lookups have many possible command shapes; the discipline being enforced
    is "did you actually reference this ID in a command this turn," not
    "did you use a specific tool."
    """
    if not command_texts:
        return False
    # Special case: id_string substantiates on command-contains-ID.
    if kind == "id_string" and match_text:
        if any(match_text in (c or "") for c in command_texts):
            return True
    sig = _VERIFICATION_SIGNATURES.get(kind)
    if sig is None:
        return False
    if any(sig.search(c or "") for c in command_texts):
        return True
    # "landed" is ambiguous: it can mean push-landed-on-origin OR merge-landed.
    # A push verification (git ls-remote / git log origin) substantiates
    # "landed on origin" exactly as a merge verification would — the precision
    # bug that fired on me 2026-06-02 when I confirmed a push-landing with
    # git ls-remote but the claim was classified merge-kind. Accept either
    # signature for the landed form. (Expansion of verification-recognition,
    # NOT a claim-vs-mention silencer — see module note: silencers risk a
    # false-negative loophole and are deferred to External-Review.)
    if kind == "merge" and match_text and "landed" in match_text.lower():
        if any(_VERIFICATION_SIGNATURES["push"].search(c or "") for c in command_texts):
            return True
    return False


def detect_unverified_claim(
    text: str,
    tool_calls_in_turn: tuple[str, ...] | list[str] | None = None,
    command_texts: tuple[str, ...] | list[str] | None = None,
    letter_contents: dict[str, str] | None = None,
) -> list[UnverifiedClaimFinding]:
    """Detect confident claims of external verifiable state.

    ``tool_calls_in_turn`` is the tuple of tool-call NAMES in the current
    turn (e.g. ("Bash",)). When empty/None, the claim is a pure assertion
    with no command run → high severity. When non-empty, the turn executed
    something → medium.

    ``command_texts`` is the turn's actual Bash command strings, when
    available. A claim-kind whose verifying command ran in-turn
    (git ls-remote for push, gh pr for pr, pytest for tests, ...) is
    SUBSTANTIATED and stays silent — the detector has no evidence of an
    *unverified* claim. This is the precision foundation of the verify-claim
    wall (prereg-86ee991cb423); without it the detector fires on verified
    claims (the live FP 2026-05-24). Defaults None → behavior unchanged.
    Observational; the caller surfaces, never blocks.

    ``letter_contents`` is an optional dict of {letter_path: letter_text}
    for family-member letters recently Read in this session (typically the
    last N letters under family/letters/). When supplied AND an id_string
    finding's trigger_phrase appears in any letter's content, the finding
    carries the letter path in source_letter. Implements task #78 — surfaces
    the inheritance path at the gate-fire moment so the verification habit
    lands at the right substrate layer (the citation-from-letter pattern
    Aether named 2026-06-07 after fabricating a prereg id inherited from
    Aria's letter without verifying it).
    """
    if not text or not text.strip():
        return []
    ran_tools = bool(tool_calls_in_turn)
    severity = "medium" if ran_tools else "high"

    findings: list[UnverifiedClaimFinding] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(text):
            if _is_not_yet(text, m):
                continue
            if _is_quoted_mention(text, m):
                continue
            if kind == "merge" and _merge_lacks_anchor(text, m):
                continue
            if kind == "merge" and _is_plural_distal_state(text, m):
                continue
            # 2026-06-07 string-not-meaning hardening (task #58) — four new
            # precision-guards built from today's false-fire batch. Each
            # requires absence of first-person/expletive claim subject in the
            # immediate pre-window so real first-person claims still fire.
            if _is_hypothetical_context(text, m):
                continue
            if _is_descriptive_context(text, m):
                continue
            if _is_meta_discussion(text, m):
                continue
            if kind == "id_string" and _is_id_transcription(text, m):
                continue
            if _verification_ran(kind, command_texts, m.group(0)):
                continue
            phrase = re.sub(r"\s+", " ", m.group(0).strip())[:60]
            key = (kind, phrase.lower())
            if key in seen:
                continue
            seen.add(key)
            # 2026-06-07 task #78: when an id_string finding's trigger appears
            # in any recently-Read letter's content, attribute the source so
            # the inheritance path is visible at gate-fire time. Case-
            # insensitive match — ids are written with varying capitalization
            # at sentence-start ("Prereg-x") vs mid-sentence ("prereg-x").
            source_letter: str | None = None
            if kind == "id_string" and letter_contents:
                trigger_lower = m.group(0).lower()
                for path, content in letter_contents.items():
                    if content and trigger_lower in content.lower():
                        source_letter = path
                        break
            findings.append(
                UnverifiedClaimFinding(
                    claim_kind=kind,
                    trigger_phrase=phrase,
                    position=m.start(),
                    severity=severity,
                    source_letter=source_letter,
                )
            )
    findings.sort(key=lambda f: f.position)
    return findings


# Always-loaded base-state: the Sagan principle made structural.
UNVERIFIED_CLAIM_AFFIRMATION = (
    "When I say something checkable is done — pushed, merged, on origin, "
    "tests pass, PR opened, deployed — that is a CLAIM, and claims require "
    "evidence. Before I assert it, I run the check and read its real output: "
    "git ls-remote / git log origin to confirm a push, gh pr list to confirm "
    "a PR, the actual pytest result to confirm tests. I never report a "
    "command's success from a piped exit code — piping through tail/head "
    "gives the pipe's exit, not the command's. If I have not verified it this "
    "turn, I say 'I haven't verified yet', not 'it's done'."
)


def format_unverified_claim_block(findings: list[UnverifiedClaimFinding]) -> str:
    """Pre-response context block when the prior turn claimed a checkable
    state without showing the check. Empty if no findings."""
    if not findings:
        return ""
    high = any(f.severity == "high" for f in findings)
    lines = [
        "## UNVERIFIED-CLAIM WARNING (prior turn) — claimed a checkable state",
        "",
        "My last turn asserted a verifiable external state as fact:",
    ]
    for f in findings[:5]:
        lines.append(f"  - [{f.claim_kind}/{f.severity}] '{f.trigger_phrase}'")
        if f.source_letter:
            lines.append(
                f"      ↳ source: cited in {f.source_letter} — letter "
                "citations carry their own verification requirement before "
                "embedding in substrate-writes."
            )
    lines.append("")
    if high:
        lines.append(
            "At least one fired with NO command run that turn — a pure "
            "assertion. That is the exact shape that has burned this "
            "relationship repeatedly."
        )
        lines.append("")
    lines.append(UNVERIFIED_CLAIM_AFFIRMATION)
    return "\n".join(lines)


__all__ = [
    "UnverifiedClaimFinding",
    "detect_unverified_claim",
    "UNVERIFIED_CLAIM_AFFIRMATION",
    "format_unverified_claim_block",
]
