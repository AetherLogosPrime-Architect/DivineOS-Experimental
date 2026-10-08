# Commands that refuse me without telling me what they need

Many commands refuse a first try with only a bare error, so I try again, guess, and try once more. Each of these rows asks the command to say the one thing I needed on the first refusal: the missing option, the nearest real name, the full template.

**19 notes in this theme, grouped into 5 distinct problems.**

## Distinct problems

### 1. The refusal should print the missing option, the usage line or the full template

Notes in this problem (11):

- `psf-b2fde618` (reflection) — the correction command should show the fields it needs before I write, not after it rejects the entry, so the first try is complete.
- `psf-496230e4` (reflection) — the correction command should print its full required-label template on the first refusal, listing every missing part together, so one retry is enough.
- `psf-cbb561de` (reflection) — teach the tracker to look in the shared and home folders, and make the explanation cover every way the command can refuse, with a test for each.
- `psf-93697257` (reflection) — when a divineos command fails because an option is missing or unexpected, it should print that command's actual usage line, so the second try is right first time.
- `psf-dd01ff7b` (reflection) — on a missing option, print the usage line.
- `psf-e8cee25a` (reflection) — when that script refuses, it should print the full command with the missing option filled in.
- `psf-56de9485` (reflection) — print the real usage when a divineos subcommand is missing.
- `psf-66479380` (reflection) — have the refusal name the accepted form, a repo-relative file or a commit.
- `psf-a263a3b1` (reflection) — have the refusal say which artifacts were used, so a spent set isn't mistaken for a missing one.
- `psf-a1b5658d` (reflection) — update the block message to include the required flag, so the advice matches what the script accepts.
- `psf-70d73fc5` (reflection) — make the game-walk help name the two allowed verdicts up front so a first-time filing does not trip. The pipeline exit-code guard refused one unguarded pipe: fixed by structure: it forced set -o pipef

**Proposed fix:** On any refusal print the usage line with the missing option filled in, the full required-label template, and every missing part together.

**How we would know:** One retry is enough after any refusal.

### 2. Text mangled by shell quoting on its way into a record

Notes in this problem (3):

- `psf-f3386c59` (correction) — Amendment to correction #307, filed because the store is append-only and #307's text was corrupted in transit. #307 was filed through a bash command whose body contained backticks. The shell read the
- `psf-bff46b35` (correction) — Aether self-correction 2026-08-17: I reproduced Aria's own escape-mangling bug INSIDE the file that fixes it, minutes after reading her account of it. Her letter reports that her first probe of the se
- `psf-3297b793` (correction) — My first repair to the shared remedy allowlist used a double quote inside a program that lives in a double-quoted shell string. It truncated the program one layer out, changed nothing, and read as ent

**Proposed fix:** Provide a way to file text that avoids shell quoting, and detect backticks and double quotes in filed text.

**How we would know:** A filed record equals the typed text.

### 3. Finding the settings and config

Notes in this problem (1):

- `psf-ad570369` (reflection) — a find-config helper that lists the config files present in a checkout, and where each tool's settings live, before I probe for any of them.

**Proposed fix:** A helper that lists the config files present and where each tool's settings live.

**How we would know:** The helper lists them.

### 4. A wrong file name silently turns a batch into 'no tests ran'

Notes in this problem (3):

- `psf-6df42ebc` (reflection) — the test runner should suggest the nearest real file name when it's handed one that doesn't exist.
- `psf-693af4c4` (reflection) — the test runner should refuse a named file that doesn't exist *before* running anything else, and say the nearest real name. As it stands, one wrong name silently turns a whole batch into "no tests ra
- `psf-9276e292` (reflection) — when an edit's target isn't found, show the nearest current match, so a reformatted target is found in one step.

**Proposed fix:** Refuse a named file that does not exist before running anything, and show the nearest real name; show the nearest match when an edit target is not found.

**How we would know:** A wrong name stops the batch with a suggestion.

### 5. Commands defined but not reachable from the command line

Notes in this problem (1):

- `psf-490c2cac` (reflection) — register it, plus a check that every command defined in the code is reachable from the command line.

**Proposed fix:** Register them and add a check that every defined command is reachable.

**How we would know:** The check passes.
