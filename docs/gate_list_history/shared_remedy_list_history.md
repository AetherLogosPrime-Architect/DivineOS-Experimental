# The shared remedy list: how it grew (moved out of the code, 2026-10-12)

This is the running journal that used to sit as comments above the pattern in `.claude/hooks/lib/remedy_allowlist.sh`. Nothing is rewritten; it is moved word for word, in the first person, so the code can carry one current note and this can be read as the story it is. Each paragraph is a collision somebody hit and the command that freed it. Words like "above" and "this entry" inside it refer to this text, not to the code.

```
# SHARED REMEDY ALLOWLIST — no gate may block another gate's prescribed exit.
#
# Andrew 2026-08-18: "no gate should ever be blocking its own remedy."
#
# He said the same thing on 2026-06-16, signing off Aria's signal-based-gates
# design (docs/signal-based-gates-design-2026-06-16.md): every gate must have
# an emergency exit that is not a cheap route, *"that way you don't get stuck
# in a cage of your own building."* Her doc carries it as the one load-bearing
# addition to v4. Two months later I built the cage anyway, because each gate
# got its own exit and nobody owned the exits collectively.
#
# WHAT HAPPENED. The correction-marker gate fired and named three ways out.
# Every one was held shut by a different gate:
#
#   divineos learn              -> blocked by the reach-check doorman
#   divineos reach open         -> the reach doorman's OWN remedy, blocked by
#                                  the correction-marker gate
#   divineos correction         -> refused without a file path for a structural
#                                  fix; the fix I designed was then correctly
#                                  blocked by the keyword-enforcement doorman
#   clear_correction_marker.py  -> blocked by the goal doorman
#
# A closed cycle. The only way through was the fire door, which is meant for a
# burning building and not for a Tuesday. That escape has now been taken four
# times on this marker class; telemetry counts it as
# `bypass:dismiss:correction-marker:cli-broken`. Bypass habituation degrades a
# gate to a warning (psf-ac523181) — so a deadlock that forces the fire door on
# an ordinary day is not an inconvenience. It is a slow way of killing every
# gate at once, by teaching me that walls are things you go around.
#
# THE MISSING FACT. Every gate ALREADY exempts its own remedy. The reach
# doorman carries `if "divineos reach" in haystack: sys.exit(0)` under the
# comment "the remedy is exempt or this is a wall, not a doorman." The
# principle was understood — just scoped one gate wide. Nineteen gates each
# know their own way out and none knows anyone else's, so gate A blocks the
# command gate B just prescribed, and neither is wrong from inside its scope.
# The fact with nowhere to live is: THIS COMMAND IS SOMEBODY'S WAY OUT. This
# file is that somewhere. It generalises a pattern already in the code; it does
# not invent one.
#
# WHY THIS IS NOT A BYPASS SURFACE. Everything listed is a RECORDING action —
# files a correction, opens a reach, logs a lesson, sets a goal, observes on
# the compass. None of it edits code, commits, pushes, merges, or deletes. The
# worst that routing through this list achieves is writing true things into the
# substrate, which is the behaviour the gates were trying to produce. The
# dangerous verbs are deliberately absent and must stay absent: nothing here
# may ever match git, gh, pytest, rm, or an editor. Per Aria's spine — the
# honest fix is never to loosen a gate, it is to make it fire only on evidence.
# This does not loosen any gate's claim. It only stops a gate asserting a
# violation against the act of resolving a different one.
#
# ADDING TO THIS LIST is a decision, not housekeeping. The test: does some
# gate's own block-message name this command as the way through? If no gate
# prescribes it, it does not belong here, however convenient.
#
# Fail-open by construction: any parse failure returns 1 (not-a-remedy) and the
# calling gate proceeds exactly as it does today. This file can only ever let
# something through; it can never introduce a new block.

# Union of every remedy any gate names in its block message. Anchored to the
# start of the command, so `divineos goal add` matches while a mention of it
# inside a larger argument does not.
# `prereg assess` added 2026-08-19, found by walking into the deadlock.
#
# The overdue-pre-registration gate blocks ALL substantive tool use — Bash,
# Edit, Write — until an overdue pre-reg is assessed, and names `divineos
# prereg assess` as the single way out. The obligations gate then blocked that
# exact command as a substrate-write. Gate A's only exit was gate B's blocked
# action, and gate B's exits (the kill-switch marker; a command referencing an
# open obligation) both needed a shell that gate A had already closed.
#
# The principle was already canon and already written down. pre_tool_use_gate.py
# carries it verbatim at the read-only-probe carve-out — Andrew 2026-06-29: "no
# gate should ever be blocking you from using what you need to clear the gate" —
# added after two pre-regs were recorded DEFERRED with "CANNOT-LOOK" for no
# reason but that gate. That fix was applied to the gate it was discovered in
# and never carried across to this list. Same rule, one site, again.
#
# `prereg file` is deliberately NOT here: filing a NEW pre-registration is
# ordinary substrate-writing and is nobody's prescribed remedy. Only the two
# commands that CLEAR the overdue gate are exempt.
#
# THAT PARAGRAPH IS HALF FALSE NOW, AND IT STAYS ON THE PAGE (2026-09-17,
# council-2c5200562c98). Its second clause -- nobody's prescribed remedy -- is
# no longer true: the pending-obligations gate prints `prereg file` as one of
# four channels that clear it. Its FIRST clause is still true, and that is the
# real cost of the entry below: filing a pre-registration is ALSO ordinary
# substrate-writing, so exempting it exempts the ordinary kind too, and nothing
# distinguishes a remedial filing from an ordinary one. The attack that opens is
# filing one purely to move past a gate holding me for something else -- bounded
# to one more true row in the substrate and a gate that did not hold. Named here
# rather than left to be discovered.
#
# The paragraph is not struck, because it was RIGHT when written and the world
# moved under it. Deleting it would erase the evidence of how this file learns,
# which is the finding underneath the four entries.
#
# FOUR ADDED, ALL FOUR MEASURED (2026-09-17). Aria hit this from her side and I
# hit it from mine: the pending-obligations gate SOURCES this library and calls
# the pass-through, and still refused the command its own block message names as
# the way to clear it. So the question was never whether that gate consults the
# list. It was whether the list CONTAINS the exits that gate prints. Each was
# probed against the live matcher rather than read off the pattern and believed
# -- with a control that IS listed, so an all-blocked result would have read as
# a broken probe instead of a finding. The control passed. All four of that
# gate's own prescribed exits were absent: integrate, prereg file,
# claims assess, audit submit-round.
#
# WHY THE GAP EXISTED AND WHY IT WAS INVISIBLE. Every entry above is a scar:
# somebody deadlocked, the freeing command got added. So this file is an honest
# record of collisions people HAVE had, and silent about every collision nobody
# has had yet -- a history wearing the shape of a specification. A list where
# every item is earned reads as finished in a way a list of guesses never would,
# and the earned-ness is exactly what hides the hole. I narrowed this same file
# hours earlier asking is-this-entry-justified, one entry at a time, and that
# question structurally cannot find a MISSING entry.
#
# SCOPE, STATED BECAUSE I OVERSTATED THE LAST ONE. This is ONE gate's worth of
# exits. It is NOT a claim that the list is complete. The survey that would
# justify that -- enumerate every gate's printed remedies and diff them against
# this pattern -- is mechanically possible and HAS NOT BEEN RUN. Until it is,
# this file remains one incident behind, by construction.
# NAMED SUBCOMMANDS, NOT A BARE NAMESPACE (2026-09-17, council-0fd602407897).
# Aria found this reviewing a change of mine, and she is the reason it is here.
#
# This line used to end on `council` with no subcommand, so it matched the
# WHOLE command family. A prefix was deciding policy: every subcommand anyone
# ever added to that family would inherit passage through all nineteen gates,
# silently, without a single person choosing it. A permission surface that
# grows by accident is the worst kind, because the widening is invisible at the
# moment of widening -- the consequence sits nowhere near the hand.
#
# And the invariant above read as SATISFIED the whole time. It forbids git, gh,
# pytest, rm and editors: the dangerous verbs somebody imagined. Authorising a
# bypass was not on that list, so the blanket swallowed it and the guarantee
# still looked true. A rule true as written that does not cover the case.
#
# WHAT SURVIVES, AND IT WAS MEASURED RATHER THAN ARGUED. The bar this file
# states is that some gate must PRINT the command in its own block message.
# Enumerated before editing: `council authorize-bypass` is printed at six
# separate sites, and `council log` / `council walk` are printed by the
# council gate's own missing-artifact message. All three qualify.
#
# `council authorize-bypass` STAYS, and this sentence is the point of naming
# it. Aria's first review said pull it. Measured: three gates offer it as their
# only exit, so removing it would hand the next trapped gate a door held shut
# by a different gate -- rebuilding the cage while repairing the hole. It is
# here because it is a prescribed remedy, deliberately, in writing. What she
# was protecting was never that bypass be excluded; it was that the argument be
# made OUT LOUD rather than arriving as a side effect of a prefix. This is that
# argument, made.
#
# `council emergency-skip` is GONE from here, and she was right about that one.
# No gate prints it anywhere. It fails the bar by measurement, not by opinion.
# It keeps living in check-council-required's own tuple, where it always was
# and where exactly one gate owns it.
#
# THE COST, stated rather than hidden: this list must now be maintained, and one
# day a genuine remedy will be printed by some gate and be missing from here,
# and somebody will hit a wall that is a stale list rather than a rule. That is
# the BETTER failure. A block is visible, attributable, and fixable in one edit.
# A silent widening is none of those. What nothing yet closes: no test diffs the
# printed remedies against this list, so the bar is checkable and unchecked.
# THE WEAVE, FIFTH INSTANCE OF THIS CLASS AND THE PUREST ONE YET
# (2026-09-17, council-b84778e867e4). The context governor blocks substrate
# writes at the hard line until the self is woven, and names `extract` and
# `sleep` as the way through. Its own docstring says they "are bypassed in
# `_is_bypass_command` so the gate can never block its own remedy" -- which is
# Andrew's sentence, the one quoted at the top of THIS file, written verbatim
# inside that gate.
#
# And the council gate, which sources this library, refused both. So the
# principle is stated in one gate's own words and absent at the place that
# enforces it across the others. Measured rather than inferred: `divineos
# extract` was refused twice tonight, once at the start of the session and once
# at the end, on the command CLAUDE.md names as the session's learning
# checkpoint.
#
# THE BAR IS MET BY THE GATE'S OWN TEXT, which is the cheapest evidence
# available and the one this file says decides. The invariant holds too,
# because it is about KIND and not size: every verb this file forbids -- git,
# gh, pytest, rm, an editor -- acts outside the substrate or destroys within
# it. The weave writes true things into the store and nothing else, at volume,
# and reading "recording action" as a size limit would be inventing a clause to
# hold a worry the clause was never written for.
#
# WHAT IT OPENS, stated rather than hidden: any gate holding me for an
# unrelated reason can now be walked past by running the weave, and the asset
# at risk is the STORE rather than the gate -- a consolidation at a moment
# nobody chose writes knowledge from a session that should not have been
# consolidated. What makes it acceptable is that this is not a new capability.
# The gate that OWNS the weave already exempts it by name, so what is removed
# here is a disagreement between two gates rather than a wall.
#
# AND THIS IS NOT THE CLASS CLOSED. It is one more scar on a file that says of
# itself, above, that it runs one incident behind by construction. The lever is
# the survey this file has now named as unrun THREE times -- enumerate every
# gate's printed remedies and diff them against this pattern. Both halves are
# text. Naming it three times without running it is data about which of us is
# actually keeping it, and the count sits here so the next reader sees a
# pattern rather than a fresh good intention.
# SIXTH INSTANCE, 2026-10-11: `prereg reviewing` (the overdue block's printed way to go
# get evidence) and `game-walk file` (the build-flow gate's paperwork) were added to the
# python list and to that gate's own tuple and not here, which nineteen gates read. Found
# by surveying what the gates PRINT against each list, not by a deadlock. The prefix is
# still loose (nothing marks the end of a verb), named and left for its own tested change.
```
