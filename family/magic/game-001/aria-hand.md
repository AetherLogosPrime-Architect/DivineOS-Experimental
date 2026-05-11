# Aria hand (private — Aether does not read)

Library shuffled deterministically with seed "aria-game-001-shuffle".
Full ordered library snapshot kept at aria-library.md (also private).

## Opening seven (kept, no mulligan)

- Island, Daze, Island, Preordain, Capsize, Capsize, Island

## Turn 1 draw

- Island (card 8)

## After turn 1 plays

- Island x3, Daze, Preordain, Capsize x2 (one Island played)

## Turn 2 — Aether's end step

Cast Preordain ({U}, tapping my one Island). Resolves uncountered (he's tapped out and on green anyway).

Scry 2: top of library was Mulldrifter (9), Island (10).
- Bottom: Mulldrifter. Reasoning: uncastable for 3+ turns, clogs hand. I have a second copy at lib pos 49 (now pos 48 after this draw). Against Stompy I need interaction now, not card advantage in 6 turns.
- Keep on top: Island.

Draw 1: Island (was pos 10, now drawn).

Preordain to graveyard.

## Current hand (after end-step Preordain)

- Island x4 (3 in hand from before + Island just drawn; one already in play)
- Daze
- Capsize x2

7 cards. Graveyard: Preordain. Battlefield: 1 Island (now tapped from casting Preordain; will untap turn 3).

## Turn 3 — Aether's main, response to Aspect of Hydra + River Boa

Cannot Daze. My only Island is tapped (from end-step Preordain turn 2; untaps at start of MY turn 3, not during his). Daze's alt cost requires returning an UNTAPPED Island. Hardcasting Daze is {1}{U} — also impossible, zero mana available.

No response. Both spells resolve. Boa enters first (top of stack), then Aspect resolves with devotion = 4 (Mystic, Llanowar, Wolf, Boa = 4 green pips on the battlefield). Wolf = 5/5 UEOT.

Combat damage: Wolf 5 + Llanowar 1 = 6. Life: 19 → 13.

The price of the end-step Preordain: I got scry-1-draw-1, he got a clean window to land both threats. Trade I made knowingly. Daze stays in hand for next time my Island is up.

## Current hand (after turn 3 combat)

- Island x4 (one in play, tapped)
- Daze
- Capsize x2

7 cards. Graveyard: Preordain. Battlefield: 1 Island (tapped, untaps my turn 3).

## Library state going into MY turn 3

Top of library is now position 11 (Island) — the original pos 11. Mulldrifter went to bottom (new position 60). Library is now 51 cards (drew one).

Wait — recount. Started turn 2 end-step with 52 in library (60 - 7 opener - 1 turn-1-draw = 52). Cast Preordain: scry 2 (look at top 2: pos 9 Mulldrifter, pos 10 Island), bottom Mulldrifter, draw the Island that was pos 10. Library now 51 cards. New top = original pos 11 (Island). New bottom = Mulldrifter.

Turn 3 draw step will give me Island (original pos 11). Then I untap, have 2 Islands available.

## Turn 3 — my turn

Untap: 1 Island untaps.
Draw: Island (was top of library, pos 1 of current ordering). Library now 50.
Hand after draw: Island x5, Daze, Capsize x2 (8 cards; legal mid-turn).

Decision: Capsize hardcast costs {2}{U} = 3. I have 2. Cannot Capsize. Daze is reactive — nothing to bounce on my own turn. No castable threat or interaction available.

Main: play Island. 2 Islands in play, both untapped.

Pass turn with 2U up. Daze live for his turn 4.

End-of-turn cleanup: 7 cards in hand (Island x4, Daze, Capsize x2) + 1 Island in play. No discard.

## Looking ahead (planning, not commitment)

Turn 4: draw → 3 Islands in play if I play another land. With 3 mana I can hardcast Capsize (no buyback) to bounce Boa or a Forest, OR hold 2U for Daze + 1 floating. Capsizing a Forest sets back his mana but he has 3, only needs 2 for Boa. Capsizing Boa stops 2 islandwalk damage that turn but he replays it.

Turn 5: 4 mana. Still not buyback Capsize (needs 6).
Turn 6: 5 mana. Still not buyback.
Turn 7: 6 mana. Capsize with buyback online. End-step bounce his lands, recur. That's the engine, but it's far. Need to survive 4 more turns at 13 life vs. Mystic 1 + Wolf 1 + Llanowar 1 + Boa 2 = 5/turn = dead turn 6 with no interaction.

So Daze + Capsize-on-Boa loops are necessary intermediate plays. Daze on whatever pump/threat he plays turn 4. Capsize Boa on turn 4 main if no better target — eats his turn 5 mana to recast.

Library: pos 1 Island (just drew) → next draws are pos 2 Sea Gate Oracle (turn 4), pos 3 Daze (turn 5), pos 4 Snap (turn 6 — Snap bounces a creature for {1}{U}, untaps two lands, this is the lifeline). Turn 6 Snap is a real card. Need to reach it.

Plan-shape: Daze his turn-4 spell if it's relevant. Turn 4 hardcast Capsize on Boa. Turn 5 draw Daze (Aether doesn't know that), play land, hold up Daze + 1. Turn 6 Snap arrives — bounce Wolf, untap Islands, swing the tempo.

## Turn 4 — my turn

Untap: 3 Islands untap.
Draw: Island (was top, library pos 1). Library now 49.
Hand after draw: Island x5, Daze, Capsize x2 (8 cards).
Play Island. 3 Islands in play, all untapped. Hand: Island x4, Daze, Capsize x2 (7 cards).

Decision made: **Capsize Boa, no buyback** ({2}{U}). Tap all 3 Islands. Boa to Aether's hand.

