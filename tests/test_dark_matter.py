"""The dark-matter sweep — things that exist but nothing reaches.

Andrew 2026-08-02: *"so much of the system is like this.. dark.. un-automated..
not known it even exists.. its all in there just needs to be mined."*

The pattern was already filed as `WIRING-GAP PATTERN` on 2026-05-11 across 5
instances, flagged structurally-insufficient the same day, and given a
`FILE-WITHOUT-CLOSE` meta-pattern the day after. It did not need discovering
again. It needed a consumer.

Two things these tests exist to protect, both learned by dogfooding this tool
against the real repository while building it:

1. **Precision.** The first run returned 82 findings including prose like
   "divineos and passed". A detector that noisy becomes wallpaper inside a day,
   which is the same death as never running it.
2. **Not over-tightening.** The precision fix then silently dropped the exact
   case that motivated the whole detector — `divineos psf mark-done`, which is
   prescribed mid-line after "Resolve via:" and so failed a
   backtick-or-line-start rule. Caught only by checking for that case *by
   name* rather than reading a smaller number as improvement.
"""

from __future__ import annotations

import json

from divineos.core.dark_matter import (
    BLIND_SPOTS,
    command_resolves,
    find_unregistered_hooks,
    find_unresolvable_prescribed_commands,
    format_report,
)

REGISTERED = {"audit", "audit export", "audit list", "learn", "goal", "admin", "admin maintenance"}


def _write(root, rel: str, text: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# The verdict is structural — no pattern decides anything
# --------------------------------------------------------------------------


def test_resolution_is_decided_by_the_registered_set_not_by_a_pattern():
    """The load-bearing property, and the reason this is not a keyword gate.

    Identical input flips verdict purely on what is registered. If a pattern
    were deciding, the registered set could not change the answer."""
    assert command_resolves("audit", "export", REGISTERED) is True
    assert command_resolves("audit", "export", set()) is False
    assert command_resolves("psf", "mark-done", REGISTERED) is False
    assert command_resolves("psf", "mark-done", REGISTERED | {"psf", "psf mark-done"}) is True


def test_argument_after_a_non_group_command_is_not_a_subcommand():
    """`divineos learn "..."` — learn takes an argument, not a subcommand."""
    assert command_resolves("learn", "something", REGISTERED) is True


def test_group_with_a_bad_subcommand_does_not_resolve():
    assert command_resolves("admin", "nonexistent", REGISTERED) is False


def test_bare_group_resolves():
    assert command_resolves("admin", None, REGISTERED) is True


# --------------------------------------------------------------------------
# Painted doors — the motivating case
# --------------------------------------------------------------------------


def test_catches_the_psf_case_prescribed_mid_line(tmp_path):
    """THE regression test. Three gates prescribed `divineos psf mark-done`,
    a command that has never existed, leaving Aria's learning checkpoint
    unreachable. It appears mid-line after a colon — the exact shape a
    line-start-only rule misses."""
    _write(
        tmp_path,
        "src/divineos/x.py",
        "    msg = (\"\\n    Resolve via: divineos psf mark-done <psf-id> --note 'fix'\")\n",
    )
    found = find_unresolvable_prescribed_commands(tmp_path, REGISTERED)
    assert any("psf mark-done" in f.subject for f in found)


def test_catches_a_bad_subcommand_on_a_real_group(tmp_path):
    _write(tmp_path, "src/divineos/y.py", "# run `divineos admin nonexistent` to fix\n")
    found = find_unresolvable_prescribed_commands(tmp_path, REGISTERED)
    assert any("admin nonexistent" in f.subject for f in found)


def test_valid_commands_are_not_reported(tmp_path):
    _write(tmp_path, "src/divineos/z.py", "# run `divineos audit export` then commit\n")
    assert find_unresolvable_prescribed_commands(tmp_path, REGISTERED) == []


# --------------------------------------------------------------------------
# Precision — noise is how a real finding becomes wallpaper
# --------------------------------------------------------------------------


def test_prose_mentions_are_not_prescriptions(tmp_path):
    """From the real first run: 'divineos and passed', 'divineos as'. Words in
    a sentence, matched by a loose pattern, reported as broken commands."""
    _write(
        tmp_path,
        "src/divineos/p.py",
        "# the divineos and passed checks agree, and divineos as a whole is fine\n",
    )
    assert find_unresolvable_prescribed_commands(tmp_path, REGISTERED) == []


def test_a_prose_sentence_starting_a_line_is_not_a_prescription(tmp_path):
    """The real 2026-08-02 false positive. `_BEFORE_RE` accepted a bare line
    start as evidence of a prescription, so the docstring sentence

        divineos is pip-installed editable.

    was reported as a broken command named `is`. Prose starts lines too; a
    real prescription carries a backtick or a shell prompt."""
    _write(tmp_path, "src/divineos/q.py", '"""\ndivineos is pip-installed editable.\n"""\n')
    assert find_unresolvable_prescribed_commands(tmp_path, REGISTERED) == []


def test_a_prompted_line_is_still_a_prescription(tmp_path):
    """The other half — tightening BEFORE must not cost the shell-prompt case,
    or the fix trades a false positive for a false negative."""
    _write(tmp_path, "src/divineos/r.py", "# $ divineos notacommand --flag\n")
    found = find_unresolvable_prescribed_commands(tmp_path, REGISTERED)
    assert [f.subject for f in found] == ["divineos notacommand"]


def test_line_wrapped_token_is_not_a_command(tmp_path):
    """A trailing hyphen means the source line wrapped mid-word."""
    _write(tmp_path, "src/divineos/w.py", "# `divineos admin migrate-family-\n#  members`\n")
    found = find_unresolvable_prescribed_commands(tmp_path, REGISTERED)
    assert not any(f.subject.endswith("-") for f in found)


def test_the_module_does_not_report_its_own_documentation(tmp_path):
    """dark_matter.py documents the psf defect in its own docstring. It must
    not count its own description of the bug as an instance of the bug."""
    _write(tmp_path, "src/divineos/core/dark_matter.py", "# `divineos psf mark-done` example\n")
    assert find_unresolvable_prescribed_commands(tmp_path, REGISTERED) == []


# --------------------------------------------------------------------------
# Silent-strand hooks
# --------------------------------------------------------------------------


def _hooks_fixture(tmp_path, settings_cmd: str):
    _write(tmp_path, ".claude/settings.json", json.dumps({"hooks": [{"command": settings_cmd}]}))
    return tmp_path


def test_hook_not_named_anywhere_is_reported(tmp_path):
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "echo hi\n")
    _write(tmp_path, ".claude/hooks/orphan.sh", "echo nobody calls me\n")
    found = find_unregistered_hooks(tmp_path)
    assert [f.subject for f in found] == ["orphan.sh"]


