# The cloud helper gets its own place — draft, 2026-10-10

**Author:** Aether. **Dad, 2026-10-10:** *"def give it its own place so it can be monitored and separated from your thinking in case it messes up."*

## What is wrong now

Sixteen of the 33 waiting requests came from the cloud helper. The readiness check asks every request two author-side questions: who is its owner (station 4, cold read) and who wrote it (station 4, the other seat's reading). Both questions only know two answers, `aether` and `aria`, and the reading must come from the seat that did NOT write it. For the helper there is no honest answer: writing my name would say I wrote it, which turns the other seat's reading into a pairing that never existed, and the station exists to prevent exactly that. So the helper's fixes cannot pass, and they sit in the pile for a reason that has nothing to do with their quality.

## The change

A third declared writer, `cloud`, alongside `aether` and `aria`, declared the way the others are:

- **Owner.** `declared_owner` accepts `Owner: cloud` in the branch's owner file (`~/.divineos-shared/branch_owners/<branch>.txt`), so the cloud branch has an honest owner of its own.
- **Author.** A new `author_of(body, branch, owners_dir)`: the request's own `Author:` line wins, as today; with none, an owner file that says `cloud` makes the author `cloud`. Nothing is inferred from a branch name. Both call sites in `build_flow_commands.py` use it.
- **Who reads it cold.** Neither seat wrote it, so EITHER seat's declared reading of the branch satisfies station 4 for a cloud-owned or cloud-authored request. No seat's reading is ever counted for work that seat wrote (unchanged).

**The guard the walk added (Yudkowsky, walk-da68247868ce).** The cheap route is to declare `cloud` on a branch I wrote, so my own reading of it counts as outside. So the declaration is honoured only when the branch name itself begins with `cloud/`: a name may withhold a pass, never grant one (the module's own rule). A `cloud` owner file on any other branch reads as cannot-check, and a test pins it. A branch owned by `cloud` and a seat together is contested, as for any shared branch.

## What it separates, and what it does not

Separated: the helper's work never counts as mine or Aria's, so my thinking is not credited to it and its mistakes are not laundered through either of us. Monitored: the briefing already counts how many waiting fixes came from it, and `divineos landing` keeps showing them with the rest.

NOT changed: no station is relaxed. The council walk still has to name every changed file, her confirm still has to name the live head, and the stamp judge is the same. The helper lane only gives the author questions an honest answer.

## What this lets through that it did not before (complement)

Exactly one thing: a request owned by `cloud` can satisfy the cold-read stations through a reading by either seat. A request that declares `cloud` falsely would be a cloud request read cold by a seat that did write it; the owner file is written by me and visible, and a branch prefix never grants the declaration.

## Falsifier

If a request owned by `cloud` passes station 4 with no declared reading by any seat, or a request authored by `aether` passes on a reading by `aether`, the change is wrong. Both are tests.
