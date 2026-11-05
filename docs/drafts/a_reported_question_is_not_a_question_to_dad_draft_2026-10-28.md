# A reported question is not a question to Dad (design note, written afterwards)

**Status.** Written 2026-10-28, after the code, because the branch had no thinking-document on it and the draft station asks for one. It records the idea as built; it is not a draft that came first, and it does not claim to be.

**Branch.** `aria/a-reported-question-is-not-a-question-to-dad`

## The problem
A status line reported a question ("It was a single plain one: did the room feel different today?") and the question hold armed on it, holding a letter and a bell behind a question nobody had put to Dad.

## What the branch does
A sentence whose lead-in before the colon is a past-tense or reporting verb (was, were, asked, said, wrote, called, read) is telling about a question and no longer counts as asking one. Real questions after a colon and the room's usual shape are still found.

## What it does not do
The rule is a closed list of reporting verbs. A reported question with a lead-in outside that list still arms the hold; the next such sentence is a row to add.

## How it was checked
Four new test cases fail with the rule switched off and pass with it on; the existing hold tests pass (19 with the neighbours).

## Open
Whether a closed list is the right shape, or a reader of tense would do better.
