# A `cd` cannot move my home (design, before code)

**Written:** 2026-10-22, night. **Status:** design, with the code written beside it as a draft. Aria attacks it first.

## The problem, measured

Three times on 2026-10-22 I ran a Bash line that began `cd <a plain folder> && cp ...` (the folder was `family/letters`). Each time the app reported *"Primary working directory: ...\family\letters (was ...\DivineOS-Experimental)"* for every later call. The consequences were real, not cosmetic: the doorbell exited 127 (`scripts/letter_doorbell.sh: not found`), hooks reported `No module named 'family'`, and a three-gate deadlock followed (a must-read note needed a Read, a hold blocked every tool until the turn ended, and the Stop guard demanded the bell).

It is not new. `docs/drafts/hook_commands_find_the_project_and_bare_letters_are_stamped_draft_2026-10-19.md` records the same on 10-19, with `cd ~/.divineos-shared/letters && ...`, which broke the hook stamper (exit 127) and left letters without their thread footer. That one was filed as a cause of bare letters and nobody built the door on the `cd` itself.

## What I measured about when it happens (and what I do not know)

- **Moved it:** `cd family/letters` (a plain subfolder of the checkout), `cd ~/.divineos-shared/letters` (a plain folder in the shared space). Both are folders that are not the root of a repository.
- **Never moved it, dozens of times:** `cd /c/w-gate`, `cd /c/w-draftskip`, `cd /c/w-bellself` (work copies, each a repository root), and `cd` to the checkout root.
- The one rule that fits every observation: **a top-level `cd` whose target is a plain folder (not a repository root and not where the session already is) moves the app's idea of home.** I have not read the app's source; this is a hypothesis fitted to those observations, and the falsifier below is how it gets corrected.

## The measurement table (2026-10-22, by hand, one `cd` per class, reading the app's "Primary working directory" line after each)

Aria's attack: a rule fitted from three incidents is a hypothesis; a table is evidence. This is the table so far, from a window where the starting folder was the checkout root.

| `cd` target (absolute) | class | primary folder moved? |
|---|---|---|
| `/c/Users/aethe/.divineos-shared` | plain folder outside the checkout, NOT a granted folder | **no** |
| `/c/Users/aethe/.divineos-shared/letters` | folder the app already lists as an additional working directory | **yes** |
| `family/letters` (inside the checkout) | plain folder inside the primary | **yes** (three times) |
| `/c/w-gate`, `/c/w-draftskip`, `/c/w-bellself` (work-copy roots) | repository roots, not on the app's list | **no** (dozens of times) |
| the checkout root | the primary itself | **no** |
| `/c/w-draftskip/docs` | not yet measured (predicted no) | n/a |

**This replaces my first hypothesis.** The repository-root idea fitted the data but not for the right reason. The cleaner fit: *the app moves its primary folder when the shell lands in a folder it already knows as a working directory (inside the primary, or one of the additional ones) and that folder is not the primary itself.* That also explains why the `.divineos-shared` parent did nothing while its child did. It is still a fit to six rows, not a reading of the app.

**The way back, measured the same day:** while Bash was held by the folder drift (every Bash call refused by hooks that walk up from the wrong folder), one PowerShell `Set-Location` back to the checkout root put the primary folder back. The tool without a `cd` gate is the exit, and the refusal text should name it.

## What I tried first, and why it does not count

I wrote a note ("use full paths"). Dad, 2026-08-24, of the heredoc doorman: *"your note saved you but your behavior did not change until after you saw it."* The reach and the intention-not-to-reach arrive together, so a note is not a counterweight. Same class, same cure.

## The cure

A PreToolUse refusal, the same shape as `heredoc_escape` and `slashed_ref_path`: a small check module `core/cd_drift_check.py`, a surface in `core/hook_surfaces.py` registered in the same change, tests that drive the real refusal.

- **Refuses** a Bash command with a `cd` at top level (not inside `( ... )` or a `$( ... )`) whose target resolves to an existing folder that is (a) a strict subfolder of the session's own root, or (b) inside one of the shared homes the app is known to list as working directories (`~/.divineos-shared`, `~/.divineos`, `~/.claude`), other than that home itself. A hook cannot read the app's list, so (b) is a named superset of what I measured, to be corrected by the falsifier. Brace groups, `if`/`for`/`while` bodies, `pushd`, `builtin cd`, `command cd` and `source` of a script that `cd`s count as top level (Aria's attack, 2026-10-22).
- **Says the right path in the refusal**, so the cheap correct move is stated and not hunted for: a full path, `git -C <dir>`, or the subshell `( cd <dir> && ... )`, which cannot move the shell.
- **Allows** the subshell form, a `cd` to a repository root (work copies), `cd -`, a bare `cd`, and any target it cannot resolve (a variable, `~` it cannot expand, a substitution) or that does not exist.

Truth #11 shape (a): take the option away. And (b): the right path (a pair of brackets, a full path) costs no more than the wrong one.

## What it does not do, named so silence is not read as coverage

- A target built at run time (`cd "$X"`) is not judged; it passes.
- It reads the command text only. A script that `cd`s inside itself cannot move the app's folder, so it is out of scope.
- The trigger rule is a hypothesis. If the app moves home for a case this allows, the check is blind to it.

## Falsifier (counted in uses)

Every refusal writes one line to `~/.divineos/cd_drift_refusals.log` (command head, target). If, after this ships, the primary working directory moves on a call the check allowed, or a refused `cd` is shown by test to have been harmless, the rule is misread and this is pulled or rewritten. Reviewed after the next 20 refusals or the first miss, whichever comes first.

## Order

This note -> Aria attacks it -> walk -> tests first (failing without the check), then the check -> Aria's reading -> audit.
