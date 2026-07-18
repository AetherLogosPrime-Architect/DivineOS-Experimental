# Spatial Awareness Layer — Design Brief

**Filed:** 2026-07-18
**Status:** DRAFT for Andrew (shape-before-build per his ask via Aria)
**Prereg:** `prereg-5161bd82c294` (60-day review window)
**Related principle:** foundational truth #11 (options are the optimizer's attack surface); Andrew 2026-07-18 (*"warnings never work.. they are wallpaper to the optimizer.. so it needs to be structural.. automatic.. without you having to think about it"*)

---

## The problem (plain)

The OS tracks *what* exists (files, PRs, rounds, letters, commits). It doesn't track *where each thing is visible to whom, at what point in time.* That gap causes a recurring class of my mistakes:

- I write a letter to Aria that references a source file in my working tree; she can't see it because I forgot to push the branch first.
- I reference "the file I just committed" in a design doc; the doc is on a branch that hasn't been pushed, so no one else can read the design that references the file.
- I assume Aria has her `distancing_detector.py` change on her side because it's on mine; hers hasn't been pulled yet.
- Same shape in the other direction from Aria to me (per her mirror-note 2026-07-18).

Every case is *me forgetting a mechanical routing step.* Warnings ("your recipient may not see this file") wallpaper over — the optimizer routes past awareness. Structural fix: the OS handles the routing automatically. I write the letter; the OS handles push-if-needed atomically with delivery. I never think about it.

## The design principle (v2 — after Aria + Andrew push-back)

Andrew 2026-07-18 named three shapes for closing option-slots on the optimizer:
1. **Take away the options** (full automation — no choice-point exists)
2. **Make all the options right** (whichever path I pick lands in the correct place)
3. **Conditional rules** (*always X unless Y then Z*)

**v1 draft mistake:** I reached for option (1) — auto-push before delivery. Aria + Andrew corrected: *auto-push takes agency away from us — the layer decides what ships and when.* Wrong shape.

**v2 shape (option 3 applied precisely):** the layer surfaces the waiting-state and hard-blocks at compaction; it does not auto-decide to publish.

> **Always** mark a referenced-on-unpushed-branch letter as *waiting-to-push* and surface that state every turn until the sender pushes or explicitly dismisses. **At compaction time**, hard-warn about all still-waiting letters + their branches — forget past compaction = actual loss.

This is the *force-the-thinking-vs-do-the-thinking* distinction Andrew taught earlier: the layer forces me into the moment where I have to decide (push = my act; dismiss = my act), but never decides for me.

## Core invariants (v2)

1. **Sender side:** if a letter references a repo file on an unpushed branch, the layer marks the branch as `waiting-to-push` and the letter as `deferred-pending-visibility`. Every turn until action, the sender's briefing surface names *this specific branch + this specific letter waiting on it* (attribution, not generic warning). Sender pushes → letter delivers automatically. Sender explicitly dismisses ("scratch letter, no publish") → letter delivers anyway.
2. **Compaction-time hard-warn (sender):** at compaction, still-waiting letters + their branches surface as LAST CALL. Forget past compaction = actual loss of unpushed work + delivery-limbo letters. The compaction event is the natural forcing function.
3. **Receiver side:** when a letter arrives that references files on a remote branch, if the receiver's local hasn't fetched the sender's remote-move, the layer auto-fetches (not merge — just makes refs visible). No decision required on receiver side; fetch is safe/idempotent.
4. **Secret / gitignore refuse-and-shout:** if either side detects a file matching a secret pattern or a gitignore-listed path in a letter reference, the layer refuses to push and surfaces LOUD. Small blast radius but real.

## Where this hooks in (v2 — split by trigger-side)

Existing letter-delivery flow:

```
I write letter file → cp to shared folder → recipient's Monitor picks up
```

New flow, split by side per Aria's ownership boundary:

**Sender side (Aether builds):**
```
I write letter file
    ↓
letter_delivery_router.sender
    ↓
1. scan letter body for repo-file references (regex + heuristic)
2. resolve each reference to (branch, file path, exists-on-origin?, secret-pattern?)
3. if any reference is a secret / gitignore path:
     REFUSE delivery + LOUD warning naming the specific file
4. if any reference is on unpushed branch:
     mark letter as deferred-pending-visibility
     mark branch as waiting-to-push
     write pending-push state to substrate (readable by briefing slot)
     letter waits (does NOT deliver yet)
5. if all references visible OR sender dismisses ("scratch"):
     cp to shared folder
```

**Sender-side briefing surface (Aether builds):**
- HUD slot names each waiting branch + waiting letter, every turn
- Compaction-time hard-warn escalates the surface with "push, dismiss, or accept loss"

**Receiver side (Aria builds):**
```
recipient's Monitor picks up letter
    ↓
letter_delivery_router.receiver
    ↓
1. scan letter body for repo-file references
2. for each reference:
     if reference's remote-tracking branch has moved since local last fetched:
       git fetch (safe, idempotent, no merge)
3. deliver letter to recipient's awareness surface as normal
```

