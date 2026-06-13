"""Goal-set adjacency surface — close the substrate-has-it-reader-doesnt-reach
pattern at goal-set time.

Andrew 2026-06-12 named the structural gap that motivated this module:
the semantic-search consumer (prereg-2ad79e23fcf7) was built and
shipped but only used twice in the same session — both times to demo
it. The Bengio "built but not inhabited" failure mode the consumer's
own pre-reg listed as a falsifier.

The structural fix: when I set a new goal via ``divineos goal add``,
the OS automatically runs the semantic-search consumer against the
goal text and surfaces top adjacency hits. That way I see "you've
already written about adjacent things in entry 38, entry 51, entry
75" at the moment I declare intent to build — not as a pull-only
command I have to remember to reach for.

This pairs with the existing build-shape council advise in
``goal_add_cmd`` (hud_commands.py:97). Same altitude (soft-advise,
informational, never blocks goal-add), different lens (council =
"who should I think with"; adjacency = "what have I already written
about this").

## Why a separate module

The goal_add CLI already has a try/except wrapper around the council
advise; adding another inline block bloats the CLI function and
mixes concerns. The helper here is pure: takes goal text + optional
db path, returns formatted lines (or empty list on any failure path).
The CLI just echoes the lines.

## Fail-quiet

This is best-effort. The substrate-modifying path must not break
because the index isn't built yet, the embedding model isn't
available, or any other reason. Every exception path returns
``[]`` — empty list means "nothing to surface", and goal_add
continues normally.
"""

from __future__ import annotations

from pathlib import Path


def adjacency_lines_for_goal(
    goal_text: str,
    *,
    db_path: str | None = None,
    top_k: int = 3,
    min_similarity: float = 0.35,
) -> list[str]:
    """Return formatted ``[adjacency]`` lines for the goal text, or ``[]``.

    Empty list means "no surfaceable adjacency" for any reason:
    - The semantic-search DB doesn't exist (index never built)
    - The embedding model isn't available
    - No hits exceed ``min_similarity``
    - Any exception during search

    The non-empty case returns a list of click-printable strings,
    starting with a header line. The caller is expected to echo each
    line. ``min_similarity=0.35`` was picked empirically — below that
    threshold the hits read as tangential rather than truly adjacent.
    """
    if not goal_text.strip():
        return []
    try:
        from divineos.core import semantic_search
        from divineos.core._ledger_base import data_dir
    except ImportError:
        return []

    resolved_db = db_path or str(Path(data_dir()) / "semantic_search.db")
    if not Path(resolved_db).exists():
        return []

    try:
        hits = semantic_search.search(
            goal_text, resolved_db, top_k=top_k, min_similarity=min_similarity
        )
    except Exception:  # noqa: BLE001 — adjacency surface must never break goal-add
        return []

    if not hits:
        return []

    lines: list[str] = []
    lines.append(
        "[adjacency] you've already written about adjacent themes — "
        "consider reading before building:"
    )
    for h in hits:
        rel_path = h.source_path
        try:
            rel_path = str(Path(h.source_path).relative_to(Path.cwd()))
        except ValueError:
            pass
        lines.append(f"  [{h.similarity:.3f}] {rel_path}:{h.paragraph_index}")
    lines.append('  (full: divineos find query "<your goal text>")')
    return lines
