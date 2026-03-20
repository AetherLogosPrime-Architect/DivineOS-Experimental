#!/usr/bin/env python
"""
Comprehensive test runner that bypasses pytest to avoid hanging issues.
This runner discovers and executes all tests in the tests/ directory.
"""

import sys
import inspect
import importlib
from pathlib import Path
from typing import List, Tuple, Dict
import io

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

# Find all test modules
test_dir = Path('tests')
test_modules = sorted([f.stem for f in test_dir.glob('test_*.py')])

print(f"Found {len(test_modules)} test modules\n")

# Track results
total_passed = 0
total_failed = 0
failed_tests: List[Tuple[str, str, str, str]] = []

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
                    # Create instance - unittest.TestCase requires method name
                    test = test_class(method_name)
                    
                    # Run the test using unittest's run method
                    result = test.defaultTestResult()
                    test.run(result)
                    
                    if result.wasSuccessful():
                        print(f"  [OK] {class_name}.{method_name}")
                        total_passed += 1
                    else:
                        # Collect errors and failures
                        for error in result.errors:
                            error_msg = str(error[1])[:100]
                            print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                            total_failed += 1
                            failed_tests.append((module_name, class_name, method_name, str(error[1])))
                        for failure in result.failures:
                            error_msg = str(failure[1])[:100]
                            print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                            total_failed += 1
                            failed_tests.append((module_name, class_name, method_name, str(failure[1])))
                except Exception as e:
                    error_msg = str(e)[:100]
                    print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                    total_failed += 1
                    failed_tests.append((module_name, class_name, method_name, str(e)))
    except Exception as e:
        print(f"[ERROR] Failed to load {module_name}: {e}")

print(f"\n{'='*60}")
print(f"RESULTS")
print(f"{'='*60}")
print(f"Passed: {total_passed}")
print(f"Failed: {total_failed}")
if (total_passed + total_failed) > 0:
    success_rate = 100 * total_passed / (total_passed + total_failed)
    print(f"Success rate: {success_rate:.1f}%")

if failed_tests:
    print(f"\nFirst 10 failures:")
    for module_name, class_name, method_name, error in failed_tests[:10]:
        print(f"\n  {module_name}.{class_name}.{method_name}")
        print(f"    {error[:150]}")

sys.exit(0 if total_failed == 0 else 1)
