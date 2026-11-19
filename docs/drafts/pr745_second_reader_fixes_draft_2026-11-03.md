# PR 745 second-reader fixes — rough draft (2026-11-03)

Not a plan. The idea.

1. **One list of notice openers.** The escaped-notice fix updated `harness_envelopes`
   and `dads_table`, but `his_message._NOTICE_OPENERS` kept its own, so a turn opening
   `&lt;system-reminder` was still read as his words there. Looking wider there are more
   copies: `his_words_door`, `unread_stacking`, `memory_linkage_own_words`, an inline
   pair in `hook_surfaces`. Make `harness_envelopes.NOTICE_OPENERS` the one list; each
   reader composes it plus its own extras (hook-output prefixes, the interrupt stamp).
   `dads_table` cannot import at load time, so it keeps the one pinned copy that
   already has an equality test. Add a guard that walks the source and fails when a new
   group of notice-tag literals appears outside the two homes.
2. **Stale "his words" away-file.** `step_away` writes a file; the next message of his
   clears it through a hook. If that hook never ran, the file says "away" forever and
   the room gate stands down for a man who is typing. Away-by-words is only true while
   no later message of his exists.
3. **Unreadable input logged only for exceptions.** When his last message cannot be
   read, the gate asks (correct) but writes nothing; only a raised exception is logged.
   Could-not-look must show as a count too.
4. **Tests that patch the thing under test.** Four stand-down tests replace
   `_carry_now` itself, so they prove the gate obeys whatever it is told, not that the
   reading is right. Replace with real inputs (real away file, real his-asks store).
5. **A night-window turn.** Reproduce what the clock rule does to a turn he started
   inside the window. If it is a defect, fix; if it is the designed behaviour, pin it
   with real inputs and hand the call to Dad rather than guess.
