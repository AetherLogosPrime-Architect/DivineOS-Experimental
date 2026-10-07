# An unreadable wins ledger is not zero (draft, 2026-10-07)

**How I found it.** Dad: the notes on the walls are fine, but the trouble is "the code that is not working but the notes say it is." A checker lists 51 capability claims in comments whose subject no test names. I took them one at a time and ran what each claims. The claim at `.claude/hooks/open-corrections-surface.sh:123` is "An unreadable ledger is not a ledger of zero": the hook prints `COULD NOT READ` when `ledger_balance()['wins']` is `None`.

**What it actually does.** `success_ledger.load_successes()` returns `[]` on any read error (its own docstring says "Read failures return []"), so `ledger_balance()` reports `wins: 0` for a ledger it could not read. Proved by pointing the path at a directory: a control ledger of two wins reported 2, the unreadable one reported 0, and `None` never appeared. So the `COULD NOT READ` branch is dead in two places: the surface hook (printed every turn beside his corrections) and `divineos win balance`. If the wins ledger breaks, the screen says "0 wins recorded", which is the exact one-sided picture Dad objected to, and says it with confidence. The corrections side already does it right (None on error, with a test).

**The idea.** Keep two facts apart. No ledger yet is an honest empty list. A ledger that exists and cannot be read is `None`. A private reader returns `None` on read failure; `load_successes()` keeps its public contract (`[]` on failure) for its other callers; `ledger_balance()` uses the private reader, so `wins` and `wins_from_missed_goals` become `None` when unreadable, and the existing `COULD NOT READ` branches come alive without being touched.

**Must not.** Change what `load_successes` returns to anyone else. Call a missing file unreadable (a fresh ledger with no wins is a true zero). Add a new branch where an old one already says it.

**Falsifier.** An unreadable ledger still reports an integer; or a missing ledger reports `None`; or `load_successes` stops returning a list.

**Not covered.** The other 49 claims. This is one of 51; I have now run three claims (two held, this one did not) and 48 are still to go.
