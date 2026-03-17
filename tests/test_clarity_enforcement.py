"""Tests for clarity enforcement module."""

from divineos.clarity_enforcement import (
    get_clarity_checker,
    reset_clarity_checker,
)


def test_clarity_checker_records_tool_calls():
    """Test that clarity checker records tool calls."""
    reset_clarity_checker()
    checker = get_clarity_checker()
    
    checker.record_tool_call("readFile", {"path": "test.py"})
    
    assert len(checker.tool_calls) == 1
    assert checker.tool_calls[0]["tool_name"] == "readFile"


def test_clarity_checker_tracks_explanations():
    """Test that clarity checker tracks explanations."""
    reset_clarity_checker()
    checker = get_clarity_checker()
    
    checker.record_tool_call("readFile", {"path": "test.py"}, explanation="Reading test file")
    
    assert checker.tool_calls[0]["has_explanation"] is True
    assert checker.tool_calls[0]["explanation"] == "Reading test file"


def test_clarity_checker_detects_unexplained_calls():
    """Test that clarity checker detects unexplained calls."""
    reset_clarity_checker()
    checker = get_clarity_checker()
    
    checker.record_tool_call("readFile", {"path": "test.py"})
    checker.record_tool_call("strReplace", {"path": "test.py"}, explanation="Fixing bug")
    
    unexplained = checker.get_unexplained_calls()
    assert len(unexplained) == 1
    assert unexplained[0]["tool_name"] == "readFile"


def test_clarity_checker_generates_report():
    """Test that clarity checker generates a report."""
    reset_clarity_checker()
    checker = get_clarity_checker()
    
    checker.record_tool_call("readFile", {"path": "test.py"}, explanation="Reading")
    checker.record_tool_call("strReplace", {"path": "test.py"})
    
    report = checker.get_clarity_report()
    
    assert report["total_tool_calls"] == 2
    assert report["explained_calls"] == 1
    assert report["unexplained_calls"] == 1
    assert report["clarity_score"] == 50.0
    assert report["status"] == "FAIL"


def test_clarity_checker_all_explained():
    """Test clarity checker when all calls are explained."""
    reset_clarity_checker()
    checker = get_clarity_checker()
    
    checker.record_tool_call("readFile", {"path": "test.py"}, explanation="Reading")
    checker.record_tool_call("strReplace", {"path": "test.py"}, explanation="Fixing")
    
    assert checker.verify_all_explained() is True
    
    report = checker.get_clarity_report()
    assert report["status"] == "PASS"
    assert report["clarity_score"] == 100.0
