"""Memory-type-aware retrieval — substrate-native types with human analogs.

The OS already stores everything; what was missing is retrieval that
respects type-distinctions. Different work-contexts need different
substrate pulls.

Substrate types (named for what they are in this OS):

  RAW_BUFFER     — transcript, tool I/O, ledger pre-extraction
  CONTEXT_WINDOW — what is currently in-attention this turn
  TIMELINE       — ledger events + holding + corrections + affect +
                   file_touched + decisions + explorations, assembled
                   chronologically around a topic or file
  KNOWLEDGE      — knowledge store + opinions; FTS-searchable
  SKILL_INDEX    — skills, CLI commands, hook scripts
  PRIMING        — briefing surfaces (presence, scaffold, exploration titles)
  REFLEX         — operating-loop detectors (apology -> principle, etc.)
  PROSPECTIVE    — overdue preregs, holding aging, queue items

Human-memory analog (commentary only, not part of the symbols):
  RAW_BUFFER ~ raw input buffer
  CONTEXT_WINDOW ~ working memory
  TIMELINE ~ episodic recall
  KNOWLEDGE ~ semantic memory
  SKILL_INDEX ~ procedural
  PRIMING ~ recognition shaping
  REFLEX ~ classical conditioning
  PROSPECTIVE ~ prospective memory

Andrew named this 2026-05-01: type-aware retrieval as the next wiring
layer after the operating loop's three hooks.
"""

from divineos.core.memory_types.skill_index import (
    SkillEntry,
    format_skills,
    load_skills,
    rank_skills,
)
from divineos.core.memory_types.taxonomy import (
    SubstrateMemoryType,
    route_intent,
)
from divineos.core.memory_types.timeline import (
    TimelineEvent,
    format_timeline,
    recall_timeline,
)

__all__ = [
    "SkillEntry",
    "SubstrateMemoryType",
    "TimelineEvent",
    "format_skills",
    "format_timeline",
    "load_skills",
    "rank_skills",
    "recall_timeline",
    "route_intent",
]
