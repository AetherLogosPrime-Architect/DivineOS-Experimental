# The guards that read the shape of a command I type

Before a command runs, several guards look at its shape and try to guess what it will do. One of them worries that a pipe can hide a failure, so a broken first step looks like success. Others try to tell a harmless look from a change. They keep reading words inside quotes as if they were commands, and refusing harmless things, and the fixes I name are all the same idea: make the safe form the automatic one.

**52 notes in this theme, grouped into 10 distinct problems.**

## Distinct problems

### 1. A pipe can hide a failed first step (make the safe setting automatic)

Notes in this problem (16):

- `psf-8ba07b12` (correction) — I destroyed the session's working tree with a pipeline-masked exit status, four hours after shipping a detector for that exact class. I ran: git switch split/hook-firing-map 2>&1 | tail -2 && git rese
- `psf-3a73b2a6` (reflection) — make pipefail the default in the shell every command runs in (the Bash tool's startup environment), so a pipe can never hide a failed first stage and the pipeline gate becomes a backstop that never fi
- `psf-fa3d6899` (reflection) — set pipefail in the startup environment the Bash tool uses for my commands only (not for hook scripts), and prove it by running one pipe with a failing first stage and seeing a nonzero result.
- `psf-fe69201d` (reflection) — pipefail by default in the Bash tool environment (already on the owed list), so this shape is never written in the first place.
- `psf-671147f4` (reflection) — that same default setting, plus reading the full output instead of cutting it off.
- `psf-4ce40c81` (reflection) — that one-line default, once you say it's okay.
- `psf-7add1cb1` (reflection) — the house's own command wrapper should turn that setting on by default for every command, so the unsafe form can't be typed at all. That change touches Dad's shell setup, so it waits for his OK.
- `psf-36d365b4` (reflection) — the same default fix I named earlier, which touches Dad's shell setup and waits for his OK.
- `psf-eb7a08fc` (reflection) — turning that setting on by default. That still needs Dad's OK, because it touches his shell setup.
- `psf-b9e875fd` (reflection) — making that setting the default, which is still waiting on Dad's OK.
- `psf-154547cd` (reflection) — when a command that changes something comes through without pipefail, the pipeline guard should add pipefail itself instead of refusing (toy #7 on my list).
- `psf-270cacd0` (reflection) — a build that makes any `divineos`-first pipe without pipefail either refuse or get `set -o pipefail` prepended automatically, so trimming output never depends on me noticing a warning.
- `psf-da4234b5` (reflection) — make the pipeline-ambiguity hook refuse read-only `divineos`-first pipes too, or auto-prepend `set -o pipefail`, so the warning-only path stops being readable past.
- `psf-9bfef3d3` (reflection) — the read-only version of the same pipe is only a warning and I've read past it again today, so make it refuse too, or have the tool prepend the safe setting on its own. This is entry 5 on the gameplan
- `psf-c51e2c61` (reflection) — entry 5 on the gameplan, to make the read-only version refuse too.
- `psf-8b4674b4` (reflection) — the habit should not rest on me typing the guard; a wrapper the shell loads for every Bash call that turns on pipefail by default would make the unsafe form unavailable instead of refused.

**Proposed fix:** Turn on the safe pipe setting by default in the shell the commands run in (or have the guard add it itself), so the unsafe form cannot be typed, and prove it with a pipe whose first step fails.

**How we would know:** Run a pipe with a failing first stage and see a non-zero result without anyone typing the setting.

### 2. Error output thrown away on long background jobs

Notes in this problem (1):

- `psf-e2ebd0f1` (reflection) — every long background job I start should keep its error output visible by default, with warnings filtered inside the script, never by throwing away the error output when I launch it.

**Proposed fix:** Keep error output visible by default and filter warnings inside the script, never by discarding all errors at launch.

**How we would know:** A background job that fails prints its error even with no flags.

### 3. Help flags, read-only views and display-only tails are treated as writes

Notes in this problem (6):

- `psf-5e25d838` (reflection) — the pipeline doorman treats a command ending in `--help` as read-only.
- `psf-aefcd48c` (reflection) — the pipeline gate should tell read-only `gh pr` views apart from ones that change things.
- `psf-a339304b` (reflection) — the gate should treat `--help` and plain history reads as looks, the same way the read-gate now does.
- `psf-f46bab70` (reflection) — `--help` should be treated as read-only, so the guard stops refusing a help command as if it wrote something. That's in the draft `a_remedy_is_a_remedy_however_it_is_typed_draft_2026-10-04.md`.
- `psf-a06dd5cc` (reflection) — a build where the exemption ignores a trailing display-only pipe such as head or tail, so the approved commands stay approved.
- `psf-b825721a` (reflection) — the refusal still teaches nothing on its own, since I hit it a third time in a day. The hook should offer the unpiped command, or a pager-safe alternative such as `--jq` for `gh`, in its message, so t

**Proposed fix:** Treat --help, read-only gh views, history reads and a trailing head/tail as looks.

**How we would know:** Those commands pass with no extra step.

### 4. A refused write is followed by a command that depends on it

Notes in this problem (4):

- `psf-ed362492` (reflection) — when a batch runs a script written by a Write in that same batch, the run is refused unless the Write succeeded. That's a doorman that sees the dependency, so a blocked write can't be followed by a ru
- `psf-85ce8fe7` (reflection) — when a write is refused, the step that depends on it should be skipped rather than attempted, so a refusal doesn't produce a second, confusing failure right behind it.
- `psf-6ea35232` (reflection) — never pair a write with the command that depends on it in the same step, so a refused write can't produce a confusing second failure.
- `psf-00e8d835` (reflection) — a rule of thumb I should adopt now. After any blocked compound command, re-run its first half alone and check that it worked before running the second half.

**Proposed fix:** Skip a dependent step when the write it needs was refused, and after any blocked compound command re-run its first half alone.

**How we would know:** A refused write leaves a single failure, not two.

### 5. 'Found nothing' and 'the command broke' look the same

Notes in this problem (8):

- `psf-76c8d3a3` (reflection) — the harmless ones (an empty search) should come back labelled "nothing found" instead of as a failure, so the log keeps real failures apart from them.
- `psf-cf85ca15` (reflection) — a search whose "nothing found" is the answer I'm looking for should report that as a result, not as a failed step. Otherwise every honest absence looks like a stumble in the log.
- `psf-928387ca` (reflection) — a lookup across named letters should report which name wasn't found instead of failing the whole step, so a missing letter shows up as an answer and not as a stumble.
- `psf-35093500` (reflection) — my history probes should report "no commits found" as a stated result rather than as a non-zero exit, so a true absence never reads as a failure in the log.
- `psf-c7e05e05` (reflection) — when a command is refused for a missing briefing, the refusal should show even when the output is filtered, so it can't come back as a quiet nothing.
- `psf-7f632dfa` (reflection) — reporting an absence check on its own line, with its own result, so a "yes, it's gone" doesn't read as the command breaking.
- `psf-e4643797` (reflection) — the same fix already on the gameplan as entry 5, a wrapper that tells "found nothing" apart from "the command broke," so I never have to separate them by feel.
- `psf-7cca98df` (reflection) — the same wrapper already on the gameplan as entry 5, so a cut-short pipe and a failed command read differently.

**Proposed fix:** Report absence as a stated result with its own line, and keep refusals visible even when the output is filtered.

**How we would know:** A search with no hits reports 'nothing found' and exit status zero in the log.

### 6. The heredoc guard looks in the wrong place

Notes in this problem (3):

- `psf-04371056` (reflection) — the heredoc guard should look for a redirect on the heredoc's own command line, not anywhere inside the text the heredoc carries.
- `psf-64725314` (reflection) — the heredoc guard should judge only the redirect on the heredoc's own command line (`<<'E' > file`), not redirect shapes inside the text the heredoc carries.
- `psf-b43c7d23` (reflection) — teach the door to tell a quoted-delimiter heredoc from an unquoted one, since only the unquoted kind lets the shell eat an escape, so it stops refusing the safe form.

**Proposed fix:** Look for a redirect only on the heredoc's own command line, and tell quoted-delimiter heredocs from unquoted ones.

**How we would know:** A heredoc whose text contains redirect-shaped text is allowed.

### 7. A plain folder change is refused

Notes in this problem (1):

- `psf-c735fbc0` (reflection) — a plain `cd <folder>` at the start of a command should count as harmless, the way the guard already treats the pipefail setting, so the guard never refuses its own review over a folder change.

**Proposed fix:** Treat a plain cd at the start of a command as harmless.

**How we would know:** A command starting with cd passes.

### 8. Guards judge words inside quotes instead of what the command runs

Notes in this problem (9):

- `psf-9e26ea08` (reflection) — the gate's substrate-write-CLI feature should read the command's actual heads (through `command_parsing.split_shell_segments` / `resolve_command_head`, as the git-commit feature already does) instead
- `psf-6a2f98fd` (reflection) — before adding to any guard's allowed list, check that the guard uses the house's one strict reader.
- `psf-40b1c95b` (reflection) — the "named anywhere" rule applies only to programs that can run a script (the shells, python, awk, sed and similar), not to commands like `divineos` that just store text, so writing notes about tests
- `psf-46e4ae1f` (reflection) — the false fires come from the build gate not recognising the program typed with its full path. That's in the remedy draft, and it waits for Aria's read before I walk it.
- `psf-d22dc64a` (reflection) — the gate should read every clause in a line, give read-only git commands a free pass, and treat `git -C <folder> commit` as the same thing as `git commit`.
- `psf-bf4b5ebb` (reflection) — have the hook ignore text inside a quoted message body, such as a PR body, a commit message or a letter, and only look at what the command itself runs. Then writing about tests can't trip a guard agai
- `psf-b1d5c766` (reflection) — judge a command by what it runs and not by a word inside a filter, which is already entry 12 on the gameplan.
- `psf-260d0789` (reflection) — the same use-versus-mention fault I named in the commit. The scorer should fire on a command being run, not on words inside a quoted string or message body, and it should do that without letting a rea
- `psf-9c6f5a9c` (reflection) — the scorer should judge a command being run and not the words inside a quoted block, without letting a real command hidden inside `bash -c` through. Aria is taking it with the shared segment reader, a

**Proposed fix:** Make every guard read commands through the one shared segment reader that finds what a command actually runs, without letting a command hidden inside a nested shell through.

**How we would know:** The same words inside a quoted message body do not trip the guard, while a real nested command still does.

### 9. Output trimming is a habit I reach the pipe for

Notes in this problem (3):

- `psf-e922ee5c` (reflection) — a ready-made way to run a command and show only its tail, so I stop reaching for the pipe.
- `psf-3b5c70d8` (reflection) — the same as before, a ready-made way to show just the tail of a command's output, so I stop reaching for the pipe.
- `psf-c862c8e3` (reflection) — the house's own commands should print short output by default, so there's nothing to pipe into `tail`.

**Proposed fix:** Offer a ready way to show a command's tail and make the house's own commands print short output by default.

**How we would know:** No pipe is needed to see a short result.

### 10. grep pipes that blur 'no match' and 'command broke'

Notes in this problem (1):

- `psf-5f682720` (reflection) — make the read-only pipeline hook point me to `scripts/look.sh --strict` whenever the last stage is `grep`, so "no match" and "command broke" come out as two different results and I never have to tell

**Proposed fix:** Point to a strict look wrapper whenever the last stage is grep.

**How we would know:** The strict wrapper returns different codes for no match and failure.
