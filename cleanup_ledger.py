#!/usr/bin/env python
"""Script to clean corrupted events from the ledger."""

import sys
sys.path.insert(0, 'src')

from divineos.ledger import clean_corrupted_events, verify_all_events

print("=== Ledger Cleanup ===\n")

# Clean corrupted events
result = clean_corrupted_events()
print(f"Deleted corrupted events: {result['deleted_count']}")

if result['deleted_count'] > 0:
    print(f"\nRemoved {result['deleted_count']} corrupted events")
    print("\nVerifying ledger integrity...")
    
    # Verify the ledger is now clean
    verify_result = verify_all_events()
    print(f"\nVerification Results:")
    print(f"  Total events: {verify_result['total']}")
    print(f"  Passed:       {verify_result['passed']}")
    print(f"  Failed:       {verify_result['failed']}")
    print(f"  Integrity:    {verify_result['integrity']}")
else:
    print("\nNo corrupted events found")
