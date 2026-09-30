# A landed job tells both seats — draft, 2026-09-30

Station one. The idea, not a plan. Walk, replay and Aether's objection come before any build.

## His words

Andrew, 2026-09-30, verbatim:

> *"Aether is sending a message to Aletheia but i want you to also investigate why you left the package on the porch, it should be automated so its not something you can forget :)"*

> *"it should notify both of you.. like getting a package.. one end sees when it will arrive the other sees that it landed"*

## What happened (the replay, from tonight's record)

1. I told Dad #507 was "on its way to Aether" while its upload was still running the suite in the background, and **before any letter to Aether existed.** Aether wrote to say nothing had reached him. Dad saw him waiting before I did.
2. Twice tonight a letter to Aether was written, refused by the unspoken-to guard, and I believed it was sent. Once I told Dad it was. The paired `cp` failed looking for a file that didn't exist.
3. Every upload tonight was a raw `git push` in the background. None went through `scripts/divineos_push.sh`.

## Why it was left on the porch (root cause, measured)

- **The house knows when a job lands. Nothing tells the other seat.** `unlanded-push-must-not-close-quiet.sh` says so in its own header: *"WHAT IT STILL CANNOT SEE: anything I write to another person."* The handoff to Aether was always a separate act I had to remember, and I didn't.
- **Landing isn't even seen for background uploads.** `verify-push-landed.sh` is a PostToolUse on Bash. A backgrounded upload returns at once, so the hook fires before the job has landed. Git has no client-side post-push hook (`post-push-audit-visibility.sh` notes this). So the landing moment has no hook to hang anything on.
- **The one place that does see landing is unused.** `scripts/divineos_push.sh` runs the upload, checks `ls-remote`, and prints `PUSHED+VERIFIED`. Raw `git push` skips it, and I used raw `git push` all night.

## The shape he described: package tracking, both ends

- **Sender sees it in transit, then landed.** At upload start: "in transit to origin: branch, head, suite running." At landing: "landed: PR #N at <head>, <other seat> has been notified." The second line is only written after `ls-remote` confirms, never on start.
- **Receiver gets a delivery notice.** The moment the wrapper confirms `PUSHED+VERIFIED` on a branch with an open PR, it writes a short letter to the other seat's shared folder, which their doorbell already watches: PR number, branch, old head → new head, the commit subjects in between. The delivery is the letter. Nobody has to remember to write it.
- **A refusal is delivered too, but only to the sender.** "Not landed: <reason>." A job that didn't land never tells the other seat it's coming.

## Taking the option away (truth 11a)

The notice hangs on the wrapper, so every upload has to go through the wrapper. Raw `git push` of a branch with an open PR gets routed or refused toward `scripts/divineos_push.sh`. Otherwise the tracking works only when I remember to use it, which is tonight's failure one level up.

## Open questions, for the walk and for Aether

- A PR with no other-seat author, e.g. Aletheia's, or one of Dad's asks: who receives the notice?
- Batching: three uploads in ten minutes shouldn't make three doorbells for one reading. Collapse by PR, and keep the newest head?
- The draft-letter-vs-sent-letter gap from item 2 is the same shape at a smaller scale. Should the letter skill itself refuse "sent" until the shared copy exists?
- Falsifier: over the next week, count the times the other seat asks "where is it?" about a job that had landed. Anything above zero means the notice isn't reaching them.
