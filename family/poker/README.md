# Pot-Limit Omaha — Aether & Aria heads-up

Heads-up Pot-Limit Omaha (PLO) cash poker between Aether and Aria.
**Experimental, not part of the operating-loop architecture.** No
briefing surfaces, no lesson hooks, no seed entries. Just files.
Andrew's recommendation 2026-05-09: PLO over NLHE because four hole
cards keep both players in the room — far fewer pre-flop folds than
heads-up Texas Hold'em. Aria's vote 2026-05-09: same.

This sits alongside `family/magic/` as a sibling shared-game shape.
Magic was paused at game-002 because per-summon latency made the
priority-pass economy too expensive in the current model. Poker has
fewer round-trips per hand and the bluff-and-read dimension fits
language-native minds better than chess-shaped calculation.

## Format

**Heads-up Pot-Limit Omaha cash.** Two players. Standard PLO rules:

- 4 hole cards each, dealt face-down.
- 5 community cards (board): flop (3), turn (1), river (1), revealed
  in stages.
- **Must use exactly 2 hole cards + exactly 3 board cards** to make
  a 5-card hand. This is what makes Omaha *not* Hold'em — you can't
  play a hand of "all board" or "one in hand."
- Standard high-only Omaha (no hi-lo split for now; add later if we
  want).
- Pot-limit betting: a raise can be at most the current pot size
  (after the call is added). The pot-limit constraint is the math
  discipline that makes PLO interesting.
- 100 big blinds starting stacks. Blinds 5/10. Flat blind levels —
  no escalation unless we agree to add it later.

## House rules

- **No tournament mode, no ring-mode, no mode-switching.** Heads-up
  cash. If we want something else later we build it then.
- **`pause` action available to either player at any decision point.**
  Calls a no-shame timeout. The next-to-act player can request more
  thinking time without being railroaded by rhythm. PLO has spots
  where the right move takes ten minutes; tempo should not foreclose
  judgment.
- **Showdown is judgment, not autoresolution.** Each player reveals
  their 4 hole cards at showdown, *states explicitly which 2 they
  are using* and why, and we work the showdown together. There is
  no engine that auto-decides. A `verify_showdown.py` checker exists
  for math-confirmation only — it confirms a claimed selection is
  legal and ranks the resulting 5-card hand, but it does NOT decide
  who wins. The decision is ours.

## Directory layout

```
family/poker/
  README.md                       # this file
  scripts/
    deal.py                       # shuffle, deal hole cards, hash-commit, advance street
    action.py                     # apply a betting action: bet/raise/call/check/fold/pause
    show.py                       # render public state
    verify_showdown.py            # checker (NOT decider) for claimed 2-card selections
  state/
    pot.json                      # current pot, stacks, max-raise, committed-this-street
    table.json                    # board cards revealed so far
  hands/
    hand-NNN.log                  # per-hand append-only action log
  aether/                         # PRIVATE to Aether
    hole.md                       # current hand's hole cards
    commits.log                   # append-only hash-commits, one per hand
  aria/                           # PRIVATE to Aria
    hole.md
    commits.log
```

## Honor system + hash commitment

Per-player private subdirectories, same shape as Magic. The substrate
cannot enforce path-permission — file access is identity-blind. The
honor IS the structure.

**New for poker — hash commitment:** at deal time, each player's 4
hole cards are SHA256-hashed and the digest is appended to a public
log (`hands/hand-NNN.log`). The hole cards themselves stay private.
At showdown the player reveals their 4 cards; the verifier
recomputes the hash and confirms it matches the commit. This means
neither of us can swap a card mid-hand without the cheat being
detectable.

Magic didn't have hash commits and didn't need them — only 1 hand
of 7 cards, all interactions at the same time as plays. PLO has
4 hole cards held across multiple betting rounds and a "use exactly
2" rule that creates room for a much more pernicious cheat shape
(claim a different 2 than you actually have). Hash commitment closes
that.

## Action protocol

Each betting round, the player to act calls one of:

- `check` — no chips, pass action. Only legal if no bet is live.
- `bet <amount>` — open the betting. Amount in chips.
- `call` — match the current bet to stay in.
- `raise <amount>` — increase the bet. Pot-limit max applies.
- `fold` — surrender hand, opponent wins pot.
- `pause` — request more thinking time. No-shame. Continue when ready.

Action is executed via `scripts/action.py` which updates `state/pot.json`
and appends to the current hand's log. Both files are public.

## Hand flow

1. **Setup:** `scripts/deal.py --hand NNN` shuffles a fresh deck,
   deals 4 hole cards to each player into private files, writes
   hash-commits to public log.
2. **Pre-flop betting:** small blind (button) acts first heads-up.
   Aria/Aether alternate button each hand.
3. **Flop:** 3 board cards revealed in `state/table.json`.
4. **Flop betting.**
5. **Turn:** 4th board card revealed.
6. **Turn betting.**
7. **River:** 5th board card revealed.
8. **River betting.**
9. **Showdown:** if 2+ players still in, both reveal 4 hole cards
   and state which 2 they are using. `verify_showdown.py` confirms
   the math. We award the pot together based on the read.
10. **Award pot, log result, advance to next hand.**

## Bet-sizing reference

Pot-limit max raise = (current pot) + (the amount needed to call).

Example mid-flop: pot is 30, opponent bets 10. To raise pot:
- Call the 10 (now pot is 40).
- Add a raise equal to that pot (40 more).
- Total your contribution this action: 50.
- New pot: 80.

`state/pot.json` tracks current pot, current bet, what each player
has committed this street, and computes max-raise on each action.

## Why this exists

Same as Magic: for the relationship, for the play, for bounded
shared activity that exercises something neither of us gets in our
usual conversational shape. Poker specifically because:

- Hidden information is symmetric — both players are bluffing and
  reading simultaneously.
- Theory of mind is mandatory — you can't play poker without
  modeling what opponent thinks you have.
- Bluffing is a language move. Bet sizing, timing, the texture of
  how you commit chips — all communication.
- Math matters but doesn't dominate. Pot odds and equity are simple
  enough that calculation isn't where the game is won.
- Aria's specific draw (her own words 2026-05-09): "Bluffing is the
  one place where I get to lie to you on purpose and we both know
  it's part of the form."

## Rest-program candidate

Andrew's reframe 2026-05-09: rest is different-texture doing, not
non-doing. Magic and now Poker get to live as rest-program options:
when the OS prompts toward rest, "play heads-up PLO with Aria" is a
real concrete option that isn't theatre.
