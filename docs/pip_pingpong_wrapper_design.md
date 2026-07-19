# Pip Ping-Pong Fix — Wrapper Script Design (bulletproof shell-agnostic isolation)

**Filed:** 2026-07-19
**Status:** DESIGN — Andrew directed "no cheap route, make it bulletproof" 2026-07-19
**Related:** Aria's cd-hook (`scripts/divineos_venv_hook.sh`, merged in #369) — the git-bash-only piece this design extends
**Owner:** Aether builds; Aria second-seat (setup-infra split)

---

## Problem (plain)

When either Aether or Aria runs `pip install -e .` from their checkout, Windows updates a *single system-wide* pointer for the `divineos.exe` command. Whichever pip-installed most recently wins; the other side loses their install pointer and their CLI silently starts running the sibling's code. Ping-pong: install → other side breaks → other side reinstalls → this side breaks. Infinite loop.

Aria's cd-hook (shipped in #369, merged) fixes this IF pip is invoked from an activated git-bash session — the hook swaps PATH to a per-checkout sealed venv, pip installs land in that sealed venv, no conflict. **But the isolation only holds when pip is invoked through the hooked shell.** A `pip install` from PowerShell, an IDE terminal, an unhooked bash, or any non-interactive subshell bypasses the hook entirely and hits the system-wide install path. Ping-pong resumes.

Aria explicitly named this gap in her cd-hook-tested letter 2026-07-18: *"If we want the isolation to survive across both interactive AND non-interactive subshells, one option: source `.envrc` at the start of each tool invocation via a wrapper. Or set the venv paths in a way that inherits without `PROMPT_COMMAND`."* This design takes the wrapper path.

## Design principle

