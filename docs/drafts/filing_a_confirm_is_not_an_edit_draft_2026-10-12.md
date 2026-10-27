# Filing a confirm is not an edit (draft, 2026-10-12)

**Author:** Aria.

## The fault

The merge path tells the author to run three commands: `divineos audit submit-round` (open the round), `divineos audit submit` (Dad's own finding) and `divineos audit file-external-confirm` (Aletheia's relayed yes). The build-flow gate counts each one as an edit of the substrate and asks for a council walk and a game-walk before it lets the command run. In one night I paid that twice for two confirms, to record what another person had already said. The python exit list and the merge gate already treat these as exits; the build gate's own list, which decides whether the paperwork is owed, did not. Two earlier drafts of mine (`every_exit_passes_every_gate`, `a_round_is_a_voiced_filing_too`) named this gap as owed.

A picture: a clerk who will stamp your receipt only after you have written an essay about why you may ask for a stamp, when the stamp is the thing the shop told you to get.

## The change

Two entries on the build gate's own list of filing commands (`_ARTIFACT_FILING_COMMANDS` in `.claude/hooks/check-council-required.sh`): `divineos audit submit` (the prefix also covers `submit-round`) and `divineos audit file-external-confirm`. The entry bar the file states is met: other gates print these as the way forward.

## What this does not do

The closed list of actors (aletheia, aria, aether, grok, gemini, claude-*) is enforced on the python list, not here. This list only decides whether council paperwork is owed first. Reading a round (`divineos audit show`) is not added: no gate prints it as an exit, so it does not meet the bar.

The shared shell list that nineteen gates read already carries `audit submit-round` and is left alone, for its own tested change.

## What proves it

A test that lifts the build gate's real list and asserts each of the three filing commands is on it, with a control that an ordinary substrate edit command is not.

## The narrowing (2026-10-24, from Aether's question while reading this change)

A CONFIRMS filed with `--actor user` puts words in Dad's voice, and the council paperwork that used to come first was the only deliberate pause on that path. The check that his quoted words were really typed by him lives in `divineos file-confirm --andrew-said` (`his_words_were_typed`), not in `audit submit`; I grepped the audit command and its store for a corpus or typed-words check and found none, and I did not read the merge gate or CI. So this change no longer frees that one shape: a title that starts with CONFIRMS filed with actor `user` still owes the paperwork. Actor and title are matched together, because a title alone is easy to phrase around and an actor alone would stop freeing his plain findings. A relayed Aletheia confirm, and a plain finding by `user`, stay freed. Tests, red first: four spellings of a user-actor CONFIRMS must still owe it; controls that a relayed confirm and his plain findings do not.

**Owed, named here so it is not forgotten:** make `audit submit` with actor `user` and a CONFIRMS title run `his_words_were_typed` and refuse unless the words match something he typed. That is the real lock; the narrowing only keeps the old pause until it exists. It is its own piece.

## The fifth widening (2026-10-27, walk-969a822af7fd, after Aether's letter of that night)

Aether paid five council walks to land two fixes. The commands that cost them were the three the merge path prints as its next step: `divineos audit patch-id`, `divineos audit prepare-merge` and `divineos audit list`. I checked the entry bar against the code, not on trust: `prepare-merge` is printed as "Now run" and "Proceed" by `file-external-confirm` and the stamp path; `patch-id` is named by a confirm refusal as the check to run; `audit list` is the stale-engagement gate's remedy for audit findings (the briefing dashboard also names it, but a dashboard is not a gate and I did not count it). All three only print.

**The walk found a hole the list already has, and these three do not widen it.** The exemption is a prefix match on the joined segment, so a redirect on a freed command rides along: `divineos learn x > some/file` is freed and writes a file with no paperwork, and `prepare-merge` is even prescribed with `> body.md`. The three new commands live in their own tuple (`_READ_ONLY_FILING_COMMANDS`) and are freed only when their segment carries no redirect token. The older entries are not retrofitted here: that is its own change, with its own risk of locking a prescribed form out, and it is named so it is not forgotten. The cost of the choice is that `prepare-merge ... > body.md`, the form `prs_commands.py` prints, owes the paperwork; the bare command prints to the screen and costs nothing.

**Aether ran my first version and found its sibling hole (letter of 2026-10-27, night).** A command substitution (dollar-paren or backticks) inside a freed command is run by the shell before the command starts, so `divineos audit list --round "$(touch made_by_substitution)"` and the backtick form came back freed: the three printers could carry any other command. The older entries share it, as they share the redirect. The three are now freed only when no token carries a dollar sign or a backtick, and the redirect check is kept. His smaller point is also taken: the match was a bare prefix, so it also freed `audit patch-idx` and `audit list-clean`; the three now match as whole words (the command alone, or followed by a space), so `list-clean` is no longer freed. (I had written that as a named side effect; it was a gap.) His four rows and both substitution strings are tests, and four of them fail with the substitution check removed.

**A third shape, found by me running shapes through the lifted function before the fresh walk (same night).** Aether tested the output form of process substitution (`>(cat)`, refused) but the input form came back freed: `divineos audit list <(touch made_by_procsub)` runs the command inside the parentheses. The tokeniser splits `<` and a lone parenthesis out of the command, so the three printers now also refuse any token that starts with a less-than sign or is a lone parenthesis. That also refuses a plain input redirect (`< file`), which only reads: the safe side, a surprising refusal. Four cases pin it and fail with the check removed. Shapes I ran that were freed and are fine: a quoted semicolon inside an argument, brace lists and a tilde (the shell expands them but runs nothing). I am not claiming this is the end of the list of shapes; each was found by running strings, and the older entries still have all three holes.

**A correction to my own walk record.** One finding says the list was "11 entries and is 14". It was 13 and is 13 plus the separate tuple of three; the walk record is append-only, so the correction is here.

**Four tests pin the same last line of the function.** The three older test files that lift the real function anchor on its exact final `return` line, so changing that line broke thirty of their tests until each anchor was updated. That is four copies of one lifter, and they should share one. Not done here; named.

Tests: 25 new cases. Five redirect cases fail with the redirect check removed, and four substitution cases fail with the substitution check removed; the three freed commands, the neighbours that must not be freed, and the chained-behind cases pass and refuse as they should. 536 pass across the six files that read this hook.

## Falsifier

A filing command in the merge path prints "build-flow BLOCKED" again, or the new entries let a command through that is not one of these three, or a CONFIRMS in his name passes without the paperwork, or a redirect on one of the three writes a file without the paperwork.