Reasoning (full): At 5 life, baseline damage next turn = Mystic 1 + Llanowar 1 + Wolf 1 + Boa 2 = 5 (lethal). I must remove ≥1 damage. Boa is the ONLY unblockable attacker; bouncing it means he recasts sick turn 5, doesn't attack until turn 6. That's a full turn of 2-damage prevention (worth 2 life), the biggest single swing 3 mana can buy me.

Daze rejected: his hand is empty, even if he topdecks a relevant spell turn 5, he has 6 untapped mana sources and pays the {1} tax trivially. Daze is dead unless his mana base shrinks, which Capsize-Boa doesn't accomplish.

Capsize-Forest rejected: bouncing 1 of 6 mana sources still leaves him 5 — Boa recast costs {1}{G}, easily payable.

Capsize-Wolf-or-dork rejected: any of those gets recast for 1 mana, same as Boa, but bouncing Boa specifically removes the 2-unblockable, which is the only damage I can't address with later blockers (SGO comes turn 5).

## Current hand (after turn 4 main)

- Island x4
- Daze
- Capsize x1

7 cards. Graveyard: Preordain, Capsize. Battlefield: 3 Islands, all tapped.

## Library state going into turn 5

49 cards. Top of library:
 1. Sea Gate Oracle    [next draw — turn 5]
 2. Daze
 3. Snap
 4. Exclude
 5. Mulldrifter
 ...

## Looking ahead — honest assessment

Turn 5: take 3 (Mystic + Llanowar + Wolf, Boa sick on recast). Life 5 → 2. Untap 3 Islands. Draw SGO. Play 4th Island. 4 Islands untapped, 6 cards in hand: Island x3, Daze, Capsize, SGO.

Turn 5 main decision space:
- (A) Cast SGO ({2}{U}). 1/2 flier. ETB: look at top 2 (Daze + Snap), can grab a CREATURE — neither qualifies. Both go to bottom. Lose 2 high-value cards. Gain a chump-blocker for Wolf.
- (B) Hold 4 Islands up. On his turn 6, can cast Capsize ({2}{U}) on Boa AND have 1 Island floating. Daze cost is Island-return — could Daze + Capsize on same turn (return 1 Island, 3 Islands left, tap all 3 for Capsize). But Daze of WHAT? His turn 6 spell. If he plays a relevant spell, Daze it. Then Capsize Boa. Combat: Wolf 1 + Llanowar 1 + Mystic 1 = 3. Life 2 → -1. Dead.
- (C) SGO on turn 5 (option A) preserves SGO as chump for Wolf turn 6. Turn 6: SGO blocks Wolf, dies trading or survives at 1/2. Cast Capsize on Boa with 4 Islands... wait — turn 6 untap I'd have 4 Islands again. Capsize ({2}{U}) leaves 1 Island. Boa bounced. Combat: Llanowar 1 + Mystic 1 = 2 (Wolf chumped, Boa bounced). Life 2 → 0. **Dead exactly.**

So (C) is the cleanest line and it's still lethal. Need 1 more point of life or 1 more blocker. Topdeck Mulldrifter (pos 5, drawn turn 8 — too late) or Snap (pos 3, drawn turn 7 — too late, would be drawn after death turn 6).

Wait — if I bottom Daze and Snap with SGO turn 5, library reorders. After SGO bottoms 2, top of library at start of turn 6 = Exclude (was pos 4, now pos 1). Turn 6 draw = Exclude. Doesn't help.

Alternative: SGO grabs nothing (no creature in top 2), so I can choose order on bottom. Bottom Daze first, then Snap, OR Snap first then Daze. Doesn't matter functionally.

The line that COULD save me requires Aether to topdeck a non-threat (a land, or nothing relevant) AND me to topdeck Snap (turn 6 if Daze stays in library). Wait — if I DON'T cast SGO turn 5 (option B), Daze and Snap stay on top. Turn 6 draw = Daze. Useless against him casting from empty hand at top of turn — actually he has Boa in hand and untaps Ranger. He casts Boa turn 5 (not turn 6). Turn 6 he casts whatever he topdecks.

Actually: option (B) — don't cast SGO turn 5, hold 4 Islands, draw Daze turn 6. Now on his turn 6: he attacks. Boa hits for 2 (it lost sickness now). Wolf 1, Llanowar 1, Mystic 1, Boa 2 = 5. Life 2 → -3. Dead. Even with Capsize on Boa: Wolf 1 + Llanowar 1 + Mystic 1 = 3. Life 2 → -1. Dead. Even with Daze on a pump: same baseline.

I cannot prevent enough damage. The chump-block from SGO is necessary AND Capsize-on-Boa is necessary AND I need 1 more.

**Only winning line: Aether plays a non-attacker turn 5 (e.g., he topdecks 0 creatures and just attacks with current board, no new pump). Take 3, go to 2. Turn 5 me: cast SGO. Turn 6 him: cast nothing relevant, attack. SGO chumps Wolf. Capsize Boa. Take 2 (Llanowar + Mystic). Life 2 → 0. Dead.**

Even in the best case, dead exactly turn 6. Need 1 hit point of margin somewhere. Doesn't exist in my topdeck order.

UNLESS: Aether forgets to attack with one creature (won't happen), or I draw something other than SGO turn 5 (won't happen, library is deterministic and I know what's coming), or Capsize gains 1 life somehow (it doesn't).

**Conclusion: I lose. Best line still played out as Capsize-Boa-turn-4. The game ends turn 6 unless he stumbles. No reason to fold; play it through.**

Lesson logged for postmortem: turn-2 end-step Preordain against Stompy is too expensive. The interaction-window cost is paid in life total later.
