# gate_list_history

The stories behind the two lists that decide which commands are a gate's way out. They used to be comments inside the code; the code now carries one short current note per list and points here.

- `shared_remedy_list_history.md`: the shared shell pattern in `.claude/hooks/lib/remedy_allowlist.sh`, read by nineteen gates. Six instances of the same class, each a deadlock somebody hit.
- `build_gate_filing_list_history.md`: the build gate's own list in `.claude/hooks/check-council-required.sh`, with its second, third and fourth widenings.

These are records, moved word for word and not edited. Add a new paragraph here when a list changes, and keep the code note to the current rule. A test (`tests/test_the_gate_lists_are_unchanged_by_the_tidy.py`) pins what each list contains, so changing an entry on purpose means changing that test in the same diff.