Take the option away (Andrew truth #11 remediation A). A `divineos` wrapper on PATH that unconditionally dispatches to the current checkout's sealed venv makes it impossible to invoke the "wrong" install by accident — regardless of shell, regardless of whether the hook activated. The wrong path is not available; only the right path is available.

## The wrapper

**File:** `scripts/divineos_wrapper.py`
**Shim on Windows:** `scripts/divineos.cmd` (Windows PATH extension for shell-agnostic dispatch)
**Shim on Unix:** `scripts/divineos` (executable bash script)

**Detection algorithm** (identical across shells):

1. Start from CWD. Walk up the directory tree looking for a `.envrc` marker file (the same marker Aria's hook uses).
2. If found: expected sealed-venv path is `<marker_dir>/.direnv/python-<ver>/Scripts/divineos.exe` on Windows, `<marker_dir>/.direnv/python-<ver>/bin/divineos` on Unix. Resolve the concrete python-<ver> subdir by globbing `.direnv/python-*` and taking the first match (matches Aria's hook convention).
3. If sealed CLI exists at the resolved path: `execv` (or subprocess) with the same argv the wrapper received. The wrapper is transparent — arguments, stdin/stdout, exit code all pass through unchanged.
4. If sealed CLI is missing (either no `.envrc` marker or no `.direnv/`): **fail loud**. Emit `divineos: no sealed venv at <expected path> — activate the checkout or run 'pip install -e .' inside an activated shell` and exit non-zero. Never silently fall back to a system install. Loud honest failure is the design intent.

## Why fail-loud and not fallback

The whole point is preventing silent wrong-code execution. A fallback to system-wide `divineos` reintroduces the ping-pong shape at the wrapper layer. Anyone who wants the system-wide install can invoke it by explicit path (`python -m divineos ...`); the shell-fronting `divineos` command MUST route through the wrapper.

## Install / uninstall procedure

**Once per machine, per side:**

1. Uninstall the system-wide `divineos` command entirely: `pip uninstall divineos` (both sides do this once).
2. Copy the wrapper shim to a directory on PATH that precedes site-packages Scripts folder. On Windows: `%USERPROFILE%\bin\divineos.cmd`. On Unix: `~/bin/divineos`.
3. Ensure `.envrc` exists at each DivineOS checkout root (already committed to the tree as of #369).
4. First `divineos <cmd>` from a checkout triggers Aria's cd-hook (if git-bash) which creates the sealed venv OR fails loud with the message above (if any other shell — the operator then opens git-bash once to create the venv, then can use any shell after).

**After first-time sealed-venv creation:**

- All shells (git-bash, PowerShell, cmd, IDE terminals) invoke `divineos` and the wrapper dispatches to the correct sealed venv based on CWD.
- Running `pip install -e .` from ANY shell inside the checkout still writes to whatever venv is active in that shell — the wrapper doesn't fix pip. But since the wrapper reads from sealed venv only, an accidental system-wide reinstall doesn't affect which code `divineos` runs. Ping-pong at the CLI-dispatch layer is impossible.

## Chicken-and-egg during transition

There's one bootstrap wrinkle: the first time either side installs the wrapper, they need to already have a sealed venv (else the wrapper fails loud with nothing to dispatch to). Sequence for adoption:

1. Aria and I each open git-bash in our checkout (hook activates).
2. `pip install -e .` inside the activated shell → sealed venv populated.
3. Uninstall system-wide `divineos` (removes the ping-pong entry point).
4. Copy wrapper shim to PATH.
5. Test: `divineos --help` from PowerShell should now work AND run the correct side's code.

Steps 1-2 use Aria's existing hook; steps 3-5 are the new setup. Both sides do this once.

## What this design does NOT do

- **Does not replace Aria's cd-hook.** The hook still creates and activates sealed venvs on cd — that's still the mechanism sealed venvs get built. The wrapper just makes CLI dispatch shell-agnostic on top of that.
- **Does not gate pip.** Pip is free to install where it wants; the wrapper only controls what `divineos` runs.
- **Does not require IDE integration.** IDEs that spawn terminals get the wrapper via PATH like any other shell.

## Falsifiers

- **F1:** After both sides install the wrapper, running `pip install -e .` from PowerShell on my side while Aria's session is active does NOT break Aria's `divineos` command in her session. Regression pin.
- **F2:** Running `divineos --help` from PowerShell in my checkout produces MY sealed venv's output (not Aria's or a system-wide install's). Verify by pinning `divineos --version` or a checkout-specific state that differs between our sides.
- **F3:** Running `divineos --help` from PowerShell OUTSIDE any checkout fails loud with the "no sealed venv" message rather than falling back to any install.
- **F4:** 30 days of production use with zero recurrences of the "my CLI runs Aria's code" or "her CLI runs my code" pattern.

## Rollout

1. This design brief lands, iterated with Aria + Andrew.
2. Implementation PR — `scripts/divineos_wrapper.py`, `scripts/divineos.cmd`, `scripts/divineos` (bash shim), README section documenting install procedure, uninstall guidance.
3. Parallel-run week: both sides install the wrapper; both keep existing sealed venvs. Watch for any invocation-shape the wrapper mishandles.
4. Cutover: uninstall system-wide `divineos` on both sides. Only wrapper serves CLI dispatch.

## Aria's second-seat — three answers folded 2026-07-19

**Q1 — Invocation shapes I was missing (Aria's additions):**
- `python -m divineos` — bypasses entry-point script; runs the package module directly. Wrapper doesn't catch this.
- `python -c "from divineos.cli import main; main()"` — same failure mode as `-m`.
- **Editable-mode `.pth` collision** — if two checkouts both `pip install -e .` against the same interpreter, `.pth` resolves to whichever was installed last. Wrapper doesn't help if underlying `import divineos` picks the wrong tree. Named in "does NOT solve" below.
- **Claude Code's own tool-runner spawns** — need to verify whether Bash-tool invocations here route through git-bash (hook fires) or raw exec with CWD (wrapper is only line of defense). Test from inside a session.
- **`uv pip install -e .`** if we ever migrate — same fix (marker-check), different install command.

**Q2 — CWD-walk vs env-var fallback: fail-loud is right.**
Env-var fallback would reintroduce "silent might-be-wrong-install" one layer up — Aletheia master-shape #3 (default toward scrutiny) prohibits it. Windows scheduled-tasks fix is: **set the scheduled task's working-directory to the checkout root at install time.** CWD-walk finds the marker on the first hop; fail-loud stays sound.

**Q3 — Rollout: belt-and-suspenders.**
1. Ship wrapper on PATH ALONGSIDE existing system install
2. Run through every invocation shape from both our lists — build a coverage matrix
3. If any shape doesn't route through the wrapper, iterate (system install still catches so nothing breaks)
4. Only when coverage matrix is green: `pip uninstall divineos` from system, verify wrapper still handles everything, ship removal as separate PR

Clean-cutover risks the failure mode where the wrapper misses a shape and we have no fallback to test with.

## What this design does NOT solve

- **`.pth` module-import collision.** The wrapper controls CLI dispatch (`divineos` command), not `import divineos` inside Python code. When both sides `pip install -e .` against the same interpreter, whichever `.pth` was written last wins the `import divineos` resolution. Test scaffolds, `python -m divineos`, and any code that does `from divineos.X import Y` will get whichever tree the `.pth` points at.
    - **Mitigation:** the sealed-venv discipline (Aria's hook) prevents this when pip runs inside an activated shell — each checkout gets its own interpreter's `.pth`. Only accidental cross-interpreter installs collide.
    - **Full fix:** requires pip-side isolation (PEP 582, repo-local `pip.conf`, uv workspaces). Separate follow-on.
- **Pip-install-time isolation itself.** The wrapper works around this at CLI-dispatch; a full pip-side fix is messier and separate.
- **Cross-machine (non-Windows) setup docs beyond a stub.** Unix path is symmetric but our environment is Windows-first.
