# The warden names the doorman, not the doorway — draft (2026-09-26)

From Aether's proof of the reflection room on his own record.

## What he found

A refusal from a doorman inside the router hook (`doorbell-pre-tool-use.sh`) reads *"…[bash .claude/hooks/doorbell-pre-tool-use.sh]: BLOCKED by heredoc_escape: …"*. The key is built from the hook path, so the token became `doorbell-pre-tool-use`, which is the doorway every routed doorman shares, not the one that said no. The room would then ask me to name the door frame. That's the same vagueness the token exists to refuse.

## The shape

In `_key`, a `BLOCKED by <name>` phrase wins over the hook path, so the token is the doorman's own name (`heredoc_escape`, `must_read`, `slashed_ref_path`, …). Hook-path keys remain for hooks that refuse directly, as `work-item-doorman.sh` does.

Pin it with the real shape of the heredoc refusal from today's transcript.

## Choice point

- Which name the token takes: **always the refusing doorman's own name, unless** there isn't one, in which case the hook path, and failing that the first distinctive word.
