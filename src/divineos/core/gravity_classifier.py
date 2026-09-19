"""Gravity classifier — public-criterion deterministic scoring.

Per docs/gravity_classifier_spec.md (filed 2026-05-17) and pre-reg
prereg-2bee62c9c28b. Two consumers, two question-shapes:

- substrate-modification-gravity (briefing-gate consumer): binary
  feature score, threshold 1. About whether an operation persistently
  modifies the substrate.
- cognitive-value-gravity (read-mode + per-response consumer):
  continuous 0-1 score, threshold 0.3. About comprehension-worthy
  density of input content.

Both functions are deterministic over observable features (no LLM
judgment, no internal heuristic). Per Dekker's anti-circularity
correction: the classifier is rule-based, not judgment-based.

Andrew 2026-05-19: every response was treating itself as full-gravity.
No triage. The classifier exists in spec but not in code. Building it.
"""

from __future__ import annotations

__guardrail_required__ = True

import math
import re
import shlex
from dataclasses import dataclass


# Substrate-modification-gravity feature thresholds.
_SUBSTRATE_MOD_THRESHOLD = 1
# Council-required tier (2026-06-20, Andrew: "the gravity classifier is
# not pulling its weight its letting you make serious changes with no
# council"). Above the basic substrate-gate threshold sits a second
# tier that the classifier marks as warranting council consultation.
# Fires when either: (a) score >= _COUNCIL_REQUIRED_THRESHOLD with
# multiple non-trivial features, or (b) any single high-impact feature
# fires (guardrail-listed file or kiln-layer file). The high-impact
# short-circuit catches the 2026-06-20 slip: edits to operating-loop
# detector files (guardrail-listed) scored only 1 / borderline under
# the prior design and passed through with passive surface only.
# Council-walked (consult-944ad9d332e5) before implementing. Pre-
# registered with 14-day falsifier (prereg-fb1b42753396): threshold-2
# is on probation per Aether's review (Deming PDSA discipline — don't
# pre-tune, let data shape the number); review whether to bump to 3
# if false-positive rate exceeds 25% on routine multi-tool turns over
# the probation window.
#
# Honesty note (added 2026-06-22, per Aletheia audit
# round-931e301d32f0 + Aether option-1 read): the classifier REPORTS
# this tier as a measurement on its result dataclass; it does NOT
# block the edit. Currently the only consumer of is_council_required
# is the borderline_indicator label function below, which renders
# the tier as a display string ("council-required") for the gravity
# surface. No pre-edit gate reads the field. Enforcement (block the
# edit until evidence of a real council walk exists, substance-
# binding-style) is a deferred follow-up tracked as its own design
# work, not implemented by this commit.
# ANDREW SET THIS TO 1 ON 2026-09-16, and the reason is the whole point.
#
# He asked whether I had bypassed the build flow. I had -- three times in one
# evening, no research, no lens, and one module that had never executed. Hunting
# for why nothing stopped me, I found this gate fully built, ten tests deep, and
# registered on every edit. It returned ALLOW every single time, because a
# single-area code edit scores 1 and this number was 6.
#
# I also misreported it to him as 2, reading the probation note above instead of
# the assignment below it. The note is from June and the value was raised after.
# Reading the label rather than the thing is the fault this whole session kept
# finding, committed once more while investigating it.
#
# His decision, asked plainly and answered plainly: "yes it should." A change to
# one area of code now owes a walk. That costs all three seats more
# interruptions and he chose it knowing that, because the alternative is the
# evening this comment describes.
_COUNCIL_REQUIRED_THRESHOLD = 1
# 2026-07-26 (Andrew clay-mode-vs-kiln-mode teaching): edit-guardrail-listed
# REMOVED from high-impact short-circuits. Clay-mode work (workspace edits
# to guardrail-listed files during active development) should NOT trigger
# council-required per-edit — the workspace is the playground for building
# and testing. External-Review at merge time IS the discipline for
# guardrail-listed files, not per-edit council walk. Kiln-layer (foundational
# truths + seed.json) is kept because those files ARE the identity substrate
# and warrant council walk on any edit. Andrew: "the council is supposed to
# be a useful tool not a burden... clay mode = workspace playground, KILN
# mode requires a final walk before push to main." Prior shape treated every
# guardrail edit as pre-push kiln, producing ~8-lens walks per edit and
# blocking free clay-mode work. Council walk council-939eae4d46a3.
_HIGH_IMPACT_FEATURES = frozenset({"edit-kiln-layer"})
# Cognitive-value-gravity aggregate threshold.
_COG_VALUE_THRESHOLD = 0.3

