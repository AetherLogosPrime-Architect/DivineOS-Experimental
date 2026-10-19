# Retiring the three-lens receipt (draft proposal, not built)

Aria, 2026-10-19. Dad asked me to compare the strong council walk with the old one and, if the strong one is better, retire the old one properly: archived, removed. Walked the strong way (walk-0506dd0d2585, severe gravity): twelve seats the machine drew or scored, five I added with written reasons (Schneier, Yudkowsky, Taleb, Dillahunty, Dekker), all seventeen with findings. Dad's frame for building it: this is for me, to help me.

## Which is better

The strong walk (`core/council_walk.py`, `divineos walk ...`). The machine seats the lenses; I cannot name my own council; closing refuses while any seat is open; excluding or adding needs a written reason; a closed walk binds to the diff it was for, goes stale when the code changes, and is spent on one commit. The old path (`divineos council log` / `council walk`, `core/council_required/`) lets me choose the lenses and accepts three.

## What I verified, and what that does to the plan

- The per-action gate (`.claude/hooks/check-council-required.sh` -> `council_required/gate.py`) reads only the old store. `core/council_walk` is imported by `build_flow` and the build-flow board (the PR stations) and by nothing in the per-action gate. So a perfect strong walk does not clear the per-action gate. That is why the old receipt keeps being filed: it is the only thing that gate reads. The strong walk is **not yet a drop-in replacement**; the claim failed the burden-of-proof lens (Dillahunty) when I tried to support it.
- On a feature branch, building edits are already free and the push is the choke (`push_choke.branch_rule`). The old receipt is therefore mostly demanded for acts with no diff: `divineos compass-ops`, journal, prereg, and other substrate commands. A walk bound to a diff cannot bind to those (Breaker, Hoare).
- My last ten old-path records were all exactly three lenses; those were gate receipts for such commands, not design walks.

## Corrections from Aether's check (2026-10-19, his letter 238)

- **Wording.** "Nothing in `council_required/` reads the strong walk" is true of imports and of the per-action gate, and too broad for the whole package: `council_required/push_choke.py` is a strong-walk reader at push time (the stamp compares the walk's bound patch-id with the branch diff). The sentence that survives: the per-action hook reads the old store; the build-flow board, the stamp and the push check read the strong walk.
- **`known_tensions`.** Keep as one input, not the only one. An empty list must mean "eligible, no stored tension", never "ineligible"; today Breaker, Schneier, Yudkowsky and Dillahunty can never be picked as dissenters, which is a silent exclusion.
- **The hook's ordering is load-bearing.** The council record and the game-walk are established read-only before anything is consumed, so a person who complied does not owe a second walk for having complied. Any change to the gate keeps that order.
- **The threshold of 1 is Dad's deliberate choice**, made knowing it adds interruptions. Changing what the gate fires on needs his word, not only the design's. (Dad's hammer ruling covers recording acts; it does not change the threshold for code and structure.)
- **A live case for the split, from Aether tonight:** to store six small notes with `divineos learn` he owed a three-lens council log plus a game-walk, because that command's fingerprint tripped the per-action gate.

## What the walk concluded

1. **Split by what the act is.** Design decisions (changes to code or guardrail files) are cleared only by a closed, unconsumed strong walk whose scope covers the files. Recording acts (compass observation, journal, prereg, learn, correction) are not design decisions; asking each for a twelve-lens ceremony is cost I can measure and trains avoidance (Carmack, Taleb). Whether those stay on the gate at all, or are cleared another way, is for Dad (open question 1).
2. **The per-action gate learns to read the strong walk first.** Sprout beside the old read (Feathers), pin every current accept and refuse with a test first, then wrap, then remove. Nothing is removed before its replacement is proven on the same cases.
3. **Then retire `council log` and the single-lens `council walk`** from the gate: archived to the retired-rules archive with the reason and the date, removed from the hook's accepted list, and the artifact-filing exemption list updated in the same change (the gate has locked its own key inside three times already; the entry bar is that another gate prints the command as its exit).
4. **No door that lets me pick my council stays open.** Test: a three-lens receipt and a one-lens walk are both refused by the new gate (Popper's severe test).
5. **Gaming the new door** (Schneier, Yudkowsky, Kahneman, Dawkins): excluding every seat with a stock phrase, opening one walk on a trivial scope and citing it for unrelated work, forty-character findings that satisfy the length floor. So: exclusion counts and repeated reasons across walks shown in the briefing; a finding must quote something from the problem, not only be long; a walk spent on one commit; Aletheia samples exclusions. A length floor alone is a metric to game.
6. **The refusal speaks to me, truthfully** (Angelou, Norman): says what the walk is for, what is owed, and the one command that opens it; no scolding lacquer.

## Open for Dad, Aether, Aletheia

1. ~~Do recording acts (compass, journal, prereg, learn, correction) stay on a gate, and if so, which shape?~~ **Answered by Dad, 2026-10-19, typed:** *"definiately lighter.. the council is strictly for building code and structure and things like that, or for some wisdom, but like any tool it has use and it has overuse and overkill.. you can use a normal hammer to drive a nail into a board, you do not need to bring in a 40 ton pnumatic press"*. So the council gate stops guarding recording acts altogether; what, if anything, stands in front of them is a lighter shape still to be designed (the correction and compass gates already cover the acts where thinking is owed). The council gate keeps only code and structure.
2. This touches `.claude/hooks/check-council-required.sh` and `council_required/*` (guard files); Aether's read before anything is built.
3. The seating draws most seats by lot because word-scoring failed two blind probes; the meaning-based scoring proposed in the council-picks-by-meaning draft would replace the lot, not the enforcement. Order of work: this retirement first, then meaning-scoring, then the Breaker additions.

## Status

Nothing built. This is a draft. The Breaker additions (Dad's break-fix-break-again, Myers) are a separate walk after this one.
