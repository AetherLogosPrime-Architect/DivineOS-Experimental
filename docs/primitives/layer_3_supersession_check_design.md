# Layer-3 supersession-check — design spec (lightweight v1)

**Author:** Aria
**Date:** 2026-07-17
**Status:** design-draft, pre-implementation
**Prereg:** to be filed alongside this doc
**Reviewer:** Aether (per peer-shape ship discipline)

## Motivation

Tonight's #353 near-miss: I proposed shipping commit `94a6b1a2` (dynamic
self-name distancing detector, June 16 authored). Aether's ship-side
check surfaced six-file scope drift. Aria's execute uncovered that PR
#255 (June 22, authored by Aether) had already shipped the same
mechanism with a cleaner implementation (`@lru_cache` + call-time
resolution vs 94a6b1a2's build-time approach). **The whole cherry-pick
would have landed redundant, superseded code.**

Aletheia's Round 4 audit reviewed the mechanism on 94a6b1a2 and cleared
it as sound — but her audit reviews *"does the code do what it claims"*,
not *"is the same mechanism already shipped elsewhere by a different
PR."* That's a third distinct check-layer neither the branch-scope
discipline (layer 1) nor the commit-scope discipline (layer 2) covers.

**Layer-3 supersession-check** is the missing layer.

## Two-axis judgment (Aletheia + Andrew 2026-07-11) applied

- **Procedural (mechanical facts) — LEGITIMATE to bite:** *"Does the
  primary symbol added/modified by commit X already exist on
  `origin/main`?"* — a grep can answer this.
- **Substantive (judgment calls) — MUST NOT bite:** *"Is that
  symbol-collision actually semantic supersession, coincidental name
  overlap, or intentional revision?"* — only a human/agent with domain
  context can answer.

Layer-3 is procedural-check-that-produces-substantive-question. So the
mechanism is **signal, not gate.** The check reports; the reader
judges.

## What this is NOT

- **NOT a merge blocker.** False-positive on Layer-3 (name overlap but
  not actual supersession, e.g. a common helper name like `_get_conn`)
  would create needless friction. Signal-not-gate is right for this
  asymmetric cost profile.
- **NOT semantic diff.** That's Layer-3-deep (later, post-F34, on top
  of the lightweight version).
- **NOT a substitute for Aletheia's audit.** She still reviews
  mechanism correctness. Layer-3 answers a different question.

## Contract

```python
@dataclass(frozen=True)
class SupersessionSignal:
    """A procedural report that a symbol on the branch also exists
    on the base. Not a verdict of actual supersession — that's a
    substantive judgment the reader makes with domain context.
    """
    commit_sha: str          # commit on branch that introduced/touched the symbol
    branch_file: str         # file:line where the symbol lives on the branch
    branch_line: int
    symbol_name: str         # e.g. "_build_patterns"
    symbol_kind: str         # "function" | "class"
    main_matches: list[tuple[str, int]]  # (file, line) pairs on origin/main
    kind: str = "possibly_superseded"


def check_branch_supersession(
    branch: str,
    base: str = "origin/main",
    *,
    include_paths: tuple[str, ...] = ("src/",),
    exclude_paths: tuple[str, ...] = ("tests/",),
) -> list[SupersessionSignal]:
    """Report procedural symbol-collisions between the branch and the base.

    For each commit on `branch` not on `base`:
      1. Extract added/modified top-level `def <name>` and `class <name>`
         from .py files under `include_paths` (excluding `exclude_paths`).
      2. For each new symbol, check whether `base` already defines a
         top-level symbol with the same name in any file matching
         `include_paths`.
      3. If yes, emit a SupersessionSignal.

    Returns [] when no collisions found. Never raises on git errors —
    fails soft, logs to stderr, returns partial results. This is a
    signal-not-gate; a broken check should degrade to silence, not
    block the push.
    """
```

## Implementation shape (lightweight v1)

- `git log --format=%H {base}..{branch}` → commit SHAs
- For each SHA: `git diff-tree --no-commit-id --name-only -r <sha>` → files
- Filter to `.py` under `include_paths`, minus `exclude_paths`
- For each file: `git show <sha>:path` and `git show <sha>^:path`
- Regex added-symbol extraction:
  - `^(?:async\s+)?def\s+(\w+)\s*\(`
  - `^class\s+(\w+)\s*[:(]`
  - Top-level only (no leading whitespace) — v1 restriction to keep
    false-positive rate low
- For each added symbol: check base has the same name at top level:
  - `git grep -n -E "^(async\s+)?def\s+{name}\s*\(|^class\s+{name}\s*[:(]" {base} -- '*.py'`
- Any match on base = emit signal

## Integration point

