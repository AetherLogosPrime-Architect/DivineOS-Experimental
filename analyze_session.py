#!/usr/bin/env python
"""Analyze the current session for quality issues."""

import sys
sys.path.insert(0, 'src')

from divineos.analysis import export_current_session_to_jsonl, analyze_session, format_analysis_report
from pathlib import Path

print("Analyzing current session...")
print()

try:
    # Export current session to JSONL
    print("1. Exporting current session...")
    session_file = export_current_session_to_jsonl(limit=10000)
    print(f"   ✓ Session exported to: {session_file}")
    print()
    
    # Analyze the session
    print("2. Running quality checks...")
    result = analyze_session(session_file)
    print(f"   ✓ Analysis complete")
    print()
    
    # Format and display report
    print("3. Quality Report:")
    print()
    report_text = format_analysis_report(result)
    print(report_text)
    print()
    
    # Check for failures
    print("4. Summary:")
    if hasattr(result.quality_report, 'checks'):
        failed_checks = [c for c in result.quality_report.checks if not c.passed]
        if failed_checks:
            print(f"   ⚠ {len(failed_checks)} quality checks FAILED:")
            for check in failed_checks:
                print(f"      - {check.check_name}: {check.summary}")
        else:
            print("   ✓ All quality checks PASSED")
    
except Exception as e:
    print(f"✗ Analysis failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
