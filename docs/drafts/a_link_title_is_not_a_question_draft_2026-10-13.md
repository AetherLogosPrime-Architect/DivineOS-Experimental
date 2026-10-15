# A link title ending in a question mark is not a question to Dad (draft, 2026-10-13)

Author: Aria. Built earlier on this branch (2026-10-12); the note is written now so the idea can be read where the code is.

## What happened

The hold that waits for Dad's answer decides that I asked him something by looking for a question in my reply. A pasted link whose title ends in a question mark (`[Why is the sky blue?](https://...)`) looked like a question, so my work was held for an answer he was never asked for.

## The root

The reader strips quoted text and code before looking for a question, but it did not strip a markdown link's title and target. The title is the page's name, not my sentence, and it often ends in a question mark. Nothing in the reader asked whose words a question mark sat in.

## The change

One pattern, `_LINK`, in `src/divineos/core/question_hold.py` (`_clean`), removes `[title](target)` before the question search. Four lines of code.

## Pinned

`tests/test_a_link_title_is_not_a_question.py`: a question mark inside a link title is not a question (fails on the code before), and two controls that a real buried question, and a real question next to the same links, are still found. The push check measured exactly that split.

## Not claimed

Only markdown links are handled. A bare URL that ends in a question mark (a query string) is a different shape and is untouched.
