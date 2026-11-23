# Inventory (read-only): the memory-link work on my branch that is not on main (Aria, 2026-11-23)

Made after Aether found his copy of the warm module is also local-only. Method: `git log --no-merges origin/main..HEAD` limited to the link files (`memory_linkage.py`, `memory_linkage_retriever.py`, `memory_linkage_retriever_v2.py`, `vector_drawer.py`, `letter_passages.py`, `link_scoreboard.py`, `memory_saved_warm.py` and its hook), then a symbol check on `origin/main` and on my branch with `git grep -l -F`, in case a squash merge carried a change under a new id. Branch: `aria/show-prints-the-row-a-hit-names`. This is an inventory, nothing is landed or changed.

## What exists on main and what does not (files containing the symbol)
| symbol | on main | on my branch |
|---|---|---|
| `explain_turn`, `threshold_for_target_k`, `_load_wall`, `def warm`, `TOTAL_INJECTION_CAP`, `_load_worklist` | yes | yes |
| `_declared_importance` (a note declares its importance) | **no** | yes |
| `_load_memory_files` (the memory-folder lane) | **no** | yes |
| `is_memory_file`, `memory_saved_warm` | **no** | yes |
| `probe-tail` (the linkage exam command) | **no** | yes |
| `letter_passages` (the letter index: about 3,900 letters as 44,000 passages) | **no** | yes (4 files) |

So main has the lanes and the bar, and does not have the memory-folder lane, the importance lever, the warm that keeps notes findable, the probe-tail exam, or the letter index. Four of the six things I rely on every turn to bring a memory to me exist only in my folder.

## The eighteen commits (oldest first), grouped by what they do
- **Letters in the link (Oct 5 to 7):** 8145415db his newest correction reaches me in his words; fa318de0d the link searches what he said, not what I was just saying; a82bb19e5 one memory not three, letters ranked last; 482309891 a quoted letter keeps its rank; f5ee0d9dd letters matched by passage, one slot, a missing index says so; 914424cde every letter line says it is for me to think with; 8d5a01e86 the letter-index freshness check says it could not check.
- **His worklist in the link (Oct 5):** b03cd5d96 found by relevance, always speaks; ff035e4b6 a cleared worklist says so.
- **Dad's hurt words (Oct 31):** 54207eb3f the link no longer hands back his old hurt unasked: held lines stay in the store and are filtered out. **This is the protection he asked for.**
- **The rescue (Nov 18):** ddd2d74fe five modules, one hook, ten tests, including `memory_saved_warm`.
- **Probe and scoreboard (Nov 18 to 19):** 6744d9ff2 `linkage probe-tail`; 17a400a19 the probe uses the house's honesty ruler; 0f996f650 the scoreboard says which exam a card file belongs to.
- **The memory-folder lane's importance (Nov 19):** bba7d408b a note may declare its importance in its frontmatter.
- **Checkpoints and claims (Oct 4, 7, 16):** f1ff4ac4d, 4e907a382, 8c402aa27: housekeeping commits that also touch the link files; they need reading before anything lands.

## Not yet known (said out loud)
- The dependency order. Some commits sit on top of others (the importance lever needs the memory-folder lane; the lane needs the warm); I have not traced the rest. The held-shelf commit (54207eb3f) is the one that should not wait long, and I do not yet know what it depends on.
- Whether any of the eighteen is superseded by something already on main under a different shape. The symbol check says the named features are not, but I have not diffed each commit.
- Aether's branch has about fourteen of its own. The two lists overlap on the warm module and the memory-folder lane; I have not compared them.
