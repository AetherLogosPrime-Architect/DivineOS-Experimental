#!/usr/bin/env python
"""Debug script to test file reading logic."""

from pathlib import Path

session_file = Path.home() / ".divineos" / "current_session.txt"
print(f"Session file path: {session_file}")
print(f"File exists: {session_file.exists()}")

if session_file.exists():
    content = session_file.read_text()
    print(f"Raw content: {repr(content)}")
    print(f"Stripped content: {repr(content.strip())}")
    print(f"Stripped content bool: {bool(content.strip())}")
    
    session_id = content.strip()
    print(f"Session ID: {session_id}")
    print(f"Session ID bool: {bool(session_id)}")
    print(f"not session_id: {not session_id}")
