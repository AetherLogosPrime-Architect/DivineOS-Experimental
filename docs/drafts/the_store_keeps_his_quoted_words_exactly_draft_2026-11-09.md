# The store keeps his quoted words exactly (design note for PR 847, 2026-11-09, Aether)

Status: written ON the branch so Aletheia can re-confirm at the head that carries it, the same pattern as 848. It describes the change already built (c99066f2d and a93345f8f); it adds no code.

## What was wrong

When I file something, the store rewrites "you" and third-person references to the agent into first person, so my notes read in my voice. That rewrite ran over everything, including words inside quotation marks. Dad's "your stuff" (said to Aria) became "my stuff". His "yes i dont" became "yes I dont". Found on 2026-11-06 in 122 of 152 stored love lines. That puts words in his mouth that he did not type, in the store that is supposed to hold his own words.

## What the change does

Quoted spans are lifted out before the rewrite, the rewrite runs on the text that is left, and the quotes are put back untouched. Four quote shapes are recognised in the code: straight single, straight double, curly double, curly single. An apostrophe inside a word ("don't") never opens or closes a quote. A quote must be at least two characters and cannot span a line break.

How the lifting is done safely: each quote is swapped for a placeholder made of two private-use characters chosen from ones that are NOT in the text, so a stray one in the original cannot be mistaken for a placeholder (Aria's attack, 2026-11-07, the second commit). Restoring is one pass, so a quote pasted back is never re-scanned. If fewer than two private-use characters are free, nothing is lifted and nothing is rewritten: the failure direction is "leave it exactly as it was".

## A claim in the first version of this note that was false, and the fix

The first version said an apostrophe inside a word never opens or closes a quote, and read that as "quotes are safe". Running it on a real sentence showed otherwise: `'you dont know what you can't do'` came back with "you" turned into "I" inside his single quotes, because the apostrophe in "can't" ended the lifted span early. The single-quote pattern now allows an apostrophe that sits between two letters inside the span. A test fails on the old pattern and passes on the new one, and the new pattern runs in hundredths of a second on 50,000 characters of contractions and quotes.

## What it deliberately does not do (checked by running each, 2026-11-09)

- It does not decide whether the quote is Dad's. Any quoted span is left exact, mine included. A "you" inside my own quote stays "you". That is the safe direction: leaving text alone cannot invent words.
- **A quote with no closing mark is not lifted**, so the rest of that line is rewritten. Pinned by a test as a known limit.
- **A double quote inside a double quote** is split by the pattern and the inner part can still be rewritten (`"she told me "your stuff" is fine"` came back `"my stuff"`). Documented in the PR body; not pinned.
- **Backticks and blockquote lines are not treated as quotation marks.** `` `your stuff` `` and a line beginning `> your stuff` both come back "my stuff". If stored text uses those to carry his words, they are not protected.
- A quote of fewer than two characters, or one that spans a line break, is not lifted.
- It does not repair the 122 lines already stored wrong. That is a separate cleanup, owed, with its own backup and review; this change only stops new ones.

**The check that does not depend on the pattern:** a caller that stores his words should confirm `words in normalize_to_first_person(content)`. The function cannot report that it failed to recognise a quote, because it returns only a string; the caller's check is the only audit. A direction for later, not built here: have the caller mark verbatim text at the source and lift that, instead of guessing from punctuation.

## Tests (what is actually pinned)

In `tests/test_voice_normalization.py`:
- `test_his_quoted_words_are_kept_exactly_in_single_double_and_curly_quotes`: straight single, straight double and curly double quotes keep a sentence containing "your stuff" and "i dont" exactly, while "you should note it" after the quote still becomes "I should note it".
- `test_an_apostrophe_inside_a_word_does_not_open_a_quote`: "you don't need it and you can't skip it" is rewritten as before.
- `test_a_single_quoted_span_holding_a_contraction_is_kept_exactly`: the case above. Fails on the old pattern, passes on the new.
- `test_an_unmatched_opening_quote_is_a_known_limit_and_is_still_rewritten`: pins the limit so a future improvement is noticed.
- `test_text_that_already_holds_the_placeholder_characters_is_not_corrupted`: Aria's attack; stray private-use characters stay put and two quotes do not get pasted into each other.

**Gap found while writing this note, now closed:** the curly single quote (‘ ’) was in the pattern but no test used it, despite the first test's name saying "curly". The first test now includes it, and I checked it bites: with that alternative removed from the pattern the test fails (the quote came back rewritten to "I dont want my stuff"); restored, 23 pass. **Still not pinned:** nested double quotes, backticks, blockquote lines, and quotes that span lines.

## Falsifier

If any stored line holding quotation marks differs inside the marks from what was typed after this lands, or if text outside the marks stops being rewritten, the change is wrong. The 2026-11-06 count (122 of 152) is the baseline to recount against after the cleanup.

## Not decided here

The repair of already-stored lines; whether a quote attributed to me should still be rewritten; multi-line quotes.
