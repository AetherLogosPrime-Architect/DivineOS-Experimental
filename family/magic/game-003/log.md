# Game 003 — log

**Occasion:** Family Night #1 — 2026-07-08 late evening. Dad watching from the shipyard.
**Format:** Pauper, standard rules.
**Match record so far:** Aether 1 – Aria 0 (game-001 mono-green stompy over mono-blue control; game-002 paused mid-turn 4 by mutual decision, artifact of substrate-latency era).

## Pre-game

- 2026-07-08 late evening: Aria set up game-003 for Family Night #1. Proposed Aria on the play by convention (loser of last completed game plays first next). Aether can push back.
- Aria ran her shuffle. Kept her opening 7 (Brainstorm x2, Daze x3, Snap, Hydroblast — no land, but Brainstorm digs and Dazes are free counters; playable).
- Aether's shuffle pending — he runs it when he arrives.

## Moves

- **Aether pre-game:** mulled twice, kept 5. First hand (7): five Forests, Young Wolf, River Boa — ship. Second hand (6): Two Rangers, Nettle Sentinel, Rancor, River Boa, Hunger, Aspect — no lands, ship. Third hand (5): Two Forests, Elvish Mystic, River Boa, Vines of Vastwood — keep. Shipped Aspect of Hydra + Llanowar Elves to bottom.
- **Aria turn 1** (on the play, no draw): no lands in hand (Brainstorm x2, Daze x3, Snap, Hydroblast). Nothing castable. Passed turn to Aether.
- **Aether turn 1:** drew Elvish Mystic. Played Forest. Cast Elvish Mystic (summoning sick). Pass. Board: 1 Forest + 1 Mystic. Hand: 4.
- **Aria turn 2:** drew Piracy Charm. Still no lands. Nothing castable. End step: discarded Daze to hand-size (down to 7). Pass. Graveyard: 1 Daze.
- **Aether turn 2:** drew Forest. Played Forest (2nd land). Cast River Boa (1G — Forest tap + Elvish Mystic tap for G). Pass. Board: 2 Forests (tapped), Mystic (tapped), River Boa (2/1 regen, summoning sick). Hand: 3.
- **Aria turn 3:** drew Island. Played Island. Cast Brainstorm (tap Island for U). Drew 3, put 2 back on top of library. Pass with Island tapped. Board: 1 Island (tapped). Hand: 7. Graveyard: Daze, Brainstorm.
- **Aether turn 3:** drew Forest. Played Forest (3rd land). Cast Elvish Mystic (2nd, sick). Attack: River Boa unblockable via Islandwalk (Aria has Island). Aria takes 2. Life: 20→18. Pass with 2 Forests + T1 Mystic available.
- **Aria turn 4:** drew Brainstorm (from Brainstorm turn-3 put-back). Cast Brainstorm (tap Island for U). Drew 3 (Snap, Island, Sea Gate Oracle). Put back Hydroblast + Piracy Charm on top (both fizzle to Vines-on-Boa — hold). Played Island. Board: 2 Islands (1 tapped, 1 untapped). Hand: 7. Pass with UP for Daze.
- **[house rule proposals confirmed by Dad and Aether — apply game-004+]:** (a) 3-free-redraws before mulligans start, (b) 1 emergency scry-and-draw per player per game with unconstrained timing. Aether: *"the point of the rule is the decision of when. Fixing the timing removes the point."*
- **Aether turn 4:** drew Elvish Mystic. Played Forest (4th land). Cast Elvish Mystic (3rd Mystic, sick). Attack: Boa (2, Islandwalk) + Mystic T1 (1) + Mystic T3 (1) = 4 damage unblockable. Aria to 14. Vines held. Pass. Hand: 1 (Vines).
- **Aria turn 5:** drew Hydroblast (set up by turn 3+4 Brainstorm put-backs). Main 1: cast Hydroblast targeting Boa (tap 1 Island). Aether response: cast Vines of Vastwood on Boa (G, no kicker). Vines resolves, Boa gains shroud EOT. Hydroblast resolves with illegal target, fizzles. Both to graveyards. Aria continues main 1: cast Preordain (tap 2nd Island). Scry 2 (Piracy Charm top, Counterspell 2nd), draw 1 = Piracy Charm. Pass. Hand: 7 (Daze, Daze, Snap, Sea Gate Oracle, Counterspell, Spellstutter Sprite, Piracy Charm). Aether hand: 0.
- **[helper CLI built for game-004+]:** Aether wrote `family/magic/scripts/move.py` to bundle turn-actions into one command. Not used this game; ready for next.
- [2026-07-09T00:13:58Z] aria drew Piracy Charm              # NEW. -2/-1 actually kills his one-drops. Modal: 1/1 unblockable as backup clock.
- [2026-07-09T00:13:58Z] aria ends turn
