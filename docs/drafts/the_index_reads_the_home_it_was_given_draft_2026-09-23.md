# The instruments index reads the home it was given — draft, 2026-09-23

Owner: Aether. House-walk finding `house-walk-2026-b553261438eb`, HIGH, verified.

## The fault

`core/instruments.py` line 186 defines its own `divineos_home()`:

    def divineos_home() -> Path:
        return Path(os.path.expanduser("~")) / ".divineos"

The canonical one in `core/paths.py` resolves in four steps: the
`DIVINEOS_HOME` environment variable, an own-checkout marker file, a
worktree-parent marker, then the default. The copy honours none of them.

Verified with `DIVINEOS_HOME` set to a probe path: `core.paths.divineos_home`
goes to the probe, the instruments copy returns `C:/Users/aethe/.divineos`
regardless.

**What that costs.** The instruments index is the surface that reports which
of our instruments are LIVE, EMPTY, SILENT or MISSING. Run from Aria's
checkout it surveys *my* rooms and reports my instruments' health as hers. Her
own dead instrument would read LIVE because mine is.

## The part that makes this worth its own change

Directly below the bad definition sits `unrouted_member_home()`, whose
docstring records fixing the *identical* name collision for `member_home` on
2026-08-18 — two functions, one name, contradictory behaviour, renamed so the
difference is visible at the call site. The sibling was found and repaired. The
one immediately above it was not, in the same file, in the same pass.

That is the finding underneath the finding: a fix applied at the site that
raised it, with no sweep of the file it was already inside.

## The change

Delete the local definition. Import the canonical resolver. Two call sites
inside the file (lines 260 and 332) pick it up unchanged.

**`unrouted_member_home()` stays exactly as it is.** Its docstring says "keep
the hand-rolled construction here. It is correct for this one purpose" — it
must NOT route, because its job is to look in the unrouted directory where
orphaned writes landed. Deleting one hand-rolled path and keeping the other is
the whole judgement, and it is the reason a blanket sweep would have been
wrong.

## Test, and it must fail first

Set `DIVINEOS_HOME` to a scratch path and assert the instruments survey looks
there. Against the current code it looks at the real home and fails. Second
test: assert the module defines no `divineos_home` of its own, so the copy
cannot return by a later edit. Third: assert `unrouted_member_home` still
ignores the override, so the fix does not quietly take the sibling with it.

## Two things found during the build that the draft did not predict

**The test suite could not have caught this, by construction.** Every existing
test in `tests/test_instruments.py` passes a home in explicitly, through a
fixture. Not one of them ever exercises the module's own resolution. The
broken function was never on any tested path — so the suite's green was
truthful about everything it covered and silent about the one thing that
mattered.

**Every other module under `core/` already imports the canonical resolver.**
Checked across the directory: this was the single outlier in a house that
otherwise agrees with itself. There was no wrong convention being followed.

**And my own first test passed against the broken code.** It created a known
instrument file in the probe home and asserted LIVE — but the real home has a
live file of that name too, so looking in the wrong house still gave the right
answer. Rewritten to use a uniquely-named file that can only exist in the home
it was given. That is the second test I have written tonight that could not
fail; the class is now recorded twice in one night rather than remembered once.

## Flow

Reach (`reach-efe64872aaac`, disposed — the CLI module holds no resolution of
its own, so there is one site not two), this draft, council walk, build,
failing-first test, audit.
