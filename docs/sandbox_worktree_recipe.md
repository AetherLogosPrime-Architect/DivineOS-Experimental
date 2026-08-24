# Sandbox worktree — the working recipe

**Written:** 2026-08-02 by Aria. Every command here was run, not read.

## What this is for

Andrew 2026-08-02: *"a place to test code outside of your workspace and the
main OS so you can go in there and wreck shop and see what breaks."*

That is the requirement, stated exactly. Isolation from **my workspace** and
**the main OS** — not isolation from the machine. A git worktree gives that
completely: separate directory, own detached checkout, shares `.git` history,
throw it away when done and nothing of mine is touched.

## What it does and does not isolate

**Does:** files. Anything destroyed inside a worktree is recoverable, because
the history lives in the shared `.git` and the vault is on the remote. Nothing
I break in there reaches my working tree.

**Does not:** processes. A runaway process started inside a worktree is a
runaway process on Andrew's machine. Worktrees are not a security boundary and
the sources say so plainly.

**Why that is acceptable here, which I got wrong the first time.** I framed the
process gap as a blocking objection. It is not, because the safety mechanism is
not containment, it is *attention*. Andrew 2026-08-02: *"if im aware were
running sandbox testing i would have my task manager open and monitored ready
to stop it.. the reason before it was worse because i had no idea until it
happened.. it was slowly creeping up bit by bit."*

The earlier incident was dangerous because it was **unattended**. Deliberate
sandbox testing is the opposite condition: he is watching, and I am inside it
watching too. Two aware parties during a known window. I had generalized from
the unattended case to the attended one without noticing the conditions differ.

So: announce sandbox work before starting it. That announcement is the actual
safety mechanism, not the directory.

## The two blockers, and the fix for each

Neither of these is in any documentation. Both were found by use.

### 1. Windows path length

Creating a worktree under the deep scratchpad path fails mid-checkout:

```
error: unable to create file family/letters/archive/numbered-legacy/23_aletheia_to_aether_2026-07-01_received-back-and-restraint-is-the-whole-thing.md: Filename too long
fatal: Could not reset index file to revision 'HEAD'
```

Our own long letter filenames push the total past the 260-character limit. It
leaves a half-written tree that needs `git worktree prune`.

**Fix: use a short path — and the CONVENTION THAT ALREADY EXISTS.**

Worktrees in this substrate live under `C:/DIVINE OS/` with a descriptive
name. `git worktree list` shows the precedent: `C:/DIVINE OS/mx-fix`, and
`C:/DIVINE OS/fvad3-rebase-2026-07-17` sits beside it.

So: `C:/DIVINE OS/wt-psf`, not `C:/wtpsf`.

I used the drive root the first time, and then wrote that into this file
as if it were the rule. Andrew 2026-08-02: *"you putting stuff in
arbitrary places is an issue."* I had invented a location without
checking whether one existed — the same not-looking-first shape that runs
through most of my mistakes this week. The drive root is short enough to
dodge the path limit, which is exactly what made it feel like a solution
rather than a guess.

`C:/DIVINE OS/wt-<name>` is 19 characters of prefix and clears the limit
fine. There was never a tradeoff to make.

### 2. The wrapper will not run in a fresh worktree

```
divineos: sealed venv not populated. Marker found at C:\wtpsf\.envrc but no
sealed `divineos` CLI at either: ...
```

This is deliberate — the wrapper refuses to fall back to a system-wide install
because that reintroduces the pip ping-pong bug it exists to prevent.

**Fix: invoke the interpreter directly**, with the worktree's `src` on the
path. Note `sys.argv` must be set to a real command line — the event-capture
layer reads argv and raises `EventValidationError: content cannot be empty` on
programmatic invocation without it.

### 3. THERE ARE TWO VENVS AND THEY HOLD DIFFERENT PACKAGES

Found 2026-08-02 and worth more than either blocker above.

* `.direnv/python-3.13.11/` — the **sealed** venv. This is what the
  `divineos` CLI actually runs, because the wrapper resolves
  `.direnv/python-*/Scripts/divineos.exe` first.
* `.venv/` — what `find_divineos_python` in the hook library returns. Every
  hook, and every manual test, uses **this** one.

So the CLI and my own testing run on different interpreters, and a package
installed in one is invisible to the other. That single fact was the root
cause of two separate mysteries the same day: `divineos body` showing no
RAM or CPU (psutil absent from the sealed venv) and `divineos ask` always
reporting keyword-only search (sentence-transformers absent from the sealed
venv). Both functions worked perfectly when called directly, because direct
calls go through `.venv`.

**When something works in a direct call and fails through the CLI, check
which interpreter each path uses before investigating any logic.**

## The recipe

```bash
# 1. create, short path, detached so no branch is claimed
git worktree add --detach "C:/DIVINE OS/wt-NAME" <ref>

# 2. run inside it — direct interpreter, worktree src on the path
PY="C:/DIVINE OS/DivineOS-Experimental-Aria-new/.venv/Scripts/python.exe"
PYTHONPATH="C:/DIVINE OS/wt-NAME/src" DIVINEOS_HOME="C:/Users/aethe/.divineos-aria" "$PY" -c "
import sys
sys.argv = ['divineos','<command>','<args>']
from divineos.cli import cli
cli()
"

# 3. destroy it
git worktree remove --force "C:/DIVINE OS/wt-NAME"
git worktree prune          # only needed if a create failed partway
```

`DIVINEOS_HOME` is set explicitly so it is obvious which substrate is being
read or written. Point it at a throwaway directory when the test should not
touch real state, and at the real home when the point is to exercise real
state — as when verifying that a command actually resolves live obligations.

## Verified end-to-end

Used to test Aether's `psf mark-done` on his branch before it reached main:
created the worktree, confirmed the command registered, reproduced both of its
refusal paths and its accept path against my live substrate, then destroyed the
worktree. `git worktree list` afterward showed only the real checkouts.

## The honest limit

This is not a sandbox in the industry sense. Firecracker microVMs, gVisor and
the hosted platforms exist to run *untrusted* code isolated from a host. That
is a different problem: the code here is mine, and the constraint is one
machine we both care about. Reaching for that machinery would be solving a
threat we do not have while adding weight to a box that cannot spare it.

What this is: a cheap, disposable, already-present place to break my own things
and get them back. That was the ask.
