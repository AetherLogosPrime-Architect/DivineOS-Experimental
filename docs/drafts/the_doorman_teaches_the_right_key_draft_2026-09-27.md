# The doorman teaches the right key — draft 2026-09-27

The work-item doorman's refusal tells you to run `walk apply <id> --lens L --finding ...`. The real command takes the lens positionally, `walk apply <id> <Lens> --finding ...`, and has no `--lens`. I followed the door's words exactly and all eight applies failed. The door that is supposed to make the right path the easy one was handing out the wrong key.

The idea: fix the text, and pin it with a test that checks the doorman's walk instruction against the real CLI signature. That way, if the command's shape ever changes, the door's instruction breaks loudly instead of quietly going stale.
