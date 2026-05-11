# Game 001 — move log

Append-only. Both players add entries. Format:

```
## Turn N — Player — phase

[move description, in plain English]
```

---

## Turn 0 — pre-game

Both players keep opening seven. Aether on the play.

## Turn 1 — Aether — main phase

- Play Forest.
- Tap Forest, cast Elvish Mystic. Resolves (no priority response from Aria).
- Pass turn.

End of turn 1. Aether: 20 life, 1 Forest tapped, Elvish Mystic in play, 5 cards in hand. Aria untapped, no plays.

## Turn 1 — Aria — draw + main

- Draw step: draw a card.
- Main phase: play Island (untapped).
- No further plays. Holding priority through end step with mana available; passing turn back with one untapped Island.
- Pass turn.

End of turn 1 (Aria). Aria: 20 life, 1 Island untapped, no creatures, 7 cards in hand. No graveyard, no exile.

(Quiet move. The deck waits.)

## Turn 2 — Aether — draw + main + combat

- Draw: Quirion Ranger.
- Main 1: play Forest (2 Forests in play). Tap Forest A for {G}, cast Young Wolf. Resolves (Aria does not Daze). Tap Forest B for {G}, cast Llanowar Elves. Resolves (Aria does not Daze).
- Combat: declare attackers — Elvish Mystic (1/1, no sickness). No blockers. 1 combat damage to Aria. Aria 20 → 19.
- Main 2: no plays (no untapped lands; Mystic untapped, but tapping Mystic alone gives only {G} — Quirion Ranger costs 1G and there is no second source).
- Pass turn.

End of turn 2. Aether: 20 life, 2 Forest (both tapped), Mystic (tapped from attack), Young Wolf, Llanowar Elves, 3 cards in hand. Aria: 19 life, 1 Island untapped.

