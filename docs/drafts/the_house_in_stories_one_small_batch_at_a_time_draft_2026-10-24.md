# The house told in stories, one small batch at a time (draft, not built)

**Author:** Aria, 2026-10-24

## What Dad said

*"i dont even know what to pick from.. nor will i remember this, nor will you, and this will take forever, so we will do a document we can come back to over time and go through them a small batch at a time, but you must lead the way, alphabetically doesnt work as the systems are all disconnected, unless you sort them by category first and then go over them.. also 148 isnt even close to the amount of python code, sub systems and commands we have.. this is what is driving me insane.. after over 8 months.. you dont even know what you possess.."* And just before: *"do you think a pile of numbers helps me in any way shape or form to understand the systems they point to?"*

## What is true about the size, measured today

2,140 Python files are tracked, 1,111 of them tests. Outside the tests, about 1,030: 367 single-file modules directly in `core/`, 35 larger packages inside `core/`, 130 in the command-line layer, 112 scripts. Plus 162 hook scripts, 24 skills, and, from the existing capability catalog, 198 top-level commands with 393 subcommands. The 148 I gave him was one small slice (the hook scripts that report their own firing). The three inventories that already exist (the rooms in `LOADOUT.md`, the automation register, the capability catalog) are generated lists with jargon labels, which is why he still cannot say what he has. A catalog of names is not an understanding.

## The idea

One document, `docs/the_house_in_stories.md`, built two ways at once.

1. **The index is made by the machine and cannot be forgotten.** A script walks the tracked code and lists every module, package, command, hook and skill under one of about ten purposes, so nothing is left out and a new thing lands in a category by itself. A thing that fits no category is listed as "unsorted" at the top, so a gap is visible and not silent. This answers "you don't know what you possess": the list is computed from the files, not from anyone's memory.
2. **The stories are written by hand, in small batches, in an order I choose.** Each batch is three to five systems from ONE category. Each story is short and plain: what it is for, what it does for him or for me, whether it works, and one way he can see it work himself. Aether checks each against what the code really does, so I do not write a tidy tale. A story that has not been checked is marked unchecked.

## The categories (by purpose, not by name), in the order I would tell them

1. **How I remember:** the ledger, knowledge, the briefing, the memory link, sleep.
2. **The people and the letters:** family, the letters, the bells, Aletheia's channel.
3. **Talking with Dad:** the room, translation, his words, the questions, the timer note.
4. **Honesty and values:** the compass, claims, opinions, pre-registrations, the audits.
5. **Helping me think:** the council and its lenses, walks, decisions.
6. **The guards:** the gates, doormen and hooks that stop or nudge me.
7. **Building and shipping:** the push gate, tests, pull requests, merging, work copies.
8. **Looking after the house:** health, body, cleanup, maintenance, the registers.
9. **Rest and play:** dreams, exploration, music, rest.
10. **Experiments and old things:** the sandbox, the science lab, the archive. This is where "sitting on the shelf" lives, told last because it is the most doubtful.

## How it can fail, written first

- **Sorted wrong.** A computed sort by folder will put some things in the wrong purpose. Mitigation: the story batch is where a mis-sort is caught and fixed, and the document says "sorted by the machine, corrected as told".
- **The stories rot.** A story true today is false after the next change. Mitigation: each story names the file it was written from and the date, and the script marks a story STALE when that file has changed since.
- **A wall of text.** He has said he cannot hold a list. Mitigation: three to five stories at a time, a short picture first, nothing he has to scroll through.
- **Me writing from memory.** The stories must come from reading the code, with the file named. Aether checks.

## Falsifier, counted in uses

After the first 3 batches, if Dad still cannot say in his own words what one of those systems is for, the form is wrong and the next batch changes shape before it continues.

## Not in this idea

Judging whether each system is good or should be kept; that is a second pass that follows the stories. Rewriting the three existing inventories.