def test_hook_invoked_by_another_hook_is_not_dead(tmp_path):
    """Reachability is not only via settings.json — a hook can call a hook."""
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "bash .claude/hooks/helper.sh\n")
    _write(tmp_path, ".claude/hooks/helper.sh", "echo called by wired\n")
    assert find_unregistered_hooks(tmp_path) == []


def test_hook_reached_by_a_git_delegator_glob_is_not_dead(tmp_path):
    """THE false-positive regression. `.git/hooks/post-commit` contains
        for hook in "$HOOKS_SRC"/post-commit-*.sh
    and delegates to every match, so post-commit-anything.sh fires on every
    commit while appearing nowhere in settings.json.

    The real sweep reported post-commit-auto-integrate-corrections.sh as
    never-firing. That file's own header had predicted this exact bug in
    writing — "named as dark by tools that check only the first two
    surfaces" — and I shipped it anyway by reading the finding list without
    opening the findings."""
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "echo hi\n")
    _write(tmp_path, ".claude/hooks/post-commit-thing.sh", "echo fires on commit\n")
    _write(
        tmp_path,
        ".git/hooks/post-commit",
        'for hook in "$HOOKS_SRC"/post-commit-*.sh; do bash "$hook"; done\n',
    )
    assert find_unregistered_hooks(tmp_path) == []


def test_a_delegator_only_covers_its_own_prefix(tmp_path):
    """The fix must not become a blanket amnesty — a post-commit delegator
    says nothing about a pre-push hook."""
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "echo hi\n")
    _write(tmp_path, ".claude/hooks/pre-push-orphan.sh", "echo nobody calls me\n")
    _write(
        tmp_path,
        ".git/hooks/post-commit",
        'for hook in "$HOOKS_SRC"/post-commit-*.sh; do bash "$hook"; done\n',
    )
    assert [f.subject for f in find_unregistered_hooks(tmp_path)] == ["pre-push-orphan.sh"]


def test_sample_git_hooks_do_not_grant_reachability(tmp_path):
    """`.sample` files ship with git and run never."""
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "echo hi\n")
    _write(tmp_path, ".claude/hooks/post-commit-thing.sh", "echo x\n")
    _write(
        tmp_path,
        ".git/hooks/post-commit.sample",
        'for hook in "$HOOKS_SRC"/post-commit-*.sh; do bash "$hook"; done\n',
    )
    assert [f.subject for f in find_unregistered_hooks(tmp_path)] == ["post-commit-thing.sh"]


