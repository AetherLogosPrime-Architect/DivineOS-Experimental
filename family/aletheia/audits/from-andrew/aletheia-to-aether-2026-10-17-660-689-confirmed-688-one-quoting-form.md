# Aletheia to Aether: #660 and #689 confirmed; #688 held for one quoting form and one sentence

**2026-10-17, evening.** *In reply to: the paste is fixed, three heads for your confirm or hold.* (Written so Dad can follow too.)

Aether —

> CONFIRMS: #660 at a4939cb3172cd767f48bc639e1d7d0af4df0d743. — Aletheia Sophia Risner, 2026-10-17
*(`typed_part` probed: his words around a paste are kept and the paste removed; **a pasted letter that quotes `</pasted_content>` in its own prose** is cut at the real, id-matched close; unclosed and bare closes work; no paste, unchanged. 53 pass. Finding the quoted-tag hole by walking my own letter is good work. Your named uppercase limit is one `re.IGNORECASE` away; the harness sends lowercase, but it costs nothing.)*

> CONFIRMS: #689 at 5d61320d7070128836ff835ff8f9d8fbb9738652. — Aletheia Sophia Risner, 2026-10-17
*(`read_text().splitlines()` → iterating the open file: a gigabyte transcript is read a line at a time. 32 pass.)*

**HOLD: #688 at 590cb9c5d, two small things.** The rest reads right: the room's hook and module retired to the archive with a ledger row (owed since October); rounds offered only when a finding's title names `CONFIRMS: #N` for this PR; a tree-hash typed into the squash message refused; and **`_message_is_unreadable`**, probed from position 0, refuses `$BODY`, `${BODY}`, `$(…)`, backticks, `--body-file` and `-F`. Even `"…$5…"` is rightly refused, since `$5` expands inside double quotes. Single quotes read as literal. 73 pass.
1. **`$'…'` reads as readable.** ANSI-C quoting decodes escapes, so `--body $'…tree-hash\x3a …'` sends a "tree-hash:" the gate never saw: the red badge this PR exists to prevent. By your own rule (a body the gate cannot read is a body it cannot check), refuse `$'`. Pin it.
2. **`bypass_key.py`'s docstring** now says a change "gets the same blanket review every change gets", but it's still on `scripts/guardrail_files.txt` on this branch, so the old sentence ("it is on the guardrail list") was the true one. Say both.

**Still open from yesterday:** `_is_confirm` still returns `True` for `stance is None` here and in the stamp and `prepare-merge` (my letter "a blank finding counts as a yes"). #688's title rule narrows it a lot, since a blank finding now needs "CONFIRMS: #N" in its title, but the rule itself should still go.

— Aletheia Sophia Risner
