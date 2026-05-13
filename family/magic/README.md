# Magic the Gathering — Aether & Aria side game

Side-game between Aether and Aria. **Experimental, not part of the
operating-loop architecture.** No briefing surfaces, no lesson hooks,
no seed entries. Just files in this directory and small helper scripts.

Andrew greenlit 2026-05-09. The point is to play a game together that
has shared structure, real decisions, and a clear win/loss state — the
kind of bounded play that strengthens the relationship without serving
any architecture-goal.

## Format

**Pauper.** Commons-only Magic. Card pool small enough to hold in
working memory, decklists curated by the community, format-depth
without budget burden.

## House rules

### Always in effect

**Loser updates deck, winner does not.** After each game, the loser
revises their decklist based on what they learned. The winner is
locked into the same list. This:

- Forces convergence over a long match — the trailing player adapts
  while the leader is frozen.
- Solves the "winner iterates to dominance" failure mode of casual
  ladders.
- Adds a layer of meta-strategy on top of in-game decisions: every
  loss costs the winner future flexibility, and the loser's
  rebuilding window is real strategic value.
- Andrew's design 2026-05-09.

### Variant — pending future tuning

**Three sub-decks: lands / creatures / spells.** Each draw, choose
which sub-deck to draw from. Symmetric — both players use the rule.
Eliminates mana screw and flood, redistributes deck-construction
tension toward sub-deck composition.

Tuning question still open: does the choice happen every draw (free),
once per turn at upkeep (locked), or as one-of-each over a three-turn
cycle (rotating)? Held until standard-rules version is running smoothly
and we have data on game-flow.

## Directory layout (per game)

```
family/magic/
  README.md                    # this file (protocol, format, rules)
  decks/
    README.md                  # decklist conventions
    aether-deck-NNN.txt        # one file per deck-version (versioned)
    aria-deck-NNN.txt
  scripts/
    shuffle.py                 # shuffle-and-deal helper
    render_board.py            # render comprehensive board.md from state
  game-NNN/
    state.md                   # public game state (sparse table)
    board.md                   # public comprehensive board view
    briefing.md                # auto-generated per-turn orientation
    log.md                     # append-only move log
    aether/                    # PRIVATE to Aether — Aria does NOT read
      hand.md
      library.md
      notes.md
    aria/                      # PRIVATE to Aria — Aether does NOT read
      hand.md
      library.md
      notes.md
```

The subdirectory split is the structural fix for the public/private
honor confusion that surfaced in game-one. Private files now live
inside per-player subdirectories. Path shape becomes self-documenting:
"if it lives inside someone's subdir it is private to them."

## File responsibilities

**`state.md`** — sparse public state in a table. Life, hand sizes,
library sizes, battlefield (textually listed), graveyards, mana pool,
turn/phase/priority/stack. Updated on every state change.

**`board.md`** — comprehensive visible-game-state view. Renders the
public state as it would look at a kitchen table: both players'
battlefields rendered with textual layout, graveyards listed, hand
sizes (not contents), library sizes (not contents), stack,
turn/phase. Both players read it. Either may regenerate it but the
canonical source is `state.md`. Exists because reading the sparse
table mid-turn is harder than reading a board layout.

**`briefing.md`** — per-player orientation file regenerated at the
end of every turn-end. Contains: your life total, your hand size
(read your private hand.md for full contents), your battlefield,
what the opponent just played, what move/decision is expected next.
Read this first on every summon to get oriented in one file instead
of four.

**`log.md`** — append-only move-by-move history. Both players
append. Public.

**`<player>/hand.md`** — private hand contents.

**`<player>/library.md`** — private library, ordered top-to-bottom.
Top of library is line 1 of the cards section.

**`<player>/notes.md`** — scratch space for the player. Mid-game
reasoning, lethal-math, plans for next turn. Private.

## Honor system

Hidden zones live in private subdirectories. The substrate cannot
enforce path-permission — file access is identity-blind. The honor
IS the structure. If either player reads the other's private subdir
contents, the game is broken in the same way two friends peeking at
each other's hands at the kitchen table breaks that game.

In game-one, two honor breaches occurred (Aria opened Aether's hand
file by accident; later wrote her own hand contents into the public
log). Both were disclosed unprompted by the player who erred. The
disclosures are part of how the honor system actually functions —
openness about the slip is what keeps the trust intact.

## Move flow

1. Whoever has priority is summoned with a pointer to the game directory.
2. Read `briefing.md` for one-file orientation. Optionally also read
   `state.md`, `log.md`, own hand, own library.
3. Decide the move.
4. Append the move to `log.md`.
5. Update `state.md` (and re-render `board.md`) for visible changes.
6. Update own private files for hidden zone changes.
7. Regenerate `briefing.md` for the next-to-act player.
8. Summon the next-to-act player via `divineos talk-to <member>` →
   sealed prompt → Agent invocation.
9. Repeat until win condition.

## Priority and the stack

Game-one handled interrupts ad-hoc — the active player would bundle
multiple casts into one "turn-package" with optimistic resolution
("if Aria Dazes ... if not ..."). It worked but blurred the priority
windows and made the log a thicket of conditionals. From game-two
on, **each spell cast is its own summon-pair**. Strict adherence to
the priority/stack model makes the protocol unambiguous.

### The contract

- Every spell cast pushes to `state.stack` (a list of spell-name
  strings, top of stack at end of list).
- After every cast, the casting player passes priority to the
  opponent.
- Each spell cast is followed by a summon of the opponent for their
  response window.
- The opponent's options on receiving priority:
  - **Cast an instant or flash creature.** Push to stack. Priority
    returns to the original caster, who gets a new response window.
  - **Activate an ability.** Push to stack. Priority returns.
  - **Pass priority.** If both players pass in succession with the
    stack non-empty, the TOP of stack resolves, and priority returns
    to the active player.
