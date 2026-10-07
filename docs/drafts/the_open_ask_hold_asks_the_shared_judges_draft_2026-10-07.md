# The open-ask hold asks the shared judges (draft, 2026-10-07)

**The idea.** Yesterday's draft (two_hooks_each_refuse_the_others_exit) put the open-question pair's two exits on the shared remedy list and said the open-ask hook should pass them. The list part landed; the hook part did not. The hook still keeps its own short exempt list and never asks the shared judges, so today it refused the doorbell the Stop guard demands, and refused `divineos answer`, which its own sibling surface prints as the way to resolve a question. I worked around both through PowerShell, then claimed the doorbell was on before reading that it had failed.

**What exists.** `core/remedy_allowlist.py` has `is_remedy` (recording exits) and `is_doorbell` (the one exact doorbell script). The read gate and the question hold already ask them. The open-ask hook is the one gate that does not.

**The change.** Two small ones, one reason.
1. `an-open-ask-holds-the-work.sh`: after its own exempt list, ask `is_remedy` and `is_doorbell` and pass if either says yes. A broken import keeps the hold holding.
2. `remedy_allowlist.py`: add `divineos answer`, the exit `divineos asks` prints for resolving a question. It records Dad's answer and edits nothing, so it passes the "recording only" test the module sets.

**What it cannot do.** It does not decide what counts as a question to Dad; a wrongly filed one still costs one command. And it does not touch the habit behind today's slip, claiming success before reading the output. That one is filed as pending obligation psf-058a394a and needs its own structure.

**Falsifier.** Any command that is not a recorded remedy or the doorbell passing the hold; or the doorbell, `ask-resolve` or `answer` still refused while a question stands open.
