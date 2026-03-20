# Ledger Architecture Options - Decision Framework

## Current State

**Ledger Module** (`src/divineos/core/ledger.py`):
- Provides module-level functions: `log_event()`, `get_events()`, `search_events()`, etc.
- Functional programming style
- Direct SQLite database access
- No abstraction layer

**Ledger Integration** (`src/divineos/supersession/ledger_integration.py`):
- Expects class-based API: `ledger.store_fact()`, `ledger.store_event()`, etc.
- Object-oriented style
- Tries to import non-existent `get_ledger()` function
- Currently broken

---

## Option 1: Refactor Ledger Module to Class-Based API

**Approach**: Convert ledger module to provide a Ledger class

**What it looks like**:
```python
# src/divineos/core/ledger.py
class Ledger:
    def log_event(self, event_type: str, actor: str, payload: dict) -> str:
        """Log an event to the ledger"""
        ...
    
    def get_events(self, event_type: str = None, actor: str = None) -> list:
        """Get events from the ledger"""
        ...
    
    def store_fact(self, fact: dict) -> str:
        """Store a fact (new method)"""
        ...
    
    def store_event(self, event: dict) -> str:
        """Store an event (new method)"""
        ...

def get_ledger() -> Ledger:
    """Get the global ledger instance"""
    ...
```

**Pros**:
- Clean OOP design
- Ledger integration works as designed
- Type-safe with proper annotations
- Easier to test and mock
- Extensible for future features

**Cons**:
- Requires refactoring existing ledger module
- May break existing code that uses module-level functions
- More complex than current functional approach

---

## Option 2: Redesign Ledger Integration to Use Module Functions

**Approach**: Rewrite ledger_integration to work with existing module-level functions

**What it looks like**:
```python
# src/divineos/supersession/ledger_integration.py
from divineos.core import ledger

class LedgerIntegration:
    def store_fact(self, fact: dict) -> Optional[str]:
        """Store a fact using module-level functions"""
        fact_id = fact.get("id")
        if fact_id is None:
            return None
        
        # Use module-level function
        event_id = ledger.log_event(
            event_type="FACT_STORED",
            actor="supersession",
            payload=fact
        )
        return fact_id
    
    def store_event(self, event: dict) -> Optional[str]:
        """Store an event using module-level functions"""
        event_id = event.get("event_id")
        if event_id is None:
            return None
        
        # Use module-level function
        ledger.log_event(
            event_type="SUPERSESSION",
            actor="supersession",
            payload=event
        )
        return event_id
```

**Pros**:
- No changes to ledger module
- Minimal refactoring
- Works with existing code
- Simpler implementation

**Cons**:
- Ledger integration becomes a thin wrapper
- Doesn't provide the abstraction it claims to provide
- Still doesn't match the expected API
- Type system still has issues

---

## Option 3: Create a Ledger Wrapper Class (Hybrid)

**Approach**: Create a Ledger class in the ledger module that wraps module-level functions

**What it looks like**:
```python
# src/divineos/core/ledger.py
class Ledger:
    """Wrapper around module-level ledger functions"""
    
    def log_event(self, event_type: str, actor: str, payload: dict) -> str:
        """Delegate to module-level function"""
        return log_event(event_type, actor, payload)
    
    def get_events(self, event_type: str = None, actor: str = None) -> list:
        """Delegate to module-level function"""
        return get_events(event_type, actor)
    
    def store_fact(self, fact: dict) -> str:
        """Store a fact"""
        return self.log_event("FACT_STORED", "supersession", fact)
    
    def store_event(self, event: dict) -> str:
        """Store an event"""
        return self.log_event("SUPERSESSION", "supersession", event)

def get_ledger() -> Ledger:
    """Get the global ledger instance"""
    return Ledger()

# Keep module-level functions for backward compatibility
# (they now delegate to the class)
```

**Pros**:
- Provides class-based API that ledger_integration expects
- Backward compatible with existing code
- Minimal changes to ledger module
- Clean separation of concerns
- Type-safe

**Cons**:
- Adds a wrapper layer (slight performance overhead)
- Requires understanding both APIs

---

## Recommendation

**Option 3 (Hybrid)** is the best choice because:

1. **Enables proper OOP design** - Ledger integration gets the class-based API it expects
2. **Backward compatible** - Existing code using module-level functions still works
3. **Minimal refactoring** - Only adds a wrapper class, doesn't rewrite ledger module
4. **Type-safe** - Can add proper type annotations
5. **Extensible** - Easy to add new methods like `store_fact()` and `store_event()`
6. **Testable** - Can mock the Ledger class easily

---

## Implementation Plan

1. Create `Ledger` class in `src/divineos/core/ledger.py`
2. Implement wrapper methods that delegate to module-level functions
3. Add new methods: `store_fact()`, `store_event()`, `query_facts()`, `query_supersession_events()`
4. Implement `get_ledger()` function that returns Ledger instance
5. Update `ledger_integration.py` to use the new Ledger class
6. Add comprehensive type annotations
7. Add integration tests that verify the full chain works

---

## Decision

Which option do you prefer?

- **Option 1**: Full refactor to class-based API
- **Option 2**: Redesign integration to use module functions
- **Option 3**: Create wrapper class (recommended)