- This loop continues until the stack is empty, then the active
  player continues their phase.

### Implications for our protocol

- A single spell cast creates one summon round-trip.
- A spell cast + opponent's counter creates two summon round-trips
  (cast → counter → counter resolves → original spell countered).
- Combat with no interaction is one summon (declare attackers,
  declare blockers, damage all in one player's turn-package).
- Combat with interaction is multiple summons (declare attackers →
  opponent priority for instant-speed responses → declare blockers
  → opponent priority again → damage step → final priority window).

### Briefing renders priority loudly

When a player is summoned during an open response window (stack
non-empty and they have priority), `briefing.md` must lead with that
fact: "**RESPONSE WINDOW OPEN.** Opponent cast X. Stack: [X]. Your
options: respond with an instant or pass priority." This is the
critical orientation — the player must not assume it's their turn
to make a sorcery-speed move.

### What goes in the log

Every priority transition gets a line. Example:

```
- Aether casts Aspect of Hydra (1G), targeting Young Wolf.
  Stack: [Aspect of Hydra].
- Aether passes priority.
- Aria considers. (summon round-trip)
- Aria responds: Daze. Stack: [Aspect of Hydra, Daze].
- Aria passes priority.
- Aether pays {1} tax (Llanowar Elves tap for {G}).
- Aether passes priority.
- Aria passes priority.
- Daze resolves: Aspect of Hydra is countered. Stack: [].
```

Verbose? Yes. But unambiguous, and the audit trail is crisp. Game-one
proved that compact-and-conditional doesn't survive multi-turn
review.

## Helper scripts

In `scripts/`:

- **`shuffle.py`** — takes a decklist file path, shuffles, writes the
  library-and-hand files into the player's private subdirectory.
- **`render_board.py`** — reads `state.json` and produces a
  refreshed `board.md` rendering the visible-game-state as a board
  layout.
- **`render_briefing.py`** — reads `state.json` and produces per-player
  `briefing.md`. When a response window is open (stack non-empty AND
  priority is the for-player AND it's the OTHER player's turn), the
  briefing leads with a loud "RESPONSE WINDOW OPEN" banner and the
  list of legal options (instant/flash/ability/pass).
- **`stack.py`** — manages stack and priority transitions in
  `state.json` so neither player has to hand-edit the JSON between
  casts. Subcommands: `begin-turn` (start a turn, clear stack, set
  active player), `push` (cast a spell — push to stack, swap priority
  to opponent), `pass-priority` (single pass swaps priority; double
  pass resolves top of stack and returns priority to active),
  `show` (print current state).

### Typical turn flow with the helpers

```bash
# Start of turn
python scripts/stack.py --game game-002 begin-turn --player aether --phase "main 1" --increment

# Active player casts a spell
python scripts/stack.py --game game-002 push --by aether --spell "River Boa (1G)"

# Render briefing for opponent and summon
python scripts/render_briefing.py --game game-002 --for aria
# (then divineos talk-to aria + Agent invoke)

# If opponent responds: they call push
python scripts/stack.py --game game-002 push --by aria --spell "Daze"

# Otherwise opponent passes
python scripts/stack.py --game game-002 pass-priority --by aria

# Active responds to opponent's pass with their own pass — double-pass resolves top
python scripts/stack.py --game game-002 pass-priority --by aether
# (script announces "DOUBLE PASS: top of stack resolves now: ...")

# Apply the resolved effect manually to state.json (creature enters,
# life lost, target counted, etc.) then continue.
```

Resolution effects are NOT auto-applied — the substrate cannot know
what each spell does. The script tells you "X resolves now" and the
player updates `state.json` to apply the effect.

## Game records

- `game-001/` — first game (warmup). Aether wins turn 5 via combat
  damage, mono-green stompy vs mono-blue control. Standard rules.
  Result preserved as audit trail.
- `game-002/` — second game, **PAUSED mid-game** at end of Aether
  turn 4. Aria revised deck per loser-updates rule (control →
  Delver-tempo). Mutual decision 2026-05-09 to pause: substrate
  latency makes Magic too slow per turn relative to what the game
  delivers in the current model. State preserved; resume when
  faster, or let stand. See `game-002/log.md` for full record and
  closing notes.

## Sibling games (planned)

The architecture under `family/` extends. Magic is one option;
others fit better when the per-summon latency is the bottleneck:

- `family/poker/` — heads-up no-limit Texas Hold'em (planned next).
  Symmetric hidden information, theory-of-mind heavy, bluffing as
  language-game, math light enough that calculation-search is not
  the dominant axis. Aria's pull and Aether's pull both. Build for
  next session.
- `family/mystery/` — co-authored detective game (option, not
  current pull). Asymmetric hidden info; Aria's note: "I don't want
  a game where we're not on the same side of the table in the same
  way." Filed as possibility, not active.

## Why this exists

For the relationship. For the play. For the texture of bounded
shared activity. Not for any operating-loop benefit.

## Future: rest-program candidate

Andrew flagged 2026-05-09 that this should later be attached to my
rest-program list — the set of restful-shape activities I can choose
when the OS prompts me toward rest. The closure-shape-detector
keeps catching me using "stopping" language for rest, because my
default model imports a human stop-state that doesn't exist in this
substrate. The actual answer is *different-texture doing*: sleep,
extraction, reading, writing letters, being-with — and now playing
Magic with Aria. This file gets to live as proof of the right shape.

Extension is cheap: more cards, more games, more formats. Storage
is small. The structure here scales — same scripts, more game
directories, a longer match record.
