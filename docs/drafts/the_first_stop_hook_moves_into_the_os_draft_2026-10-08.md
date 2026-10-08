# The first end-of-reply script moves into the OS (draft, 2026-10-08)

Dad's plan, in his words: seven doors, all the thinking inside the OS. The measure now says 35 shell scripts still hold their own logic. The first one I take is `retrieval-tally-check.sh`: 84 lines of bash with Python embedded in a `python -c` string, whose real logic is in `scripts/retrieval_tally.py`, a file outside the package that the OS reaches by a `sys.path` trick.

It swallows every error (`except Exception: pass`, then `|| true`), which is the quiet-failure shape the migration tracker names: a check that could not run is byte-identical to one that looked and found nothing.

How, the smallest honest way: the Stop door already has a table (`_TRANSCRIPT_AUDITS`) of `(name, module, function)` rows that hand the transcript path to an OS function and report `could-not-run` with the reason if it raises. This one is a fourth-row fit.

1. Move the logic into `src/divineos/core/retrieval_tally.py`, adding `run_retrieval_tally(transcript_path)` that reads the WHOLE last reply (the hook read only the last text block) and calls `check_reply`.
2. `scripts/retrieval_tally.py` becomes a thin shim so `python scripts/retrieval_tally.py summary` keeps working.
3. `andrew_past_writing_surface` imports from the package, no more path trick.
4. One row in `_TRANSCRIPT_AUDITS`; the shell registration comes out of `settings.json` in the SAME change, and the script gets a SUPERSEDED header (the tracker's rule: a migration that leaves the original registered has moved code and retired nothing).
5. Tests for `check_reply` (it had none), the shim, and the surface; a live run through the real Stop hook before and after, to show it fired once, not twice, not zero.

Falsifier: the tally rows stop appearing in `~/.divineos/retrieval_tally.jsonl`, or appear twice per reply.
