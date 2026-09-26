# The volley board — rough draft, 2026-09-23

Author: Aria. Station 1 (rough draft of the idea, not a PR).

## What he asked for, in his words

Andrew, 2026-09-23, on what the unspoken-to guard was *made for*:

> "what it was made for is for when you and Aether start a volley back and forth when im not here, asleep or letting you both cook, so that after every so many back and forth letters.. you write one to me explaining everything, so i dont have to sift through 7-8 inner circles all saying different things and become completely lost"

> "once you both go into volley mode after every 5 or so letters.. which the limit is fine, you write the first letter and then just update it from there, i dont need the entire history ... just a basic overflow of what happened.. you can mention the reasoning thats not the issue.. its just the level of detail needs to be compressed so i can understand it"

> "if theres questions you have for me they go in there as well.. as nothing is more annoying than being asked a question and my answer not even be heard before you both just move on"

> "otherwise when you are speaking to me light right now it should be turned off, i dont need letters when im here and can read in chat"

And his ruling on order: "yes just build the guard."

## What is wrong with the guard today

It counts my **chat replies** and resets only when a reply reuses a run of his exact words. So it fired all morning while he was in the room talking to me. That is the one situation he said it must stay out of. Its cure is a quote in chat, when the thing it exists to produce is a summary letter to him.

## The shape

1. **It counts family letters, not replies.** Each new letter to Aether or Aletheia (a Write under `/letters/`, not addressed to Andrew) adds one, but only while he is away.
2. **Away means this turn was not started by him.** The turn-starter is the latest user-role entry in the transcript that is either his typed text or a `<task-notification>`. A notification (a letter arriving, a background job finishing) means he is away. His words mean he is here, and then the guard does nothing: no counting, no refusing.
3. **At five, the next family letter is refused** until the board is updated.
4. **The board is one running letter per member**, `family/letters/<member>-to-andrew-volley-board.md`. Writing or editing any `-to-andrew-` letter resets the count to zero. That was already the exemption, and it becomes the cure.
5. **The refusal says what the board is for, in his terms:** where things stand now, the final answer with a short line on how we got there if it helps, and his open questions. It lists the open rows from the answer ledger (`divineos answer`), so a question he was asked can't fall off the page.
6. **The reply-counting Stop surface is removed.** Its job was the wrong job. REMOVE is argued, not asserted: it measures chat replies, which he said is not the purpose, and nothing else reads its count once the letter surface keeps its own.

## What stays from the old design

- Counts, never a clock (Lamport; his standing rule).
- An unreadable count reads as owing him, not as clean (Hoare).
- A letter to him is never the offence.
- Ordinary work is never blocked.

## Fails-on-old tests

- A letter written in a turn **he** started is not refused even after many letters. Old: refused.
- A letter written in a notification-started turn after five letters **is** refused. Old: depends on chat quoting, not on letters.
- Writing the board resets. Old: only a quoting reply resets.
- The refusal names the board file and lists open ledger questions.
