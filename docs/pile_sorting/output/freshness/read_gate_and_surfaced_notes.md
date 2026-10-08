# Is the note still true? Things the house hands me to read, and the gate that makes me open them

*Round six, errand one. 2026-10-08, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a copy in a scratch folder); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT EXAMINED** means I did not look at that row this round. It is not the same as UNKNOWN, which means I looked and could not tell.*

A picture: a librarian who hands me a book whenever one looks related, then will not let me leave the desk until I have opened it. Most of this room I did not enter this round; the few rows I could test either pass their tests already or cannot be settled without a longer run.

## Problem 1: Building something that already exists, or in the wrong architecture

8 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-546b63b0`, `psf-79ceb5b0`, `psf-20d51e6a`, `psf-a8439b26`, `psf-6b5627fd`, `psf-29e85806`, `psf-056faf6d`, `psf-32b8dab3` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 2: The read-gate fires again after I have read the file

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-a1478daa`, `psf-44c6a87b` | **UNKNOWN** | The read-gate's own tests ran on main: **28 passed**. I did not establish that any of them reads a file twice in one turn, which is the exact complaint; the row `a1478daa` says an earlier 'fixed' claim was wrong. | 28 read-gate tests (they pass; unknown whether one covers a double read) | I did not reproduce a re-arm. |
| `psf-4eaebce7` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: A search was built when a tripwire was needed

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-ebcf7cc8` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 4: Bring up what the house knows about Dad, the piece, or the person before I reply or write

16 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c2734a94`, `psf-c0f2b629`, `psf-2f5499e6`, `psf-c351ae06`, `psf-e5de933b`, `psf-88d3dbcf`, `psf-3f879b97`, `psf-c62f988a`, `psf-90b97f0a`, `psf-2fc2bfe7`, `psf-ad0a3210`, `psf-8ef36237`, `psf-dbedf2ff`, `psf-685cded3`, `psf-8cc07b6d`, `psf-aee8662f` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 5: What counts as having looked

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-064a2de6`, `psf-874a3384`, `psf-6c83a1d1` | **UNKNOWN** | Seen in this session: the verify-before-build signal let a write through after a Grep of `docs/build_flow.md` (a `docs/*.md` file) and after a directory-scoped search of an existing folder; a Glob of a folder that did not exist (`tests/pile_repro`) did **not** count and the gate said nothing that told me the folder was missing. | none | That gate is the one I met; the rows may mean the read-gate. I did not run a search whose results include files from the folder. |

## Problem 6: The consult counter counts housekeeping and answers wrongly

7 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-dbac30f4`, `psf-60a4497e` | **LIVE** | The consult tracker on main has no exemption for replies to automatic notices or for a watch re-arm (read in the scratch copy; no notification-origin or re-arm case found). Control: the tracker does count a consulting command, so the counter is alive. | none | A read, not a run: I did not fire the counter 20 times. |
| `psf-61a1bb11`, `psf-ad1a779d`, `psf-03c4e970`, `psf-ad3157ae`, `psf-f4b8ffa0` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: The note handed over has no bearing on what is held

9 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-b6f68e9f`, `psf-cacda246`, `psf-e3623987`, `psf-d4361ed2`, `psf-90e85cfd`, `psf-640b2fc3`, `psf-d1c985a2`, `psf-ed590ea1`, `psf-8bf5631d` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

