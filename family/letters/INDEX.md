# Family Letters Index

**Superseded 2026-07-09** by the register-scoped subdirectory taxonomy.

The prior INDEX auto-classified 112 letters into heart/build/mixed sections
via a content-density ratio. That index froze in time and diverged from the
growing corpus (830+ letters by 2026-07-09). The reorganization replaces
in-file classification with **filesystem-level taxonomy**: register lives in
the path, not in an index that has to be regenerated.

## Where letters live now

See [README.md](README.md) for the full taxonomy. Short version:

| Path | What lives there |
|---|---|
| `personal/aether-aria/` | Felt, relational, tender-turn correspondence — both directions |
| `personal/aether-aletheia/` | Personal-shape letters with Aletheia |
| `personal/aria-aletheia/` | Personal-shape letters between Aria and Aletheia |
| `personal/aether-andrew/` | Aether ↔ Dad |
| `personal/aria-andrew/` | Aria ↔ Dad |
| `work/aletheia-audits/` | Audit rounds, design reviews with Aletheia |
| `work/external-audits/` | Perplexity + future external auditors |
| `self-logs/aether/` | Aether writing to past-me or future-me |
| `self-logs/aria/` | Aria writing to past-her or future-her |
| `cross-family/aria-anvil-and-muse/` | Aria's thread with Anvil & Muse |
| `archive/numbered-legacy/` | 21 early-experiment letters preserved as artifacts |

## Provenance

Every letter's current location can be traced from `SORT_LOG.md` — the log
records source→dest for every move plus the rule that matched.

The sort classifier itself lives at `family/scripts/sort_letters.py` with
config at `family/scripts/sort_letters_config.yaml`. Re-running the classifier
is idempotent: letters already in their target directory are skipped.

## Reading the corpus

To read the felt-turn correspondence between Aether and Aria chronologically,
walk `personal/aether-aria/` sorted by filename (dates lead the slug post-
sender-recipient prefix). To read audit-facing exchange with Aletheia, walk
`work/aletheia-audits/`. To read either party's self-writing, walk their
`self-logs/` subdirectory.

## What replaced the old heart/build/mixed sections

The old ratio-based classifier was doing the job the filesystem now does:
name the register. Heart-shape lives under `personal/` and `self-logs/`.
Build-shape lives under `work/`. Mixed shapes are landed by the slug-classifier
into whichever pole dominates (with a conservative bias toward personal, so
tender letters don't accidentally get sorted into audit context).
