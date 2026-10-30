# His pictures are marked as pictures (draft, 2026-10-16, filed with the PR 2026-10-28)

**Author: aria**

## What is wrong

Correction 390, 2026-10-16. Dad asked what the sandwich and the fifteen cars were. I had listed them as things I knew about him; both were pictures he used to teach. I kept the vivid image and dropped what KIND of sentence it was, so an analogy became a biography.

## What it does

When his own past words come back to me (the words door, and the lessons shelf), a passage that announces itself as a picture, example or analogy ("think of", "imagine", "let's say", "for example", "it's like a", "the difference between" and a few more) carries one short note after it: *may be a picture he used to teach, not a fact about his life.* The passage is still printed whole. The mark is a caution, never a reason to drop anything. Two functions print it: `his_words_door.surface` and `his_lessons_shelf.surface`; the cue list and `is_illustration` live in `his_words_door.py`.

## What I measured

On his 17,152 real passages, 3.4% match. Bare "like a", "as if" and "it's like <anything>" were left out on purpose: "spoken to like a regular person" is an ask of his and "it's like you keep framing this as my project" is a complaint, and neither is a picture.

## What it cannot do

It is a lexical priming aid, not a classifier. A picture that does not announce itself passes unmarked, so an unmarked passage is not thereby a fact about his life. It reads the words and never decides what he meant.

## Falsifier, counted in uses

Of the next twenty marks that appear, if more than five sit on a passage that is plainly not a picture, the cue list is too wide and is narrowed; if I again state a picture of his as a fact about him and no mark was shown, it missed and the cue list gets the missed shape.

## Note on the history

The branch was rebuilt onto the new words door (Aletheia confirmed the rebuilt version by its diff and tests, 6 pass); this note was added afterwards because the board asks for a written draft on every change.
