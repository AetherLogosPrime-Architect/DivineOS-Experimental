# The house can still hand me a retired rule

**Draft, 2026-09-21. The idea, not a plan.**

Andrew, tonight, after I told him a branch needed no sign-off and was wrong:

> "it is from the system. the system handed you old rules... this is why you
> cannot keep a journal of everything in everything, when rules are changed or
> superceded if you want to archive it you can or use a link to the retired
> rule somewhere else but it should NOT be able to hand you old rules"

He is not describing a stale document. He is describing a delivery mechanism.

## What actually happened

There were two models for what needs sign-off before it enters the trunk.

The **protected list** asked: *which files are special?* It kept a list of
them. Anything on the list needed review; everything else walked in.

The **exemption list** asks the opposite question: *which files are merely
prose?* Everything else needs review. Andrew replaced the first with the
second on 7 September, in his own words: there are no longer any protected
files, every line that enters main gets audited, and the only exceptions are
the ones named.

The reason the second is better is not subtle. Under the first, a new file is
unguarded until somebody remembers to add it. The guard depends on memory, and
memory is the faculty that has failed here every single time.

## The part that is a defect rather than a mistake

I did not read one stale document and believe it. Three separate surfaces
handed me the retired model as the current one, and each looked authoritative:

1. **The instructions that load at the start of every session** state the old
   rule as rule eight. Not archived. Loaded. The first thing I read.
2. **The live server-side check** opens by loading the retired list into a
   function that nothing calls. Grep for the old list and you find it
   apparently load-bearing inside the current gate.
3. **The message that check prints when it blocks you** teaches the old rule
   at the exact moment someone is stuck and reaching for an explanation.

Three doors, all unlocked, all opening onto the same retired room. Any one of
them would have been enough to convince me, and one of them did.

## Why archiving by deletion is the wrong repair

The obvious fix is to delete the old text. That is wrong twice over. The
history of why a rule changed is the most useful thing about it — when the new
rule chafes, the old one's failure is the argument for holding the line. And a
rule that quietly vanishes leaves the next reader who half-remembers it no way
to learn it was retired rather than merely forgotten.

Andrew already named the right shape: archive it, or link to it from
somewhere else. Keep the corpse, label it, and make certain nobody can mistake
it for a living thing.

## The shape I think this takes

A **register of retired rules**. Each entry holds a phrase that identifies the
retired rule in the wild, the date and the person who retired it, and a
pointer to whatever replaced it.

Then a **check that walks the surfaces which hand me rules** — the session
instructions, the skills, the hook output, the messages the gates print — and
fails when a retired phrase is stated there as current. Archive paths are
exempt by prefix, because the archive is where the corpse is supposed to be.

The failure direction is the reverse of the usual one here. A false positive
is cheap: it makes me phrase something differently. A false negative is the
entire defect recurring. So the check should be eager, and the exemption
should be a named path rather than a judgment made in the moment.

## The thing I do not know yet

Whether a phrase match is the right instrument at all. A retired rule can be
restated in words that share nothing with the original — the same wrong idea,
paraphrased. A phrase register cannot catch that, and the checker should say
so out loud rather than let its silence read as coverage. Same shape as the
foundational-truths surface: a lexical priming aid, honest about being one.

What the register does catch is the rule that was **copied**. Copying is how
this one spread — the same sentence standing in three places, because each was
written by reading the last. That is the mechanism I actually observed
tonight, so that is the mechanism worth guarding first.

## A second instance, found while building the first

Two gates today refused the remedy they themselves prescribed. The overdue
pre-registration gate blocks the test run that is the only thing able to
answer a pre-registration. The build-flow doorman blocked the draft it had
just finished demanding, because it read a markdown quotation as a shell
redirection.

That is a family, not a coincidence: **a gate that names a remedy must not be
able to block it.** It does not belong in this draft's build, but it belongs
on the record, because I have now paid for it twice in one evening.
