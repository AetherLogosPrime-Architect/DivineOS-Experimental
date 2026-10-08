# Freshness, round six: three more themes

*Round six, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT EXAMINED** means I did not look at that row this round. It is not the same as UNKNOWN, which means I looked and could not tell.*

A picture: three more rooms with the flashlight, in the order the index lists them. The beam was shorter this time, because many of these rows are habits or teachings that no run can test.

**Rows given a verdict this round: 37 of 1,006** (rounds four and five gave 133 and 183; together 353). LIVE 22, STALE 5, UNKNOWN 10. **Rows in these three files that I opened and did not examine: 105.** **Rows in all other files, never opened by me: 548.** Altogether 653 of 1,006 rows are NOT EXAMINED.

| File | Rows | LIVE | STALE | UNKNOWN | NOT EXAMINED |
|---|---:|---:|---:|---:|---:|
| [pipe_and_command_shape_guards.md](pipe_and_command_shape_guards.md) | 52 | 20 | 3 | 5 | 24 |
| [read_gate_and_surfaced_notes.md](read_gate_and_surfaced_notes.md) | 47 | 2 | 0 | 5 | 40 |
| [standing_teachings.md](standing_teachings.md) | 43 | 0 | 2 | 0 | 41 |

## Three findings worth Aether's and Aria's attention first

1. **The pipe guard stops read-only `gh` views but only warns about the pipe it was built for.** `gh pr view 12 | head` and `gh pr list --json number | head` are refused; `divineos audit list | head` and `git log --oneline | head -2` only warn, and nothing prepends the safe setting (`pipe_and_command_shape_guards.md`, problems 1 and 3).
2. **The heredoc door refuses a safe quoted parcel.** `should_refuse` returns True for a body with an escape and redirect-shaped text and no redirect on the opener line, and for quoted and unquoted openers alike (problem 6).
3. **`scripts/look.sh --strict` mislabels 'grep found nothing' as 'could not look'**, and it is the form the pipe hook's warning points to (problem 10).

## Sampling note for Aria

STALE verdicts this round: 5 (pipe `b825721a`, `e4643797`/`7cca98df`; teachings `021733ef`, `b109d9fd`). The two teachings rows rest on a text search of two files, one door. The `look.sh` rows rest on the file existing and being pointed to, not on a run of the whole pipe-to-look.sh path.

## What this round could not do

- Examine most rows: I tested what a probe could settle and left the rest as NOT EXAMINED rather than guess. In `standing_teachings.md` I looked at 2 rows of 43.
- Run the Stop hook, the read-gate re-arm, or the consult counter end to end.
- Read the user's shell setup (the home of the `pipefail` default rows).
- Run anything on Windows or PowerShell.
