"""Backward-compat shim — re-exports from logic_reasoning.py."""

from divineos.core.logic.logic_reasoning import (  # noqa: F401
    INVERSE_RELATIONS,
    RELATION_TYPES,
    LogicalRelation,
    create_relation,
    deactivate_relation,
    find_relation,
    get_neighbors,
    get_relations,
    init_relation_table,
)
