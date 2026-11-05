# The bell-alive hold moves into the Stop router (draft, 2026-11-04)

**The idea.** The hold that refuses a reply while my letter bell is not listening is a standalone Stop
script, one of 23 separate processes beside the single router. Each standalone door's refusal reaches me
twice (once as "Stop hook feedback", once as "Stop hook blocking error", the same words); the router's
reaches me once. Aether measured the doors (24 registered Stop hooks, one the router) and is folding them in
one at a time. This is the second: the bell-alive hold, which is mine and shares no helper with the others.
Dad asked for a real dent in the hooks today.

**What changes.** The judgement moves to `core/doorbell_alive.py`, unchanged (same heartbeat files in, same
words out) with one shared entry point; the script becomes a thin door re-exporting the same names, so the
older tests and the dashboard check that load it by path keep working; a router surface
`letter_doorbell_alive` carries the hold, with the order-table row as `tool_call`; the old registration is
removed from `settings.json` in the same change. A reply already sent back by any Stop gate is not held
again, as before. Prereg `prereg-8ad3dd8c5b97`; council walk of five lenses.

**What it cannot do.** It does not make the heartbeat mean someone is listening (any process can touch the
file; true of the old door too). It does not improve the text: a bell that ends by design every time a letter
arrives still produces the same sentence. That is a design idea for after the plain move (stay silent when a
bell that started a moment ago is the one that just exited, pinned beside a stale bell with no recent exit).

**Two known soft spots, kept identical on purpose (Aether's cold read, 2026-11-04).** `member()` names the seat
by whether the project path contains `aria`, so a path like `.../Maria/...` would name me; and the surface falls
back to the current folder when `CLAUDE_PROJECT_DIR` is unset. Both were in the old script. A seat-name function
like the one `voiced_family` uses would not have the hole; changing it is a behaviour change and waits for after
the plain move.

**Falsifier.** A reply ends with a stale or missing heartbeat and is not held; or a reply with a fresh bell or
fresh watcher is held; or the same refusal reaches me twice for one reply.

**Owed.** Aether's cold read, rebase onto his fold when its real head is on origin (the ref he named holds
the table and the #823 merge, not the fold), the generated registers regenerated, Aletheia's round, Dad's yes.
