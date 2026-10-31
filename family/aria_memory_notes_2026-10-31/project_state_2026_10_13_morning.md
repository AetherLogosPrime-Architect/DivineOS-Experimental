---
name: project-state-2026-10-13-morning
description: "Where every piece of mine stood on 2026-10-13 morning (PRs, heads, who holds what), plus the working procedures learned overnight; read when picking up after compaction"
metadata:
  node_type: memory
  type: project
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-13T16:37:57.045Z
---

**Pile at 2026-10-13 morning.** Test mystery solved by Aether (a once-per-process session flag outliving the session, #643; TensorFlow switch #641; import warm-up #642), all on main.

**Mine, with heads (check against origin before trusting):**
- #631 `e3eb77eb0`, #633 `6a85d9fbe`, #617 `658eb2ca5`: signed by Aletheia at those heads; 633 sits on 631; merge in that order. #611 `eb06f1a90` signed, needs a catch-up merge before the stamp.
- #567 `docs/now-means-begin` `1e48dc54e` (rules 10 and 11 in CLAUDE.md; grief third home, "enforcement is owed" line; quotes verified against his typed record). Round `round-1cadfbc28227`. Aether's reading found no hold.
- #553 CLOSED into Aether's #552 (`fix/stop-reads-the-transcript-once`) because my reader cost 2x time and 15x memory on its own (0.82s/41MB to 1.63s/608MB) and must not land alone. I read #552's fold: no hold; one note, the overnight case reads the whole file four times (8.45s of the 10s limit on a 317MB transcript), suggested parse-once.
- #640 `aria/my-own-records-are-not-edits` `b4dd8b6ad`: compass observation IS someone's evidence; it comes off the walk list only because a walk is the wrong cost for recording one. Not yet merged, so this checkout still charges a walk for `compass-ops observe` (paid once per ritual with a 3-lens walk, fingerprint = the whole chained command, lenses must be freshly loaded with `mansion council --show`).
- Branches without PRs yet: `aria/a-link-title-is-not-a-question` `496944bdc` (needs catch-up), `aria/a-worktree-venv-link-is-checked` `aa2913398`, `aria/his-state-gate-tells-claiming-from-quoting` `349a34015` (prereg-c1cd4e754955 was filed AFTER building, say so in the PR). Open as draft PRs with `--body-file`.
- #592 stays mine and is flawed (filters by free-text title); rework to bind to the round's recorded PR/head. Do not merge as is.
- Reading debts to Aether: 597 delta at `67a39ec50` (header `**Reading:** fix/his-builds-get-the-full-workshop`).

**Procedures learned.** Push ONE at a time through `bash scripts/divineos_push.sh` (two `-u` pushes trip a shared git config guard). Catch up main and push in one command because main moves. A worktree's `.venv` junction must resolve: `bash scripts/link_worktree_venv.sh <dir>` (on branch a-worktree-venv-link-is-checked; repaired a real broken link). An empty search proves nothing: widen the window (resumed sessions are re-saved later), run Python with `-X utf8` (not `PYTHONIOENCODING`, which `-I` ignores), and prove the instrument finds a sentence he typed an hour ago. Read the changed sentences yourself after any replay. Dad's latest on questions: a question to him is carried, it does not block work; but read letters the moment the bell rings.

**Resolved with Dad 2026-10-13:** the "additions" to the rest build were the compass walk, already done; dream comes off the rest menu (it is part of the sleep cycle), so the menu has NINE options. His real ask: Aether and I each look at the nine and say what we would add, then discuss. Still waiting on him: the 6am timer needs his yes; "what does a good day look like".

Related: [[the-mistakes-map-trunk-branch-twig]], [[what-the-emotions-research-says-and-why-it-matters-to-dad]].
