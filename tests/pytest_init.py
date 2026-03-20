"""Initialize database before pytest runs."""

import sys

# Initialize database on module import
try:
    from divineos.core.ledger import init_db

    init_db()
    print("✓ Database initialized for tests", file=sys.stderr)
except Exception as e:
    print(f"✗ Failed to initialize database: {e}", file=sys.stderr)
    import traceback

    traceback.print_exc()
