#!/usr/bin/env python
"""
Simple test runner that executes pytest-style tests without using pytest.
"""

import sys
import inspect
import importlib
from pathlib import Path
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
failed_tests = []

# Run tests
for module_name in test_modules[:5]:  # Run first 5 modules for now
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
            
            for method_name in test_methods[:2]:  # Run first 2 methods per class
                try:
                    # Create instance (pytest-style tests don't need method name)
                    test = test_class()
                    
                    # Run setUp if it exists
                    if hasattr(test, 'setUp'):
                        test.setUp()
                    
                    # Run test
                    getattr(test, method_name)()
                    
                    # Run tearDown if it exists
                    if hasattr(test, 'tearDown'):
                        test.tearDown()
                    
                    print(f"  [OK] {class_name}.{method_name}")
                    total_passed += 1
                except Exception as e:
                    error_msg = str(e)[:80]
                    print(f"  [FAIL] {class_name}.{method_name}: {error_msg}")
                    total_failed += 1
                    failed_tests.append((module_name, class_name, method_name, str(e)))
    except Exception as e:
        print(f"[ERROR] Failed to load {module_name}: {e}")

print(f"\n{'='*60}")
print(f"RESULTS (sample run - first 5 modules, 2 tests each)")
print(f"{'='*60}")
print(f"Passed: {total_passed}")
print(f"Failed: {total_failed}")
if (total_passed + total_failed) > 0:
    success_rate = 100 * total_passed / (total_passed + total_failed)
    print(f"Success rate: {success_rate:.1f}%")

if failed_tests:
    print(f"\nFailures:")
    for module_name, class_name, method_name, error in failed_tests[:5]:
        print(f"\n  {module_name}.{class_name}.{method_name}")
        print(f"    {error[:120]}")

sys.exit(0 if total_failed == 0 else 1)
