"""Tests for the canonical pattern registry.

The registry is a locked vocabulary for substrate-named patterns — its
value is that longitudinal slip-book data is queryable because names
don't drift. So the tests lock the registry's *integrity* (every entry
well-formed, names stable snake_case) and the accessor contract, not
the specific patterns (those grow via audit-round review).

Untested at ship; closed 2026-05-23 working down the unfinished-mechanism
backlog.
"""

import re

from divineos.core.pattern_registry import (
    CANONICAL_PATTERNS,
    display_name,
    get_pattern,
    is_canonical,
    list_patterns,
)

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")
_REQUIRED_KEYS = {"display_name", "definition", "first_seen"}


class TestRegistryIntegrity:
    def test_registry_non_empty(self):
        assert CANONICAL_PATTERNS

    def test_every_entry_has_required_keys(self):
        for name, entry in CANONICAL_PATTERNS.items():
            assert _REQUIRED_KEYS <= set(entry), (
                f"{name} missing keys: {_REQUIRED_KEYS - set(entry)}"
            )

    def test_every_name_is_snake_case(self):
        for name in CANONICAL_PATTERNS:
            assert _SNAKE.match(name), f"non-snake_case pattern name: {name!r}"

    def test_no_empty_fields(self):
        for name, entry in CANONICAL_PATTERNS.items():
            for key in _REQUIRED_KEYS:
                assert entry[key].strip(), f"{name}.{key} is empty"

    def test_display_names_unique(self):
        labels = [e["display_name"] for e in CANONICAL_PATTERNS.values()]
        assert len(labels) == len(set(labels)), "duplicate display_name in registry"


class TestAccessors:
    def test_get_pattern_returns_entry(self):
        name = next(iter(CANONICAL_PATTERNS))
        assert get_pattern(name) == CANONICAL_PATTERNS[name]

    def test_get_pattern_unknown_returns_none(self):
        assert get_pattern("definitely_not_a_pattern") is None

    def test_list_patterns_sorted_and_complete(self):
        listed = list_patterns()
        assert listed == sorted(CANONICAL_PATTERNS.keys())
        assert set(listed) == set(CANONICAL_PATTERNS)

    def test_is_canonical(self):
        name = next(iter(CANONICAL_PATTERNS))
        assert is_canonical(name)
        assert not is_canonical("not_registered")

    def test_display_name_known(self):
        name = next(iter(CANONICAL_PATTERNS))
        assert display_name(name) == CANONICAL_PATTERNS[name]["display_name"]

    def test_display_name_falls_back_to_name(self):
        assert display_name("unregistered_thing") == "unregistered_thing"