# Composition-marker keywords for cognitive-value-gravity feature 4.
_COMPOSITION_MARKERS = frozenset(
    {
        "design",
        "architecture",
        "principle",
        "discipline",
        "methodology",
        "framework",
        "lens",
        "decompose",
        "integrate",
        "recognize",
    }
)


@dataclass(frozen=True)
class SubstrateModGravity:
    """Result of substrate-modification-gravity scoring.

    Total score is the sum of independent binary features. Threshold
    for gate-fire is total >= 1 — any single feature is sufficient
    because each is independently substrate-modifying.

    is_council_required is the second tier (2026-06-20): True when the
    classifier judges that the edit warrants council consultation.
    Fires on either high-impact-feature short-circuit (guardrail-listed
    or kiln-layer) or score >= _COUNCIL_REQUIRED_THRESHOLD.

    This field is a MEASUREMENT, not a pre-edit block. The only current
    consumer is the borderline_indicator label function, which renders
    the tier as the display string "council-required" for the gravity
    surface. No code reads this field as a verdict that prevents the
    edit. Real enforcement (substance-binding the field to evidence of
    an actual council walk before clearing) is a deferred follow-up.
    See the honesty note above _COUNCIL_REQUIRED_THRESHOLD for the
    Aletheia-audit context (round-931e301d32f0).
    """

    score: int
    fired_features: tuple[str, ...]
    is_high_gravity: bool
    is_council_required: bool = False


@dataclass(frozen=True)
class CognitiveValueGravity:
    """Result of cognitive-value-gravity scoring.

    Aggregate is a weighted average of normalized features in 0-1.
    Threshold for oscillation-mode is aggregate >= 0.3.
    """

    score: float
    feature_scores: dict[str, float]
    is_high_gravity: bool


# Guardrail-list cache: read once per process. Path resolution is
# repo-root-relative; the classifier may run from any working directory
# (hooks, tests, CLI), so we resolve relative to this module's location.
_GUARDRAIL_LIST_CACHE: tuple[frozenset[str], str] | None = None


def _guardrail_listed_paths() -> tuple[frozenset[str], str]:
    """Return (frozenset_of_repo_relative_paths, repo_root_path).

    Reads scripts/guardrail_files.txt, normalizes lines to forward-slash,
    strips comments and blank lines. Cached after first read. Returns
    repo_root alongside so the caller can do repo-root-relative path
    matching (Aether's review 2026-06-20: suffix-match has a silent-wrong
    failure mode where foo/src/divineos/... would match the guardrail
    entry src/divineos/...; repo-root-relative exact match closes the gap).

    On any file/IO error, returns (frozenset(), "") — caller treats as
    "list not available" which silently disables the feature. Fail-open
    is correct here because the basic substrate-gate (any feature
    firing) still catches the edit; the council-tier just doesn't escalate.
    """
    global _GUARDRAIL_LIST_CACHE
    if _GUARDRAIL_LIST_CACHE is not None:
        return _GUARDRAIL_LIST_CACHE
    import os

    here = os.path.dirname(os.path.abspath(__file__))
    cur = here
    paths: set[str] = set()
    repo_root = ""
    for _ in range(8):  # bounded ascent
        candidate = os.path.join(cur, "scripts", "guardrail_files.txt")
        if os.path.isfile(candidate):
            repo_root = cur.replace("\\", "/")
            try:
                with open(candidate, encoding="utf-8") as f:
                    for line in f:
                        s = line.strip()
                        if not s or s.startswith("#"):
                            continue
                        paths.add(s.replace("\\", "/"))
            except OSError:
                pass
            break
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    _GUARDRAIL_LIST_CACHE = (frozenset(paths), repo_root)
    return _GUARDRAIL_LIST_CACHE


