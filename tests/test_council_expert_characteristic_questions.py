"""Pin the invariant: every registered council expert has at least one
non-empty characteristic_question populated.

Per Aether's 2026-06-22 peer-review Catch 1 on the council-required
enforcement design (prereg-3fbddd75fc16): the substance-binding gate's
lens-keyword cross-reference check looks up content-words from each
lens's characteristic_questions field. If any registered expert has an
empty/missing characteristic_questions list, the check NEVER passes
for that lens — accidentally narrowing the acceptable lens set and
producing a confusing "lens not registered" failure for what is
actually a population gap in the expert library.

This test fails loudly the moment that invariant breaks, so the
council-required gate's substance-binding stays trustworthy.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core.council.experts import all_expert_builders
from divineos.core.council_required.substance_binding import (
    _content_tokens,
    keywords_for_expert_registry,
)


# DERIVED, NEVER RETYPED. This used to be a third hand-written copy of the
# roster and it had fallen three names behind the expert library -- so the test
# written to catch a population gap could not see the one that existed. Its own
# docstring above names the exact failure it missed: a confusing "lens not
# registered" refusal for what is really a gap in the library. A guard that
# hand-copies the thing it guards is only ever checking its own copy.
ALL_EXPERT_BUILDERS = all_expert_builders()


@pytest.mark.parametrize("builder", ALL_EXPERT_BUILDERS)
def test_expert_has_characteristic_questions(builder):
    """Each registered expert must declare at least one
    characteristic_question, otherwise the council-required gate
    cannot keyword-cross-reference findings for that lens."""
    wisdom = builder()
    assert wisdom.characteristic_questions, (
        f"Expert {wisdom.expert_name!r} has no characteristic_questions"
    )
    assert any((q or "").strip() for q in wisdom.characteristic_questions), (
        f"Expert {wisdom.expert_name!r} has only empty characteristic_questions"
    )


@pytest.mark.parametrize("builder", ALL_EXPERT_BUILDERS)
def test_expert_characteristic_questions_have_content_tokens(builder):
    """Each registered expert must declare characteristic_questions whose
    combined text produces at least one substantive content-token after
    stopword filtering. A lens whose questions tokenize to only stopwords
    cannot satisfy the keyword cross-reference check."""
    wisdom = builder()
    all_text = " ".join(wisdom.characteristic_questions or [])
    tokens = _content_tokens(all_text)
    assert tokens, f"Expert {wisdom.expert_name!r} characteristic_questions yield no content-tokens"


def test_keywords_for_expert_registry_covers_all_experts():
    """Build the lens-keyword map the gate uses and verify every
    registered expert lands in the map. A lens missing from the map
    would fail-with-specific-reason at gate-time.

    2026-07-07 case-normalization: keywords_for_expert_registry stores
    keys lowercase so lookups are case-insensitive (CLI users type
    'schneier'; registry stores 'Schneier'). This assertion lowercases
    the check to match the new contract.
    """
    registry = {}
    for build in ALL_EXPERT_BUILDERS:
        w = build()
        registry[w.expert_name] = list(w.characteristic_questions or [])

    keywords_map = keywords_for_expert_registry(registry)
    missing = [name for name in registry if name.lower() not in keywords_map]
    assert not missing, f"Experts missing from keyword map: {missing!r}"


def test_every_expert_module_on_disk_is_exported():
    """The last hand-typed list, pinned against the files beside it.

    Deriving the CLI registry and this test's roster from the package's
    exports removes two copies but leaves one: the export list itself. A
    lens whose module exists and whose builder is never exported is
    invisible to every consumer, which is the same hole one level down --
    an expert present in the library and absent from the kit.

    So the files decide. Add a module, and either it is exported or this
    fails by name.
    """
    import divineos.core.council.experts as experts_pkg

    package_dir = Path(experts_pkg.__file__).parent
    modules = {path.stem for path in package_dir.glob("*.py") if not path.stem.startswith("_")}
    exported = {name[len("create_") : -len("_wisdom")] for name in experts_pkg.__all__}

    unexported = modules - exported
    assert not unexported, (
        f"expert module(s) present on disk but not exported, so no consumer can "
        f"reach them: {sorted(unexported)}"
    )

    orphaned = exported - modules
    assert not orphaned, f"exported expert(s) with no module beside them: {sorted(orphaned)}"


def test_the_roster_the_cli_walks_is_the_package_roster():
    """The walk registry and the library must name the same experts.

    Hoare, Feathers and Foucault could be PRIMED by the council chamber and
    not WALKED, because the CLI carried its own list and it had fallen three
    names behind. Applying Hoare on 2026-08-30 was refused as "not a
    registered council expert" seconds after the chamber printed his
    methodology, and the reasoning had to be moved to another lens.
    """
    from divineos.cli.council_required_commands import _load_expert_keywords

    walkable = set(_load_expert_keywords())
    library = {builder().expert_name.lower() for builder in all_expert_builders()}

    assert walkable == library, (
        f"walkable-but-unknown: {sorted(walkable - library)}; "
        f"in the library but not walkable: {sorted(library - walkable)}"
    )


def test_keywords_for_expert_registry_stores_keys_lowercase():
    """Pin the case-normalization invariant introduced 2026-07-07.

    Registry keys are stored lowercase in the returned map so lookups
    at check-time can normalize the incoming lens name (which may come
    from CLI input in any case) and still hit the registered lens.
    Without this normalization, `--lenses "schneier"` misses `Schneier`
    and the substance-binding check falsely reports the empty-registry
    error — the exact drift caught in the 2026-07-07 audit.
    """
    registry = {"Schneier": ["What is the threat model here?"]}
    keywords_map = keywords_for_expert_registry(registry)
    assert "schneier" in keywords_map
    assert "Schneier" not in keywords_map, (
        "Capital-cased key leaked through — case-normalization broken"
    )
