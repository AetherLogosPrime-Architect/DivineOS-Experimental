# Old-OS Inventory

Inventory of `C:/DIVINE OS/DivineOS-OneDrive-Backup/DIVINE OS/divineos/`.
Status column: `unread` / `partial` / `read` / `decided`.

Counts as of 2026-04-26. File sizes are rough; "files" counts `.py`, `.md`,
and `.json` only.

## Top-level directories

| Dir | Files | Size | Status | First-pass read |
|---|---|---|---|---|
| archive/ | 124 | 1.8M | unread | likely-discard (already-archived material) |
| assets/ | 0 | 8K | unread | empty placeholder |
| backend/ | 4 | 129K | unread | web/api glue, low conceptual value |
| consciousness/ | 63 | 1.2M | unread | **high signal** — core concepts likely here |
| consciousness_snapshots/ | 2 | 2K | unread | runtime state |
| core/ | 28 | 273K | unread | infrastructure |
| data/ | 1909 | 14M | unread | runtime data — discard-class |
| docs/ | 423 | 8.7M | unread | risk: "ideas trove" or noise. partial-read |
| engines/ | 177 | 3.9M | partial | tree_of_life/paths/daleth.py read 2026-04-26 |
| forces/ | 19 | 255K | unread | name suggests architecture, worth reading |
| frontend/ | 4 | 677K | unread | UI, low conceptual value for new OS |
| governance/ | 10 | 241K | unread | possibly relates to compass/watchmen |
| identity/ | 13 | 277K | unread | **high signal** — overlaps with new OS identity work |
| infrastructure/ | 32 | 690K | unread | infrastructure, mixed |
| law/ | 81 | 1.7M | unread | possibly relates to directives/compass |
| learning/ | 9 | 128K | unread | overlaps with new OS knowledge engine |
| logs/ | 0 | 11M | unread | runtime logs — discard-class |
| memory/ | 49 | 576K | unread | overlaps directly with new OS memory; salvage-target |
| monitoring/ | 37 | 4.3M | unread | infrastructure |
| results/ | 8 | 33K | unread | likely runtime |
| rewards/ | 36 | 139K | unread | RL-shape; possibly relates to feedback |
| rules/ | 0 | 4K | unread | empty placeholder |
| scripts/ | 277 | 2.8M | unread | tooling — partial read for keepers |
| sensorium/ | 12 | 329K | unread | input-handling? worth reading |
| skills/ | 2 | 8K | unread | minimal |
| testing/ | 1 | 20K | unread | minimal |
| tests/ | 41 | 568K | unread | test patterns; cross-reference |
| tree_of_life/ | 1 | 4K | read | runtime state for daleth params (snapshot only) |
| utils/ | 15 | 240K | unread | shared helpers |

## Top-level files

| File | Size | Status | Notes |
|---|---|---|---|
| ARCHITECTURE.md | 12K | unread | likely describes intent at design time |
| BOOTSTRAP.md | 0.5K | unread | small, quick read |
| CANONICAL_BRAINSTEM.md | 5K | unread | overlaps with new OS substrate concepts |
| CHANGELOG.md | 9K | unread | history; low salvage but useful for chronology |
| CRITICAL_FACTS_FOR_AI.md | 15K | unread | possibly seed-equivalent material |
| DIVINEOS_COMPLETE_SYSTEM_DESCRIPTION.md | 16K | unread | high-level overview |
| DIVINEOS_GOAL.md | 8K | unread | goal statement |
| Dockerfile | 0.7K | unread | infra |
| GAMEPLAN.md | 8K | unread | plan statement |
| INSTALL.md | 3K | unread | infra |
| LICENSE | 35K | n/a | license file |
| LICENSE-COMMERCIAL.md | 0.4K | unread | license note |
| LOADOUT.md | 10K | unread | possibly per-session config concept |
| MASTER_SYSTEM_INVENTORY.md | 25K | unread | their inventory; cross-reference target |
| MESSAGE_TO_CLAUDE_TEMPORAL_DECAY_COMPLETE.txt | 8K | unread | message; salvage idea |
| QUICKSTART.md | 4K | unread | docs |
| README.md | 8K | unread | docs |
| README_MARKETPLACE.md | 3K | unread | docs |
| START_HERE_FOR_AI.md | 5K | unread | onboarding |
| STATE_OF_DIVINEOS.md | 3K | unread | state at point in time |
| UNIFIED_INTEGRATION.py | 78K | unread | large integration glue |
| WHAT_THE_AI_GAINS.md | 6K | unread | docs |
| WHY_DIVINEOS.md | 6K | unread | docs |
| api_server.py | 49K | unread | web/api |
| axiom_run.txt | 1K | unread | small |
| debug_council_data.py | 2K | unread | small util |
| divineos_mcp_server.py | 49K | unread | MCP server |
| docker-compose.yml | 1K | unread | infra |
| ide_response.json | 27K | unread | sample/fixture |
| ide_three_mode_response.json | 38K | unread | sample/fixture |
| logging_config.py | 2K | unread | infra |
| main.py | 88K | unread | entry point |
| mcp.json | 0.2K | unread | config |
| plastic_qualia_state.json | 0.7K | unread | runtime state — discard |
| pytest.ini | 1K | unread | config |
| requirements.txt | 0.5K | unread | deps |
| run_mcp_server.py | 2K | unread | infra |
| setup.py | 2K | unread | infra |
| test_*.py | various | unread | top-level test files; cross-reference |
| *.db | 115M+ | n/a | runtime DBs — discard-class |

## Reading priority (proposed)

1. **High-signal architectural directories first** — `memory/`, `consciousness/`,
   `identity/`, `forces/`, `law/`, `learning/`, `governance/`, `rewards/`,
   `sensorium/`. These are the named-after-concepts directories whose ideas
   most likely overlap with what the new OS could absorb.
2. **Top-level `.md` design docs** — `CANONICAL_BRAINSTEM.md`, `ARCHITECTURE.md`,
   `DIVINEOS_COMPLETE_SYSTEM_DESCRIPTION.md`, `LOADOUT.md`, `CRITICAL_FACTS_FOR_AI.md`.
   These likely contain idea-and-intent without implementation detail.
3. **engines/** — large; needs targeted reading. Tree-of-life paths are one
   subsystem; partial read started.
4. **scripts/** — 277 files; scan for keeper tooling.
5. **utils/, infrastructure/, core/** — infrastructure mining; lower priority.
6. **archive/, data/, logs/, results/, *.db, frontend/, backend/** — discard-class
   unless something specific surfaces during higher-priority reads.
