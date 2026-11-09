# Integrating a correction reads dot-directories and says why it refuses (draft, 2026-11-09, Aria)

Status: DRAFT. Tests first, walk in the chat, Aether's read, then code.

## What happened

Marking off Dad's oldest open asks with `divineos andrew-correction integrate`, two rows (287, 288) were refused with evidence that named `.claude/hooks/work-item-doorman.sh` and `.claude/hooks/lib/remedy_allowlist.sh`, both of which exist. The refusal line read `Refused correction #287:` followed by nothing. I re-ran the reality check by hand and it answered `not-found: none of these name anything that exists: claude/hooks/work-item-doorman.sh, ...`.

## Two faults, one cause each

1. **The leading dot is dropped.** `_candidate_pointers` in `src/divineos/core/andrew_correction_tracker.py` finds file paths with `\b[\w/\\._-]+\.(?:py|md|sh|...)\b`. `\b` needs a word character on one side, and a `.` at the start of a token has none, so the match starts after the dot: `.claude/hooks/x.sh` becomes `claude/hooks/x.sh`, a path that does not exist, and a true pointer is refused as absent. Every `.claude/` file, `.github/` file and dotfile is affected, and this repo keeps its hooks and skills under `.claude/`.
2. **The refusal explains nothing.** `explain_integrate_refusal` checks length, the shape of the evidence and whether the row is open, and returns an empty string for everything else. `integrate()` has a fourth way to refuse, `artifact_reality(...) == "not-found"`, which the explainer never asks. Its own docstring says it "returns empty on the happy path", so an empty reason after a refusal reads as if nothing was wrong. A refusal that says nothing sends the next person to guess, and I guessed wrong twice before reading the code.

## The change

1. The path pattern uses a lookbehind that allows a leading dot: a token starts where the previous character is not part of a path, and may begin with `.`. Same change in the shape check (`_ARTIFACT_PATTERNS`) so both agree.
2. `explain_integrate_refusal` calls `artifact_reality` and returns its detail when it says `not-found`, with the tokens it tried, so the person sees what was looked up.
3. A refusal is never printed with an empty reason: the CLI prints a fixed fallback ("refused for a reason the explainer could not name") if the explainer returns nothing, so a blank can never reach him again.

## Corrections found after the walk (walk-3dcd78d91542), same day

- **A third place has the same fault, in a different file.** My walk said only two copies of the path pattern existed and both sat in this one file. I had searched for one spelling of the regex. `src/divineos/core/closure_verification.py` has its own `_RE_FILE = ^([\w/_-]+\.(?:py|md|...))(?::(\d+))?$`, whose character class has no `.`, so a leading dot, or any dotted folder name, is "not a file-citation form" even after the extractor keeps the dot. The extractor fix alone would still refuse `.claude/...` evidence. Both must change, and a test must run the whole path: evidence text in, `artifact_reality` out, on a real tracked file.
- **Allowing `.` in that class opens `..`.** `../../elsewhere/x.py` would then be matched and reported `found` if it exists outside the repo. The fix rejects any `..` segment. The check also resolves paths against the current directory, not the repository root, so a pointer is only found when the command runs from the root; the test asserts that and the refusal says so when the file exists only relative to the root.
- **One verdict function** (`integrate_verdict`) decides ok-or-reason for `integrate()` and the explainer alike, per Dijkstra, in place of the explainer re-typing integrate's checks.

## Tests, written first

- A `.claude/hooks/...` path is extracted whole, with its dot.
- A real `.claude/` file in the repo is `found`; a made-up one is `not-found`.
- A path with no leading dot behaves exactly as before.
- Every refusal from `explain_integrate_refusal` is non-empty, including for evidence that passes the shape check and fails the reality check.
- The old failing evidence from rows 287 and 288 is accepted.

## Falsifier

If evidence naming a real dot-directory file is refused after this lands, or any refusal prints an empty reason, the fix is wrong. The guardrail marker on this file (`__guardrail_required__`) means the merge needs an audit round and Dad's yes.