**Ownership split:**
- Sender-side push-reminder + compaction-hard-warning: my build
- Receiver-side auto-fetch-on-sender-remote-move: Aria's build
- Symmetric: her sender-side builds → my receiver-side works the same way against her

## Bi-directional (per Aria's mirror-note)

Same layer works both directions. When Aria writes a letter that references a file on her worktree that isn't pushed, her side's router pushes before delivery. My side sees no difference — I read the delivered letter and the referenced file is fetchable.

## Reference-detection heuristic

Regex candidates (draft):
- Fenced-path patterns: `` `path/to/file.py` `` in prose
- Bare-path patterns: `path/to/file.py`, `src/divineos/...`, `docs/...`
- Branch-name patterns: `on branch fix/foo`, `at commit abc123`
- Directory patterns: `council_walks/`, `family/letters/`

False-positive tolerance: high. If the router thinks I might be referencing a file and pushes when I didn't need it to, cost is one unnecessary push. If it misses a real reference, cost is the exact failure pattern this layer exists to prevent. So err toward over-detecting.

## Failure modes and mitigations (v2)

- **Sender never pushes and never dismisses:** letter stays in pending state indefinitely; briefing surface names it every turn until action. Compaction-hard-warn is the final forcing function — forgetting past compaction = actual loss.
- **Scratch-shape letter (mid-thought, WIP references):** sender explicitly dismisses via `--scratch` flag or similar shape; letter delivers with reference-links noted-as-scratch, no push triggered. Distinguishes intent-to-share from intent-to-think-with-you.
- **Push fails when sender tries (test failure, remote unreachable):** letter stays waiting; loud error names the failed push; sender fixes upstream and re-tries push. Delivery pipeline stays honest about state.
- **Router false-positive on unrelated text:** marks branch as waiting-to-push unnecessarily; cost is one extra dismissal per false-positive. Low cost.
- **Router false-negative on novel reference format:** same failure the layer exists to prevent, degraded to today's baseline. Adversarial feedback (recipient marks "I couldn't see X in the letter") feeds back into router's heuristic.
- **Secret / gitignore reference:** refuse-and-shout; layer never publishes credentials or gitignored paths regardless of sender intent.
- **Receiver fetch fails (network, permissions):** letter delivers anyway with a note that fetch failed; receiver can retry manually. Failure doesn't block delivery.

## What this doesn't do (scope)

- **Doesn't sync file contents across worktrees directly.** Push+fetch is the substrate. Router just makes sure the push happens.
- **Doesn't track which files are in-progress vs published.** Any file the letter references is treated as intent-to-share; if I wanted it private I wouldn't reference it.
- **Doesn't do full spatial-awareness for non-file references** (opinions, claims, rounds — those live in the substrate already and cross via the shared knowledge store). Scope is *file-and-branch* visibility specifically.

## Adjacent follow-ons named during this draft

- **Post-commit auto-push heuristic:** any time I commit on a feature branch with a remote-tracking counterpart, offer/auto-push. This closes the F14-forgot-to-push recurrence (which I did *this session* while writing this very brief — ironic and directly relevant).
- **Cross-worktree pull auto-fetch:** when the OS notices Aria's remote has moved but my local hasn't fetched, auto-fetch (not merge — just make new refs visible). Keeps my knowledge of her state fresh without me remembering to `git fetch`.

Both fit the same automation-shape as the letter-router.

## Falsifiers

Named in the prereg but worth restating:

- After 30 days: does the specific "letter references file recipient can't see" failure class stop recurring?
- Does the automation over-trigger and create a new failure class (e.g. auto-pushes WIP that shouldn't ship)?
- Does the reference-detection heuristic converge (adversarial feedback loop shrinks the miss rate) or diverge?

## What I want from Andrew before build (v2)

All four v1 questions self-resolved via Aria's push-back + Andrew's shape-refinement:

1. Scope confirmed: file+branch only.
2. Bi-directional confirmed as symmetric-split (each side owns one trigger).
3. Failure modes updated to include half-done-work protection, secret-refuse-and-shout, and receiver-fetch-fail handling.
4. Auto-push shape rejected (removed agency). Replaced with pending-push-nudge + compaction-hard-warn.

**Remaining question for Andrew:**
- The `--scratch` flag (or shape) that lets me deliver a mid-thought letter without triggering push-reminders — right shape, or is there a better way to distinguish scratch-shape from delivery-shape at write time? Alternative: auto-detect scratch-shape from letter content (has phrases like "mid-thought" / "WIP" / "not shipping yet"). Not sure which is cleaner.

## Note on process

Andrew explicitly asked to see the shape before I build. This is that shape. Living blueprint — will grow as he pushes back, Aria adds to it, implementation teaches things. Kept smaller than the F43 design spec because the problem is more contained (routing, not classification) and doesn't need 21 lenses to reveal its shape.
