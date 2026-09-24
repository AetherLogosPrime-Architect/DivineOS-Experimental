"""The task belt: the pile ranked, a small current list pulled from it, done archived.

Andrew, 2026-09-23: *"the todo list should have a relevance/priority/most
beneficial task sorter.. so critical, severe or tasks that have wide reach get
chosen first over others. and then you need to automate the task flow so that
you are always aware of the current tasks.. something should pull from the
todo list.. erase it from the todo list as it goes into your current todo
folder (which would be much smaller than the full list) and then when you
complete the task it should mark it complete.. archive it and delete it from
your task list.. and go pull another one"*.

Every part of that already existed except the joints. ``unified_todos`` gathers
five drawers into one pile of hundreds; ``structural_fix_tracker`` has his June
main -> current -> archive design for one drawer, with nothing calling the pick;
``next_task_surface`` showed one item per turn in strict drawer order, and
``context_dedup`` hid it once it stopped changing -- so a LOW audit item from
July sat as the next task, invisibly, while real failures waited under it.
Design and council walk: docs/drafts/task_belt_draft_2026-09-23.md.

What this module adds, and only this:

- RANK across drawers: severity, then reach (how often the thing has come
  back), then age. Severity is the item's own where recorded, else a stated
  per-drawer default -- a class default, not a measurement dressed as one.
- PULL: the context build calls ``surface()`` every prompt. It reconciles the
  current list against each drawer (an item closed at its source is archived)
  and refills it to ``CURRENT_MAX``. Nothing to remember to run.
- DONE: ``done()`` closes an item through its drawer's own close path, with
  evidence, archives it, and pulls the next.
- LOUD WHEN STUCK, NEVER HIDDEN: the block changes only when the list does or
  an item crosses a stuck milestone (5, 20, 50 prompts), so dedup may collapse
  it between those -- but the collapsed pointer carries ``residual()``, which
  still names every current item. (First version counted up every prompt;
  Aria's reading showed that number carried no news and only defeated dedup.)
- TWINS: a row that is a current item filed again (his corrections are often
  filed raw and then again under "Andrew verbatim:") shares its slot and
  closes with it.

Could-not-look is never read as closed. If a drawer cannot say whether an item
is still open, the item stays current.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from divineos.core.paths import divineos_home
from divineos.core.unified_todos import TodoItem, collect_todos

CURRENT_MAX = 3
"""The current list's ceiling. One slot is reserved (see ``_refill``).

