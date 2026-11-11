# A dream hit says it is a dream at goal-add too (draft, 2026-11-04)

## What happened

`divineos find query` labels a dream hit "(a dream, not a record of what happened)". The goal-add adjacency
surface reads the same semantic index and printed "you've already written about adjacent themes" with no label, so
a dream could be read as prior work done. Separately `memory_linkage.py` spelled the label out twice instead of
using the shared constant.

## Fix

`goal_adjacency` tags a hit with `A_DREAM_LABEL` when `is_dream_path` says so, the same rule `find query` uses.
`memory_linkage` uses the constant in both places. Text is unchanged.

## Test

A dream hit and a plain hit through the adjacency lines: only the dream carries the label.