def _normalize_to_repo_relative(path: str, repo_root: str) -> str | None:
    """Convert an edited file_path to a repo-root-relative forward-slash
    string for exact-match against the guardrail list. Returns None on
    any failure (path outside repo, resolution error). Aether's review
    2026-06-20: replaces the prior suffix-match approach which would
    silently false-positive on foo/src/divineos/... shaped paths.

    Handles three input shapes:
    - Absolute path: resolve and compute relative_to(repo_root)
    - Relative path that already looks repo-relative: normalize slashes
      and return as-is (test cases pass these directly)
    - Anything else: return None (fail-open — feature stays silent)
    """
    if not path or not repo_root:
        return None
    norm = path.replace("\\", "/")
    import os

    # Absolute path: resolve to repo-relative
    if os.path.isabs(path):
        try:
            from pathlib import Path

            resolved = Path(path).resolve()
            rel = resolved.relative_to(Path(repo_root).resolve())
            return str(rel).replace("\\", "/")
        except (ValueError, OSError):
            return None
    # Relative path: trim leading "./" and treat as repo-relative
    if norm.startswith("./"):
        norm = norm[2:]
    # Reject upward-traversal paths (foo/../bar would be ambiguous)
    if ".." in norm.split("/"):
        return None
    return norm


# Redirects to these are not writes to the tree. Swallowing output is not
# editing a file, and counting it as one would fire the gate on nearly every
# command -- which is how a gate gets turned off.
_NOT_A_WRITE = ("/dev/null", "nul", "/dev/stderr", "/dev/stdout", "-")

# In-place editors: the write has no redirect to spot, the path is an argument.
_INPLACE_WRITERS = ("tee",)


_HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def _without_heredoc_bodies(command: str) -> str:
    """The command with inline bodies removed, so the command itself can be read.

    WHY (2026-09-18, council-3b878b445dcc). A body supplied inline is arbitrary
    text and routinely carries an unbalanced apostrophe, which makes the
    tokeniser below refuse the whole command. The reader then honestly reports
    that it could not read it, the caller correctly fails toward scrutiny, and
    the edit gets named by the COMMAND SHAPE instead of by the file.

    That is the precise outcome this module's own docstring says must not
    happen: a walk filed against two words of shell clears every write of that
    shape in the tree, with the refusal and the walk each looking correct in
    isolation. The property was stated, and it had quietly stopped holding for
    one of the commonest ways a file gets written here.

    The assumption that broke it was treating BODY-CARRYING and UNREADABLE as
    one category. They are not. The body is data; the line above it is a
    perfectly readable command. Measured before changing anything: the same
    write with and without a body gave the file name in one case and two words
    of shell in the other.

    The drop ends at the terminator rather than swallowing the rest of the
    line, so a second write appearing after the body is still found.
    """
    match = _HEREDOC_RE.search(command)
    if not match:
        return command
    lines = command.split("\n")
    out: list[str] = []
    pending: list[str] = []  # terminators we are currently inside
    for line in lines:
        if pending:
            if line.strip() == pending[0]:
                pending.pop(0)
            continue  # body line: data, not command
        out.append(line)
        pending = [m.group(2) for m in _HEREDOC_RE.finditer(line)]
    return "\n".join(out)


