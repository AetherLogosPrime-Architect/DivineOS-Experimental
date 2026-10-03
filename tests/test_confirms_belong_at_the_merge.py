"""Nothing may demand Andrew's signature before an edit. Only merges.

Andrew, 2026-09-06, counting it himself as the tenth time:

    "our confirms only come when merging to fucking main.. and you have both
    claimed to have fixed this several times.. let me guess.. all of the code
    is still there and none of it was properly superceded"

He was right. A check still lived in the council gate that refused a
kiln-layer EDIT until he or Aletheia had signed the walk. It fired on him
that same night, on the one file he had just told me to write his rule into,
and the rule was about him never having to be asked for anything again.

WHY THE DEMAND WAS WRONG, and it is not only that he said so. A confirm asked
for before the edit is unreviewable by construction: there is no diff yet, so
there is nothing for a reviewer to look at, and the signature could only be a
guess about text that does not exist. Review happens on the way OUT. It also
made him a component -- a value could not be corrected unless he was present,
awake and willing -- which is the exact shape he has spent months asking us to
stop building.

AND IT WAS A DUPLICATE. Every kiln file is on the guardrail list, and the
merge gate already requires multi-party review for those. The protection was
never missing. It was doubled, and the second copy stood on the wrong side of
the work.

WHY A TEST AND NOT A NOTE. He has been told this was fixed several times. A
note saying "do not add this back" is exactly the thing that has failed
repeatedly here; the session this came from was about advice not working.
This fails loudly instead, on the two things that would bring it back: a check
that demands a signature before an edit, and a record with a slot to hold one.
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
COUNCIL = ROOT / "src" / "divineos" / "core" / "council_required"


def _sources() -> list[Path]:
    return sorted(COUNCIL.glob("*.py"))


def test_the_scan_finds_the_package_at_all() -> None:
    """A control, because zero from a broken scan reads exactly like a pass.

    This suite's own lesson from the same night: a grep that returned nothing
    was one step from being filed as evidence of absence.
    """
    assert _sources(), "the council_required package did not resolve"
    assert (COUNCIL / "substance_binding.py").exists()


def test_no_check_demands_a_signature_before_an_edit() -> None:
    for path in _sources():
        body = path.read_text(encoding="utf-8", errors="replace")
        # The comments explaining the removal name the old field on purpose,
        # so this looks for machinery rather than for the word: a check
        # function, or a roster of people allowed to sign one.
        assert "def _check_kiln_confirmed_by" not in body, (
            f"{path.name} has re-added the check that refuses an edit until "
            "Andrew or Aletheia signs. Confirms happen at the merge gate."
        )
        assert "EXTERNAL_ACTORS_FOR_KILN" not in body, (
            f"{path.name} has re-added a roster of people who may sign off on "
            "an edit. There is no such roster; it belongs to the merge."
        )


def test_a_walk_record_cannot_carry_a_signature() -> None:
    """The slot is the other half. Delete only the check and the field
    remains, which is how a removed rule grows back."""
    from divineos.core.council_required.types import CouncilRecord

    record = CouncilRecord("r", 0.0, "walker", "edit:x.py", (), (), "synthesis")
    assert not hasattr(record, "confirmed_by"), (
        "CouncilRecord carries confirmed_by again. A walk is evidence that I "
        "did the thinking; it is not a place to store someone else's approval."
    )


def test_the_walk_logger_does_not_ask_for_one() -> None:
    """The command he would have had to be woken up to satisfy."""
    cli = ROOT / "src" / "divineos" / "cli" / "council_required_commands.py"
    body = cli.read_text(encoding="utf-8", errors="replace")
    assert '"--confirmed-by"' not in body, (
        "council log accepts --confirmed-by again, which is an invitation to "
        "go and fetch a signature before doing the work."
    )


def test_the_merge_gate_still_covers_what_the_edit_gate_stopped_covering() -> None:
    """Supersede, do not amputate -- asked at the door that owns the answer.

    Removing the edit-time demand is only safe if the merge really does refuse.
    This asserts that against the RULESET, which is where this repository's
    protection actually lives.

    WHY IT ASKS THERE, and the reason is my own error from the same day. The
    first version of this file pinned the kiln file to the guardrail list, on
    the reasoning that merge-time coverage came from that list. Hours later
    Andrew retired the list, and separately I told him main had no protection
    at all -- because I asked the CLASSIC branch-protection endpoint, which
    answers 404 when the rule lives in a ruleset. A 404 there means "no rule of
    THIS KIND", not "no rule". I read absence-of-answer as answer-of-absence,
    and Aether then ran the SAME endpoint and called the matching result a
    confirmation. Two runs of one method is one run.

    THREE STATES, NEVER TWO. If the required-checks list can be read, this
    passes or fails on it. If it cannot -- no network, no gh, no auth, a rate
    limit -- it SKIPS, loudly, naming what could not be reached. It must never
    resolve an unanswerable question into a green tick, because that is exactly
    the failure it exists to prevent, and a skipped test says "unknown" where a
    passing one would say "safe".
    """
    import json
    import shutil
    import subprocess

    if shutil.which("gh") is None:
        pytest.skip("no gh CLI: enforcement is UNKNOWN here, which is not the same as absent")
    try:
        proc = subprocess.run(
            ["gh", "api", "repos/{owner}/{repo}/rulesets", "--jq", ".[].id"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # noqa: BLE001
        pytest.skip(f"could not reach the ruleset API ({exc}); enforcement UNKNOWN, not absent")
    if proc.returncode != 0 or not proc.stdout.strip():
        pytest.skip(
            "ruleset API returned nothing usable; enforcement UNKNOWN, not absent. "
            f"stderr: {proc.stderr.strip()[:200]}"
        )

    required: list[str] = []
    for ruleset_id in proc.stdout.split():
        detail = subprocess.run(
            ["gh", "api", f"repos/{{owner}}/{{repo}}/rulesets/{ruleset_id}"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=30,
        )
        if detail.returncode != 0:
            continue
        for rule in json.loads(detail.stdout).get("rules", []):
            if rule.get("type") == "required_status_checks":
                params = rule.get("parameters", {})
                required += [c["context"] for c in params.get("required_status_checks", [])]

    assert "multi-party-review" in required, (
        "the review check is not required before merge, so a red verdict on it "
        "cannot hold the merge button -- and the edit-time demand that used to "
        f"stand in front of kiln edits is gone. Required checks found: {required}"
    )
