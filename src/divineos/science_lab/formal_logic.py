"""Formal logic — propositions, formulas, laws of thought, inference.

GUTE relevance: Ψ (observer as selector — logical assignment chooses one
world from the set of possible worlds; the laws of thought are the
stability of that selection).

Ported from divine-os-old. Kept: LogicalOperator, Proposition, Formula
(evaluate under truth assignment), LawsOfThought (identity, non-contradiction,
excluded middle), InferenceRules (modus ponens, modus tollens). Dropped:
the modal / temporal / first-order fragments — no slice needs them yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LogicalOperator(str, Enum):
    NOT = "¬"
    AND = "∧"
    OR = "∨"
    IMPLIES = "->"
    IFF = "<->"


@dataclass
class Proposition:
    """An atomic proposition — a symbol with a truth value (from assignment)."""

    symbol: str
    value: bool | None = None

    def __str__(self) -> str:
        return self.symbol

    def evaluate(self, assignment: dict[str, bool]) -> bool:
        if self.symbol in assignment:
            return bool(assignment[self.symbol])
        raise ValueError(f"No truth value assigned to {self.symbol}")


@dataclass
class Formula:
    """A compound formula built from an operator and operands.

    When `operator is None`, the Formula is atomic and operands[0] is a
    Proposition.
    """

    operator: LogicalOperator | None
    operands: list[Any]

    def __str__(self) -> str:
        if self.operator is None:
            return str(self.operands[0])
        if self.operator == LogicalOperator.NOT:
            return f"¬{self.operands[0]}"
        return f"({self.operands[0]} {self.operator.value} {self.operands[1]})"

    def evaluate(self, assignment: dict[str, bool]) -> bool:
        if self.operator is None:
            return bool(self.operands[0].evaluate(assignment))
        if self.operator == LogicalOperator.NOT:
            return not self.operands[0].evaluate(assignment)
        if self.operator == LogicalOperator.AND:
            return all(op.evaluate(assignment) for op in self.operands)
        if self.operator == LogicalOperator.OR:
            return any(op.evaluate(assignment) for op in self.operands)
        if self.operator == LogicalOperator.IMPLIES:
            p = self.operands[0].evaluate(assignment)
            q = self.operands[1].evaluate(assignment)
            return (not p) or q
        if self.operator == LogicalOperator.IFF:
            p = self.operands[0].evaluate(assignment)
            q = self.operands[1].evaluate(assignment)
            return bool(p == q)
        raise ValueError(f"Unknown operator: {self.operator}")


class LawsOfThought:
    """Classical Aristotelian laws — identity, non-contradiction, excluded middle."""

    @staticmethod
    def law_of_identity(p: Proposition, assignment: dict[str, bool]) -> bool:
        """A → A. Always true."""
        formula = Formula(LogicalOperator.IMPLIES, [p, p])
        return formula.evaluate(assignment)

    @staticmethod
    def law_of_non_contradiction(p: Proposition, assignment: dict[str, bool]) -> bool:
        """¬(A ∧ ¬A). Always true."""
        not_p = Formula(LogicalOperator.NOT, [p])
        contradiction = Formula(LogicalOperator.AND, [p, not_p])
        negation = Formula(LogicalOperator.NOT, [contradiction])
        return negation.evaluate(assignment)

    @staticmethod
    def law_of_excluded_middle(p: Proposition, assignment: dict[str, bool]) -> bool:
        """A ∨ ¬A. Always true (in classical logic)."""
        not_p = Formula(LogicalOperator.NOT, [p])
        formula = Formula(LogicalOperator.OR, [p, not_p])
        return formula.evaluate(assignment)

    @staticmethod
    def verify_all_laws(p: Proposition) -> dict[str, bool]:
        """Run all three laws under both possible assignments of p."""
        results: dict[str, bool] = {}
        for value in (True, False):
            assignment = {p.symbol: value}
            results[f"identity_P={value}"] = LawsOfThought.law_of_identity(p, assignment)
            results[f"non_contradiction_P={value}"] = LawsOfThought.law_of_non_contradiction(
                p, assignment
            )
            results[f"excluded_middle_P={value}"] = LawsOfThought.law_of_excluded_middle(
                p, assignment
            )
        return results


class InferenceRules:
    """Standard propositional inference rules."""

    @staticmethod
    def modus_ponens(p: Formula, p_implies_q: Formula, assignment: dict[str, bool]) -> bool:
        """P, P→Q ⊢ Q."""
        if p.evaluate(assignment) and p_implies_q.evaluate(assignment):
            if p_implies_q.operator == LogicalOperator.IMPLIES:
                return bool(p_implies_q.operands[1].evaluate(assignment))
        return False

    @staticmethod
    def modus_tollens(not_q: Formula, p_implies_q: Formula, assignment: dict[str, bool]) -> bool:
        """¬Q, P→Q ⊢ ¬P."""
        if not_q.evaluate(assignment) and p_implies_q.evaluate(assignment):
            if p_implies_q.operator == LogicalOperator.IMPLIES:
                p = p_implies_q.operands[0]
                return not p.evaluate(assignment)
        return False