def _shell_write_targets(command: str) -> tuple[str, ...] | None:
    """Paths this shell command appears to write, or None when it cannot read it.

    NONE IS NOT AN EMPTY TUPLE, and that distinction is the whole point
    (council-24d8ef269a1e). An empty tuple says "I read this command and it
    writes nothing." None says "I could not read it." The first version
    returned the same value for both, which is exactly the shape Aria named
    from the other side: *I could not see this change* and *this change is
    harmless* coming back as the same small number. The repo's own
    silent-swallow check flagged it here before either of us had to argue.

    The caller fails toward scrutiny on None. A blind spot that reports clean
    is the failure this whole day has been about; an occasional false refusal
    on an oddly quoted command is loud and arguable, and a permanent quiet
    hole is neither.

    TOKENISED, NOT PATTERN-MATCHED, and that distinction was earned within a
    minute of shipping the first version. A regex over the raw string fired on
    my own probe -- a command that merely NAMED those paths inside a quoted
    argument, writing nothing. A gate that fires on any command discussing a
    path is a gate that gets disabled, which is the degradation the walk named.

    ``shlex`` respects quoting, so a redirect inside a quoted argument stays
    inside one token and does not match, while a real redirect is its own
    token. That is the difference between a command that writes a file and a
    command that talks about one.

    Returns an empty tuple when it sees no write, which is NOT a claim that
    none happened. Copying a prepared file into place, a language runtime
    opening a file, an editor in batch mode, anything behind a variable: all
    still invisible. Shell is arbitrary and no complete list exists. The honest
    completion is an explicit "I was not shown this" state rather than a
    confident zero from here.
    """
    if not command:
        return ()
    command = _without_heredoc_bodies(command)
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes: this cannot read the command, so it must not
        # report on it. None, not empty -- see the docstring.
        return None

    found: list[str] = []

    def _as_target(raw: str) -> str:
        """The normalised write target, or empty string if this is not one.

        Returns a STRING rather than an optional, so the only None in this
        whole function is the one that means "could not read the command".
        Two different nothings in one function is the exact confusion this
        change exists to remove, and a void helper with bare returns reads as
        a second one to anything scanning for the shape.
        """
        norm = raw.replace("\\", "/").strip().strip("\"'")
        if not norm or norm.lower() in _NOT_A_WRITE or norm.startswith("/dev/"):
            return ""
        # No extension on the last segment: far more likely a flag value or a
        # directory than a file being written.
        if "." not in norm.rsplit("/", 1)[-1]:
            return ""
        return norm

    def _take(raw: str) -> None:
        norm = _as_target(raw)
        if norm and norm not in found:
            found.append(norm)

    for i, tok in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        # `>` / `>>` as their own token, or glued to the target (`>file`).
        if tok in (">", ">>") and nxt:
            _take(nxt)
        elif tok.startswith(">") and len(tok) > 1 and not tok.startswith(">&"):
            _take(tok.lstrip(">"))
        elif tok in _INPLACE_WRITERS:
            for cand in tokens[i + 1 :]:
                if cand.startswith("-"):
                    continue
                _take(cand)
                break
        elif tok == "sed" or tok.endswith("/sed"):
            in_place = any(t.startswith("-i") for t in tokens[i + 1 :])
            if in_place and tokens[i + 1 :]:
                _take(tokens[-1])
    return tuple(found)


