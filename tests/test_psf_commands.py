"""`divineos psf` — the command three gates prescribed and none provided.

THE PAINTED DOOR (found by Aria, 2026-08-02). Three separate gates instructed
the agent to run `divineos psf mark-done <psf-id>` to clear a pending
structural-fix obligation. The command had never existed.
`structural_fix_tracker.mark_done()` worked fine and was reachable from no CLI
surface. Aria verified by exhaustion — absent from `--help`, `todos` is
read-only, `obligations` exposes only check/disabled/is-write/list — and filed
it as knowledge rather than routing around it. Her learning checkpoint was
unreachable as a direct consequence, with 139 obligations pending and no way
to close any of them.

WHAT THESE TESTS PROTECT. Making "mark done" easy is precisely the cheap
escape the obligation mechanism exists to prevent. So the note must point at
something real — a resolvable commit or an existing file — and that is checked
mechanically. It deliberately does NOT check whether the fix is any good: that
is a semantic property no gate can decide, and it stays the seat's to judge.
The check raises the cost of a hollow close above the cost of an honest one,
which is the whole of the repricing rule.
"""

from __future__ import annotations

import subprocess

from divineos.cli.psf_commands import find_evidence


def test_a_bare_claim_is_not_evidence():
    """The load-bearing one. 'handled it' must never close an obligation."""
    assert find_evidence("handled it") == []
    assert find_evidence("fixed, trust me") == []
    assert find_evidence("") == []


def test_an_existing_file_counts(tmp_path):
    (tmp_path / "real_module.py").write_text("x = 1\n", encoding="utf-8")
    ev = find_evidence("closed by rewriting real_module.py", repo_root=tmp_path)
    assert ev == ["file: real_module.py"]


def test_a_nonexistent_file_does_not_count(tmp_path):
    """Naming a plausible path is not the same as the path existing — this is
    the difference between a claim and evidence."""
    assert find_evidence("fixed in imaginary_module.py", repo_root=tmp_path) == []


def test_a_real_commit_counts(tmp_path):
    """Requires a real repo, so build one."""

    def run(*a):
        return subprocess.run(a, cwd=str(tmp_path), capture_output=True, check=False)

    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t.t")
    run("git", "config", "user.name", "t")
    (tmp_path / "f.txt").write_text("hello\n", encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "-q", "-m", "first")
    sha = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()

    ev = find_evidence(f"closed by commit {sha}", repo_root=tmp_path)
    assert any(e.startswith("commit:") for e in ev), ev


def test_a_fabricated_sha_does_not_count(tmp_path):
    """A hex string that looks like a commit but resolves to nothing is the
    obvious forgery, and it must not pass."""

    def run(*a):
        return subprocess.run(a, cwd=str(tmp_path), capture_output=True, check=False)

    run("git", "init", "-q")
    assert find_evidence("closed by commit deadbeefdeadbeef", repo_root=tmp_path) == []


def test_multiple_pieces_of_evidence_are_all_reported(tmp_path):
    """The operator should see everything that was actually checked, not just
    that something passed."""
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.sh").write_text("", encoding="utf-8")
    ev = find_evidence("touched a.py and b.sh", repo_root=tmp_path)
    assert set(ev) == {"file: a.py", "file: b.sh"}


def test_prose_alone_never_resolves(tmp_path):
    """A long, confident, entirely unevidenced note is the exact shape this
    refuses. Length is not evidence."""
    note = (
        "I performed a thorough structural remediation addressing the root cause "
        "and verified the behaviour comprehensively across the affected surfaces."
    )
    assert find_evidence(note, repo_root=tmp_path) == []
