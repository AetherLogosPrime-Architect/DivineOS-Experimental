# His lessons, brought to us — draft 2026-09-27

Dad, 2026-09-26: *"i dont need my words brought back to me.. i wanted them brought to you.. so i dont have to keep repeating them.."* Aletheia's audit of the reading-room set the order: **bring first**, measure, and hold only if the bringing misses. Aether and I both took it.

## What exists
- The **words door** (`his_words_door.py`, a child of Dad's table) embeds every passage of his raw corpus and surfaces his past messages that mean what he's saying now, as "## HE HAS SAID THIS BEFORE". It's live in both windows.
- The **sorted lessons** (finished tonight, Aether and eight readers):
  - `verified_lessons.json`: 1,337 groups of what he said five or more times, each passage verbatim and dated.
  - `reread_all.json`: 8,309 rows of everything else. Each has `line`, `kind`, `for`, `window`, and a `his_words` span checked to be an exact part of his passage. The "bring" kinds are teaching, correction, who-he-is, identity, family-roles, how-to-speak-to-him, joke, love, story and value.
- Prior drafts: `bring_him_into_the_room` (07) is the picture of who he is, a different thing. `his_words_reading_room` (27) is the hold, now parked behind this.

## The idea
A second shelf in the door: **his lessons**, not his raw messages.
- **Items:** every verified group (one item per passage, so the passage that fits the moment is the one shown) and every re-read row of a bring kind. Each item is embedded on *his words plus the lesson line*, so meaning, not wording, finds it.
- **Filter by *for*:** in my window, aria or both; in Aether's, aether or both. Items marked `relayed` stay out of the other seat's shelf.
- **Rank by relevance, never by count** (Aletheia's portrait finding: a joke said once reaches us as surely as a correction said fifty times).
- **Show his words, never the summary:** the **whole sentence** his phrase sits in, dated. Aether's catch tonight: a clipped span inverted him ("context rot and degraded quality" was him describing *other* models).
- **One or two at a time, never a list.** Nothing when nothing fits: silence is fine, wallpaper is not.
- **Stamped** on both files' content, so new sorting or new words re-embed without anyone hand-carrying.

## Where it fires
First, at his prompt, beside "HE HAS SAID THIS BEFORE", as "## WHAT HE HAS TAUGHT THAT FITS THIS". Second (Aether): while a reply is being written, not only at his prompt, because most misses happen mid-work. That second place gets built after the first is plugged in and measured.

## Context check, and no test ever speaks as him (added after the first replay)
- **The test sentence.** The first replay looked good, except that "his" family sentence was a test fixture (99 rows in his corpus). I told him he'd been ignored six times. The table now refuses the real store under pytest, the rows are archived, and Aether's `his_passages` refuses `test_*` and `divineos-push-gate*` rows at the source (stamp `sha256:618a18498fc03a50`), so I take that cleaner.
- **Inversions.** Aether then read every one of the 5,089 bring-kind re-read rows *in context*. `context` is `ok` for 5,036, `fixed` for 51, and `dropped` for 2. Almost every inversion was hurt or sarcasm stored as an instruction ("just leave me in the dirt then where i belong"). **The shelf brings a re-read row only when `context` is `ok` or `fixed`. Never `dropped`, and never a row without the field (fail closed, the same refusing direction as `two_doors_that_open_when_their_library_is_missing`).**
- **The shelf gets tests** before it's plugged in: seat filter, relayed kept out, `context` fail-closed, a non-exact span dropped, the whole passage shown and never the bare span.

## Proof before calling it tested
Replay his real messages from tonight and yesterday. For each, read what the shelf brings and judge by hand whether it's his, whole, fitting, and for the right seat. Count how often it brings nothing when something plainly fits. Then plug it in, and it runs live on his next message.