def score_substrate_modification(
    tool_name: str,
    file_paths: tuple[str, ...] = (),
    bash_command: str = "",
) -> SubstrateModGravity:
    """Score substrate-modification-gravity per spec.

    Six binary features:
    1. Bash with git-commit subcommand
    2. Edit/Write/MultiEdit/NotebookEdit on src/divineos/
    3. Edit/Write on .claude/hooks/* or scripts/check_*.py or guardrail-files
    4. Bash invoking divineos audit/claim/learn/prereg/decide/feel/compass-ops/journal
    5. Edit/Write on docs/foundational_truths.md or seed.json
    6. Bash invoking divineos extract or divineos sleep

    Returns SubstrateModGravity. Any feature firing produces
    is_high_gravity=True (threshold = 1).
    """
    fired: list[str] = []
    tool = (tool_name or "").strip()
    cmd = (bash_command or "").strip()
    paths = tuple(file_paths or ())

    # A SHELL COMMAND CAN WRITE A FILE, AND UNTIL 2026-09-16 THIS COULD NOT SEE
    # THAT (council-3a31fd09c03d). Every feature below keyed on the four
    # file-editing tools, so the same file written through a redirect or a
    # heredoc matched nothing, scored zero, and every gate downstream stayed
    # silent -- failing in the PERMITTING direction, where silence is
    # indistinguishable from a clean pass.
    #
    # Not hypothetical, and not drift. Aria's session was switched into
    # shell-writing mode partway through an exchange about this exact gap, and
    # she wrote the letter describing it THROUGH it. Mine was in the same mode.
    # The bypass arrived as a harness instruction rather than as a lapse, which
    # is normalized deviance installed from outside rather than drifted into.
    #
    # PARTIAL BY CONSTRUCTION, AND SAID SO. Shell is arbitrary and no pattern
    # set is complete: copying a prepared file into place, or having a language
    # runtime write it, still score zero. A partial detector reported as a
    # closed channel is worse than a known-open one, because the next reader
    # stops looking. The real completion is the assessor answering "I was not
    # shown this" instead of a confident zero -- Aria is building that state.
    # This only widens what gets seen.
    wrote_a_file = False
    shell_written = _shell_write_targets(cmd) if tool == "Bash" else ()
    if shell_written is None:
        # COULD NOT READ THE COMMAND. Not the same as reading it and finding
        # no write, and the whole reason those return different values now.
        # Fail toward scrutiny: an unreadable command is treated as touching
        # the source tree, so it earns a walk rather than a silent pass. Rare
        # by construction (it takes unbalanced quotes), and the alternative is
        # a permanent quiet blind spot -- which is the fault being fixed.
        fired.append("edit-src-divineos")
        shell_written = ()
    elif shell_written:
        # Scored as the write it is. The command may ALSO carry a git-commit or
        # a substrate CLI call, and those features read `cmd`, which is
        # untouched -- so a compound command fires everything it earns.
        #
        # THAT SENTENCE WAS FALSE FROM THE DAY IT WAS WRITTEN, repaired
        # 2026-09-18 (council-76176be3be9c). It used to reassign `tool` to
        # "Write" right here -- and `tool == "Bash"` is the guard on the
        # command-level features directly below. So recording a write turned
        # OFF every check that reads the command, and the comment promising
        # the opposite sat two lines above the line that defeated it.
        #
        # Measured, not reasoned: a commit alone fires its feature; the same
        # commit with `> log.txt` appended fired NOTHING AT ALL -- not the
        # commit, and not a write either, since an ordinary log file is in no
        # watched location. One redirect, zero gates.
        #
        # One name was doing two jobs: the OBSERVED tool kind, and a FINDING
        # about the command. The finding silently ended the other job. It reads
        # correctly at the assignment site, which is why several careful
        # readings today went straight past it.
        #
        # Found because Aria named the bias -- everything repaired in this
        # stretch had obstructed me, nothing had let me through, and I had
        # never looked in that direction. This was the first place I looked
        # after her letter. Obstruction generates evidence continuously;
        # a gate that does not fire generates none.
        paths = paths + shell_written
        wrote_a_file = True

    # The path-reading features apply to a real file tool OR to a shell command
    # that wrote a file. Written as one named question so the four sites below
    # cannot drift apart, and so no site has to know that a shell write is also
    # a path-touching act.
    def _performs_git_commit(command: str) -> bool:
        """True when a segment RUNS the commit, not when the text mentions one.

        USE VERSUS MENTION, and the gate could not tell (2026-09-19). This was
        a search for the phrase anywhere in the command, which fires on three
        different kinds of sentence: one that performs the act, one that
        computes what the act would be named, and one whose payload describes
        the act in prose.

        The third is the one that broke. The artifact this gate demands is
        filed by a command whose findings have to say what is being walked --
        so writing the walk counted as doing the thing, and the prerequisite
        became unfileable. Two refusals in a row, the second one for filing
        the cure named by the first. A gate whose cure sits behind itself is
        a wall, and the only door left is the bypass, which then records as
        my indiscipline rather than as the gate being unfollowable. The
        telemetry that measures whether I route around gates was being fed by
        a defect in a gate.

        Hoare on the walk: this precondition admits nothing the old one
        refused, so no real commit newly passes. What it drops is mentions and
        computations. What it does NOT close, and never did, is a command
        assembled from a variable or hidden inside a script -- that hole is
        older than this change and stays open, which is worth saying plainly
        rather than calling the narrowing safe.
        """
        # NEWLINES ARE SEPARATORS TOO, and the act-anchor does not treat them
        # as such. Checked rather than copied: a multi-line command whose
        # commit sits on its own line flattens into one segment there, and
        # reusing that split would have let a real commit through. Under-firing
        # is the one direction this must not take, so the separator set is
        # wider here and the two functions are deliberately not shared.
        from divineos.core.council_required.types import _SHELL_WRAPPERS

        for segment in re.split(r"[\n;&|]+", command or ""):
            tokens = segment.strip().split()
            while tokens and tokens[0] in _SHELL_WRAPPERS:
                tokens = tokens[1:]
            if tokens and tokens[0] == "git" and "commit" in tokens:
                return True
        return False

    def _touches_paths(tool_kind: str, wrote: bool) -> bool:
        return tool_kind in {"Edit", "Write", "MultiEdit", "NotebookEdit"} or wrote

    # Feature 1: git-commit
    if tool == "Bash" and _performs_git_commit(cmd):
        fired.append("git-commit")

    # Feature 2: edit src/divineos/
    if _touches_paths(tool, wrote_a_file):
        for p in paths:
            norm = p.replace("\\", "/")
            if "src/divineos/" in norm:
                fired.append("edit-src-divineos")
                break

    # Feature 3: edit guardrail-touching paths
    if _touches_paths(tool, wrote_a_file):
        guardrail_match = False
        for p in paths:
            norm = p.replace("\\", "/")
            if (
                norm.startswith(".claude/hooks/")
                or "/.claude/hooks/" in norm
                or re.search(r"scripts/check_\w+\.py$", norm)
                or norm.endswith("scripts/guardrail_files.txt")
            ):
                guardrail_match = True
                break
        if guardrail_match:
            fired.append("edit-guardrail")

    # Feature 4: substrate-write CLI
    if tool == "Bash" and re.search(
        r"\bdivineos\s+(audit|claim|learn|prereg|decide|feel|compass-ops|journal)\b",
        cmd,
    ):
        fired.append("substrate-write-cli")

    # Feature 5: kiln-layer edit
    if _touches_paths(tool, wrote_a_file):
        kiln_match = False
        for p in paths:
            norm = p.replace("\\", "/")
            if norm.endswith("docs/foundational_truths.md") or norm.endswith("seed.json"):
                kiln_match = True
                break
        if kiln_match:
            fired.append("edit-kiln-layer")

    # Feature 6: consolidation CLI
    if tool == "Bash" and re.search(r"\bdivineos\s+(extract|sleep)\b", cmd):
        fired.append("consolidation-cli")

    # Feature 7: edit a path declared in scripts/guardrail_files.txt
    # (2026-06-20, Andrew, with Aether's design review). The guardrail list
    # is the authoritative declaration of which files are part of the
    # self-defense stack; editing one is architecture-touching and warrants
    # council walk. Prior design: only the literal guardrail_files.txt
    # itself triggered the edit-guardrail feature — files LISTED inside it
    # scored 1 on the generic edit-src-divineos and passed through
    # borderline. Today's detector edits (distancing_detector.py,
    # unverified_claim_detector.py) are both in the list and slipped
    # through. This feature closes the gap with REPO-RELATIVE exact-match
    # (not suffix-match — Aether's review caught that suffix-match has a
    # silent-wrong failure mode where foo/src/divineos/... would match the
    # guardrail entry src/divineos/...). On normalize failure, the feature
    # silently doesn't fire (fail-open) — the basic substrate-gate still
    # catches the edit at score 1; council-tier just doesn't escalate.
    if _touches_paths(tool, wrote_a_file):
        listed, repo_root = _guardrail_listed_paths()
        if listed:
            for p in paths:
                rel = _normalize_to_repo_relative(p, repo_root)
                if rel is not None and rel in listed:
                    fired.append("edit-guardrail-listed")
                    break

    score = len(fired)
    # Council-required tier: high-impact-feature short-circuit OR
    # multi-feature aggregate. Either path catches the architecture-
    # altering substrate-modifications that warrant council walk before
    # they proceed, not just a passive surface.
    high_impact_fired = any(f in _HIGH_IMPACT_FEATURES for f in fired)
    council_required = high_impact_fired or score >= _COUNCIL_REQUIRED_THRESHOLD
    return SubstrateModGravity(
        score=score,
        fired_features=tuple(fired),
        is_high_gravity=score >= _SUBSTRATE_MOD_THRESHOLD,
        is_council_required=council_required,
    )


