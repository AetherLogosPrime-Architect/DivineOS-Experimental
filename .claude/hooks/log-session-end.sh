#!/bin/bash
# Log session end event to the DivineOS ledger

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")"
divineos emit SESSION_END 2>/dev/null
exit 0