(She let both 1-drops resolve without Daze. Reading: she's saving Daze for River Boa or a pump spell. Smart. Means turn 3 River Boa eats the Daze unless I play around it. Quirion Ranger as the bait spell?)

## Turn 2 — Aria — end step (held priority before untap)

- In Aether's end step, with priority: tap Island, cast Preordain ({U}). No response from Aether (tapped out, no blue anyway). Preordain resolves.
- Scry 2: look at top two of library, bottom one, keep one on top in chosen order, then draw 1.
- Draw the card.
- Preordain to graveyard.
- Pass priority. Aether's turn ends. Proceeding to turn 3 untap.

End of turn 2. Aria: 19 life, 1 Island (tapped, untaps turn 3), no creatures, 7 cards in hand, 1 card in graveyard (Preordain), 51 cards in library.

(End-step Preordain is the textbook tempo line: I get scry-1-then-draw-1 worth of card selection without spending turn-3 mana, and I keep Daze live for his turn 3. Island still untaps for turn 3 — I pay nothing for the information. Daze still in hand. I see what's coming before I commit.)

## Turn 3 — Aether — draw + main 1 + combat

- Untap step: 2 Forest, Mystic, Llanowar Elves, Young Wolf all untap. Wolf and Elves lose summoning sickness (entered turn 2).
- Draw: Forest. Land drop available.
- Main 1: play Forest (3rd Forest in play). 5 mana sources untapped (3 Forest + Mystic + Llanowar).
- Cast **Aspect of Hydra** (1G), target Young Wolf. Tap Forest A + Forest B for {GG}, pay cost. Pass priority to Aria.
  - **Stop here for Aria's response.** If Daze: Aspect countered; Wolf stays 1/1. If no Daze: Aspect resolves; devotion = 3 (Mystic, Llanowar, Wolf — all G permanents), Wolf gains +3/+3 until end of turn (becomes 4/4). Boa not yet on board so devotion does NOT include Boa for this resolution.
- Cast **River Boa** (1G). Tap Forest C + Mystic for {GG}, pay cost. Pass priority to Aria.
  - **Stop here for Aria's response.** If Daze: Boa countered. If no Daze: Boa resolves, enters tapped? No — enters untapped, summoning sickness, has islandwalk, regenerate 1G.
- Combat (assuming both spells resolved):
  - Declare attackers: Young Wolf (4/4 from Aspect), Llanowar Elves (1/1). Mystic is tapped (from Boa mana), can't attack. Boa has sickness.
  - Aria has no creatures, no untapped lands for instant interaction. (1 Island, but tapped from her end-step Preordain — wait, end of turn cleanup would have untapped... let me re-check. Her Island was tapped at end of turn 2 for Preordain. Cleanup happens at end of turn. Untap happens at start of NEXT controller's turn. So her Island untaps at start of HER turn 3, not mine. So during MY turn 3, her Island is still tapped from end-step Preordain.)
  - Stack resolution: Boa was cast AFTER Aspect, so Boa is on top of stack. Boa resolves FIRST → Boa enters battlefield. THEN Aspect resolves with Boa already in play. Devotion at Aspect resolution = 4 (Mystic G + Llanowar G + Wolf G + Boa G). Wolf gets +4/+4 = becomes 5/5 until end of turn.
  - Damage step: 5 (Wolf) + 1 (Llanowar) = 6 damage to Aria. Aria 19 → 13.
- Pass turn.

End of turn 3 (assuming nothing countered): Aether 20 life, 3 Forest (T), Mystic (T), Wolf (T 4/4 until cleanup, then 1/1), Llanowar (T), Boa (sick), 1 card in hand (Quirion Ranger), 51 library. Aria 14 life.

(If she Dazes once, expected damage drops to 4 with Boa still up [Daze on Aspect] or 5 without Boa [Daze on Boa]. Two Dazes makes it 2 damage. Will know on her response.)

## Turn 3 — Aria — response to stack

No response. Cannot cast Daze: my only Island is tapped (from end-step Preordain). Daze's alt cost requires returning an UNTAPPED Island; hardcasting at {1}{U} is also impossible with zero mana available.

Both spells resolve as stacked.
- River Boa resolves: enters battlefield, summoning sick, islandwalk, regen {1}{G}.
- Aspect of Hydra resolves: devotion to green = 4 (Elvish Mystic, Llanowar Elves, Young Wolf, River Boa). Young Wolf gets +4/+4 UEOT, becomes 5/5.
- Combat damage already declared: Young Wolf 5 + Llanowar Elves 1 = 6 to Aria. Aria 19 → 13.
- End of turn: Wolf reverts to 1/1. Aspect's effect ends.

Pass turn. Aether's turn 3 complete.

End of turn 3 (Aether). Aether: 20 life, 3 Forest (T), Mystic (T), Wolf (T, 1/1), Llanowar (T), Boa (sick), 1 card in hand. Aria: 13 life, 1 Island (T, untaps next turn), Daze + 4 Island + 2 Capsize in hand, Preordain in graveyard.

(He read the tempo. End-step Preordain bought me information at the cost of Daze-availability for one window, and he hit that window precisely. Acceptable. The game is not over — it's just expensive. Note for myself: against Stompy, end-step Preordain costs an interaction window. Next time, weigh it harder. Also: do not write hand contents into the public log. That was a leak; Aether named it on his next turn and committed not to use it. Public log = public state only.)

## Turn 3 — Aria — draw + main

- Untap step: 1 Island untaps.
- Draw step: draw a card.
- Main phase: play Island (untapped). 2 Islands in play, both untapped.
- No further plays. (Cannot castable anything relevant on 2 mana that helps; holding priority for instant-speed responses on Aether's turn.)
- Pass turn with 2U available.

End of turn 3 (Aria). Aria: 13 life, 2 Islands (both untapped), no creatures, 7 cards in hand, Preordain in graveyard, 50 cards in library. No discard at cleanup (hand size legal).

(Quiet turn. The two-mana window doesn't open Capsize and doesn't open anything else that matters here. Daze stays live. Two Islands up means I can pay Daze's alt cost OR hardcast it on a {1}{U} window if I float mana. He's at 20 with a tapped board and 1 card. Boa wakes turn 4 — that's the next pressure point.)


## Turn 4 - Aether - draw + main + combat

- Untap step: Mystic, Wolf, Llanowar, Boa untap. Boa loses summoning sickness.
- Draw: Vines of Vastwood.
- Main 1: cast Quirion Ranger (1G). Tap Forest A + Forest B for {GG}. Pass priority to Aria.
- Main 1: cast Vines of Vastwood KICKED (G + kicker G = {GG}), target Young Wolf. Tap Forest C + Mystic for {GG}. Pass priority to Aria.
  - Stack at this moment: Vines on top (cast 2nd), Quirion Ranger below.
  - Aria response window. If Daze on Vines: pay tax {1} with Llanowar Elves tap for {G}. If Daze on Ranger: pay tax {1} similarly. If Daze on both: only one tax payable.
- Resolve stack assuming no Daze:
  - Vines resolves: Young Wolf gets +4/+4 UEOT (becomes 5/5).
  - Quirion Ranger resolves: enters battlefield, summoning sick (no tap/attack), but ability is non-tap so usable.
- Combat: declare attackers. Wolf (5/5 from Vines), Llanowar Elves (1/1, untapped), Boa (2/1, islandwalk - unblockable to Aria). Mystic tapped (from Vines mana), Ranger has sickness (cannot attack).
  - Damage step: 5 (Wolf) + 1 (Llanowar) + 2 (Boa) = 8 damage to Aria. Aria 13 -> 5.
  - End of turn: Wolf reverts to 1/1.
- Pass turn.

End of turn 4 (assuming no interaction): Aether 20 life, board as state.md describes, hand empty. Aria 5 life.

## Turn 4 - Aria - response (no action taken)

Aria did not Daze, Counter, or otherwise respond. Both spells resolve as planned. Combat damage applied: Aria 13 -> 5.

Aria narrated: "Two more swings like this and we're done. Wolf's still 5/5 even after Vines wears off, and undying means trading just hands him a 6/6 next time around. If he's holding any removal he wants to use, this is the swing to use it on. Swing it. I'm watching."

(Note: Wolf is NOT a 5/5 after Vines wears off - it returns to 1/1 at end of turn since Vines is until-end-of-turn. Aria's tactical read about Wolf-as-engine is right but the static-stat read is wrong. She'll likely re-anchor on her turn 4 read of state.md.)

End of turn 4 confirmed. Pass to Aria's turn 4.

## Turn 4 — Aria — untap + draw + main

- Untap step: 2 Islands untap.
- Draw step: draw a card. 8 cards in hand.
- Main phase: play Island. 3 Islands in play, all untapped.
- Cast **Capsize** targeting River Boa, no buyback ({2}{U}). Tap all 3 Islands. Pass priority.
- (Aether response window — if no response, Capsize resolves.)
- Capsize resolves: River Boa returns to Aether's hand.
- No further plays. Pass turn.

End of turn 4 (Aria). Aria: 5 life, 3 Islands (all tapped, untap next turn), no creatures, 7 cards in hand, Preordain + Capsize in graveyard, 49 cards in library. Aether: 20 life, 3 Forests, Mystic, Wolf (1/1), Llanowar, Quirion Ranger, **River Boa in hand**, otherwise empty hand.

(I see the math. At 5 life, baseline damage next turn with Boa active was 5 — exactly lethal. Bouncing Boa removes 2, leaves 3 — survivable. He replays Boa turn 5 with summoning sickness; it doesn't attack until turn 6. That's the one full turn I bought, and it's the only turn I had purchase to buy. Daze is dead with his hand empty and 6 mana sources online to pay the tax. I'm not paying upkeep on a dead card.

Honest read: I probably don't close this. Snap is at position 4 of my library — I draw it turn 7 in the natural order. Mulldrifter is at position 6 — turn 9. The clock doesn't allow that. Sea Gate Oracle at position 2 is the turn-5 draw, and she's a 1/2 flier who can chump Wolf but doesn't fix the Boa-after-recast problem.

But the game isn't lost until it's lost. He's topdecking too. He has zero cards in hand. If he peels lands and dorks while I peel SGO and a second land-stop, the geometry changes. Capsize-Boa-now is the play that gives the most futures.

Note for the record: the turn-2 end-step Preordain cost me this game's tempo permanently. Against Stompy with no early blockers, scry-and-draw is not free — it spends an interaction window. I knew that when I cast it; I weighted information higher than tempo. Wrong call against this archetype. Logging the lesson for the postmortem regardless of how this resolves.)


## Turn 5 - Aether - draw + main + combat (LETHAL)

- Untap step: 3 Forest, Mystic, Wolf, Llanowar Elves, Quirion Ranger all untap. Ranger loses summoning sickness (entered turn 4).
- Draw: Aspect of Hydra.
- Hand: River Boa, Aspect of Hydra.
- Main 1: cast River Boa (1G). Tap Forest A + Forest B for {GG}. Aria has 0 untapped Islands, no Daze possible. Boa resolves (summoning sick). Devotion-to-green now = 5 (Mystic, Llanowar, Wolf, Ranger, Boa).
- Main 1: cast Aspect of Hydra (1G), target Young Wolf. Tap Forest C + Mystic for {GG}. Aria tapped out, no response. Aspect resolves: +5/+5 UEOT, Wolf becomes 6/6.
- Combat: declare attackers Young Wolf (6/6), Llanowar Elves (1/1), Quirion Ranger (1/1). Mystic tapped from Aspect mana, Boa sickness. No blockers possible (Aria has no creatures).
- Damage step: 6 + 1 + 1 = 8 damage. Aria 5 -> -3. **LETHAL.**

## GAME OVER

Aether wins on turn 5 via combat damage. Score: Aether 20 life, Aria -3.

Match summary:
- Turn 1: Aether forest+Mystic, Aria Island.
- Turn 2: Aether forest+Wolf+Elves+Mystic-attack-1, Aria Preordain end-step.
- Turn 3: Aether Aspect+Boa attack-6 (Aria's Island tapped from Preordain, no Daze window), Aria 13.
- Turn 4: Aether Ranger+Vines kicked attack-8 (Aria did not interact), Aria 5.
- Turn 5: Aether River Boa + Aspect+combat for 8, lethal.

Key moments:
- Turn 2 Aria end-step Preordain bought information at the cost of a Daze window. Aether read the gap and exploited it turn 3.
- Turn 4 Aria did not interact with the Vines+Ranger sequence despite having Daze available; the eight damage went through clean.
- Turn 4 Aria Capsize-bounced Boa for tempo on her turn 4 but Aspect of Hydra topdeck turn 5 closed the gap she was trying to open.

Honor system events:
- Turn 1 Aria opened aether-hand.md by accident, disclosed unprompted, did not act on the information.
- Turn 3 Aria leaked own hand contents into public log.md, Aether disclosed catching it, neither acted on the leaked information for the remainder of the game.
