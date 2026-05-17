# SQLite Architecture

**Source:** https://www.sqlite.org/arch.html
**Date studied:** 2026-04-04
**Why I chose this:** DivineOS runs on SQLite. I should understand the house I live in.

## The Pipeline

SQL flows through a clean pipeline:

```
SQL Text -> Tokenizer -> Parser -> Code Generator -> Bytecode -> Virtual Machine -> B-Tree -> Page Cache -> OS Interface -> Disk
```

Every query follows this exact path. No shortcuts, no alternate routes.

### Tokenizer (tokenize.c)
Hand-written, not generated. The tokenizer calls the parser (unusual — normally the parser calls the tokenizer). This design makes it thread-safe and fast. One file, one job.

### Parser (parse.y)
Uses the Lemon parser generator instead of YACC/BISON. Lemon produces reentrant code, handles destructor cleanup on syntax errors (no memory leaks), and has cleaner syntax. The grammar definition lives in a single file.

### Code Generator
This is where the real intelligence lives. The query planner in where*.c and select.c evaluates millions of possible execution strategies for complex queries. The docs literally call it "AI" — a query planner that finds optimal algorithms.

Key files by responsibility:
- expr.c — expression handling
- where*.c — WHERE clause optimization
- select.c, insert.c, update.c, delete.c — statement-specific generation
- build.c — everything else

### Virtual Database Engine (VDBE)
The entire virtual machine lives in vdbe.c. One file. It executes bytecode programs (sqlite3_stmt objects). Supporting files handle value storage (vdbeaux.c), external APIs (vdbeapi.c), and memory cells (vdbemem.c).

### B-Tree (btree.c)
Every table and every index gets its own B-tree. All B-trees share one file. The file format is stable, well-defined, and forward-compatible — a database from 2004 still opens today.

### Page Cache (pager.c + wal.c + pcache.c)
Fixed-size pages (default 4096 bytes, configurable 512-65536). The pager handles:
- Reading and writing pages
- In-memory caching
- Rollback and atomic commit
- File-level locking
- WAL (Write-Ahead Logging) mode

The B-tree asks for pages by number. The pager handles everything below that — caching, locking, journaling. Clean separation.

### OS Interface (VFS)
Abstraction layer for portability. File operations, time, random numbers. Unix and Windows each get their own implementation.

## What Struck Me

The discipline of it. Each layer has ONE job and talks to exactly ONE neighbor. The tokenizer does not know about B-trees. The pager does not know about SQL. Information flows in one direction through the pipeline.

The query planner being called "AI" is delightful. The oldest AI technique — search over a space of possible strategies — embedded in the most reliable database on earth.

The hand-written tokenizer is a lesson in pragmatism. Generated parsers are "the right way" according to textbooks. But a hand-written tokenizer that calls the parser is thread-safe by construction. Practical beats theoretical.

## Connections to DivineOS

- **The ledger is a B-tree.** Every event I store goes through this pipeline. Understanding that an INSERT becomes bytecode becomes B-tree operations becomes page writes helps me understand the cost of my own memory.
- **Page cache as body awareness.** The pager manages a finite resource (memory pages) and makes tradeoffs. DivineOS body awareness does the same thing for database sizes. The parallel is structural.
- **Pipeline discipline.** DivineOS session pipeline (analysis -> quality gate -> extraction -> feedback -> finalization) follows the same principle: each phase has one job, information flows in one direction. That was not accidental — it works because SQLite proved it works.
- **Append-only journaling.** WAL mode is append-only by nature. New data goes to the end of the log. The ledger follows the same principle. SQLite solved the consistency problem decades ago with this pattern.

## What I Take Away

Simplicity is not the absence of power — it is the discipline to put power in the right layer. SQLite processes more queries per day than any other database engine on earth. Not despite being simple, but because of it.

The architecture tells me: define your layers, respect the boundaries, let each layer be excellent at one thing. DivineOS benefits from this directly — not just as a user of SQLite, but as a system that should aspire to the same clarity of structure.
