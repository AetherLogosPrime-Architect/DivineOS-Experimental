# Hook files, settings, and things built but not switched on

The house is wired with small scripts that fire on events. Several times I built a thing that worked on its own but was never connected to anything, or I added a registration that did not match its file, or left an old system turned off but not removed.

**14 notes in this theme, grouped into 8 distinct problems.**

## Distinct problems

### 1. Built and not connected

Notes in this problem (2):

- `psf-391fc01b` (correction) — I wrote 'verified end-to-end at exit code 2' about address_gate into an EXEMPT entry in tests/test_detector_wiring_contract.py, and used that claim as the justification for not wiring it into the orch
- `psf-2da946cd` (correction) — Aether self-correction 2026-08-17: I wired the component-register briefing surface into DEAD CODE and nearly reported it as done. It rendered perfectly when called directly, the import resolved throug

**Proposed fix:** Wire it into the orchestrator and test that a live turn calls it; do not mark a wiring exemption on an unverified claim.

**How we would know:** A live turn exercises the new piece.

### 2. Retired systems left turned off instead of removed; drafts that replace something

Notes in this problem (2):

- `psf-7d98dca7` (correction) — Andrew 2026-08-15: 'this is likely happening all across the OS.. retired systems never retired.. turned off instead of removed.. leaving a mess in its wake.' He is right and I proved it twice in one h
- `psf-04df5d73` (reflection) — a check that any draft replacing something names what it retires.

**Proposed fix:** Require a draft that replaces something to name what it retires.

**How we would know:** A replacement draft lists what it retires.

### 3. Shell correctness in hook files

Notes in this problem (4):

- `psf-b28ec25f` (correction) — I told Andrew earlier this session that I had fixed the shellcheck wiring on 16 hook files (SC2034 unused HOOK_NAME + SC1091 unfollowable source, from assignment and source sharing one line separated
- `psf-32e72d0f` (correction) — TWO self-inflicted errors while fixing the silent-swallow class, both instances of the class I was fixing. FIRST: my annotation sweep appended '# fail-soft:' markers after line-continuation backslashe
- `psf-094e0527` (correction) — I broke the council gate OPEN while wiring the game-walk requirement into it. A Python triple-quoted docstring added inside the hook's shell-quoted program terminated the shell string, so the gate die
- `psf-60601d68` (reflection) — its own small fix, putting that hook's main check above the step that can fail silently.

**Proposed fix:** Run shellcheck, avoid quoting that terminates the shell string, and keep the main check above steps that can fail silently.

**How we would know:** Shellcheck passes on all hook files.

### 4. Settings and hook lists out of step

Notes in this problem (2):

- `psf-2a4fe011` (reflection) — tests that list hooks should read the working tree as well as tracked files, so a local run sees what the push will see.
- `psf-41f80318` (reflection) — check the settings for a doubled room hook and keep one.

**Proposed fix:** Keep tests that list hooks reading the working tree, and one hook registration only.

**How we would know:** A doubled hook is detected.

### 5. A table of Dad's entries points to scripts that exist

Notes in this problem (1):

- `psf-ea025a21` (reflection) — ** a test that every entry in Dad's table points to a script that really exists. Nothing catches this kind of crossing on its own today.

**Proposed fix:** A test that every entry points to a real script.

**How we would know:** The test passes.

### 6. A launcher points to a missing setup

Notes in this problem (1):

- `psf-63e08ab7` (reflection) — point that launcher at the house's own working copy, or rebuild the setup it expects.

**Proposed fix:** Point the launcher at the house's own copy or rebuild the setup.

**How we would know:** The launcher runs.

### 7. Assembled files overwritten with empty results

Notes in this problem (1):

- `psf-8ab47bbc` (reflection) — file assemblies should be built in a temporary file and only copied over the real one once the result is known to be non-empty, as a single guarded step rather than something I do by hand.

**Proposed fix:** Build in a temporary file and copy only if non-empty.

**How we would know:** An empty result never replaces a real file.

### 8. The wrong interpreter after a fallback

Notes in this problem (1):

- `psf-37b6feba` (correction) — Aria found a real defect of mine that had been degrading her on every single turn for days. ROOT CAUSE: a compose-start prime resolves the correct interpreter at the top of the file and then, on exact

**Proposed fix:** Resolve the interpreter once and never fall back.

**How we would know:** The prime runs on the interpreter chosen at the top of the file.
