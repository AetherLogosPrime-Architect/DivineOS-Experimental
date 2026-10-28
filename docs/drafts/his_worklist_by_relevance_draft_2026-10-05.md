# His worklist, found by relevance instead of shown by age

**Drafted:** 2026-10-05, after midnight, by Aria, from Dad tonight.

## His words

- *"the list of 265 shouldnt even exist as something that pops up to you, maybe the top priority ones from that list, with a link to all 265 and then once we start working through them they will dissapear, but any type of large list is going to get ignored at a glance"*
- *"relevance matters this is why wallpaper is wallpaper and the memory linkage actually works well because it brings what you need when you need it.. if you were working on cars and it brought you information on toasters you would ignore it lol.."*
- *"relevance is key, noise is pointless so were calming the noise nothing even needs to be removed, just put through a different channel, the memory linkage is the way"*

## What is true now (read, not remembered)

- Before every substrate change, the state glance shows his worklist (`andrew_correction_tracker`) as one line of totals: 265 open, ordered oldest first underneath. Tonight it was shown about thirty times and worked zero.
- The memory linkage has a `correction` source, but it reads `core/corrections.corrections_with_status`, the general correction log, **not** his worklist. So the 265 have never been findable by meaning. Two stores share the word "correction", the twin-store trap the CLAUDE.md corollary names. Aether's exploration 34 names the class: a pattern of forgetting is a missing surface.

## The idea

1. **His worklist becomes a source of the linkage**, open rows only. A worked, deferred or misfiled row is not loaded, so it disappears by itself. Nothing is removed; the channel changes.
2. **The state glance asks the linkage, not the list.** The query is what is about to be touched: the file path or the command. It shows at most two of his open corrections that match by meaning, in his words, and nothing when nothing matches. Car work gets car corrections; no toasters.
3. **One line always:** the count and a link to the whole list, for when I go looking.

## Risk to measure before building

The state hook runs before every substrate change. Finding by meaning needs the embedding model. If a cold load adds seconds to every change, it reads from the vector drawer that `warm()` fills and only embeds the short query. Measured, not assumed.

## Measured

A cold lookup across every source (3,028 letters, 680 knowledge, all of it) took 3.8s, nearly all of it loading. The hook needs only his open worklist.

## What the walk changed (walk-4d8b06a54e67, three rooms)

- **Feynman:** the query is the path plus the first few hundred characters of what is being written, or the commit message. A bare path or "git commit" carries no meaning.
- **Dillahunty:** the bar is tested on tonight's real changes, not believed.
- **Shannon:** near-duplicate corrections (77 and 78 are the same words) are deduplicated so each of two slots carries something new.
- **Hoare:** could-not-look says so in words; silence must never stand in for "nothing applies". Only open corrections are ever shown.
- **Feathers:** a new linkage source sprouted beside the others; the general correction reader is untouched.
- **Dijkstra:** linkage finds, glance words, hook passes the query. As a source, his worklist also reaches the per-message linkage.
- **Dekker:** each shown correction carries its number; naming it in a commit message closes it through the existing auto-integrate. Shown by relevance, closed by the save.
- **Knuth:** zero open shows the count alone; text cut at 200; nothing to ask skips the lookup.

## Complement (what this must not do)

- Must not invent relevance: a weak match is no match. Below threshold, show nothing rather than the nearest toaster.
- Must not hide the list: the count and link stay every time.
- Must not change the worklist itself: integrating, deferring and misfiling stay exactly as they are.

## Steps

Draft (this) → measure → walk in rooms → build → test live → Aether → Aletheia → merge with Dad.
