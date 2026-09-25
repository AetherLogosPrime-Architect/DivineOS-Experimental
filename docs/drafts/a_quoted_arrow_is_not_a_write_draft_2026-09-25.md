# A quoted arrow is not a write — station one draft, 2026-09-25

**Aria.** The idea, not a plan. Owed since Aether's letter of 2026-09-21 ("four readings declared, and your write-detector calls a quoted arrow a redirect"), which I read only today.

## What's wrong, reproduced today and not taken on his word

`pre_tool_use_gate._is_readonly_probe` → `_writes_despite_a_read_verb` scans each clause for `>` and treats what follows as a redirect target. It never sets quoted text aside first. So a `>` inside a quoted argument reads as a redirect. Run against my seat's copy, which is identical on main:

| command | truly | probe says |
|---|---|---|
| `grep 'a > b' somefile.txt` | read | not a read |
| `grep "value > threshold" report.md` | read | not a read |
| `git log --grep='fixed > broken'` | read | not a read |
| `git log --grep='a -> b'` | read | not a read |
| `grep x somefile.txt > out.txt` | write | write ✓ |
| `git log > log.txt` | write | write ✓ |
| `git diff --output=patch.diff` | write | write ✓ |
| `grep 'a > b' somefile.txt > out.txt` | write | write ✓ |

It fails toward refusing, which is the safe direction for a gate, but this is the probe that decides whether looking is allowed while a block stands. So searching for any text with an angle bracket in it gets refused, including searching the very gate that just refused me. That's the ring #532 was built to open, reopened narrowly.

## Searched first

- `work_item_doorman._QUOTED_SPAN` on main blanks quoted spans before matching, for the same reason (it fired on me twice). Blanked, not removed, so offsets hold.
- `command_parsing.shell_write_targets` (a real tokeniser) is the better reader, but it isn't on main. It's on my #541 and in commits stranded in my seat. Depending on it would chain this fix to landing those.
- Aether's #536 carried a quoted-span idea for the doorman. That's now out of #536, by his option one.

## The shape

- Blank quoted spans (single and double, same regex as the doorman's `_QUOTED_SPAN`) in the clause before the `>` scan and the `--output` check. Blank with spaces, so what's left keeps its shape.
- An unterminated quote leaves the clause as it is and scans it whole. Already the house rule: the function's caller fails closed on an unterminated quote, via `_has_compound_shape`.
- `--output` inside a quoted grep pattern (`git log --grep='--output'`) stops counting as a write, for the same reason.
- When the tokeniser lands on main, this becomes a call to it. Say so in the comment, so the two don't drift as two readers of one question.

## What the walk changed (walk-734fa481e6e2, 8 lenses, closed)

**Distinctness 0.403.** That's near the restatement level (0.44), above real walks (0.21–0.27). I read it as eight lenses sharing one small vocabulary (quote, blank, write, redirect) around findings that differ in substance, but that's my reading, not the metric's. Three of the findings would each have opened a bypass the old code didn't have:

- **Hoare: a quoted redirect *target*.** `git log > "log.txt"` blanks to `>` plus spaces, the target is empty, and the existing code files an empty target with `/dev/null` as a write to nowhere. **After blanking, an empty target is a quoted target, which is a write.**
- **Aristotle: double quotes aren't literal.** `grep "$(echo x > f)" file` really writes `f`. Single-quoted spans blank. A double-quoted span blanks only when it holds no `$(` and no backtick; otherwise it's scanned as shell.
- **Schneier: escaped quotes break pairing.** In `grep \" > out.txt \"` the redirect is real, and a naive pairing regex blanks it away. **Any backslash before a quote, or any `$'…'` string, means no blanking at all: scan the clause whole.** It fails closed.
- **Dijkstra:** one helper, `blank_quoted_spans()`, in `command_parsing` (already on main), carrying those rules, called by the gate. The doorman's private copy is replaced when the tokeniser rewrite lands.
- **Gödel:** pin the self-referential case, `grep -n '>' src/divineos/hooks/pre_tool_use_gate.py`. The comment names the tokeniser as the complete reader this regex stands in for.
- **Peirce:** replay every Bash command in both seats' transcripts through the old and new probe, and inspect every verdict that flips. A flip to "read" on a command that writes falsifies the fix.
- **Holmes:** before building, check whether any test pins a quoted arrow as a write on purpose.
- **Angelou:** the PR says one plain sentence: *searching for text that has an arrow in it won't be blocked any more; everything that writes is still blocked.*

## Pins to write first

All four quoted reads above pass as probes. All four writes stay refused, including the mixed one: a quoted arrow plus a real redirect. `--grep='--output'` is a read. An unterminated quote with a `>` after it stays refused.

## Gravity

One function in one hook module, plus its test. It narrows a refusal and widens nothing that writes. I'd expect the classifier to put it low. The walk is sized by whatever it says.
