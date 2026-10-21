# The pins package, part two: three proof tests carried — draft, 2026-10-11

Not a plan to build new things. The second half of a carry: a helper wrote proof tests for defects, and the first package (#625) carried five of its thirteen branches. This one carries three more.

## What is carried

| Helper PR | Test | The defect it proves |
|---|---|---|
| #604 | push wrapper, full-path refspec | the push wrapper mishandles a full-path refspec |
| #606 | no-fix claim, quoted sentences | the no-fix-claim check fires on sentences that are only quoted |
| #608 | look-strict grep, no match | a strict look that finds nothing is read as a pass |

Each test is marked as a known failure, with a reason that names the defect, so it stays red-on-purpose until someone fixes the defect and removes the mark. Each comes with the helper's own draft note.

## Proof

Run as they stand: 8 passed, 6 marked failures. Run with the marks forced off: the 6 fail with AssertionError, which is the defect showing and not a broken test. Each marked failure carries a raises clause, so a test that dies for the wrong reason (an import error, a typo) turns red instead of hiding inside the mark. Three of three raise the expected error.

One thing the next reader should know (Aria's cold read, 2026-10-12): in the push-wrapper test the marked assertion has its own "did it land" check first, so a push that failed for an unrelated reason would die with AssertionError and hide inside the mark. The third test in that file, the long-form push really landing (asserting the remote only), is the control that rules this out today. The pair is what is sound; the control carries that weight.

## Not carried

The fourth test file (council walk gate, #601) is left out: its 16 pins now pass, because the defects it proved have since been fixed. Carrying it would carry marks that are already wrong. It needs its marks removed and the tests kept as ordinary regression tests, which is a separate change. #612, #613, #615 and #616 still need the helper's work and are held.

## Falsifier

If any carried test passes with its mark on and no fix on main, the test proves nothing and the carry was wrong. The run above is the check.