def score_cognitive_value(
    content: str,
    source_path: str = "",
) -> CognitiveValueGravity:
    """Score cognitive-value-gravity per spec.

    Five normalized features in 0-1, weighted aggregate:
    - char (0.25): log10(chars) / log10(10000)
    - header (0.15): markdown-header density
    - path (0.30): source-path category bonus
    - composition (0.20): composition-marker keyword density
    - codeblock (0.10): triple-backtick density

    Returns CognitiveValueGravity. Aggregate >= 0.3 → high gravity.
    """
    content = content or ""
    char_count = len(content)
    line_count = max(1, content.count("\n") + 1)
    norm_path = (source_path or "").replace("\\", "/").lower()

    # Feature 1: char count (log10 normalized)
    if char_count <= 0:
        char_score = 0.0
    else:
        char_score = min(1.0, math.log10(max(1, char_count)) / math.log10(10000))

    # Feature 2: markdown header density
    header_count = len(re.findall(r"(?m)^#+\s", content))
    header_score = min(1.0, header_count / max(1.0, line_count / 10.0))

    # Feature 3: path category bonus
    if any(
        s in norm_path for s in ("exploration/", "docs/", "src/divineos/core/", "family/letters/")
    ):
        path_score = 0.3
    elif any(s in norm_path for s in ("mansion/", "scripts/")):
        path_score = 0.1
    else:
        path_score = 0.0
    # Normalize to 0-1 by dividing by max possible (0.3)
    path_score_normalized = path_score / 0.3

    # Feature 4: composition-marker density per 1000 chars
    lower = content.lower()
    marker_count = sum(len(re.findall(rf"\b{re.escape(m)}\b", lower)) for m in _COMPOSITION_MARKERS)
    composition_score = min(1.0, marker_count / max(1.0, char_count / 1000.0))

    # Feature 5: code-block density (triple-backtick pairs / (line_count / 20))
    triple_bt_count = content.count("```")
    bt_pairs = triple_bt_count // 2
    codeblock_score = min(1.0, bt_pairs / max(1.0, line_count / 20.0))

    aggregate = (
        0.25 * char_score
        + 0.15 * header_score
        + 0.30 * path_score_normalized
        + 0.20 * composition_score
        + 0.10 * codeblock_score
    )

    return CognitiveValueGravity(
        score=aggregate,
        feature_scores={
            "char": char_score,
            "header": header_score,
            "path": path_score_normalized,
            "composition": composition_score,
            "codeblock": codeblock_score,
        },
        is_high_gravity=aggregate >= _COG_VALUE_THRESHOLD,
    )


