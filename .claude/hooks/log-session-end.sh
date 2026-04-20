#!/bin/bash
# Log session end and run the full learning pipeline
# This is where sessions become memory — don't suppress output

cd "$(git rev-parse --show-toplevel 2>/dev/null || echo ".")" || exit 1

if ! command -v divineos &>/dev/null; then
  exit 0
fi

divineos extract 2>&1
exit 0
