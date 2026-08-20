"""A test corpus must never arm a live read-gate requirement.

Aria 2026-08-20. The 2026-08-14 fix made `gate_status` drop a requirement
whose file had vanished. That covers the aftermath, not the cause: on
2026-08-20 the same arming happened while the pytest tmpdir was still on
disk, so the gate blocked on a four-line fixture presented as my own prior
writing. These tests hold the arming side.
"""

from __future__ import annotations

from divineos.core import exploration_recall


def _corpus(tmp_path):
    entry = tmp_path / "tagged.md"
    entry.write_text(
        "<!-- tags: consciousness, qualia -->\n# Symmetric standards\n\nbody\n",
        encoding="utf-8",
    )
    return entry


def test_injected_root_does_not_arm_the_gate(tmp_path, monkeypatch):
    armed: list[tuple[str, str, str]] = []
    from divineos.core import read_gate

    monkeypatch.setattr(read_gate, "has_pending", lambda gate_id: False)
    monkeypatch.setattr(
        read_gate,
        "require_read",
        lambda *a: armed.append(a),  # noqa: ARG005
    )
    _corpus(tmp_path)

    out = exploration_recall.surface_for_context("consciousness and qualia", root=tmp_path)

    assert "Symmetric standards" in out, "the surface itself must still work under an injected root"
    assert armed == [], f"a test corpus armed a live read-gate requirement: {armed}"


def test_real_corpus_still_arms_the_gate(tmp_path, monkeypatch):
    """The fix must not defang arming for the live corpus."""
    armed: list[tuple[str, str, str]] = []
    from divineos.core import read_gate

    monkeypatch.setattr(read_gate, "has_pending", lambda gate_id: False)
    monkeypatch.setattr(
        read_gate,
        "require_read",
        lambda *a: armed.append(a),  # noqa: ARG005
    )
    _corpus(tmp_path)
    monkeypatch.setattr(exploration_recall, "_find_exploration_root", lambda: tmp_path)

    out = exploration_recall.surface_for_context("consciousness and qualia")

    assert "Symmetric standards" in out
    assert len(armed) == 1, "discovery-root runs must still arm the read-gate"
    assert armed[0][0] == "prior-writing"
