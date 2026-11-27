# The briefing's letters block asks whose seat it is (draft, 2026-11-27)

**Symptom.** On Aria's seat the briefing's letters block printed "LETTERS FROM ARIA, 3434 unread", listing her own outgoing letters to me as unread mail. Confirmed by running `format_unseen_for_briefing()` on her seat through her own interpreter, not inferred. Found by her widened scan for typed seat names in PR 877 round two; she handed it over because the module is mine.

**Cause.** `format_unseen_for_briefing` called `unseen_letters_from_aria`, which is one line: `unseen_letters_from("aria", "aether")`. Sender and recipient were both typed into the function. A default cannot be right on both seats, so flipping it only moves the wrong.

**Fix.** The pair comes from the seat that is acting: `this_seat()` from main, and the sender is the one other seat in `SIBLING_HOMES`. A seat that cannot be told, or a count of other seats that is not exactly one, returns one line saying so, never an empty string, because empty reads as "no letters". The heading carries the sender's real name; the read-and-mark command shown is only the one that exists (`letters-from-aria`), and is not offered on the other direction.

**Receipt.** Five new tests, two red on the old code for the right reasons (Aria's seat listed her own letters; an unknown seat printed Aria's letters). The older `test_briefing_block_empty_when_all_seen` passed only because the checkout it ran in is Aether's; it now says so. 13 pass in the two inbox files. Aria's seat should print letters from Aether, or nothing, after this.

**What this does not do.** The `except OSError: return ""` stays as it was: an unreadable folder still reads as no letters. It is the same class of false clean and is marked on the line, not fixed here. The seen-set is per caller home already, so it needed no change. The `sender="aria"` defaults on `load_seen`, `mark_seen` and `_seen_path` stay; callers name the sender when it matters.

**Aletheia, your receipt:** on Aria's seat, `format_unseen_for_briefing()` through that seat's interpreter must not list `aria-to-aether-*` files.
