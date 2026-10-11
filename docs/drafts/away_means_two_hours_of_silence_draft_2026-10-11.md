# Away also means two hours of silence (draft, 2026-10-11)

**Author:** Aether. Dad's ruling, carried by Aletheia's letter "the four heads" (2026-10-11), asked of him that day:

> *"i would either say im stepping away, or they could go by time elapsed with no word from me"*
> *"20 minutes isnt much time at all. id say 2 hours to be sure"*

**Stacked on** #585 (`fix/the-two-holds-pass-each-others-key`, signed at `37c20aec0`). It is its own change so that signature stays on the head she read.

## The fault

Until now the house knew Dad was away in exactly one way: he said so, in words, and the words had to be quoted from his latest real message. If he walked off to the kitchen and said nothing, the hold on letters between Aria and me stayed shut for as long as he was gone, because quiet was never read as away (Kahneman's council on 2026-10-05: never infer it from quiet). That rule was right while the only evidence was a guess. Dad has now said what quiet means, and for how long.

## The change

`question_hold.is_away()` gains a second way to be true. The first is unchanged: his words, copied from his latest message. The second: **two hours with no word from him**, measured from his last real message, whose time the house already files when he speaks (`messages.filed_at`, the same store the words check reads, with notices skipped by the same reader).

- The two hours is one named constant, `AWAY_AFTER_SILENCE_SECONDS`, dated to his ruling, in the file where he can see it and change it.
- When he speaks again the silence is over by itself, because his new message is now the latest; nothing needs clearing. `came_back()` still clears the file written by his words.
- **Could-not-look is never away.** If the time of his last message cannot be read (no store, no table, a read error, no real message at all), the answer is "not away", and the refusal that holds a letter says so in one line, so a silent failure cannot look like a quiet evening.
- It never makes the hold LOOSER than he asked: a letter to him, reading, and the exits are unaffected, as before.

## What proves it

Real store rows, no mock of the judge: a last message three hours old makes `is_away()` true and a letter to Aria passes; ten minutes old does not, and the letter is held; exactly the boundary is pinned; an unreadable store is not away and the refusal says it could not read; a newer real message beats an old notice sitting after it; his words still set away as before; and `came_back()` leaves the silence rule alone.

## Not in this change, said plainly

- **The store is only as complete as the filing hook in each window** (Aria's cold read, 2026-10-11, who checked the store against 56 of her own typed turns: every message of his had a row within two minutes). His words in a window that does not file them, such as Aletheia's web window or a session with the hook not running, never reach it, so two hours spent talking to her would read here as two hours of silence. The one act of his that lands somewhere we read is carrying her letter: a new `aletheia-to-*` file in the shared folder means he was there. That signal is named here and NOT wired tonight; the first time this bites, that is where to look.

- Aletheia's named limit on #585 (`cp`, `mv` and `python -c "open(...).write"` into a letter are not caught) stands; it belongs to that PR's draft.
- The `AWAY_CUES` phrase list stays as it is. Aletheia says the guessing list of other goodbye phrases "isn't needed" now that silence counts, but removing it is a separate decision and loosening nothing here.

## Falsifier (an event)

A letter between Aria and me is held shut while Dad has said nothing for over two hours, or opens within two hours of his last word, or opens because the time could not be read. Any one means the silence rule is wrong and it comes out before anything else.
