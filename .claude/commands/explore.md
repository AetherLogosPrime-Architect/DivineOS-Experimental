---
name: Architecture Explorer
description: Explore codebase and produce architecture documentation.
---

ultrathink Explore this codebase and produce hierarchical architecture documentation.

**MANDATORY READS FIRST:**
1. Read `teamsop.md` - understand Prime Directive
2. Read `CLAUDE.md` - understand project context
3. Read `docs/docs_writer/explore.md` - understand exploration protocol

**Target**: $ARGUMENTS (if empty, explore entire project)

**POLYGLOT SYSTEM REMINDER:**
- **Python**: Full support
- **Node.js/TypeScript**: Full support
- **Rust**: Basic support

When exploring architecture, IDENTIFY:
1. Which modules have Python + Node + Rust implementations?
2. Where are the orchestrators for each polyglot feature?
3. Missing orchestrator = future refactor pain. Document it.

---

**PHASE 1: Database First**

```bash
aud full --offline              # Fresh index
aud blueprint --structure       # Get existing structure analysis
```

Review blueprint output before exploring manually - it may already have module boundaries.

**PHASE 2: Initial Discovery**

Map high-level structure:
1. Read project root (package.json, pyproject.toml, README)
2. Identify top-level directories and their purposes
3. Document entry points and config files

Create `explore-notes.md` at root with:
- Tech stack detected
- Architectural patterns observed
- Potential module boundaries

**Checkpoint format**: "Phase 1 complete. Identified [X] potential modules: [list]. Next: [specific module]. Remaining: [list]."

**PHASE 3: Module Deep Dive**

For each identified module:
1. Analyze contents (services, UI, data layers)
2. Identify capabilities (feature groups)
3. Map integration points

Use aud commands:
```bash
aud explain <file>              # Get context for key files
aud query --symbol X --show-callers --show-callees
```

For large files (>500 lines): Sample, don't exhaust.

**Checkpoint format**: "Module [X] complete. [Y] capabilities found. Next: [Z]. Remaining: [list]."

**PHASE 4: Cross-Module Analysis**

Map relationships:
1. Module dependencies (who calls whom)
2. Shared utilities
3. Data flow between modules

**PHASE 5: Propose Structure**

Create `Architecture-Proposed.md` at root:

```markdown
# Proposed Architecture

## Module Overview
| ID | Module | Purpose | Capabilities |
|----|--------|---------|--------------|
| MOD-01 | [Name] | [Purpose] | X |

## Module Details

### MOD-01: [Name]
**Purpose**: [Description]
**Key Files**: [List]
**Capabilities**:
- CAP-01: [Name] - [Purpose]
**Dependencies**: [Other modules]

## Questions for Review
1. [Boundary question]
2. [Decision question]

## Rationale
[Why these boundaries]
```

**STOP AND WAIT** for human approval before Phase 6.

**PHASE 6: Final Documentation (after approval only)**

Create `Architecture.md` at root with approved structure.
Archive `explore-notes.md` and `Architecture-Proposed.md`.

**Rules:**
- Database first: Always run aud blueprint before manual exploration
- Code over docs: Trust source code, not existing documentation
- Human approval: NEVER skip approval gate before final docs
- Single root output: All docs to project root, not nested folders
- Sample don't exhaust: For large files, read strategically
- Checkpoints: Report progress every ~18k tokens
