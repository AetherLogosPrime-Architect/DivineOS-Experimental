"""
Integration tests for the Agent Work Clarity System.

Tests the full workflow of clarity statement generation, plan analysis,
execution analysis, deviation detection, and summary generation.
"""

import pytest
from uuid import uuid4
from datetime import datetime

from divineos.clarity_system import (
    DefaultClarityStatementGenerator,
    DefaultPlanAnalyzer,
    DefaultDeviationAnalyzer,
    DefaultLearningExtractor,
    DefaultSummaryGenerator,
    ClarityStatement,
    ScopeEstimate,
    ExecutionData,
    ExecutionMetrics,
    ToolCall,
)


class TestClaritySystemIntegration:
    """Integration tests for clarity system components."""

    def test_full_clarity_workflow(self):
        """Test the complete clarity workflow from statement to summary."""
        # 1. Generate clarity statement
        generator = DefaultClarityStatementGenerator()
        work_context = {
            "goal": "Implement user authentication",
            "approach": "Add JWT-based auth with refresh tokens",
            "expected_outcome": "Users can login and logout securely",
            "estimated_files": 5,
            "estimated_tool_calls": 20,
            "estimated_complexity": "high",
            "estimated_time_minutes": 120,
        }

        clarity_statement = generator.generate_clarity_statement(work_context)
        assert clarity_statement.goal == "Implement user authentication"
        assert clarity_statement.scope.estimated_files == 5
        assert clarity_statement.scope.estimated_tool_calls == 20

        # 2. Analyze plan
        plan_analyzer = DefaultPlanAnalyzer()
        plan_data = plan_analyzer.analyze_plan(clarity_statement)
        assert plan_data.goal == clarity_statement.goal
        assert plan_data.metrics.estimated_files == 5
        assert plan_data.metrics.estimated_tool_calls == 20

        # 3. Create execution data (simulated)
        tool_calls = [
            ToolCall(
                tool_name="readFile",
                timestamp=datetime.utcnow().isoformat(),
                input={"path": "auth.py"},
            ),
            ToolCall(
                tool_name="fsWrite",
                timestamp=datetime.utcnow().isoformat(),
                input={"path": "auth.py"},
            ),
            ToolCall(
                tool_name="readFile",
                timestamp=datetime.utcnow().isoformat(),
                input={"path": "models.py"},
            ),
        ]

        execution_metrics = ExecutionMetrics(
            actual_files=2,
            actual_tool_calls=3,
            actual_errors=0,
            actual_time_minutes=45.0,
            success_rate=1.0,
        )

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=tool_calls,
            errors=[],
            metrics=execution_metrics,
        )

        # 4. Analyze deviations
        deviation_analyzer = DefaultDeviationAnalyzer()
        deviations = deviation_analyzer.analyze_deviations(plan_data, execution_data)

        # Should have deviations in files and tool calls (actual < planned)
        assert len(deviations) > 0
        assert any(d.metric == "files" for d in deviations)
        assert any(d.metric == "tool_calls" for d in deviations)

        # 5. Extract lessons
        learning_extractor = DefaultLearningExtractor()
        lessons = learning_extractor.extract_lessons(deviations, execution_data)
        assert len(lessons) > 0

        # 6. Generate recommendations
        recommendations = learning_extractor.generate_recommendations(lessons)
        assert len(recommendations) > 0

        # 7. Generate summary
        summary_generator = DefaultSummaryGenerator()
        summary = summary_generator.generate_post_work_summary(
            clarity_statement=clarity_statement,
            plan_data=plan_data,
            execution_data=execution_data,
            deviations=deviations,
            lessons=lessons,
            recommendations=recommendations,
        )

        assert summary.clarity_statement.id == clarity_statement.id
        assert len(summary.deviations) > 0
        assert len(summary.lessons_learned) > 0
        assert len(summary.recommendations) > 0
        assert summary.metrics.actual_tool_calls == 3

    def test_clarity_statement_generation(self):
        """Test clarity statement generation."""
        generator = DefaultClarityStatementGenerator()

        work_context = {
            "goal": "Fix database connection issue",
            "approach": "Update connection string and add retry logic",
            "expected_outcome": "Database connections are stable",
            "estimated_files": 2,
            "estimated_tool_calls": 10,
            "estimated_complexity": "medium",
            "estimated_time_minutes": 30,
        }

        statement = generator.generate_clarity_statement(work_context)

        assert statement.goal == "Fix database connection issue"
        assert statement.approach == "Update connection string and add retry logic"
        assert statement.expected_outcome == "Database connections are stable"
        assert statement.scope.estimated_files == 2
        assert statement.scope.estimated_tool_calls == 10
        assert statement.scope.estimated_complexity == "medium"
        assert statement.scope.estimated_time_minutes == 30

    def test_plan_analysis(self):
        """Test plan analysis from clarity statement."""
        clarity_statement = ClarityStatement(
            goal="Implement caching layer",
            approach="Add Redis integration",
            expected_outcome="API responses are faster",
            scope=ScopeEstimate(
                estimated_files=3,
                estimated_tool_calls=15,
                estimated_complexity="high",
                estimated_time_minutes=90,
            ),
        )

        analyzer = DefaultPlanAnalyzer()
        plan_data = analyzer.analyze_plan(clarity_statement)

        assert plan_data.goal == "Implement caching layer"
        assert plan_data.metrics.estimated_files == 3
        assert plan_data.metrics.estimated_tool_calls == 15

    def test_deviation_detection(self):
        """Test deviation detection between plan and execution."""
        from divineos.clarity_system import PlanData, PlanMetrics

        plan_data = PlanData(
            clarity_statement_id=uuid4(),
            goal="Test goal",
            approach="Test approach",
            expected_outcome="Test outcome",
            metrics=PlanMetrics(
                estimated_files=10,
                estimated_tool_calls=50,
                estimated_complexity="high",
                estimated_time_minutes=120,
            ),
        )

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[],
            errors=[],
            metrics=ExecutionMetrics(
                actual_files=5,
                actual_tool_calls=25,
                actual_errors=2,
                actual_time_minutes=60.0,
                success_rate=0.92,
            ),
        )

        analyzer = DefaultDeviationAnalyzer()
        deviations = analyzer.analyze_deviations(plan_data, execution_data)

        # Should detect deviations in all metrics
        assert len(deviations) >= 3
        assert any(d.metric == "files" for d in deviations)
        assert any(d.metric == "tool_calls" for d in deviations)
        assert any(d.metric == "errors" for d in deviations)

    def test_error_handling_in_clarity_generation(self):
        """Test error handling when work context is incomplete."""
        generator = DefaultClarityStatementGenerator()

        # Incomplete work context
        work_context = {
            "goal": "Do something",
            # Missing other fields
        }

        statement = generator.generate_clarity_statement(work_context)

        # Should still generate a statement with defaults
        assert statement.goal == "Do something"
        assert statement.approach == "Unspecified approach"
        assert statement.scope.estimated_files == 0

    def test_error_handling_in_plan_analysis(self):
        """Test error handling in plan analysis."""
        analyzer = DefaultPlanAnalyzer()

        # Minimal clarity statement
        clarity_statement = ClarityStatement(
            goal="",
            approach="",
            expected_outcome="",
            scope=ScopeEstimate(0, 0, "invalid", 0),
        )

        plan_data = analyzer.analyze_plan(clarity_statement)

        # Should normalize the data
        assert plan_data.metrics.estimated_complexity == "medium"

    def test_learning_extraction(self):
        """Test lesson extraction from deviations."""
        from divineos.clarity_system import Deviation

        deviations = [
            Deviation(
                metric="files",
                planned=10.0,
                actual=5.0,
                difference=-5.0,
                percentage=50.0,
                severity="high",
                category="scope",
            ),
            Deviation(
                metric="tool_calls",
                planned=50.0,
                actual=25.0,
                difference=-25.0,
                percentage=50.0,
                severity="high",
                category="scope",
            ),
        ]

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[
                ToolCall("readFile", datetime.utcnow().isoformat(), {}),
                ToolCall("fsWrite", datetime.utcnow().isoformat(), {}),
            ],
            errors=[],
            metrics=ExecutionMetrics(2, 2, 0, 10.0, 1.0),
        )

        extractor = DefaultLearningExtractor()
        lessons = extractor.extract_lessons(deviations, execution_data)

        assert len(lessons) > 0
        assert any(lesson.type == "deviation" for lesson in lessons)

    def test_summary_generation(self):
        """Test comprehensive summary generation."""
        clarity_statement = ClarityStatement(
            goal="Test goal",
            approach="Test approach",
            expected_outcome="Test outcome",
            scope=ScopeEstimate(5, 20, "medium", 60),
        )

        from divineos.clarity_system import PlanData, PlanMetrics

        plan_data = PlanData(
            clarity_statement_id=clarity_statement.id,
            goal="Test goal",
            approach="Test approach",
            expected_outcome="Test outcome",
            metrics=PlanMetrics(5, 20, "medium", 60),
        )

        execution_data = ExecutionData(
            session_id=uuid4(),
            tool_calls=[],
            errors=[],
            metrics=ExecutionMetrics(5, 20, 0, 60.0, 1.0),
        )

        generator = DefaultSummaryGenerator()
        summary = generator.generate_post_work_summary(
            clarity_statement=clarity_statement,
            plan_data=plan_data,
            execution_data=execution_data,
            deviations=[],
            lessons=[],
            recommendations=[],
        )

        assert summary.clarity_statement.id == clarity_statement.id
        assert summary.metrics.actual_tool_calls == 20


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
