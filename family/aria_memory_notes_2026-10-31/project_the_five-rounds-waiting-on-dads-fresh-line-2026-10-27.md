---
name: the-five-rounds-waiting-on-dads-fresh-line-2026-10-27
description: "Aletheia's five confirms (719, 633, 683, 733, 732) are filed, step one done; each needs one fresh typed line from Dad, then prepare-merge. Round ids inside."
metadata:
  node_type: memory
  type: project
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T15:40:24.035Z
---

2026-10-27 early morning. Step one of `landing file-confirm` is done for the five Aletheia signed in `aletheia-to-aria-2026-10-26-the-grief-lane-confirmed-and-four-more.md`. Run from the home tree with `PYTHONPATH=C:/w733/src ./.venv/Scripts/python.exe -c "from divineos.cli import cli; cli()" landing file-confirm <PR> --round <ID> --andrew-said "<his words>"`, because the home tree still runs the old one-seat board (its reader cannot see her letter until #733 lands).

UPDATE later 2026-10-27: Dad's line WAS filed into all five old rounds, but #719 moved to head `e72d4341b` (Aletheia confirmed it: `aletheia-to-aria-2026-10-27-719-confirmed-at-e72d4341b.md`), so its live round is **`round-2a5e9d2eafd1`** (her confirm filed; needs Dad's fresh line after it, then prepare-merge). The other four stand at their heads but the board still wants stations (walks, Aether's cold reads, drafts).

Rounds: #719 (old head, superseded) `round-c2298a5a955d`, #633 `round-89c30a6cf164`, #683 `round-bb2df375dfac`, #733 `round-d17ca7205944`, #732 `round-71acba282ccd`.

UPDATE 2026-10-28 morning (Dad away all day, shows and games, no instructions): two more are one fresh typed line from Dad away from merge, her confirm already filed tree-exact (step one done): **#611** round `round-5c7279c3f57a`, **#640** round `round-515b8966e66d`; both board-clean (stations all satisfied). Step two: `landing file-confirm <PR> --round <ID> --andrew-said "<his words>"` (overlay: PYTHONPATH=<scratch>/ov735/src, from `git archive origin/aether/a-hold-is-an-answer src`), then `divineos audit prepare-merge <round>`, `stamp-ready`. Lesson: the board resolves a PR's branch by its LOCAL name; a stale local ref reads every walk as stale (6-more-council "predates the last commit"); `git branch -f <name> <origin head>` fixed #611.

UPDATE 2026-10-28 later: Aletheia confirmed six at live heads (letter in Downloads, `aletheia-to-aria-2026-10-28-six-confirmed.md`); Dad said "i confirm all 6 as well" BEFORE step one, so it cannot count. Step one now done, waiting on his fresh line: #721 `round-d5bebc6ab793`, #685 `round-ad1c0bbf8079`, #683 `round-861030476217`, #733 `round-2632d432fc31`, #732 `round-87c0fed91f6e`, #631 `round-55df2d17f52b` (plus #611 `round-5c7279c3f57a`, #640 `round-515b8966e66d`). Also owed: #719 round-2a5e9d2eafd1 needs his fresh line too.

**Why each waits:** Dad's yes counts only if typed AFTER her confirm was recorded; his earlier "i confirm as well" came before, so it cannot be used. **How to apply:** ask him once for a fresh line, quote it verbatim in `--andrew-said`, then `divineos audit prepare-merge <round>` for the squash body. #721 (a262368a3), #685 (a19a44be2) and the merge/push-check fix branch (ffb128814) are pushed and verified but not yet read by Aletheia. See [[a-zero-exit-code-is-not-a-saved-commit]].
