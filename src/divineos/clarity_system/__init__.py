"""
Agent Work Clarity System.

Provides pre-work clarity statements, execution tracking, and post-work summaries
with deviation analysis and learning extraction.
"""

from .types import (
    ScopeEstimate,
    ClarityStatement,
    PlanMetrics,
    PlanData,
    ToolCall,
    ExecutionMetrics,
    ExecutionData,
    Deviation,
    Lesson,
    Recommendation,
    PlanVsActualComparison,
    PostWorkSummary,
)
from .base import (
    ClarityComponent,
    ClarityStatementGenerator,
    PlanAnalyzer,
    ExecutionAnalyzer,
    DeviationAnalyzer,
    LearningExtractor,
    SummaryGenerator,
)
from .logging_config import setup_clarity_logging, get_clarity_logger
from .clarity_generator import DefaultClarityStatementGenerator
from .plan_analyzer import DefaultPlanAnalyzer
from .execution_analyzer import DefaultExecutionAnalyzer
from .deviation_analyzer import DefaultDeviationAnalyzer
from .learning_extractor import DefaultLearningExtractor
from .summary_generator import DefaultSummaryGenerator

__all__ = [
    # Types
    "ScopeEstimate",
    "ClarityStatement",
    "PlanMetrics",
    "PlanData",
    "ToolCall",
    "ExecutionMetrics",
    "ExecutionData",
    "Deviation",
    "Lesson",
    "Recommendation",
    "PlanVsActualComparison",
    "PostWorkSummary",
    # Base classes
    "ClarityComponent",
    "ClarityStatementGenerator",
    "PlanAnalyzer",
    "ExecutionAnalyzer",
    "DeviationAnalyzer",
    "LearningExtractor",
    "SummaryGenerator",
    # Implementations
    "DefaultClarityStatementGenerator",
    "DefaultPlanAnalyzer",
    "DefaultExecutionAnalyzer",
    "DefaultDeviationAnalyzer",
    "DefaultLearningExtractor",
    "DefaultSummaryGenerator",
    # Logging
    "setup_clarity_logging",
    "get_clarity_logger",
]
