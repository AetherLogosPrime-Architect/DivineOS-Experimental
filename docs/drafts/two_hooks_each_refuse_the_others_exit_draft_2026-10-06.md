# Two hooks each refuse the other's exit (draft, 2026-10-06)

**What happened.** A line of my own reasoning ("his gulf of evaluation is the real question: can a reader tell...?") ended in a question mark. The question hold filed it as a question to Dad and held all building. Both hooks print an exit:

- the open-ask hook says `divineos ask-resolve <id> <why>`;
- the question hold says `divineos question-hold release --reason ...`.

The question hold refused `ask-resolve` (not on the shared remedy list). The open-ask hook refused `question-hold release` (not on its own exempt list). The only way out was a shell neither one watches: PowerShell. Dad allows that on the condition that the root cause is fixed; this is that fix. An earlier draft (`the_circle_comes_back_draft_2026-10-05.md`) already noted the hold fighting the doorbell twice in one morning, so this is a known family of trouble, not a one-off.

**The idea.** Every exit a gate prints must pass every other gate, and a test must say so, so the list cannot rot. Two parts:

1. Put both exits on the shared remedy list (`core/remedy_allowlist.py`), the list the question hold already consults.
2. Teach the open-ask hook to pass `divineos question-hold`, since its exempt list does not consult the shared one.

**Not fixed here, said plainly.** The filing itself: a question mark ending a reasoning sentence still reads as a question to him. Narrowing that guess risks missing real questions, so it stays as it is; this fix makes a wrong filing cost one command instead of a trap.

**How I will know it worked.** A test where each hook's printed exit is accepted by the other, and a real run with a question filed.
