"""The council gate's key names every file a shell command writes, read by the one shared reader.

Found by running 519's own code (Aria's arc-4 reading, 2026-09-23), and every
case here failed on 765cac4d8 before the change:

- a copy onto the kiln scored ZERO, so the gate never asked for a walk at all;
- a harmless copy and a kiln copy shared one key, ``bash:cp src.md``;
- two writes keyed as ``write:a.md;`` -- the semicolon inside, the second file gone;
- a quoted arrow was read as a redirect.

THE INVARIANT, stated before the examples (Wayne, on the walk for this change):
a walk covers a command only if it names every file the command visibly writes.
"Visibly" is doing real work -- which files a command writes is not decidable
from its text in general, so ``TestTheBoundaryIsStillNamed`` pins what stays
out of reach rather than letting the passing tests imply it is covered.
"""

from __future__ import annotations

import itertools

import pytest

from divineos.core.council_required.store import _covers
from divineos.core.council_required.types import fingerprint_for
from divineos.core.gravity_classifier import score_substrate_modification

KILN = "docs/foundational_truths.md"


def _key(cmd: str) -> str:
    return fingerprint_for("Bash", (), cmd)


def _record(key: str, scope: tuple[str, ...] = ()) -> dict:
    return {"triggered_edit_fingerprint": key, "scope_fingerprints": list(scope)}


class TestTheGateFiresOnWhatTheCommandWrites:
    """Pearl on the walk: the key only matters if the gate runs. This is the
    half that decides whether it does."""

    @pytest.mark.parametrize(
        "command",
        [
            f"cp src.md {KILN}",
            f"mv draft.md {KILN}",
            f"install -m 644 draft.md {KILN}",
            f"git mv draft.md {KILN}",
        ],
    )
    def test_copying_onto_the_kiln_owes_a_walk(self, command: str) -> None:
        assert score_substrate_modification("Bash", (), command).is_council_required

    def test_it_scores_as_the_same_write_through_a_tool_would(self) -> None:
        shell = score_substrate_modification("Bash", (), f"cp src.md {KILN}")
        tool = score_substrate_modification("Write", (KILN,), "")
        assert shell.fired_features == tool.fired_features


class TestOneFileOneKey:
    def test_a_harmless_copy_and_a_kiln_copy_do_not_share_a_key(self) -> None:
        assert _key("cp src.md notes/scratch.md") != _key(f"cp src.md {KILN}")

    def test_a_copy_is_named_by_its_destination(self) -> None:
        assert _key(f"cp src.md {KILN}") == fingerprint_for("Write", (KILN,), "")

    def test_a_single_redirect_keys_exactly_as_before(self) -> None:
        """Characterisation. Every walk already on the ledger was filed against
        this form; changing it would strand all of them."""
        assert _key("echo x > a.md") == "write:a.md"

    def test_a_quoted_arrow_is_not_a_write(self) -> None:
        assert not _key("echo '>' notes.txt").startswith("write:")

    def test_discarding_output_does_not_turn_a_commit_into_a_write(self) -> None:
        """Feathers on the walk: the shared reader has no /dev filter of its own,
        so without the one carried over this would key as write:/dev/null."""
        assert _key("git commit -m x 2>/dev/null") == "bash:git commit"


class TestEveryFileWrittenIsInTheKey:
    def test_two_writes_are_both_named(self) -> None:
        assert _key("echo x > a.md; echo y > b.md") == "write:a.md + write:b.md"

    def test_the_key_does_not_depend_on_the_order_of_the_writes(self) -> None:
        writes = ["echo 1 > a.md", "cp x b.md", "echo 3 >> c.md"]
        keys = {_key(" && ".join(p)) for p in itertools.permutations(writes)}
        assert keys == {"write:a.md + write:b.md + write:c.md"}

    def test_a_file_written_twice_is_named_once(self) -> None:
        assert _key("echo x > a.md; echo y >> a.md") == "write:a.md"