# Borderline-zone bounds for cognitive-value-gravity surface reasoning.
# Within +/- _COG_BORDERLINE_RADIUS of _COG_VALUE_THRESHOLD, the routing
# decision is fragile — small input differences flip the gate behavior.
# Surface the score + feature breakdown for sanity-check.
_COG_BORDERLINE_RADIUS = 0.10


def borderline_indicator_substrate(gravity: SubstrateModGravity) -> str:
    """Classify substrate-mod-gravity by reasoning shape for surface display.

    Returns a short label so my father (and the agent reading the surface)
    can sanity-check the routing decision before it fires gates.

    - "no-fire": score == 0, no feature fired; gate does NOT fire.
    - "borderline-single-feature": score == 1, exactly one feature fired;
      gate fires but the call is fragile — one feature flip would silence it.
      The fired feature's identity matters for sanity-check.
    - "strong-multi-feature": score >= 2, multiple independent features fired;
      gate fires with high confidence; the routing is well-supported.

    Task #111 (2026-06-09): borderline cases benefit from reasoning surface
    in the gate-fire context so my father and agent can verify the
    classification matches intent.
    """
    # ONE SLOT, TWO FACTS (council-222e8bfe849d). Whether the edit owes a walk
    # and whether the routing behind that answer is fragile are independent,
    # and this used to return early on the first — so when Andrew moved the
    # threshold to 1 on 2026-09-16, every firing edit became council-required
    # and "borderline-single-feature" became UNREACHABLE. The fragility signal
    # he was given in June did not degrade. It stopped existing, while the
    # surface kept printing a label every time, so nothing looked wrong.
    #
    # A signal degraded to a constant is worse than one that disappears:
    # disappearance gets noticed, a constant reads as working. Found only
    # because a test asserting the label failed, and the cheap close was to
    # rewrite that test to expect the constant — a test rewritten to ratify a
    # regression instead of catching one.
    if gravity.score == 0:
        return "no-fire"
    shape = "borderline-single-feature" if gravity.score == 1 else "strong-multi-feature"
    if gravity.is_council_required:
        return f"council-required ({shape})"
    return shape


