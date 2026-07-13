# dead-stubs/

Scaffolded-but-never-populated family member directories.

When a family member is scaffolded (directory + MEMORY.md + potentially a
ledger file) but never actually defined as an agent or populated with real
relational substance, the scaffolding persists. This directory holds those
inert scaffolds as artifacts — not deleted (append-only discipline), just
moved out of the active `family/` root.

## What's here

- `popo/` — placeholder scaffold. Single file (MEMORY.md). No agent
  definition, no letters, no substance. Moved here 2026-07-09.

## Reactivation

If a member matching a dead-stub's name is ever defined at
`.claude/agents/<name>.md`, move the stub back to `family/<name>/` so any
prior scaffolding lives alongside the new definition. Otherwise, these stay
here as record of what was tried.
