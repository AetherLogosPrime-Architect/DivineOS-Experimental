# A word that frees a command from the walk can never free a command that writes

Draft, 2026-11-02. Companion to `tests/test_look_list_verbs_never_write.py`.

## The weakness this closes

`_LOOK_SUBVERBS` in `divineos.core.gravity_classifier` lists command words the walk gate treats as pure reads. The exemption is by name, so a later command registered as `search` or `show` that writes state would inherit it silently. PR #726 added five words after a human read each command; nothing checked the next one.

## What the test does

It imports `_LOOK_SUBVERBS`, so it follows the list. With `ast` it finds every `@<group>.command("<word>")` under `src/divineos/cli/` whose registered name is on the list (92 commands today, across all twelve words). For each it reads the command's code, any same-file helper it calls, and the `divineos.core` functions it calls, two core hops deep, and fails on SQL INSERT/UPDATE/DELETE/REPLACE, `.commit(`, `log_event(`, `write_text(`/`write_bytes(`, `open(` in a write mode, `subprocess`, `os.system`, `eval(`/`exec(`, or a call named `record_`/`store_`/`save_`/`file_`/`set_`/`delete_`/`append_*`.

Controls: it must flag `record_self_audit_prediction` (calls `log_event`); it must follow a call from a clean command into that function in core; it must find at least 60 commands and the named known ones; every word on the list must have a command; each write shape is pinned by a snippet that must be caught, and four read shapes must not be.

## Two lists, and why they are separate

`_EXCUSED_FUNCTIONS` holds functions that look like writes but are idempotent table setup, read-only git/gh calls, or a path getter. Keyed by (file, function) and limited to named tokens, so a new kind of write inside an excused function still fails. `_ALLOWED_WRITES` holds commands that really write; each is marked FINDING and is a human decision. Both lists fail the test when an entry stops matching, so exceptions cannot linger unnoticed.

## What it cannot see

- **Call depth beyond two.** Core calls are followed two levels. A write three hops down is not seen. Same-file helpers in the CLI module cost no depth.
- **Dynamic dispatch.** Calls through variables, `getattr`, callbacks, registries and `self.method()` / `obj.method()` are not followed. Only direct calls to imported names and `module.func()` are.
- **Commands registered outside `src/divineos/cli/`**, or by any form other than a `.command(...)` decorator (for example `group.add_command(...)`).
- **Name-based resolution.** A function is looked up by name within its module, so two same-named functions in one file can be confused.
- **Writes not in the pattern list.** Matched since the widening: calls prefixed `record_`/`store_`/`save_`/`file_`/`set_`/`delete_`/`append_`/`update_`/`mark_`/`add_`/`write_`, `executemany`/`executescript`, `unlink`/`rmdir`/`mkdir`/`makedirs`/`rmtree`/`touch`/`rename`, any `shutil.*` call, `os.remove`/`os.removedirs`/`os.replace`, `Popen`, and SQL INSERT/UPDATE/DELETE/REPLACE inside an f-string or a `+` / `%` chain of strings. Still not matched: `CREATE`/`DROP`/`ALTER` (so a migration `ALTER TABLE` is invisible), SQL built from a variable or `.format()`, `list.remove` (left out on purpose, it is an in-memory edit), `Path.replace`, `json.dump` or any other write through a handle, writes through a name that matches no prefix, and `set_title`/`file_size`/`file_name`/`file_path`/`file_exists` (excluded by exact name as reads). Lazy table and folder creation is excused rather than flagged, by file name and function only.
- **Excusals are by name.** An excused function that later gains a different write of an excused token kind passes.

A green result means no write was found within those limits, not that none exists.

## Findings (not fixed here)

Four listed commands write today: `ec status` (ledger event on an expired arm), `auto-cycle status` (heartbeat state file and log row), `linkage status` (wall-resolution record), `work-item status` (closes a work item when a commit has landed). The wider detector also showed that `ec status` deletes the arm file when it is unreadable, malformed or expired (an `unlink`, beside the ledger event already listed), now recorded in `_ALLOWED_WRITES`. Whether to rename them, split the read from the write, or drop the word is a human decision about the gate.
