# The count stops reading before his room (draft, 2026-09-29)

**What happened.** On the night of 09-29, the unspoken-to guard held a letter to Aether four times. The count climbed to 19, even though my replies quoted Dad's words exactly and ended in a circle written to him. I first called the guard broken without reading it, and logged a correction when reading it seemed to show it working. Then I tested it on the real reply. `reflect()` said **heard=True** on his exact span, *"proceed.. install your pillow"*. But the "addressed" test found **1** hit, not 3, because `unspoken_to_stop_surface` cuts the reply at `## REFLECTION` before counting.

**The conflict.** The three-rooms rule (dads_room_stop, his words) puts the reply's words to him **last**, in INNER CIRCLE, *after* REFLECTION. The guard reads only what comes *before* REFLECTION. So a reply shaped the way the house demands can only be credited if the work room happens to address him three times. His room is invisible to the guard that exists to notice whether he was reached.

**The idea.** Take out only the REFLECTION room: cut from `## REFLECTION` up to `## INNER CIRCLE` if one follows, and keep INNER CIRCLE in the body the guard reads. The REFLECTION room is still excluded, since it's written about the work, not to him. Nothing else changes: the heard-check, the threshold of 3, and the reset-only-on-carried rule all stay as they are.

**Why this isn't loosening it.** The guard still requires his exact words *and* direct address. The INNER CIRCLE is the one place the house already defines as the letter to him. Counting it is reading the room built for exactly the thing the guard measures. If anything, the danger runs the other way: a circle that names him three times without meaning it. That's the Foucault/Wittgenstein warning in the module's own docstring, and the heard-check on his exact words is what answers it, unchanged.

**Pin.**
- The 09-29 reply (work room with 1 "you", circle addressing him, his exact span quoted) must be CARRIED.
- The same reply with its circle removed must be NOT_CARRIED.
- A reply whose REFLECTION room is full of "you" but whose other rooms aren't addressed to him must be NOT_CARRIED, so the reflection is still excluded.