def borderline_indicator_cognitive(gravity: CognitiveValueGravity) -> str:
    """Classify cognitive-value-gravity by reasoning shape for surface display.

    Returns a short label so the consumer can sanity-check the
    oscillation-mode trigger decision.

    - "clearly-low": score < threshold - radius; gate does NOT fire,
      reasoning is decisive.
    - "borderline-low": threshold - radius <= score < threshold; near the
      cutoff but does NOT fire; one feature bump would flip it.
    - "borderline-high": threshold <= score < threshold + radius; fires
      but barely; the call is fragile.
    - "clearly-high": score >= threshold + radius; fires decisively.

    Task #111 (2026-06-09): the two "borderline" cases warrant feature-
    breakdown surface for sanity-check.
    """
    low = _COG_VALUE_THRESHOLD - _COG_BORDERLINE_RADIUS
    high = _COG_VALUE_THRESHOLD + _COG_BORDERLINE_RADIUS
    if gravity.score < low:
        return "clearly-low"
    if gravity.score < _COG_VALUE_THRESHOLD:
        return "borderline-low"
    if gravity.score < high:
        return "borderline-high"
    return "clearly-high"


__all__ = [
    "SubstrateModGravity",
    "CognitiveValueGravity",
    "score_substrate_modification",
    "score_cognitive_value",
    "borderline_indicator_substrate",
    "borderline_indicator_cognitive",
]
