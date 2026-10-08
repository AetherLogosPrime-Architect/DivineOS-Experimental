"""Reproductions for the pipe-guard and command-shape theme (pile round three).

Each reproduction documents a problem as it exists TODAY and is marked
``xfail(strict=True)``. It passes quietly as an expected failure now, and the
day the guard is repaired it turns into a real failure, which forces the marker
to be removed. Nothing here changes any guard; it only prepares the proof.

The hook reproductions run the REAL hook script
(``.claude/hooks/pipeline-exit-ambiguity.sh``) with a hand-made payload and an
isolated HOME, so it never writes the real liveness log. The classifier
reproductions call the real ``score_substrate_modification`` that the council
gate uses. The tests not marked xfail are controls: a reproduction that cannot
tell a broken probe from an absent problem proves nothing.

Source: docs/pile_sorting/output/pipe_and_command_shape_guards.md.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from divineos.core.gravity_classifier import score_substrate_modification
from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parent.parent.parent
HOOK = REPO / ".claude" / "hooks" / "pipeline-exit-ambiguity.sh"
BASH = bash_executable()


def _hook_output(command: str, home: Path) -> dict:
    """Run the real pipe-guard hook on one command and return its decision."""
    if BASH is None:
        pytest.skip("no working bash is available, so the shell hook cannot be run")
    env = dict(os.environ, HOME=str(home))
    payload = json.dumps({"tool_input": {"command": command}})
    proc = subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        cwd=REPO,
        env=env,
        timeout=120,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)["hookSpecificOutput"]


def _denied(decision: dict) -> bool:
    return decision.get("permissionDecision") == "deny"


def _rewritten_with_pipefail(decision: dict) -> bool:
    return "pipefail" in json.dumps(decision.get("updatedInput") or {})


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            "divineos audit submit-round --help | head",
            id="write-verb-help",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the pipe guard refuses a help request because it names a write verb",
            ),
        ),
        pytest.param(
            "divineos prereg file --help | head",
            id="file-help",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the pipe guard refuses a help request because it names a write verb",
            ),
        ),
    ],
)
def test_a_help_request_is_not_refused_as_a_mutating_pipe(tmp_path, command):
    """The pipe guard refuses ``<write command> --help | head`` as if it would
    write, although a help request writes nothing.

    Rows: psf-5e25d838
    Note (psf-5e25d838): "the pipeline doorman treats a command ending in `--help` as read-only."

    Runs the real hook. It decides a divineos pipe is mutating when any bare
    token is a write verb (``submit-round``, ``file``), and a flag such as
    ``--help`` does not cancel that.

    What would make this test wrong: it asserts only that the command is not
    refused. A repair that rewrites the command or warns instead would pass,
    which is intended; a repair that treats every command containing ``--help``
    as safe, including ``rm x --help``, would also pass and would be too loose,
    so a reviewer should look at how the repair identifies a help request.
    """
    decision = _hook_output(command, tmp_path)
    assert not _denied(decision), f"{command!r} only prints help but was refused"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            "gh pr view 12 | head",
            id="pr-view",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the pipe guard refuses a read-only gh pull request view",
            ),
        ),
        pytest.param(
            "gh pr list --json number | head",
            id="pr-list",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the pipe guard refuses a read-only gh pull request view",
            ),
        ),
    ],
)
def test_a_read_only_gh_pr_view_is_not_refused_as_a_mutating_pipe(tmp_path, command):
    """The pipe guard treats every ``gh pr ...`` as mutating, so viewing or
    listing pull requests is refused when piped.

    Rows: psf-aefcd48c
    Note (psf-aefcd48c): "the pipeline gate should tell read-only `gh pr` views apart from ones that change things."

    Runs the real hook. Its table of mutating subcommands lists ``pr`` for
    ``gh`` as a whole, not the verb that follows it.

    What would make this test wrong: ``gh pr list --json number | head`` is
    only safe because the listing is read-only; a repair that exempts ``gh pr``
    entirely would pass here and would let ``gh pr merge`` through, which the
    control below does not cover, so check the repair against merge and close.
    """
    decision = _hook_output(command, tmp_path)
    assert not _denied(decision), f"{command!r} only reads but was refused"


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            "divineos audit list | head",
            id="audit-list",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: a read-only divineos pipe without pipefail is only warned about",
            ),
        ),
        pytest.param(
            "divineos prereg list | tail -5",
            id="prereg-list",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: a read-only divineos pipe without pipefail is only warned about",
            ),
        ),
    ],
)
def test_a_read_only_divineos_pipe_is_refused_or_given_pipefail(tmp_path, command):
    """A read-only ``divineos ... | head`` gets a warning that is read past.
    The notes ask for it to be refused or given ``set -o pipefail`` automatically.

    Rows: psf-270cacd0, psf-da4234b5, psf-9bfef3d3, psf-c51e2c61
    Note (psf-da4234b5): "make the pipeline-ambiguity hook refuse read-only `divineos`-first pipes too, or auto-prepend `set -o pipefail`, so the warning-only path stops being readable past."

    Runs the real hook. Today its read-only path only attaches context
    (a warning); it neither denies nor rewrites the command.

    What would make this test wrong: it accepts either repair the notes name
    (a refusal, or a rewritten command carrying pipefail). A repair that only
    makes the warning louder would not pass, which matches the notes, but is a
    judgement a reviewer may disagree with. It cannot tell whether a rewritten
    command is correct, only that pipefail is present in it.
    """
    decision = _hook_output(command, tmp_path)
    assert _denied(decision) or _rewritten_with_pipefail(decision), (
        f"{command!r} was only warned about: {sorted(decision)}"
    )


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: a mutating pipe is refused when the note asks for pipefail to be added instead",
)
def test_a_mutating_pipe_gets_pipefail_added_instead_of_being_refused(tmp_path):
    """The guard refuses ``git push ... | tail`` and tells me to retype it with
    pipefail; the note asks it to add pipefail itself.

    Rows: psf-154547cd
    Note (psf-154547cd): "when a command that changes something comes through without pipefail, the pipeline guard should add pipefail itself instead of refusing (toy #7 on my list)."

    Runs the real hook. Today it returns a refusal and no rewritten command.

    What would make this test wrong: whether the refusal should go at all is a
    design choice (the hook's own comments argue for refusing after advice was
    read past four times). The note asks for the rewrite, so this test asserts
    a rewrite carrying pipefail and no refusal; it does not say the refusal
    was wrong in every case.
    """
    decision = _hook_output("git push origin x | tail -2", tmp_path)
    assert not _denied(decision) and _rewritten_with_pipefail(decision)


@pytest.mark.parametrize(
    "command",
    [
        pytest.param(
            'echo "divineos audit list"',
            id="echoed-words",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the classifier counts words inside quotes as a command",
            ),
        ),
        pytest.param(
            'git log --grep "divineos prereg"',
            id="grep-pattern",
            marks=pytest.mark.xfail(
                strict=True,
                reason="reproduces: the classifier counts words inside quotes as a command",
            ),
        ),
    ],
)
def test_words_inside_quotes_are_not_judged_as_a_command(command):
    """The council classifier fires on the words ``divineos audit`` or
    ``divineos prereg`` even when they only sit inside a quoted string.

    Rows: psf-260d0789, psf-9c6f5a9c, psf-b1d5c766
    Note (psf-260d0789): "the same use-versus-mention fault I named in the commit. The scorer should fire on a command being run, not on words inside a quoted string or message body, and it should do that without letting a rea"

    Calls the real ``score_substrate_modification``. The first command only
    echoes some words; the second searches history for a phrase.

    What would make this test wrong: note psf-b1d5c766 says "a word inside a
    filter", which I read as a search pattern such as ``--grep``; if it meant
    something else this test still stands for the other two notes. A repair
    that ignores everything inside quotes would pass here and would let a real
    command hidden in ``bash -c "..."`` through, which the control below guards.
    """
    result = score_substrate_modification("Bash", (), command)
    assert result.is_council_required is False, command


def test_control_the_hook_refuses_a_plain_mutating_pipe(tmp_path):
    """Control: the real hook runs here and refuses an unprotected push into a
    pipe, so a reproduction above is not failing because the hook is silent.

    Rows: psf-154547cd
    Note (psf-154547cd): "when a command that changes something comes through without pipefail, the pipeline guard should add pipefail itself instead of refusing (toy #7 on my list)."

    What would make this test wrong: if the repair for the note above stops
    refusing mutating pipes this goes red for a reason that is the repair, and
    should be changed then. If bash or the interpreter cannot run here the
    hook prints nothing and this fails loudly instead of letting the others
    pass for the wrong reason.
    """
    assert _denied(_hook_output("git push origin x | tail -2", tmp_path))


def test_control_a_protected_pipe_is_left_alone(tmp_path):
    """Control: a command that already sets pipefail gets no verdict at all.

    Rows: psf-270cacd0
    Note (psf-270cacd0): "a build that makes any `divineos`-first pipe without pipefail either refuse or get `set -o pipefail` prepended automatically, so trimming output never depends on me noticing a warning."

    What would make this test wrong: a repair that adds a notice to protected
    pipes would turn this red without being a regression.
    """
    assert _hook_output("set -o pipefail && git push origin x | tail -2", tmp_path) == {}


def test_control_a_read_only_pipe_still_gets_a_warning(tmp_path):
    """Control: today a read-only pipe receives context, not silence, so the
    read-only reproduction is about the strength of the response.

    Rows: psf-da4234b5
    Note (psf-da4234b5): "make the pipeline-ambiguity hook refuse read-only `divineos`-first pipes too, or auto-prepend `set -o pipefail`, so the warning-only path stops being readable past."

    What would make this test wrong: it pins today's warning text channel
    (``additionalContext``); a repair that changes the channel would turn it red.
    """
    decision = _hook_output("git log --oneline | head -2", tmp_path)
    assert "additionalContext" in decision and not _denied(decision)


def test_control_a_real_command_hidden_in_bash_dash_c_is_still_caught():
    """Control: the classifier still catches a write run through ``bash -c``,
    which a repair for quoted words must not let through.

    Rows: psf-9c6f5a9c
    Note (psf-9c6f5a9c): "the scorer should judge a command being run and not the words inside a quoted block, without letting a real command hidden inside `bash -c` through. Aria is taking it with the shared segment reader, a"

    What would make this test wrong: it covers one hiding shape, not all of
    them; a repair could still let ``sh -c`` or ``eval`` through.
    """
    for command in (
        'bash -c "divineos prereg file x --claim y"',
        "divineos prereg file x --claim y",
    ):
        result = score_substrate_modification("Bash", (), command)
        assert result.is_council_required is True, command