class TestAWalkMustNameEveryPart:
    COMPOUND = "write:a.md + write:b.md + write:c.md"

    def test_a_walk_filed_against_the_compound_key_covers_it(self) -> None:
        assert _covers(_record(self.COMPOUND), self.COMPOUND)

    def test_a_job_walk_listing_every_part_covers_it(self) -> None:
        rec = _record("write:a.md", ("write:b.md", "write:c.md"))
        assert _covers(rec, self.COMPOUND)

    @pytest.mark.parametrize(
        "named",
        [
            ("write:a.md",),
            ("write:a.md", "write:b.md"),
            ("write:b.md", "write:c.md"),
        ],
    )
    def test_a_walk_naming_only_some_of_the_files_does_not(self, named: tuple[str, ...]) -> None:
        rec = _record(named[0], named[1:])
        assert not _covers(rec, self.COMPOUND)

    def test_a_single_key_is_still_matched_exactly(self) -> None:
        assert _covers(_record("write:a.md"), "write:a.md")
        assert not _covers(_record("write:a.md"), "write:b.md")


class TestEveryCommandThatNamesAnEditUsesTheSameKey:
    """Found by running `divineos council check` live on this change: the gate
    decided on `write:docs/foundational_truths.md` and the SAME refusal then
    printed `Edit fingerprint: bash:cp` underneath it. Three CLI commands still
    took the command's first word, the anchor the shared derivation replaced.

    For `authorize-bypass` that is not cosmetic. It stores the operator's
    authorization under its key and the gate looks it up under the gate's key,
    so for any shell command the two never meet -- the channel for Andrew's own
    authorization could not clear the edit it named."""

    COMMAND = f"cp src.md {KILN}"

    def _run(self, *args: str):
        from click.testing import CliRunner

        from divineos.cli import cli

        return CliRunner().invoke(cli, list(args))

    def test_the_refusal_names_the_key_the_gate_looked_up(self) -> None:
        result = self._run("council", "check", "--tool", "Bash", "--command", self.COMMAND)
        assert f"Edit fingerprint: {_key(self.COMMAND)}" in result.output

    def test_an_operator_authorization_is_stored_under_the_gate_key(self) -> None:
        result = self._run(
            "council",
            "authorize-bypass",
            "--tool",
            "Bash",
            "--command",
            self.COMMAND,
            "--reason",
            "test of which key the authorization is stored under",
            "--quote",
            "a quote long enough to be recorded as the operator's words",
        )
        assert f"fingerprint: {_key(self.COMMAND)}" in result.output

    def test_an_operator_authorization_actually_clears_the_edit_it_names(self) -> None:
        """The behaviour, not the printout: authorise, then ask the gate."""
        refused = self._run("council", "check", "--tool", "Bash", "--command", self.COMMAND)
        assert refused.exit_code == 2, "control: with no walk and no authorisation it must refuse"
        authorised = self._run(
            "council",
            "authorize-bypass",
            "--tool",
            "Bash",
            "--command",
            self.COMMAND,
            "--reason",
            "test that the authorization reaches the gate",
            "--quote",
            "a quote long enough to be recorded as the operator's words",
        )
        assert "operator-bypass authorized" in authorised.output, authorised.output

        from divineos.core.council_required.types import STATE_MARKER_KIND_OPERATOR_BYPASS
        from divineos.core.state_markers import find_active_marker

        marker = find_active_marker(kind=STATE_MARKER_KIND_OPERATOR_BYPASS)
        assert marker is not None and marker.fingerprint == _key(self.COMMAND)

        cleared = self._run("council", "check", "--tool", "Bash", "--command", self.COMMAND)
        assert find_active_marker(kind=STATE_MARKER_KIND_OPERATOR_BYPASS) is None, (
            "the gate did not consume the authorization"
        )
        assert cleared.exit_code == 0, (cleared.exit_code, repr(cleared.exception), cleared.output)


class TestTheBoundaryIsStillNamed:
    """Turing on the walk: the key is a LOWER bound on what a command writes.
    These write files and stay invisible, and that is known, not overlooked."""

    @pytest.mark.parametrize(
        "command",
        [
            "python write_it.py",
            f"python -c \"open('{KILN}', 'w').write('x')\"",
        ],
    )
    def test_a_program_that_writes_is_still_not_seen(self, command: str) -> None:
        assert not _key(command).startswith("write:")
