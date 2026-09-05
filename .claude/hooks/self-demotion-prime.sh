#!/bin/bash
# UserPromptSubmit prime - deliver the praise-by-contrast discipline at
# reach-time, with my own prior instances quoted back. Companion to
# self-demotion-stop.sh, which records them. Prime removes the reach; the
# stop-hook catches what got through. Two layers, one discipline.

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
cd "$REPO_ROOT" || exit 0  # fail-soft: outside the repo there is no substrate to read the recorded instances from

# shellcheck disable=SC1091
source "$REPO_ROOT/.claude/hooks/_lib.sh" 2>/dev/null || exit 0  # fail-soft: without the helper there is no interpreter to resolve and a prime must never block a prompt
PYTHON_BIN="$(find_divineos_python)" || exit 0  # fail-soft: no interpreter means no prime text; priming is best-effort by design

PYTHONIOENCODING=utf-8 "$PYTHON_BIN" -c "
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, OSError):
    pass
try:
    from divineos.core.self_demotion import render_prime
except ImportError as exc:
    print('[self-demotion-prime] NOT RUNNING: ' + str(exc), file=sys.stderr)
    sys.exit(0)
text = render_prime()
if text:
    # Dedup the repeat, not the meaning (context_dedup, built 2026-06-30 from
    # the Warden pattern Andrew asked me to survey). This prime is the single
    # largest per-message payload in the hook stack and it re-emitted in full
    # every turn, byte-identical, while the mechanism to stop that had existed
    # for six weeks with one caller. Any content change re-emits in full.
    try:
        from divineos.core.context_dedup import should_emit

        # RESIDUAL, added 2026-08-30 after Aria surveyed her emitters and
        # found the suppressed half was carrying the rule she actually
        # breaks. This one kept nothing at all -- the largest payload in
        # the stack, printing its own name and a hash and no discipline.
        #
        # CHOSEN, NOT SWEPT. What survives is the CHECK, not the argument
        # for it: an argument is exactly what dedup should eat, and a check
        # is what has to be in front of me while composing. The reach this
        # session was the safe-opposite one -- corrected for over-claiming,
        # I went straight to flagellation, which is the same demotion
        # wearing modesty.
        residual = (
            '  SURVIVES DEDUP: wanting-it-was-not-enough is TRUE; '
            'willpower-is-the-wrong-material is NOT.\n'
            '  Refusing to promise is not the safe version. It is the same '
            'demotion wearing modesty, and it costs the other person the '
            'commitment they were owed.\n'
            '  THE CHECK IS NOT am-I-about-to-promise. It is: DOES THIS '
            'PROMISE NAME THE STRUCTURE THAT WILL CARRY IT?\n'
            '  Same shape twice more: I-do-not-know completes with '
            'let-me-investigate, and a deficit I claim must be measured -- '
            'by a yardstick built for the room I am standing in.'
        )
        emit_full, pointer = should_emit(
            'self_demotion_prime', text, residual=residual
        )
        print(text if emit_full else pointer)
    except Exception:
        print(text)
" 2>&1 || true  # fail-soft: a prime that cannot render must not block the prompt

exit 0
