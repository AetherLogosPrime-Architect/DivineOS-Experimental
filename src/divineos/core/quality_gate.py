"""Backward-compat shim — quality gate moved to cli/pipeline_gates.py."""

from divineos.cli.pipeline_gates import (  # noqa: F401
    QualityVerdict,
    assess_session_quality,
    should_extract_knowledge,
)