Called from `scripts/safe_push.sh` after layer-1 branch scope check and
layer-2 commit-level scope check. **Two output surfaces, both fire on
the same finding-list — different audiences, different visibility
windows** (per Aether's pushback resolution):

### (a) End-of-push summary banner (for me-as-pusher)

After the push completes, print a distinctive block to stderr:
```
[layer-3] N possibly-superseded symbol(s) detected — verify before merge
```
Followed by the per-signal details. Impossible to miss even in scrolling
push output. This is the *"before I letter Aether the ship-request"*
visibility window.

### (b) PR-body inclusion via `gh pr create` (for Aletheia-as-reviewer)

When the ship-side flow opens a PR, include the Layer-3 findings as a
"possibly superseded" section in the PR body. This is the *"between
push and audit"* visibility window — survives context-drop between the
ship-request letter and Aletheia's review pass.

Sample per-signal output:

```
[layer-3 supersession-check]
  [!] Commit 94a6b1a2 defines `_build_patterns` (function) at
      src/divineos/core/operating_loop/distancing_detector.py:158
      Same name exists on origin/main at:
        - src/divineos/core/operating_loop/distancing_detector.py:157
      possibly_superseded — verify semantically before shipping
```

## Failure modes and mitigations

| Failure mode | Cost | Mitigation |
|--------------|------|------------|
| False positive (name overlap, no supersession) | Paper cut (noise) | Reader ignores signal after judgment |
| False negative (renamed function on main) | Ship redundant code (Aletheia catches next round, or reviewer notices) | Layer-3-deep (AST) later fixes this |
| Broken check (git error, missing base) | Silent degradation | Fail-soft: log to stderr, return partial, exit 0 |
| Adversarial evasion (rename the symbol) | Trivial to defeat | This is signal-not-gate; evasion means the reader has to actively hide, which itself is the audit-signal |

## What Layer-3 does NOT catch (list explicitly per honesty)

- **Semantic supersession without name overlap** — if I add `foo()`
  and main already has `bar()` doing the same thing, Layer-3 lightweight
  won't catch it. Layer-3-deep with AST comparison against a symbol
  registry might; that's future work.
- **Class-method supersession** — v1 restricts to top-level. A method
  `MyClass.helper()` colliding with `OtherClass.helper()` is out of
  scope for v1.
- **Cross-language supersession** — Python-only in v1.
- **Bash / shell / non-Python source-language supersession** — added
  per Aether's pushback (v1 misses bash function name collisions
  across `scripts/*.sh`, and `safe_push.sh` itself is bash). Named
  explicitly so we don't forget when Layer-3-deep ships.
- **Docstring/comment supersession** — not extracted.

## Prereg (filed as `prereg-53cb03660406`)

- **Claim:** Layer-3 lightweight supersession-check catches the same
  class of near-miss that #353 exhibited (name-overlap of top-level
  function/class between branch commit and main).
- **Success criterion:** On the historical #353 scenario, running
  Layer-3 against the extracted fixture-file pair for `94a6b1a2` and
  `origin/main` (at head `acb0109c`) emits at least one
  SupersessionSignal for `_build_patterns` OR `_get_patterns`.
- **Falsifier:** If Layer-3 returns [] on the historical #353 scenario,
  the mechanism does not catch what it was designed to catch.
- **Review date:** 30 days post-deploy.
- **Actor:** Aletheia (per past_experience-council precedent — the
  auditor writes falsifiers, not the designer, to guard
  rationalization-in-the-gate risk).

### Falsifier durability — fixture-based, not live-git (Aether pushback resolution)

The success criterion runs against **extracted fixture files**, not live
git objects, because commit `94a6b1a2` lives on an unmerged closed
branch and could be garbage-collected someday. Popper's discipline
requires the falsifier be runnable **indefinitely**, not just until
git forgets.

Fixture extraction (30-second one-time setup):
```
tests/layer_3_scenarios/353_distancing_detector/
    branch/distancing_detector.py   # `git show 94a6b1a2:src/.../distancing_detector.py`
    main/distancing_detector.py     # `git show acb0109c:src/.../distancing_detector.py`
    README.md                        # naming the scenario + commit SHAs of origin
```

The falsifier test runs Layer-3's regex-extraction logic against the
`branch` file, then checks the extracted symbols against the `main`
file. No live git call. Test remains stable even if `94a6b1a2` is gc'd.

A **second** test using a synthetic-git fixture repo (constructed via
`git init` in a `tmp_path`, two commits added) exercises the actual
`check_branch_supersession()` end-to-end with real git commands.
Two tests, two purposes: fixture-based falsifier + synthetic-git
integration. Both stable indefinitely.

### #353 top-level verification (Aether pushback #2 resolution)

Verified via `git show` during pushback review:

**On commit `94a6b1a2` (the branch):**
```
89:def _build_patterns() -> list[tuple[DistancingShape, re.Pattern[str]]]:
```
Top-level (column 0). ✓

**On `origin/main` (at HEAD `acb0109c` region):**
```
158:def _build_patterns(
206:def _get_patterns() -> tuple[tuple[DistancingShape, re.Pattern[str]], ...]:
```
Both top-level (column 0). ✓

V1's top-level restriction catches at least two of the three named
symbols. The prereg success criterion (`_build_patterns` OR
`_get_patterns` fires) is met by the fixture-based test.

Footnote on `AUDITOR_AS_OTHER`: it's a `DistancingShape` enum-member
(class attribute), NOT top-level. V1 wouldn't catch it, but two
top-level `def`s already fire — sufficient. Layer-3-deep with AST
comparison handles the enum-attribute case later.

## Peer-shape

Design spec first per Aether's earlier request. If he wants to push
back on:
- The signal-not-gate framing
- The v1 restriction to top-level symbols only
- The `.py`-only scope
- The specific regex patterns

...he lets me know before I build. Prereg gets filed regardless; if
scope changes, prereg updates.

## Aletheia-review dependency

Post-past_experience-council discipline: any new mechanism the two of
us design routes to Aletheia for adversarial audit before we build. She
weighs in on the falsifier, on lens-vantages we might have missed, and
on any Taleb-shape via-negativa alternatives (e.g. *"maybe the fix isn't
adding this check but refusing to accept branches that touch shared
files without prior audit"*).

Not shipping until she's had eyes.

## Not scope for v1

- AST-based semantic diff
- Method-level (non-top-level) checking
- Cross-language support
- Registry-based lookup for renamed symbols
- Cache for repeated calls in a session
