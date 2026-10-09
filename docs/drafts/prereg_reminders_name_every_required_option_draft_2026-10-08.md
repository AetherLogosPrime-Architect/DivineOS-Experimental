# The pre-registration reminders name every required option (draft, carried onto the branch 2026-10-08 from the cloud helper's own description)

Written by the cloud helper in the pull request body; copied here so the idea sits on the branch where a reader can find it.

## The idea

A recipe card lists three ingredients for a dish that needs four. Anyone who follows it exactly gets turned away at the door. The command for filing a pre-registration needs `--claim`, `--success`, `--falsifier` and `--embarrassing`, and two places that teach it left some out. This fills in the cards and adds a test that reads the real list of options from the command, so the cards cannot fall behind again.

## Addresses

`psf-e7c4b468` (the prereg skill should list every required option) and `psf-65c6f7db` (put the missing required option in the build flow's prereg reminder so the first call is complete). Mechanical repair from round two of the sorted pile; classification in `docs/pile_sorting/output/CLASSIFICATION.md` on branch `cloud/pile-sorting-2026-10-08`.

## How we would know

The new test reads the required options from the real `prereg file` command and checks the obligations reminder and the skill's filing example each name all of them. A control test proves the reader can find a known option. It fails before the change and passes after. Aletheia checked it against the real code on 2026-10-08.

## Limits

No guard, hook, gate or doorman changes behaviour. Wording and a test only.