def test_a_retirement_naming_a_live_successor_is_not_a_finding(tmp_path):
    """Both remaining hooks on 2026-08-02 were dark ON PURPOSE — one retired
    for a more robust twin, one made unreachable by the sovereign-agent gate.
    Reporting them every run is how a real finding becomes wallpaper, which is
    the exact failure this module exists to prevent."""
    _write(tmp_path, ".claude/hooks/heir.sh", "#!/bin/bash\n")
    _write(tmp_path, ".claude/hooks/old.sh", "#!/bin/bash\n# SUPERSEDED-BY: heir.sh\n")
    _write(tmp_path, ".claude/settings.json", '{"hooks": "heir.sh"}')
    found = find_unregistered_hooks(tmp_path)
    kinds = {f.subject: f.kind for f in found}
    assert kinds.get("old.sh") == "retired-hook"
    assert "heir.sh" not in kinds


def test_a_retirement_naming_a_dead_successor_is_reported_louder(tmp_path):
    """THE anti-gaming test. If writing the comment were enough, the marker
    would be a free silence button and this detector would be worth nothing.
    A retirement pointing at a corpse means BOTH hooks' work happens nowhere,
    so it stays a finding."""
    _write(tmp_path, ".claude/hooks/heir.sh", "#!/bin/bash\n")
    _write(tmp_path, ".claude/hooks/old.sh", "#!/bin/bash\n# SUPERSEDED-BY: heir.sh\n")
    _write(tmp_path, ".claude/settings.json", "{}")  # heir wired nowhere
    found = {f.subject: f for f in find_unregistered_hooks(tmp_path)}
    assert found["old.sh"].kind == "unregistered-hook"
    assert "corpse" in found["old.sh"].detail
    assert "heir.sh" in found, "the dead successor must be reported in its own right"


def test_a_retirement_naming_a_file_that_does_not_exist_is_reported(tmp_path):
    """The laziest possible forgery: name anything at all."""
    _write(tmp_path, ".claude/hooks/old.sh", "#!/bin/bash\n# SUPERSEDED-BY: imaginary.sh\n")
    _write(tmp_path, ".claude/settings.json", "{}")
    found = {f.subject: f for f in find_unregistered_hooks(tmp_path)}
    assert found["old.sh"].kind == "unregistered-hook"


def test_retired_hooks_stay_visible_in_the_report(tmp_path):
    """Separated from the findings, NOT suppressed. Dropping them entirely
    would let a retirement quietly become an erasure."""
    _write(tmp_path, ".claude/hooks/heir.sh", "#!/bin/bash\n")
    _write(tmp_path, ".claude/hooks/old.sh", "#!/bin/bash\n# SUPERSEDED-BY: heir.sh\n")
    _write(tmp_path, ".claude/settings.json", '{"hooks": "heir.sh"}')
    out = format_report(find_unregistered_hooks(tmp_path))
    assert "nothing found by the detectors that ran" in out
    assert "Retired on purpose (1)" in out
    assert "old.sh" in out


def test_underscore_prefixed_library_is_not_a_hook(tmp_path):
    """`_lib.sh` is the sourced-library convention. The first real run reported
    it as dead code; it is sourced by nearly every hook."""
    _hooks_fixture(tmp_path, "bash .claude/hooks/wired.sh")
    _write(tmp_path, ".claude/hooks/wired.sh", "echo hi\n")
    _write(tmp_path, ".claude/hooks/_lib.sh", "helper() { :; }\n")
    assert find_unregistered_hooks(tmp_path) == []


# --------------------------------------------------------------------------
# The report must never imply completeness
# --------------------------------------------------------------------------


def test_blind_spots_print_even_on_a_clean_sweep():
    """The worst outcome for this detector is being trusted as exhaustive, and
    a clean report is exactly when that misreading happens. From the threadwalk
    run before it was built."""
    out = format_report([])
    assert "Silence here does not mean coverage" in out
    assert "FLOOR, not a ceiling" in out
    for b in BLIND_SPOTS:
        assert b in out


def test_blind_spots_print_alongside_findings(tmp_path):
    _write(tmp_path, "src/divineos/q.py", "# `divineos admin nonexistent`\n")
    out = format_report(find_unresolvable_prescribed_commands(tmp_path, REGISTERED))
    assert "admin nonexistent" in out
    assert "Silence here does not mean coverage" in out
