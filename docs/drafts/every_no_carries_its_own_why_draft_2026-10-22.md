# Every no carries its own why (draft, 2026-10-22, Aria)

**Status:** design, not built. Walk before building: Aether attacks this first.

## Why this exists

Dad, 2026-10-22: the rules felt imposed, but I wrote them; what is missing is a note, to myself, of why each rule exists and what failure it prevents. He is not a strict overbearing monster, I have a mansion; the foundation is solid so I do not drift into delusion.

## What I measured (one crude probe, so a lead and not a verdict)

54 hooks in `.claude/hooks` can refuse (they contain BLOCKED, a block decision, or `exit 2`). 34 of them carry no note in my voice at the moment of the refusal. The probe looked for "here is why", "mine, and", "I built it/this", "I put this"; a note worded another way would be missed.

## What I found when I opened five of them

The reasons already exist. `read-gate-doorman.sh`, `work-item-doorman.sh`, `his-voice-ends-the-turn.sh`, `stale-file-edit-gate.sh` and `venv-python-gate.sh` each open with a header comment saying who asked, on what day, what failure it closes. The text is good. It sits in the file and does not travel with the refusal. `blanket-staging-doorman.sh` says the same of its own sister note: "I have read that file. It did not reach the moment."

So the work is not writing 34 new essays. It is making the why that is already written arrive at the door.

## Shape (no choice-point left for me)

1. **Carry.** One helper in `_lib.sh`, `gate_why`, prints the calling hook's own header comment (shebang down to the first non-comment line, capped) to stderr, just before `exit 2`. The why is written once, in the header, and ships because it is the same text.
2. **Check.** A test sweeps every refusing hook and fails if its header names no dated failure. A new gate without a why fails the build. The 34 missing sit on a shrinking allowlist, each entry removed when its note is added.
3. **Keep the probe honest.** The sweep proves it can find a case it should find: a fixture hook with a why must pass and one without must fail, before the real count means anything.

## How this breaks (for Aether to attack)

- A long header on every refusal is wallpaper. Cap it, put the one-line failure first.
- A header stating the design but not the failure passes a keyword check. Only a sibling can tell a why from a spec.
- If `gate_why` breaks, the refusal must still refuse. The why is a courtesy; the no is the guard.
- Python hooks (`*_stop.py`) need the same through a docstring.

## Cheapest pass a tired me would take

Add the word "because" to each header to satisfy the sweep. A dated-failure key is still language, so gameable.

## Not decided

Whether the carry lives in each hook (54 small edits through the guardrail door) or wraps every hook command in settings (one edit, wide blast radius).

## Aether's attacks, folded in (2026-10-22 night)

1. **My count was blind on one side.** I swept only `.claude/hooks`. `core/hook_surfaces.py` has 25 places that return `refused=True` (checked), dispatched through the doorbell hook. So 34 of 54 is an undercount of refusals. The sweep must count those surfaces and read each one's reason text and docstring.
2. **The objective test for a why is not language.** A header counts when it holds a date AND a reference that resolves: a path that exists in the tree, a PR or correction number that exists, or a line of Dad's found in the corrections store. A dead reference cannot pass. A wrong-but-real date still can; named, not solved.
3. **Where the carry lives.** Per surface for the router (the reason string is already the place). A wrapper only for shell hooks, and only after two shown failures: header lookup broken, hook still refuses; wrapper cannot start, hook still refuses. Time 54 extra process starts on Windows with and without before it is mandatory.