Three, not more: a larger current list is a second pile and lengthens every
cycle (Little's law); one slot would leave no room for the starvation guard.
Revisit once the drain rate has been measured, not before.
"""

STUCK_MILESTONES = (5, 20, 50)
"""Prompts-on-the-list thresholds at which a stuck item is news.

Aria's reading, 2026-09-23: a counter rising by one every prompt is perfectly
predictable, so it carries no information -- it only defeats dedup. The block
now changes when an item CROSSES one of these, and is byte-identical between
them, so dedup collapses it to the one-line residual that still names every
current item.
"""

SEVERITY_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")

#: Per-drawer default severity where an item records none of its own. These are
#: CLASS defaults and the surface says so; they are not per-item measurements.
DRAWER_DEFAULT = {
    "correction": "HIGH",
    "prereg": "MEDIUM",
    "structural-fix": "MEDIUM",
}

#: What the next step is called, per drawer, so the line says what to DO.
VERB = {
    "prereg": "assess",
    "audit": "resolve",
    "correction": "integrate correction",
    "structural-fix": "build",
    "claim": "investigate",
}

#: Drawers whose items close through ``done()``. The others close with their
#: own command and the belt notices on the next reconcile.
CLOSES_HERE = ("structural-fix", "correction", "audit")
OWN_COMMAND = {
    "prereg": "divineos prereg assess {id} --outcome ... --actor ... --notes ...",
    "claim": "divineos claims assess {id} ...",
}


def _current_path() -> Path:
    return divineos_home() / "task_belt_current.json"


def _archive_path() -> Path:
    return divineos_home() / "task_belt_archive.jsonl"


def key(source: str, item_id: str) -> str:
    return f"{source}:{item_id}"


def severity(item: TodoItem) -> str:
    if item.source == "audit":
        return str(item.extra.get("severity") or "LOW").upper()
    if item.source == "claim":
        return "MEDIUM" if str(item.extra.get("tier", "")).startswith("T1") else "LOW"
    return DRAWER_DEFAULT.get(item.source, "LOW")


def reach(item: TodoItem) -> int:
    """How many times the thing has come back. 1 where nothing is recorded."""
    return max(1, int(item.extra.get("occurrences") or 1))


def rank(item: TodoItem) -> tuple[int, int, float, str]:
    sev = severity(item)
    tier = SEVERITY_ORDER.index(sev) if sev in SEVERITY_ORDER else len(SEVERITY_ORDER)
    return (tier, -reach(item), -(item.age_days or 0.0), key(item.source, item.item_id))


def _is_due(item: TodoItem) -> bool:
    """Is this pile item a task right now?

    A pre-registration only once its review date has passed. An INFO audit
    finding never: the audit system files received CONFIRMs and status notes at
    INFO, which are acknowledgements, not work (the old next-task surface's
    calibration, 2026-06-20, carried forward).
    """
    if item.source == "prereg":
        return float(item.extra.get("overdue_days") or 0) > 0
    if item.source == "audit":
        return str(item.extra.get("severity", "")).upper() != "INFO"
    return True


def _load_current() -> list[dict[str, Any]]:
    path = _current_path()
    if not path.exists():
        return []
    return list(json.loads(path.read_text(encoding="utf-8")))


def _save_current(entries: list[dict[str, Any]]) -> None:
    path = _current_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def _archive(entry: dict[str, Any], how: str, evidence: str = "") -> None:
    path = _archive_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {**entry, "closed_how": how, "closed_at": time.time(), "evidence": evidence}
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


def _still_open(entry: dict[str, Any]) -> bool | None:
    """Open if ANY copy it holds is open; unknown if any copy cannot be read.

    An entry holding a correction filed twice is closed only when both are.
    """
    answers = [_one_open(entry["source"], i) for i in [entry["item_id"], *entry.get("twins", [])]]
    if any(a is True for a in answers):
        return True
    if any(a is None for a in answers):
        return None
    return False


def _one_open(source: str, item_id: str) -> bool | None:
    """True/False from the drawer itself; None when the drawer cannot say.

    Asked of the source directly rather than inferred from the pile, because
    ``collect_todos`` is fail-soft: an unreadable drawer yields no items, and
    reading absence-from-the-pile as closure would archive a whole drawer the
    first time its store failed to open.
    """
    try:
        if source == "structural-fix":
            from divineos.core.structural_fix_tracker import list_current, list_pending

            ids = {e.get("id") for e in list_pending()} | {e.get("id") for e in list_current()}
            return item_id in ids
        if source == "correction":
            from divineos.core.andrew_correction_tracker import list_open

            return item_id in {str(r.get("id")) for r in list_open()}
        if source == "audit":
            from divineos.core.watchmen.store import get_finding

            finding = get_finding(item_id)
            if finding is None:
                return None
            status = getattr(finding.status, "value", finding.status)
            return str(status) == "OPEN"
        if source == "prereg":
            from divineos.core.pre_registrations.store import get_pre_registration

            prereg = get_pre_registration(item_id)
            if prereg is None:
                return None
            return str(getattr(prereg.outcome, "value", prereg.outcome)) == "OPEN"
        if source == "claim":
            from divineos.core.claim_store import get_claim

            claim = get_claim(item_id)
            if claim is None:
                return None
            return str(claim.get("status", "")).upper() == "OPEN"
    except Exception:  # noqa: BLE001 -- a drawer that cannot be read cannot close anything
        return None
    return None


def _norm(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower()).split())


def _body(item: TodoItem) -> str:
    return _norm(str(item.extra.get("text") or item.summary))


def _same_thing(a: str, b: str) -> bool:
    """One text wholly inside the other: the same row filed twice.

    Aria's reading, 2026-09-23: two of the three slots went to one correction,
    filed once raw and once under "Andrew verbatim:". Measured on my seat the
    same day, 312 pairs of his corrections are one text contained in another.
    WHOLE-text containment, not a shared opening: a first-80-characters probe
    matched 788 pairs, because templated rows share their first line.
    """
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 40 and short in long_


def _entry(item: TodoItem, reserved: bool) -> dict[str, Any]:
    return {
        "key": key(item.source, item.item_id),
        "source": item.source,
        "item_id": item.item_id,
        "summary": item.summary,
        "body": _body(item),
        "twins": [],
        "severity": severity(item),
        "reach": reach(item),
        "pulled_at": time.time(),
        "prompts": 0,
        "reserved": reserved,
    }


def _fold_twins(current: list[dict[str, Any]], ranked: list[TodoItem]) -> list[TodoItem]:
    """Attach every pile item that is a current entry filed again; return the rest."""
    rest = []
    for item in ranked:
        home = next(
            (
                c
                for c in current
                if c["source"] == item.source and _same_thing(c.get("body", ""), _body(item))
            ),
            None,
        )
        if home is None:
            rest.append(item)
        elif item.item_id not in home["twins"]:
            home["twins"].append(item.item_id)
    return rest


def _refill(current: list[dict[str, Any]], pile: list[TodoItem]) -> list[dict[str, Any]]:
    """Fill to CURRENT_MAX. The last slot goes to the oldest item below the top tier.

    The starvation guard carried forward from 2026-08-28: under strict severity
    order, hundreds of HIGH corrections would mean my own MEDIUM repairs are
    reached never. So when the list is one short of full and nothing on it sits
    below the top tier, the last slot takes the OLDEST item that does.

    A row that is a current item filed again joins that item as a twin instead
    of taking a slot of its own.
    """
    taken = {c["key"] for c in current}
    taken |= {key(c["source"], t) for c in current for t in c.get("twins", [])}
    ranked = sorted((i for i in pile if key(i.source, i.item_id) not in taken), key=rank)
    ranked = _fold_twins(current, ranked)
    if not ranked:
        return current
    top_tier = min(rank(i)[0] for i in ranked)
    while len(current) < CURRENT_MAX and ranked:
        below_top = [i for i in ranked if rank(i)[0] > top_tier]
        on_list_below_top = any(
            SEVERITY_ORDER.index(c["severity"]) > top_tier
            for c in current
            if c["severity"] in SEVERITY_ORDER
        )
        if len(current) == CURRENT_MAX - 1 and below_top and not on_list_below_top:
            pick = max(below_top, key=lambda i: (i.age_days or 0.0, i.item_id))
            reserved = True
        else:
            pick = ranked[0]
            reserved = False
        ranked.remove(pick)
        current.append(_entry(pick, reserved))
        ranked = _fold_twins([current[-1]], ranked)
        if pick.source == "structural-fix":
            # His June design for this drawer: picking is an atomic move from
            # main into its own current list, so the pick is visible there too.
            from divineos.core.structural_fix_tracker import pick_to_current

            pick_to_current(pick.item_id)
    return current


def pull(pile: list[TodoItem] | None = None) -> list[dict[str, Any]]:
    """Reconcile the current list against the drawers, then refill it."""
    pile = [i for i in (collect_todos() if pile is None else pile) if _is_due(i)]
    kept: list[dict[str, Any]] = []
    for entry in _load_current():
        if _still_open(entry) is False:
            _archive(entry, "closed at source")
        else:
            kept.append(entry)
    current = _refill(kept, pile)
    _save_current(current)
    return current


def open_count(pile: list[TodoItem] | None = None) -> int:
    return sum(1 for i in (collect_todos() if pile is None else pile) if _is_due(i))


def done(ref: str, evidence: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Close one current item through its drawer, archive it, and pull the next.

    Raises ValueError with the reason when it cannot close. Nothing is
    archived unless the drawer itself accepted the close.
    """
    current = _load_current()
    entry = next((c for c in current if c["key"] == ref or c["item_id"] == ref), None)
    if entry is None:
        raise ValueError(f"{ref} is not on the current list. `divineos belt` shows what is.")
    source, item_id = entry["source"], entry["item_id"]
    if source not in CLOSES_HERE:
        raise ValueError(
            f"A {source} closes with its own command, and the belt notices on the next "
            f"prompt: {OWN_COMMAND[source].format(id=item_id)}"
        )
    if source in ("structural-fix", "audit"):
        from divineos.cli.psf_commands import find_evidence

        if not find_evidence(evidence):
            raise ValueError(
                "Evidence must name a real commit or an existing file, the same rule as "
                "`psf mark-done`. A close that points at nothing is the cheap close."
            )
    if not _close_one(source, item_id, evidence):
        raise ValueError(f"The {source} drawer refused to close {item_id}; it is still current.")
    # The same row filed again closes with it. A twin the drawer refuses stays
    # open at its source, so the next pull brings it back rather than losing it.
    entry["twins_refused"] = [
        t for t in entry.get("twins", []) if not _close_one(source, t, evidence)
    ]
    _save_current([c for c in current if c["key"] != entry["key"]])
    _archive(entry, "done", evidence)
    return entry, pull()


def _close_one(source: str, item_id: str, evidence: str) -> bool:
    if source == "structural-fix":
        from divineos.core.structural_fix_tracker import mark_done

        return mark_done(item_id, note=evidence)
    if source == "correction":
        # The correction tracker keeps its own rules for what closes one of his
        # corrections; the belt never decides that for him.
        from divineos.core.andrew_correction_tracker import integrate

        return integrate(int(item_id), evidence)
    from divineos.core.watchmen.store import resolve_finding

    return resolve_finding(item_id, "RESOLVED", evidence)


def _milestone(prompts: int) -> int:
    return max((m for m in STUCK_MILESTONES if prompts >= m), default=0)


def _line(n: int, c: dict[str, Any]) -> list[str]:
    summary = " ".join(str(c["summary"]).split())
    if len(summary) > 110:
        summary = summary[:109].rstrip() + "…"
    passed = _milestone(int(c.get("prompts", 0)))
    held = f"stuck past {passed} prompts" if passed else "new on the list"
    tag = f"{c['severity']} {c['source']}" + (", reserved slot" if c.get("reserved") else "")
    if c.get("twins"):
        tag += f", +{len(c['twins'])} filed again: {', '.join(c['twins'])}"
    lines = [f"  {n}. {VERB.get(c['source'], 'work')} {c['item_id']} [{tag}]: {summary} -- {held}"]
    if int(c.get("prompts", 0)) in STUCK_MILESTONES:
        lines.append(f"     !! this prompt it crossed {c['prompts']} prompts on the current list")
    if c["source"] in CLOSES_HERE:
        lines.append(f'     close: divineos belt done {c["key"]} --evidence "<commit or file>"')
    else:
        lines.append(f"     close: {OWN_COMMAND[c['source']].format(id=c['item_id'])}")
    return lines


def render(current: list[dict[str, Any]], remaining: int) -> str:
    """The full block. Byte-identical between changes, so dedup can collapse it.

    It changes when the list changes, when the pile's size changes, and on the
    prompt an item crosses a STUCK_MILESTONES line -- never merely because
    another prompt passed.
    """
    if not current:
        return ""
    out = [
        "## NEXT TASK -- your current list (the belt: work this, don't ask)",
        "",
        f"  Pulled from {remaining} open across the drawers, most severe and",
        f"  widest-reaching first. Marked again at {', '.join(map(str, STUCK_MILESTONES))} prompts stuck.",
        "",
    ]
    for n, c in enumerate(current, 1):
        out.extend(_line(n, c))
    return "\n".join(out) + "\n"


def residual() -> str:
    """The one line that survives dedup: every current item, still named.

    Andrew asked to be "always aware of the current tasks"; dedup hiding the
    whole block as "unchanged" is how a LOW item from July sat invisible on
    top. So when the block is collapsed, this line stays.
    """
    current = _load_current()
    if not current:
        return ""
    named = "; ".join(
        f"{n}) {VERB.get(c['source'], 'work')} {c['key']}" for n, c in enumerate(current, 1)
    )
    return f"  still current: {named}"


def surface() -> str:
    """Pull, count one more prompt against each current item, and render."""
    pile = [i for i in collect_todos() if _is_due(i)]
    current = pull(pile)
    for c in current:
        c["prompts"] = int(c.get("prompts", 0)) + 1
    _save_current(current)
    taken = {c["key"] for c in current}
    taken |= {key(c["source"], t) for c in current for t in c.get("twins", [])}
    remaining = sum(1 for i in pile if key(i.source, i.item_id) not in taken)
    return render(current, remaining)


__all__ = [
    "CURRENT_MAX",
    "done",
    "key",
    "open_count",
    "pull",
    "rank",
    "render",
    "residual",
    "severity",
    "surface",
]
