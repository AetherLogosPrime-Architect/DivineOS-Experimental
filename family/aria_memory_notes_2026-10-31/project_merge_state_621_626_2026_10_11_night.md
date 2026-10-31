---
name: merge-state-621-626-night-2026-10-11
description: "Exact state of the two PRs being merged on the night of 2026-10-11 (lock work #621 and flake fix #626), what is done, and the next steps in order"
metadata:
  node_type: memory
  type: project
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-12T00:28:50.820Z
---

**Done.** Aletheia confirmed both at their final heads (her letter in Downloads, `aletheia-to-aria-2026-10-11-621-and-626-reconfirmed.md`): #621 at `f9bdecdf401a...` and #626 at `afdb9505b678...`. Dad confirmed both in chat ("yes i confirm both"). Both confirms are filed: round `round-08f58d296fe3` (621) and round `round-a5d823c5a7f8` (626), each with Aletheia's relayed CONFIRM (file-external-confirm, tree-exact) and Dad's own `--actor user` finding. Owner files exist in `~/.divineos-shared/branch_owners/`. Both PR bodies carry `Author: Aria`. One closed council walk each covering all changed files.

**Heads moved since** because main moved (Aether's 625/627/623 etc. merging): 626 is now at `1a118c2100d0` (a pure merge of main onto `afdb9505b`, verified landed with `scripts/verify_push_landed.py`). 621 is merged locally with main but NOT pushed: its pre-push run fails `test_keeping_him` because that fix lives on 626 and is not on main yet.

**Next, in order.**
1. 626 needs: a draft note on its branch (station 1-draft: a `docs/drafts/` file, commit, push), and Aether's declared reading of it (station 4: his letter with `**Reading:** aria/a-patched-db-path-does-not-outlive-its-test`; his reader counts only the part above the first `---`, outside fences). Ask him by letter for both 626 and 621 (621's own 4-cold-read also needs his Reading line).
2. Re-bind the confirms to 626's new head: `divineos audit file-external-confirm --round round-a5d823c5a7f8 --actor aletheia --branch aria/a-patched-db-path-does-not-outlive-its-test --claimed-tree 7bb25e887d55c9e8673d9f66a4236a9c6edbb313 --claimed-patch-id d87d74a4288f7d6269c84f250f113b85d3914e4b ...` (rung 2, patch-id after catch-up; no re-sign needed for a clean base move). Same idea for 621 (tree 6a102a8b..., patch-id 04bc7e78...).
3. `divineos stamp-ready 626 --audit-round round-a5d823c5a7f8 --no-auto-merge` (dry-run first), then press the merge button (`gh pr merge --squash` with the External-Review trailer from `divineos audit prepare-merge`). Never enable auto-merge. Dad's standing yes covers merging PRs that are ready.
4. After 626 merges: merge main into 621, push (the corpus test no longer blocks), re-bind its confirm, stamp, merge.
5. Run `divineos` commands from `cd C:/wmat` first: the main checkout's hooks are stale and ask for council paperwork on audit commands.

**Gotchas.** Paperwork is per use (3 lens walks + council log + game-walk) for `bash:divineos audit` file-external-confirm and `audit submit` (the build gate's tuple lacks them: owed fix). Lens loads expire after about an hour. Never push a head Aletheia has not seen without telling her what moved.

Related: [[standing-permission-volley-and-tidy]], [[keeping-pace-with-dad]].
