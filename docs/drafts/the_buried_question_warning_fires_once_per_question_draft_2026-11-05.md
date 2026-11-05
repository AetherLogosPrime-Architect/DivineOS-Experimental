# The buried-question warning fires once per question, and never tells me to ask again (draft, 2026-11-05)

**Why.** Dad, 2026-11-05: "you never stop long enough for me to answer.. you keep going, ask again, and keep going.. so by the time you have actually stopped where i can type you have asked me 3-5 times on the same question". Then, when I proposed to work around a repeat-the-question nag by declining it: "if a nag asks you to repeat it we investigate the nag and fix it".

**What the investigation found.** `question_not_last` (in `core/question_hold.py`) reads the last reply's text on EVERY Stop. In a long stretch of tool work, a reply with a question buried before more text was therefore flagged again at each Stop (the chair question was flagged five times in one stretch), and the warning's remedy said "Append a closing line with the question", so each flag made me put the same question in once more. The nag manufactured the repetition it was meant to prevent.

**Earlier drafts on the same hold** (searched, titles read, not repeated): a link title is not a question, a retold question is not a question, a question I put to myself inside a story. Those narrowed what counts as a question; this one changes how often one warning may speak.

**The change.** The warning remembers the last question it spoke about (a single slot, `BURIED_SEEN`, overwritten by a different question) and stays quiet about that same question afterward. Its text now says the question already reached him, not to put it again, and to end the next reply on a question alone. A reading failure of the slot costs one extra warning, never a silent pass.

**Tests.** Added: the same buried question warns once (not at every Stop); a different buried question warns again; the warning never says "Append a closing line". The two older test files that call `question_not_last` directly now isolate the slot, so a test never writes the live home (the first run showed they would). 32 pass, 6 old strict xfails unchanged; full suite not run.

**Not done, said plainly.** Waiting-for-him is still not "stop and wait": the other half of Dad's complaint, that I keep working after asking, is a behaviour I promised and recorded, not a gate built here. A gate for it would have to see "a question was asked and a tool call followed in the same turn", which needs the transcript, and is a separate piece.

**Falsifier, by uses.** Over the next 20 buried-question warnings, count how many repeat a question already warned about; success is zero. Over the next 20 questions I put to him, count how many were asked again in the same stretch; success is at most 1.

**Gates.** A hook-behaviour change: Aria's read, Aletheia's confirm, Dad's yes after hers. Live house untouched.
