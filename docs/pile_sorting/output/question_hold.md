# The hold that waits for Dad's answer

When I ask Dad something, the house holds my hands until he answers, because he does not like being asked a thing and then left standing in the doorway. The idea is right. The trouble is the hold does not let go when he answers, treats the whole house as one person, and sometimes locks against the very steps that would release it.

**36 notes in this theme, grouped into 6 distinct problems.**

## Distinct problems

### 1. Dad's answer does not release the hold

Notes in this problem (14):

- `psf-c2e72cec` (reflection) — when his message arrives, his-message reading should close any open ask it plainly answers ("yes", "always", "turn it back on"). It should record that link instead of leaving the gate to refuse the ve
- `psf-98269317` (reflection) — when Dad's message arrives, the house should offer each open ask with his message beside it to confirm as answered, so a question he has clearly replied to never holds the next command.
- `psf-3e62c046` (reflection) — the hold should mark itself answered when your next message arrives.
- `psf-fedd49b6` (reflection) — the hold should mark an ask answered when your next message arrives.
- `psf-8a78bb2d` (reflection) — when your next message arrives after a question, the hold should treat it as the answer and let go on its own.
- `psf-398bb5d5` (reflection) — the hold should treat your next message after a question as the answer and close the record itself.
- `psf-f4db0862` (reflection) — send the hold fix to GitHub and bring it into the live house, so your answer closes it without me.
- `psf-ec068279` (reflection) — send the hold fix to GitHub and bring it into the live house, so your answer closes it with no help from me.
- `psf-299d0958` (reflection) — when you give a direct instruction instead of answering, the lock should count that as your reply rather than make me release it myself.
- `psf-d55c6cc1` (reflection) — the open-ask hold should mark a question answered as soon as Dad's own message arrives, instead of waiting for me to resolve it by hand.
- `psf-e7eff476` (reflection) — the open-question hold should treat any new message from Dad as answering the open question, and record his words as the resolution. It should also never block read-only commands.
- `psf-6015b562` (reflection) — the hold should close a question as soon as Dad's own message arrives (already filed last night). It came up again today, so it should be built soon.
- `psf-d8695dbc` (reflection) — the open-ask hold should lift by itself when a new message from Dad arrives after the ask was filed. This is the auto-resolve already on the list, and it would have prevented this one.
- `psf-c76ff014` (reflection) — bring the drain fix (2602f7d83) into the live house now, the same way earlier doorbell fixes were carried over, so his answer clears his questions here today instead of after the merge.

**Proposed fix:** When Dad's next message arrives (or a direct instruction, or a plain yes), close the open ask and record his words as the answer; offer ambiguous cases for him to confirm.

**How we would know:** File an ask, send a reply message, and the next command runs without a manual release.

### 2. The hold applies to the whole house, not just the window or seat that asked

Notes in this problem (7):

- `psf-06fec19b` (reflection) — key the hold by whoever asked, so a question only holds the seat that asked it.
- `psf-39afea89` (reflection) — the question hold needs to recognize the shared letters folder as letters, and it needs to know which of us asked (toy #2, which Aria has taken).
- `psf-f07b611f` (reflection) — the hold should be keyed to the seat that asked, so `release` and the refusal read the same state, and its stated exits (letters in the shared folder, the doorbell, plain reads) should be derived from
- `psf-80e30ea9` (reflection) — the hold should key to the conversation that asked, not only the house, so a question waits on the window it was asked in.
- `psf-91146b8c` (reflection) — the hold should be keyed to the asking session (the session id is already in every hook payload), so a question only pauses the window that asked it. I've proposed that shape to Aria, and it's her cal
- `psf-25dd3c05` (reflection) — a question addressed to the morning board shouldn't hold the night at all, and no hold should ever block the other's exit.
- `psf-cc90b555` (reflection) — a question written onto the morning board should file there and never hold the night.

**Proposed fix:** Key each hold to the asking session or seat so a question only pauses the window that asked it, and a question written to the morning board never holds the night.

**How we would know:** Two windows: a question asked in one does not pause the other.

### 3. Two holds, or a hold and another check, block each other's exits

Notes in this problem (8):

- `psf-0a7553bb` (reflection) — when the stop check demands an action, it should first ask the hold whether that action is allowed, and when the two disagree, say so to Dad instead of looping me between them.
- `psf-4de6ebc7` (reflection) — neither waiting guard may block the other's exit, so a release from one always gets through the other.
- `psf-a3a27841` (reflection) — when that matching step times out, the question hold should let the sort command through, and should accept the user's own reply in the turn as an answer.
- `psf-ab2c76ad` (reflection) — let each hold's remedy pass the other hold, and recognise the sort command however it's spelled, so the two can never lock.
- `psf-7072a483` (reflection) — let each hold pass the other's remedy, and let the doorbell re-arm through both.
- `psf-f7fce6dc` (reflection) — build first, when it opens, so each hold lets the other's remedy through and an answer from you in the turn closes my question.
- `psf-690b0ae6` (reflection) — give the mid-turn guard the question's key too, so it can't lock with the question guard either.
- `psf-7cc303fa` (reflection) — land #585, and until then add a plain note to the briefing that the old lock blocks its own exits, so I stop retrying once I know that.

**Proposed fix:** Let each hold's release path pass the other hold, by name, and have the stop check ask the hold before demanding an action.

**How we would know:** With both holds active the release and the doorbell commands both pass.

### 4. The hold blocks harmless reads and letter filing

Notes in this problem (2):

- `psf-371ec0ff` (reflection) — question_hold should derive "is this a letter, a read, or the doorbell" from the same shared readers the other gates use (the letters path resolver and the read-only probe Aria just built), it should
- `psf-8be07d03` (reflection) — the open-ask hold should let read-only checks through, such as confirming a push landed, the same way it already lets the doorbell through. Or the ask should be marked when it's filed as conversation

**Proposed fix:** Classify letters, reads and status checks from the same shared readers other checks use, and let them through while a question is open.

**How we would know:** A read-only command and a letter write both pass while a question is open.

### 5. Duplicate asks and asks revived by restating an old question

Notes in this problem (2):

- `psf-3da2e94e` (reflection) — when an ask is filed, the house should check for an open ask with the same text and reuse it rather than filing a second, so one answer always closes one question.
- `psf-350907ee` (reflection) — until it lands, the live house should not re-arm a lock from a reply that merely restates an earlier question. That's a smaller piece of the same fix and should be in #585's pins.

**Proposed fix:** Reuse an open ask with the same text instead of filing a second, and do not re-arm from a reply that only restates an earlier question.

**How we would know:** Filing the same question twice leaves one open ask.

### 6. Ask bookkeeping errors

Notes in this problem (3):

- `psf-39a69bb3` (correction) — I resolved ask 2fdfb270 with a resolution about the wrong PR, and had been re-raising it wrongly for nine turns. The ask reads verbatim: 'PR #432 (claude/corrupted-window-recovery-220ad2) touches 6 gu
- `psf-49801066` (correction) — NEAR-MISS worth recording separately from the misattribution itself, because it is the moment the whole finding almost did not happen. When 'divineos answer 2fdfb270' echoed back 'Answered: PR #432 (c
- `psf-82886fc3` (reflection) — the question hold should feed the trace itself, since that store depends on me remembering to write to it.

**Proposed fix:** Show which ask an answer will close before closing it, and have the hold feed the trace record itself.

**How we would know:** Answering an ask echoes the right ask text; the trace gets an entry without a manual write.
