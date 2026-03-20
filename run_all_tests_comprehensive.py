#!/usr/bin/env python
"""
Comprehensive test runner with pytest fixture support.
Executes all tests in the tests/ directory without using pytest.
"""

import sys
import inspect
import importlib
from pathlib import Path
import io
import tempfile
from typing import Any, Dict

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Initialize database first
try:
    from divineos.core.ledger import init_db
    init_db()
    print("[OK] Database initialized\n")
except Exception as e:
    print(f"[ERROR] Failed to initialize database: {e}")
    sys.exit(1)

# Pytest fixture implementations
class PytestFixtures:
    """Provides pytest-compatible fixtures."""
    
    @staticmethod
    def tmp_path() -> Path:
        """Provide a temporary directory."""
        return Path(tempfile.mkdtemp())
    
    @staticmethod
    def temp_test_dir() -> Path:
        """Provide a temporary directory for test files."""
        return Path(tempfile.mkdtemp())

# Find all test modules
test_dir = Path('tests')
test_modules = sorted([f.stem for f in test_dir.glob('test_*.py')])

print(f"Found {len(test_modules)} test modules\n")

# Track results
total_passed = 0
total_failed = 0
failed_tests = []
skipped_tests = []

# Get fixture implementations
fixtures = PytestFixtures()
fixture_map = {
    'tmp_path': fixtures.tmp_path,
    'temp_test_dir': fixtures.temp_test_dir,
}

# Run tests
for module_name in test_modules:
    try:
        # Import module
        module = importlib.import_module(f'tests.{module_name}')
        
        # Collect test classes
        test_classes = []
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and name.startswith('Test'):
                test_classes.append((name, obj))
        
        if not test_classes:
            continue
        
        print(f"Module: {module_name}")
        
        for class_name, test_class in test_classes:
            # Get all test methods
            test_methods = [m for m in dir(test_class) if m.startswith('test_')]
            
            for method_name in test_methods:
                try:
                    # Create instance
                    test = test_class()
                    
                    # Get method signature to check for fixtures
                    method = getattr(test, method_name)
                    sig = inspect.signature(method)
                    
                    # Prepare fixture arguments
                    kwargs = {}
                    for param_name in sig.parameters:
                        if param_name in fixture_map:
                            kwargs[param_name] = fixture_map[param_name]()
                        elif param_name != 'self':
                            # Skip tests that require unknown fixtures
                            raise ValueError(f"Unknown fixture: {param_name}")
                    
                    # Run setUp if it exists
                    if hasattr(test, 'setUp'):
                        test.setUp()
                    
                    # Run test
                    method(**kwargs)
                    
                    # Run tearDown if it exists
                    if hasattr(test, 'tearDown'):
                        test.tearDown()
                    
                    print(f"  [OK] {class_name}.{method_name}")
                    total_passed += 1
                except ValueError as e:
                    if "Unknown fixture" in str(e):
                        print(f"  [SKIP] {class_name}.{method_name}: {e}")
                        skipped_tests.append((module_name, class_name, method_name, str(e)))
                    else:
                        error_msg = str(e)[:80]
                        print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                        total_failed += 1
                        failed_tests.append((module_name, class_name, method_name, str(e)))
                except Exception as e:
                    error_msg = str(e)[:80]
                    print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                    total_failed += 1
                    failed_tests.append((module_name, class_name, method_name, str(e)))
    except Exception as e:
        print(f"[ERROR] Failed to load {module_name}: {e}")

print(f"\n{'='*60}")
print(f"RESULTS")
print(f"{'='*60}")
print(f"Passed:  {total_passed}")
print(f"Failed:  {total_failed}")
print(f"Skipped: {len(skipped_tests)}")
total_tests = total_passed + total_failed + len(skipped_tests)
if total_tests > 0:
    success_rate = 100 * total_passed / (total_passed + total_failed) if (total_passed + total_failed) > 0 else 0
    print(f"Success rate: {success_rate:.1f}%")

if failed_tests:
    print(f"\nFirst 10 failures:")
    for module_name, class_name, method_name, error in failed_tests[:10]:
        print(f"\n  {module_name}.{class_name}.{method_name}")
        print(f"    {error[:120]}")

if skipped_tests:
    print(f"\nSkipped tests (missing fixtures):")
    fixtures_needed = set()
    for module_name, class_name, method_name, error in skipped_tests[:5]:
        print(f"  {module_name}.{class_name}.{method_name}: {error}")
        if "Unknown fixture" in error:
            fixture_name = error.split("Unknown fixture: ")[1]
            fixtures_needed.add(fixture_name)
    
    if fixtures_needed:
        print(f"\nFixtures needed: {', '.join(sorted(fixtures_needed))}")

sys.exit(0 if total_failed == 0 else 1)
