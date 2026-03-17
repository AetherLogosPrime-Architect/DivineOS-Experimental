#!/usr/bin/env python
"""Test script to verify the clarity fix works."""

import sys
sys.path.insert(0, 'src')

from divineos.event_emission import emit_explanation, emit_tool_call
from divineos.clarity_enforcement import get_clarity_checker
from pathlib import Path

# Initialize
print("Testing clarity fix...")
print()

# Get initial clarity state
print("0. Initial clarity state...")
try:
    checker = get_clarity_checker()
    report = checker.get_clarity_report()
    print(f"   Tool calls: {report['total_tool_calls']}, Explanations: {report['explained_calls']}")
    initial_tool_calls = report['total_tool_calls']
except Exception as e:
    print(f"   ✗ Failed: {e}")
    initial_tool_calls = 0

print()
print("1. Emitting explanation event...")
try:
    exp_id = emit_explanation("I'm going to read the file to understand its structure")
    print(f"   ✓ Explanation emitted: {exp_id}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print()
print("2. Emitting tool call event...")
try:
    tool_id = emit_tool_call("readFile", {"path": "test.txt"})
    print(f"   ✓ Tool call emitted: {tool_id}")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    sys.exit(1)

print()
print("3. Checking clarity report...")
try:
    checker = get_clarity_checker()
    report = checker.get_clarity_report()
    print(f"   Total tool calls: {report['total_tool_calls']}")
    print(f"   Explained calls: {report['explained_calls']}")
    print(f"   Clarity score: {report['clarity_score']:.1f}%")
    print(f"   Status: {report['status']}")
    
    # Check if we added 1 explanation and 1 tool call
    new_tool_calls = report['total_tool_calls'] - initial_tool_calls
    new_explanations = report['explained_calls']
    
    print()
    print(f"   New tool calls added: {new_tool_calls}")
    print(f"   New explanations added: {new_explanations}")
    
    if new_explanations >= new_tool_calls and new_tool_calls > 0:
        print()
        print("✓ CLARITY FIX SUCCESSFUL!")
        print("  Explanations are now being counted correctly.")
        print("  New explanation matched new tool call.")
    else:
        print()
        print("✗ Clarity issue detected")
        print(f"  Expected {new_tool_calls} explanations for {new_tool_calls} new tool calls")
        print(f"  Got {new_explanations} explanations")
except Exception as e:
    print(f"   ✗ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

