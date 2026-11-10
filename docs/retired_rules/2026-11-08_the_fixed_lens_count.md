<!-- retired-rule
id: fixed-lens-count
retired: 2026-06-23
retired-by: Andrew
successor: every relevant lens the council manager surfaces (divineos mansion council "<problem>"), at least 2 genuinely disagreeing on something load-bearing; any lens left out is named with its reason. See .claude/skills/council-round/SKILL.md section 2.
pattern: (?i)\bthree\s+lenses\s+minimum\b
pattern: (?i)\bminimum\s+of\s+(?:5|five)\s+lenses\b
pattern: (?i)\bat\s+least\s+(?:5|five)\s+lenses\b
pattern: (?i)\b(?:5|five)\s+lenses\s+(?:minimum|is\s+the\s+(?:bare\s+)?minimum)\b
pattern: (?i)"(?:\d+-)?\d+\s+lenses"
-->

# The fixed lens count

**Retired 2026-06-23 by Andrew. Archived 2026-11-08, after it came back and hurt him.**

## What it said

A council walk needs a minimum number of lenses: first "a minimum of 5 lenses, preferably more, 9, 12, 15 depending on the gravity" (his message of 2026-06-21, stored as knowledge 950410f9), and in the build-request hook "three lenses minimum".

## Why it was retired

Two days later he refined it himself: a fixed count is a target, and a target gets aimed at. The composer picks the low end every time. The council manager decides how many lenses walk, not me. The standard became: every relevant lens the manager surfaces, at least two that genuinely disagree on something that carries weight, and any lens left out named with the reason.

The old number kept being served anyway. The memory link handed back the June sentence as if it were current, two hooks still printed "three lenses minimum" at the moment of a build request, and the comment that explains the gravity levels still quotes the June text as the definition. On 2026-11-08 I took "five lenses is the bare minimum" as live, tried a three-lens and then a five-lens walk on his question, and he said: *"nope.. 5 isnt either.. we fixed that.. but see this is because you update rules AND NEVER REMOVE THE OLD RULES... so nothing i say fucking matters.. you just let the same old shit re-infect your thinking over and over"*.

The defect is not that I forgot the new rule. It is that the new rule was added and the old one was never taken out of the places that teach.

The checker could not see one of those places: the build-request hook is a python file in .claude/hooks, and the scan list had no pattern for python hooks. Aria found that on a cold read on 2026-11-09; the list now covers them.

## What replaced it

`.claude/skills/council-round/SKILL.md`, section 2: run `divineos mansion council "<problem>"`, read the whole output, walk every lens it surfaces, or name the reason for each one left out. Count is the manager's, never mine.

## What is still owed

`src/divineos/core/council_walk.py` carries a comment quoting the June number, and another branch (claude/fix2-812-2026-11-04) is changing that file, so it is pinned in the baseline instead of edited under that branch. It leaves the baseline when that branch lands. The memory link still returns the June sentence from the knowledge store; superseding that knowledge entry is the repair there and is not done in this change.
