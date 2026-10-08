# The hook-layer measure did not know the doorbell form (draft, 2026-10-08)

`divineos hook-layer show` says 47 shell files "never import or call the OS". Reading the three smallest Stop scripts to pick migration candidates found all three are plain doorbells: they find a Python and run `python -m divineos.hooks.<module>`. The measure's pattern is `from divineos|import divineos|divineos <word>`, which does not match `-m divineos.`. I recounted by hand: of the 47, twelve are exactly that form; the honest number is 35 files, 5,222 lines, not 47 and 5,939.

I told Dad 47 earlier today and wrote it into the archive entry for the hook ceiling. Same species as everything else this week: an instrument whose blind spot made a bad state look worse (here) or a good state look better (the cut-away check's first sweep).

Idea: add `-m divineos` to the pattern the measure uses, with a test pair: a script that runs `python -m divineos.hooks.x` is NOT detached (and a bare echo still is, as the control). Then correct the two places I wrote 47.

Small and self-contained: one regex, one test, two number corrections. No new mechanism.
