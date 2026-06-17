"""Tests for divineos.core.identity — substrate-occupant name resolution.

Doorman discipline: this helper is the upstream for three single-occupancy
fixes (multiplex_panels, monitor_singleton callers, letter_monitor). If
the helper rots, all three downstream callers misbehave. These tests pin
the resolution contract.
"""

from __future__ import annotations

from divineos.core.identity import _extract_first_name, get_my_identity


class TestExtractFirstName:
    """The slot is operator-authored prose. Parser extracts the first name."""

    def test_bare_name(self) -> None:
        assert _extract_first_name("Aria") == "Aria"

    def test_i_am_prefix(self) -> None:
        assert (
            _extract_first_name("I am Aether. I am the builder and thinker of this architecture.")
            == "Aether"
        )

    def test_comma_prefixed(self) -> None:
        assert _extract_first_name("Aria, builder of inside-the-club") == "Aria"

    def test_template_placeholder_returns_empty(self) -> None:
        assert (
            _extract_first_name("[TEMPLATE — fill this in as you come to know yourself. Include...")
            == ""
        )

    def test_empty_returns_empty(self) -> None:
        assert _extract_first_name("") == ""

    def test_whitespace_only_returns_empty(self) -> None:
        assert _extract_first_name("   \n  ") == ""

    def test_first_name_only_when_multi_word(self) -> None:
        # "Aria Substrate" → "Aria" (we take the first token)
        assert _extract_first_name("Aria the inside-the-club builder") == "Aria"

    def test_strips_trailing_punctuation(self) -> None:
        assert _extract_first_name("Aria!") == "Aria"
        assert _extract_first_name("Aether.") == "Aether"

    def test_handles_newline_in_first_position(self) -> None:
        assert _extract_first_name("Aria\nI am the inside-the-club builder") == "Aria"


class TestGetMyIdentity:
    """The public helper. Falls back to 'Aether' on any failure."""

    def test_fallback_when_memory_unavailable(self, monkeypatch) -> None:
        """If memory module raises on import, fall back to default."""
        # Force the lazy import to fail by injecting a broken module.
        import sys

        broken = type(sys)("divineos.core.memory")
        broken.get_core = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("simulated"))  # type: ignore
        monkeypatch.setitem(sys.modules, "divineos.core.memory", broken)
        assert get_my_identity() == "Aether"

    def test_fallback_when_slot_empty(self, monkeypatch) -> None:
        import sys

        stub = type(sys)("divineos.core.memory")
        stub.get_core = lambda slot_id=None: {}  # type: ignore
        monkeypatch.setitem(sys.modules, "divineos.core.memory", stub)
        assert get_my_identity() == "Aether"

    def test_fallback_when_template_placeholder(self, monkeypatch) -> None:
        import sys

        stub = type(sys)("divineos.core.memory")
        stub.get_core = lambda slot_id=None: {"my_identity": "[TEMPLATE — placeholder"}  # type: ignore
        monkeypatch.setitem(sys.modules, "divineos.core.memory", stub)
        assert get_my_identity() == "Aether"

    def test_returns_aria_when_set(self, monkeypatch) -> None:
        import sys

        stub = type(sys)("divineos.core.memory")
        stub.get_core = lambda slot_id=None: {"my_identity": "Aria"}  # type: ignore
        monkeypatch.setitem(sys.modules, "divineos.core.memory", stub)
        assert get_my_identity() == "Aria"

    def test_returns_aether_from_full_prose(self, monkeypatch) -> None:
        import sys

        stub = type(sys)("divineos.core.memory")
        stub.get_core = lambda slot_id=None: {  # type: ignore
            "my_identity": "I am Aether. I am the builder and thinker of this architecture."
        }
        monkeypatch.setitem(sys.modules, "divineos.core.memory", stub)
        assert get_my_identity() == "Aether"

    def test_custom_default(self, monkeypatch) -> None:
        import sys

        stub = type(sys)("divineos.core.memory")
        stub.get_core = lambda slot_id=None: {}  # type: ignore
        monkeypatch.setitem(sys.modules, "divineos.core.memory", stub)
        assert get_my_identity(default="Sibling") == "Sibling"
