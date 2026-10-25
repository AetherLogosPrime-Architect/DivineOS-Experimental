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

## Falsifier

A filing command in the merge path prints "build-flow BLOCKED" again, or the new entries let a command through that is not one of these three, or a CONFIRMS in his name passes without the paperwork.
