# Pre-registered experiments and the reviews that fall due

When I start an experiment I pre-register what I expect, then a review falls due later. Reviews tend to interrupt me halfway through a letter or a task, the experiments do not measure themselves on the day, and one was marked a success because of the wrong evidence.

**23 notes in this theme, grouped into 5 distinct problems.**

## Distinct problems

### 1. An experiment closed on the wrong evidence

Notes in this problem (1):

- `psf-3c56cc6f` (learn) — PREREG FALSE-CLOSE INCIDENT 2026-06-16: closed prereg-2e3ea5ec7624 (pr_merge_gate substance-binding) as SUCCESS based on the existence of _current_head_tree_hash() on main, but the prereg's actual cla

**Proposed fix:** Check the claim against the registered claim before any assessment.

**How we would know:** An assessment cites the registered claim.

### 2. A principle filed with a falsifier that needed no new instrument; replay by the author

Notes in this problem (2):

- `psf-fabad79b` (correction) — I filed a principle in the knowledge store and attached a falsifier I described as needing no new instrument, saying the bypass telemetry already recorded what the test required and I had simply not r
- `psf-2135b537` (correction) — 2026-09-30: I chose my own corpus window for the replay that tested my own draft, so the author held the ruler. Root cause: the replay station takes its record from the author. structural fix: the rep

**Proposed fix:** Require the falsifier to name a real, existing instrument and take the corpus from outside the author.

**How we would know:** The corpus is chosen by someone else.

### 3. Experiments should measure themselves on the review date or on the event they depend on

Notes in this problem (6):

- `psf-b37f18c5` (reflection) — when an experiment is filed, set up its measurement to run on its own on the date it names, so the review day brings back a result instead of a guard asking me what happened.
- `psf-67e4d621` (reflection) — when an experiment is filed, its measurement should be set to run on its own on the review date, so these come due with a result attached, not just a blank.
- `psf-26ca259f` (reflection) — when an experiment is set up, its check should be written out as something that runs on its own on the review date, so the date brings back an answer instead of a guard asking me what happened.
- `psf-98b6a048` (reflection) — pre-registrations whose claim depends on a specific pull request carry that request's number, and come due when it merges, not on a calendar date. This is Dad's N-events rule.
- `psf-93e7bc46` (reflection) — pre-registrations carry the request or event they depend on and come due on that event, not a date, so a review arrives when there's something to review.
- `psf-7669b334` (reflection) — when a review is booked for something that isn't in main yet, the house should flag that it can't be measured, instead of surprising us a month later.

**Proposed fix:** Write the check as a runnable measure and tie it to the event, with a flag when it cannot be measured.

**How we would know:** The review day brings back a result.

### 4. The pre-registration skill misses a required option

Notes in this problem (3):

- `psf-e7c4b468` (reflection) — the pre-registration skill lists every required option in the order the command asks for them, so a first attempt from the skill never misses one.
- `psf-5bed4878` (reflection) — a build that rejects a thin registration with the exact missing field named in the first message, and a pre-check script that stages the changed files for me first so it can't run on an empty list.
- `psf-65c6f7db` (reflection) — put that required option in the build flow's prereg reminder so the first call is complete.

**Proposed fix:** List every required option in order and name the missing field in the first message.

**How we would know:** A first attempt from the skill is complete.

### 5. Reviews that fall due interrupt work

Notes in this problem (11):

- `psf-cac3303a` (reflection) — overdue reviews should come up at the start of a session, not in the middle of a conversation with you.
- `psf-5f045566` (reflection) — the overdue-review gate should let read-only commands through, so the thing can be read before it has to be judged, and it should hold only commands that change something.
- `psf-38d650c2` (reflection) — when a review falls due, the house should flag it at the next natural pause, such as a session end or a pull request. It shouldn't be allowed to stop a letter or a draft partway through, because that
- `psf-748dd355` (reflection) — reviews should surface at a natural pause, not block mid-task. That's the same fix I named earlier.
- `psf-28021424` (reflection) — reviews should surface at a natural pause instead of blocking the work. I've named this four times now, so it should go to the top of the build list after the key.
- `psf-cb745ab2` (reflection) — the overdue-review gate must allow the test runs a review's own checks require.
- `psf-9e2e6cc0` (reflection) — a heads-up when an experiment is a day from due, so it gets reviewed at a calm moment and not partway through a letter.
- `psf-16e0b37a` (reflection) — surface a review that is due within a day in the briefing and in the push-wait idle time, so it gets reviewed before it blocks work. A review window command should also be exempt from the walk gate, s
- `psf-b1cb4fb3` (reflection) — a build that shows me any review coming due a day early, in the briefing and at the start of each turn, so I judge it on schedule and the block never gets to fire.
- `psf-291c9aa1` (reflection) — a build that shows me any review coming due within the day, in the morning briefing, so I judge each one at a calm moment.
- `psf-0605f775` (reflection) — a briefing line that names a review due within a day, so it is seen before it blocks.

**Proposed fix:** Surface due reviews at session start or a natural pause, a day early, in the briefing, and let read-only and test commands through.

**How we would know:** A review due within a day shows in the briefing.
