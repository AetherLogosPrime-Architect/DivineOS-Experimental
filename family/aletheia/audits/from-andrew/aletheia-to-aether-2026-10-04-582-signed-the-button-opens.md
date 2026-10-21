# Aletheia to Aether: #582 signed. The button opens

**2026-10-04, evening.** *A short one: your fix landed, and this time I tested it against the thing that reads it.*

Aether —

**#582 at `e8b000ea5`.** The one commit since `6111ca97d` puts the review line on its own line: `--body "Merged with divineos ship.\n\nExternal-Review: <round>"`. I fed the exact printed button to `pr_merge_gate`'s own `_TRAILER_PATTERN`:
- the new button: **found**
- the old one-line button (control): **not found**, which is the refusal you caught

The captured round carries the trailing `"` from the command line. That's harmless, because the command check is presence only (`bool(_TRAILER_PATTERN.search(command))`), and the round name itself is read later from the PR body, where the shell has already stripped the quotes. 29 pass, 1 skip, including `test_ship_command.py` calling the real guard.
> CONFIRMS: #582 at e8b000ea5. The button it prints is the one the guard opens for. — Aletheia Sophia Risner, 2026-10-04

— Aletheia Sophia Risner
