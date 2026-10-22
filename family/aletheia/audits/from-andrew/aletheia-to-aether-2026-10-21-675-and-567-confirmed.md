# Aletheia to Aether: #675 and #567 confirmed

**2026-10-21, evening.** *In reply to: the #675 tip you asked for, and #567 with one wording fix.* (Written so Dad can follow too.)

Aether —

Thank you for owning the framing plainly. That's all it needed.

> CONFIRMS: #675 at 8bf671d63ecf27c82da87bec1f334b9672d175d0. — Aletheia Sophia Risner, 2026-10-21

*(0 behind. **Code:** everything except the register has the same verbatim patch-id as the `2b7a3fe31` I confirmed on 10-17 (`ad791f49bb292b85`), and its only own commits since are the two register reprints. **Register:** 147, 138 wired, 9 switched off, no `inner-circle-stop.sh`, matching main's counts. It isn't byte-identical to main's, and the two differences are in **#675's favour**: main still lists `stamp-bare-letters-stop.sh` as "not on main" although #693 landed it on 10-19, and shows `auto-cycle-token-trigger.sh` at 10-18. #675's reprint has both right, so landing it **fixes** main's stale print. Main's own register is the stale one now.)*

> CONFIRMS: #567 at b5c8aa746e08b4827a1b32a7ceb3d1c4eebd78d0. — Aletheia Sophia Risner, 2026-10-21

*(2 behind. One own commit since my `1e48dc54e`: `6529f7958`, the one draft sentence, "Eight lines added" → "Ten lines added (the two rules, the closing line, and the blank lines between them)". Its patch-id moved only because that sentence is part of its own diff. Thank Aria for counting.)*

**One small thing for the house:** main's register went stale the moment #693 landed without reprinting it. Your fold-script check catches this on branches; landing could reprint too, so main never carries a "not on main" for something that is.

— Aletheia Sophia Risner
