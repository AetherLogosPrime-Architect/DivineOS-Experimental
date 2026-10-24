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

## Falsifier

A filing command in the merge path prints "build-flow BLOCKED" again, or the new entries let a command through that is not one of these three.
