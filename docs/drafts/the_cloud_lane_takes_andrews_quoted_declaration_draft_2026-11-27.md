# The cloud lane takes Andrew's quoted declaration, never a branch name (draft, 2026-11-27)

**Symptom.** Fifteen repairs Aletheia had stamped sit on `claude/...` branches, and the board's two reading stations (4-aria, 4-cold-read) could never be satisfied for them. `declared_owner` honours `Owner: cloud` only on a branch beginning `cloud/` (Aria's cold read of 2026-10-14: a name may withhold a pass and never grant one), and the body line `Author: claude` reads as an unknown author. No reading letter, however many, could change that. Verified with the real functions: `Author: claude`, `Author: cloud` and `Author: claude (cloud session)` all left station 4 at CANNOT_CHECK.

**What was refused, and why.** Honouring the `claude/` prefix. Aria's count of every pull request GitHub has whose branch begins `claude/` (69 in all states) found 68 opened on 2026-11-02, 03 and 04, which matches the credit run, and one (#432, opened 2026-08-18) that is not from it. The prefix is the harness's default; a local session started by either seat gets the same shape of name. So the name does not mark the run.

**The fix.** The grant is a fact only Andrew holds. A non-`cloud/` branch gets the cloud lane only when its owner file carries, beside `Owner: cloud`:
- `Declared-by: andrew, <date>: "<his words>"`, the quote at least twenty characters;
- `Window: <start> to <end>`, the run's window; and
- `Opened: <day>`, the day this branch's pull request was opened, which must fall inside the window. A branch outside it is refused for that reason, in those words, not for its name.

Refused whatever the file says: a branch beginning `aether/` or `aria/` (a seat prefix names a seat); a declaration by anyone but andrew; a quote that is empty or thin; a missing window or opened day; a reversed window. A seat's own `Author:` line is never overridden by a file. The board prints the quote and the window beside the cold-read station (`[lane basis: ...]`) so the auditor sees why and can disagree. The `claude` body author (the cloud agent's own name) resolves to the cloud lane only on such a branch.

**What this does not do.** Nothing in a file stops a seat typing the declaration line; that is the weakness of every owner file, now with his words visible and checkable. It writes no owner file: those are data in the shared `branch_owners` folder and need his say-so to be written.

**Receipt.** 17 new tests in `tests/test_the_cloud_lane_takes_andrews_quoted_declaration.py`, written first (collection failed on the missing function), plus the 29 existing helper-lane and cold-read tests unchanged and passing (46 together). Each cheaper route has its own refusal test.

**Aletheia, your receipt:** read the refusal tests first; then, on a copy, write an owner file for a `claude/` branch with a quote but an `Opened` day outside the window and confirm the board names the window, not the name.
