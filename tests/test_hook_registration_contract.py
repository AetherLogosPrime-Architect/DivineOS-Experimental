"""Every hook script is registered; every registration points at a real file.

Aria 2026-08-17, from a council walk on the question: *mechanisms in this
system keep getting built correctly, tested, and never wired to anything
that runs them — what structural change would STOP that rather than
detect it?*

Hoare's lens gave the answer: make the illegal state unrepresentable
rather than adding one more thing to remember. The illegal states here
are two, and they are mirror images:

  ORPHAN       a script exists in .claude/hooks/ that no settings.json
               entry ever invokes. It is correct, it is tested, it never
               runs. This is the shape that hid the read-gate's release
               path, the sycophancy detector, and closing_token_detector.

  PHANTOM      a settings.json entry names a script that is not there.
               The hook silently no-ops and the config still reads as
               full coverage.

Wittgenstein's lens supplied the reason a prose exemption cannot close
this: *what would count as this being wrong?* In the sibling file
tests/test_detector_wiring_contract.py, a module may be exempted from
the orchestrator-import requirement by a comment asserting that some
hook script invokes it instead. Nothing checked that assertion. An
exemption written in English is satisfied by writing English. This file
checks the ground those sentences stand on.

What this does NOT claim: that a registered hook FIRES, or fires
correctly. Registration is necessary, not sufficient — the firing
question is answered by the timing log, not by static config. Keeping
that boundary explicit is the point; conflating them is how "configured"
started passing for "working" in the first place.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _settings_path() -> Path:
    return _repo_root() / ".claude" / "settings.json"


def _hooks_dir() -> Path:
    return _repo_root() / ".claude" / "hooks"


def _named_in(path: Path) -> set[str]:
    """Return every `.claude/hooks/*.sh` basename named in a file.

    Scanned as raw text rather than walked as structure: hook commands
    appear in several shapes (bare `bash path`, chained, wrapped in a
    timeout), and a regex over the whole file catches all of them
    without this test needing to model the settings schema.
    """
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    return set(re.findall(r"\.claude/hooks/([A-Za-z0-9_.-]+\.sh)", text)) | set(
        re.findall(r"^([A-Za-z0-9_.-]+\.sh)$", text, re.MULTILINE)
    )


def _glob_dispatched(path: Path) -> set[str]:
    """Return scripts reached by a `for hook in .../prefix-*.sh` dispatcher.

    The installed post-commit hook does not name its children; it globs
    `post-commit-*.sh`. A name-only scan calls every one of those an
    orphan, which is the opposite of the truth — they are the ones
    guaranteed to be picked up without anybody remembering to register
    them, which is why the glob was written that way in the first place.
    """
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    reached: set[str] = set()
    for prefix in re.findall(r'HOOKS_SRC"?/([A-Za-z0-9_.-]+)\*\.sh', text):
        reached |= {p.name for p in _hooks_dir().glob(f"{prefix}*.sh")}
    return reached


def _registered_scripts() -> set[str]:
    """Return every hook script REACHABLE from a real entry point.

    Two roots, because hooks are launched from two places:

      settings.json        the Claude Code hook config
      setup/setup-hooks.sh the committed installer for git hooks
                           (.git/hooks itself is machine-local and
                           uncommitted, so it cannot be the root)

    Then transitive closure, which the first version of this test did
    not do — and getting that wrong is instructive enough to record.
    It reported 19 orphans; 16 of them were reached through
    session-init-once.sh, a registered dispatcher that runs fourteen
    child hooks by name. A reachability question answered without
    following edges gives a confident wrong number, and I filed a
    pre-registration FAILED on that number before checking. The
    instrument was built the same way as the defect it hunts.
    """
    installer = _repo_root() / "setup" / "setup-hooks.sh"
    roots = _named_in(_settings_path()) | _named_in(installer)
    roots |= _glob_dispatched(installer)
    reachable: set[str] = set()
    frontier = list(roots)
    while frontier:
        name = frontier.pop()
        if name in reachable:
            continue
        reachable.add(name)
        script = _hooks_dir() / name
        if script.exists():
            frontier.extend(_named_in(script) - reachable)
    return reachable


def _present_scripts() -> set[str]:
    return {p.name for p in _hooks_dir().glob("*.sh")}


# Scripts that legitimately live in .claude/hooks/ without being reachable.
# Every entry names WHY. An unexplained orphan is the failure this file
# exists to catch, so adding a name here without a reason defeats it.
_UNREGISTERED_BY_DESIGN: dict[str, str] = {
    "_lib.sh": "shared function library sourced BY hooks; not itself a hook",
}

# In-file markers a deliberately-dark hook may declare instead of taking a
# line in the dict above. Keeping the declaration in the script means it
# cannot drift away from the thing it describes — the dict is a second
# place to remember, and a second place to remember is the defect.
_SUPERSEDED_RE = re.compile(r"^#\s*SUPERSEDED-BY:\s*([A-Za-z0-9_.-]+\.sh)\s*$", re.MULTILINE)
_INTENTIONALLY_UNWIRED = "INTENTIONALLY UNWIRED"


def test_no_orphan_hook_scripts() -> None:
    """An unreachable hook must SAY it is unreachable, in its own text.

    This is the built-correct-and-never-wired shape at the hook layer.
    From outside, an orphan script and a live one are identical: both
    are present, both pass shellcheck, both read as coverage.

    Two declarations count, and both were already in use here before
    this test existed — the convention was invented by whoever needed
    it and never enforced, which is its own small instance of the class:

      # SUPERSEDED-BY: <script>.sh   a stronger mechanism stands in front
      # INTENTIONALLY UNWIRED        no wiring path exists yet
    """
    orphans = sorted(_present_scripts() - _registered_scripts() - set(_UNREGISTERED_BY_DESIGN))
    undeclared = []
    for name in orphans:
        text = (_hooks_dir() / name).read_text(encoding="utf-8")
        if _SUPERSEDED_RE.search(text) or _INTENTIONALLY_UNWIRED in text:
            continue
        undeclared.append(name)
    assert not undeclared, (
        f"Hook scripts that no entry point reaches and that do not say so: "
        f"{undeclared}. Each is built and does not run, while reading as "
        f"coverage. Register it, delete it, or declare it dark in its own "
        f"header with `# SUPERSEDED-BY: <script>.sh` or the words "
        f"`{_INTENTIONALLY_UNWIRED}` plus the reason."
    )


def test_superseded_claims_name_a_live_successor() -> None:
    """`SUPERSEDED-BY: X` must name a script that exists AND is reachable.

    Without this, a dark hook can point at another dark hook and the
    pair vouch for each other — an orphan chain that satisfies every
    check while nothing at the end of it runs.
    """
    reachable = _registered_scripts()
    present = _present_scripts()
    failures = []
    for name in sorted(present):
        text = (_hooks_dir() / name).read_text(encoding="utf-8")
        m = _SUPERSEDED_RE.search(text)
        if not m:
            continue
        successor = m.group(1)
        if successor not in present:
            failures.append(f"{name}: superseded by {successor}, which does not exist")
        elif successor not in reachable:
            failures.append(f"{name}: superseded by {successor}, which is itself unreachable")
    assert not failures, "Supersession claims pointing at nothing live:\n  " + "\n  ".join(failures)


def test_no_phantom_hook_registrations() -> None:
    """A settings.json entry naming a missing script silently no-ops.

    The mirror of the orphan case, and the more dangerous one: config
    reads as full coverage while the hook cannot possibly fire.
    """
    phantoms = sorted(_registered_scripts() - _present_scripts())
    assert not phantoms, (
        f"settings.json registers hook scripts that do not exist: {phantoms}. "
        f"These registrations cannot fire. Either restore the script or "
        f"remove the registration — a dead entry is worse than no entry, "
        f"because it reads as coverage."
    )


def _exemption_hook_claims() -> list[tuple[str, str]]:
    """Return (module_file, claimed_hook_script) pairs from the sibling test.

    The wiring-contract test exempts several operating_loop modules on
    the stated grounds that a named hook script invokes them. Those
    sentences are parsed here so the claim can be checked rather than
    trusted.
    """
    contract = _repo_root() / "tests" / "test_detector_wiring_contract.py"
    text = contract.read_text(encoding="utf-8")
    pairs: list[tuple[str, str]] = []
    for m in re.finditer(r'"(\w+\.py)":\s*"([^"]*)"', text):
        module, reason = m.group(1), m.group(2)
        for hook in re.findall(r"\.claude/hooks/([A-Za-z0-9_.-]+\.sh)", reason):
            pairs.append((module, hook))
    return pairs


def test_exemption_claims_name_real_registered_hooks() -> None:
    """An exemption that says "a hook invokes it" must be true.

    Three conditions, because a claim can fail at three depths: the
    script may not exist, it may exist but not be registered, or it may
    be registered but never mention the module it supposedly invokes.
    """
    claims = _exemption_hook_claims()
    assert claims, (
        "No hook-invocation exemption claims found in the wiring-contract "
        "test. Either the exemptions were rewritten or this parser drifted "
        "from their shape — a checker that silently checks nothing is the "
        "same defect one level up."
    )

    present = _present_scripts()
    registered = _registered_scripts()
    failures: list[str] = []

    for module, hook in claims:
        if hook not in present:
            failures.append(f"{module}: claims {hook} invokes it, but that script does not exist")
            continue
        if hook not in registered:
            failures.append(f"{module}: claims {hook} invokes it, but {hook} is not registered")
            continue
        hook_text = (_hooks_dir() / hook).read_text(encoding="utf-8")
        stem = module[:-3]
        if stem not in hook_text:
            failures.append(f"{module}: {hook} is registered but never references {stem}")

    assert not failures, "Exemption claims that are not true:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize("name,reason", sorted(_UNREGISTERED_BY_DESIGN.items()))
def test_by_design_entries_still_exist(name: str, reason: str) -> None:
    """A by-design exemption for a deleted file is stale bookkeeping."""
    assert (_hooks_dir() / name).exists(), (
        f"_UNREGISTERED_BY_DESIGN lists {name} ({reason}) but the file is gone. Remove the entry."
    )
