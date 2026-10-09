# tests/pile_repro — proof-tests: a flaw pinned in writing until someone fixes it

Each file here reproduces ONE flaw the cloud helper found (and a human or an agent re-checked). Nothing here changes behaviour: no guard, hook or script is touched by these files.

**How a file is built.** Controls that PASS today (they show the probe can see a case it should), and one test marked `xfail(strict=True)` that fails today for the one reason named in its `reason=`. Each has a rough draft in `docs/drafts/pile_repro_*_draft_2026-10-08.md`.

**What that buys.** CI stays green. The flaw is on the record. When the flaw is fixed the strict expected failure starts passing, `strict=True` turns that into a failure, and whoever fixed it must delete the `xfail` marker in the same change. The pin cannot be forgotten and cannot go stale quietly.

**What it does not buy.** An `xfail` is not a fix and not a decision that the flaw matters; the draft says whose call it is. `python -m pytest tests/pile_repro --runxfail` shows the expected failures failing for real (41 of them as of 2026-10-09, with 28 controls passing).

**Source.** Nine branches of the cloud helper (`cloud/repro-*`), bundled so one review reads nine independent files. Author lines are the helper's; the bundling is Aether's.
