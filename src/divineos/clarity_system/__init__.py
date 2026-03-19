"""Agent Work Clarity System.

Provides pre-work clarity statements, execution tracking, and post-work summaries
with deviation analysis and learning extraction.
"""

from .base import (
    ClarityComponent,
    ClarityStatementGenerator,
    DeviationAnalyzer,
    ExecutionAnalyzer,
    LearningExtractor,
    PlanAnalyzer,
    SummaryGenerator,
)
from .clarity_generator import DefaultClarityStatementGenerator
from .deviation_analyzer import DefaultDeviationAnalyzer
from .event_integration import EventEmissionInterface
from .execution_analyzer import DefaultExecutionAnalyzer
from .hook_integration import HookIntegrationInterface
from .learning_extractor import DefaultLearningExtractor
from .ledger_integration import LedgerQueryInterface
from .plan_analyzer import DefaultPlanAnalyzer
from .session_integration import SessionManagerInterface
from .summary_generator import DefaultSummaryGenerator
from .types import (
    ClarityStatement,
    Deviation,
    ExecutionData,
    ExecutionMetrics,
    Lesson,
    PlanData,
    PlanMetrics,
    PlanVsActualComparison,
    PostWorkSummary,
    Recommendation,
    ScopeEstimate,
    ToolCall,
)

__all__ = [
    # Base classes
    "ClarityComponent",
    "ClarityStatement",
    "ClarityStatementGenerator",
    # Implementations
    "DefaultClarityStatementGenerator",
    "DefaultDeviationAnalyzer",
    "DefaultExecutionAnalyzer",
    "DefaultLearningExtractor",
    "DefaultPlanAnalyzer",
    "DefaultSummaryGenerator",
    "Deviation",
    "DeviationAnalyzer",
    "EventEmissionInterface",
    "ExecutionAnalyzer",
    "ExecutionData",
    "ExecutionMetrics",
    "HookIntegrationInterface",
    "LearningExtractor",
    # Integration
    "LedgerQueryInterface",
    "Lesson",
    "PlanAnalyzer",
    "PlanData",
    "PlanMetrics",
    "PlanVsActualComparison",
    "PostWorkSummary",
    "Recommendation",
    # Types
    "ScopeEstimate",
    "SessionManagerInterface",
    "SummaryGenerator",
    "ToolCall",
    "get_clarity_logger",
    # Logging
    "setup_clarity_logging",
]
