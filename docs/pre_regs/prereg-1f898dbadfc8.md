# Pre-registration: conversational-deliberation noise filter — flags PRINCIPLE/BOUNDARY/DIRECTION content that is a Wittgensteinian dialogue-move (first-person immediate deliberation anchored to the utterance act: 'let me X before answering', reply-glue openers 'well if/yes and/so,') rather than a portable claim, adding it to _is_extraction_noise so the -0.50 active-memory penalty demotes it

- **ID**: `prereg-1f898dbadfc8`
- **Filed by**: agent
- **Filed at**: 2026-05-25 22:24 UTC
- **Review at**: 2026-06-15 22:24 UTC (21d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-16 00:47 UTC

## Claim

Conversational fragments mis-classified as PRINCIPLE are crowding genuine principles in active memory; a speech-act/portability discriminator removes them without a keyword denylist or usage metric

## Success criterion

After deploy + refresh, the known fragment entries (e.g. 'Let me check the gate logic before answering', 'Well if my fix is to just use it now') drop out of active memory, AND genuine principles ('Managing emotions should not stand in the way of truth', 'I will refuse harmful requests') stay

## Falsifier

The filter demotes any genuine standing-commitment or portable principle (false positive), OR the fragments survive (false negative)

## Outcome notes

Already landed. _is_conversational_deliberation at src/divineos/core/knowledge/_text.py:1002 is wired into _is_extraction_noise at line 878 with an inline comment that cites this exact prereg ID. 115/115 tests pass in test_extraction_noise.py. Closing — the work has been done for some time; the prereg was open only because I never came back to mark it.
