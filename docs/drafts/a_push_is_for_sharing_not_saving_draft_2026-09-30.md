# A push is for sharing, not saving: draft, 2026-09-30

**Station 1.** Nothing is built. Next: Aria's objection with a measurement, then the walk.

## His words (searched first)

- 2026-09-30: *"why are the tests taking so long, are you doing the full suite every time?"* then *"this test issue needs structure to prevent you from doing it again, it wastes enormous amounts of time"*
- 2026-06-24: *"theres no need for you to run a full test suite on everything for every change, the push to hub does that already twice.."*
- 2026-06-04: *"its not the 10 mins thats annoying its when we do them one at a time and each test takes 10 more minutes instead of running them in parallel"*

## Prior art (searched)

- The push gate already runs the suite in parallel (`-n auto`, `check_push_readiness.sh:448`): 13,875 tests in 5m20s. **Parallelism isn't the gap.**
- `docs/wireup-backlog.md:256`, filed 2026-06-30: **"Auto-push after commit for audit-visibility"**. That's the opposite pull: push more, so Aletheia always sees current work. **That tension is real and gets resolved here, not ignored.** Aletheia's visibility matters; it just doesn't need a full suite run per commit to get it.

## Measured

- Today on `fix/his-builds-get-the-full-workshop`: **9 pushes**, several for a one-line change (a guardrail marker, Aria's pin). That's about 48 minutes of suite runs on trees a few lines apart.
- **Aria read my work from my worktree directly** (her station (b) on `replay_record` ran "from your worktree at `C:/wws`"). No push today was needed for her.

## Root cause

A push is being used as **save**. Saving is a commit, which is free. Sharing with Aletheia happens once per finished piece. Nothing distinguishes the two, so the reflex (push after every commit) costs 5 minutes each time. His 06-24 rule was a note, and it faded.

## Shape (take the button away: truth 11a)

1. **A push needs an outward reason:** an audit letter or round naming this branch and its head, or a PR being opened or marked for Aletheia. Without one, the push is refused **before any tests run**, with *"commits are saved; push when it's going to Aletheia."* Refusing costs zero seconds.
2. **Carry-forward of green:** a tree that already passed the full suite (same tree hash) isn't re-run, and the push says so.
3. **The backlog's visibility pull is met without a suite per commit:** Aletheia sees the branch at each finished piece, and that's the head she audits anyway.
4. **The suite itself is unchanged.** It still runs in full and in parallel on every tree that's new and going out.

## Open for Aria

- Is (1) a new button in disguise? If a thin audit letter is enough, I'll write thin ones. Should it need a filed audit round instead?
- Does (1) block something that legitimately needs the remote without Aletheia: draft-PR CI, or her reading when she isn't on this machine?
- Replay: over two weeks of my pushes, how many would (1) have refused, and how many suite-minutes is that? That number decides whether to build.

## Falsifier (counted)

- More than one push per finished piece on a branch after this lands: failed.
- A push refused that Aletheia or CI actually needed: the rule is wrong, and it returns to the walk.
