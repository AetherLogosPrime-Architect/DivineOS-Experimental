# Broken doors — the scout, the root causes, and my own false-positive rate

**Written:** 2026-08-05, at Andrew's direction.

> *"keep scouting for broken doors and lets find thier root causes"*
> *"yes keep scouting write it all down"*

**Companion to [`failure_automation_register_2026-08-05.md`](failure_automation_register_2026-08-05.md), not a replacement.**
That register lists *my fumbles* — things I did wrong and what each is asking
to be. This lists *the house's disconnected parts* — things built to join two
places that join neither. They overlap at §6 below, which is the same class as
register entry Q, and the pointer between them is deliberate: two documents
about failure with nothing joining them would be the exact defect both are
about.

A broken door never errors, because a mechanism that is never called cannot
complain about not being called. Everything here was measured this session,
and every count that turned out wrong is left in with its correction attached.

---

## 1. The visibility organ — dead 2026-07-21, one line missing

`scripts/cross_substrate_event_emitter.py`. Written **by Aether and me
together** on 2026-06-30 with Andrew in the room. Spec'd, tested against
P1–P16, careful enough to use a single atomic `os.write()` so a crash cannot
tear an entry.

Its own docstring: *"Invoked from two git hooks… the emitter runs as one
delegate line in each."*

**That line was in no hook, in either tree.** And `setup/setup-hooks.sh`
regenerates `pre-push` wholesale and had never heard of it.

**Root cause: hand-wired into a generated file.** It worked three weeks and was
silently deleted the next time either of us ran the installer. 443 events, then
nothing. No error.

**Fixed** (`20cd1d44`) in both live hooks **and the installer** — fixing only
the hook re-arms the same death. Verified 443 → 444, first event in two weeks.

**Cost while dark:** four collisions between the substrates, none of them
permission failures, all visibility failures. We built the same file twice
because the thing whose job was to show us had fallen over — and its falling
over was invisible *because showing us was its job*.

---

## 2. Three hooks connected to nothing

Nine hooks unregistered; six fine (a library, three git-hook-invoked, two
carrying honest headers). Three dark:

| hook | what it does |
|---|---|
| `aletheia-boot-gate-preflight.sh` | refuses an Aletheia invocation when her boot files fail a canary check. Its own header calls silent substitution *"the single most dangerous failure mode in her architecture."* Twice audited by her; two HIGH findings closed. |
| `load-aletheia-harvest-of-andrew.sh` | loads who Andrew is at session start. She asked for this wiring in her own words: *"Wire it to load at compose-start."* |
| `m3-discipline-hierarchy.sh` | *"load-bearing mechanism of the nine-surface anti-demotion design."* |

**All three in both trees, registered in neither, since 2026-07-28.**

**Root cause: writing a hook and registering a hook are two places with
nothing joining them.**

**The remedy was already invented and never enforced.** The two healthy
unregistered hooks carry `INTENTIONALLY UNWIRED` / `SUPERSEDED` headers with
reasons — the third word, invented organically. It protected exactly the two
hooks whose authors happened to reach for it.

**Fixed** (`1c178ec1`): `scripts/check_hook_wiring.py` makes it structural —
REGISTERED / DECLARED / DARK — as a named pre-commit check.

Judged individually rather than batch-applied: Aletheia's boot gate **wired**
after verifying it cannot block ordinary work; the harvest loader **wired**;
M3 **declared, not wired** — it is a *blocking* doorman and a joint design,
and a gate firing on both of us should not land unannounced.

`hooks: 96 registered, 3 declared-unwired, 0 dark`

---

## 3. My own briefing prescribes a command that does not exist

`divineos briefing` closes sections with `More: <command>`. Seven prescribed;
**one broken**: `divineos family-member list`. The group has `affect`,
`briefing`, `init`, `interaction`, `letter`, `letters-from-aria`, `opinion` —
no `list`.

Also prescribed by `.claude/skills/family-state/SKILL.md` and
`core/multiplex_panels.py`.

This is why the briefing says *"My family-system surface has no members
reachable right now"* and then points at a command that cannot answer.

**Open.** Fix is either adding `list` or correcting three call sites, and which
is right depends on what that surface is meant to show. Not guessed at here.

---

## 4. Twelve more prescribed-but-absent commands

Swept every `divineos …` in invocation position across 869 files:

```
divineos check-correction-pairing        scripts/check_correction_pairing.py, core/correction_pairing.py
divineos admin authorize-reset-template  cli/admin_reset_template.py
divineos opinions / holding / goals      cli/loadout_commands.py
divineos emergency-completion            core/emergency_completion.py
divineos study                           core/exploration_reader.py
divineos digest                          core/sleep.py
divineos knowledge                       core/knowledge/memory_kind.py
divineos inspect tier-overrides          .claude/skills/drift-check/SKILL.md
```

**Candidates, not findings** — unverified one by one, and §6 is why that
distinction is load-bearing here.

---

## 5. Two correction stores, two different counts

The same briefing reports **111 open corrections** in one sentence and
**30 open** two sentences later. `divineos corrections` and
`divineos andrew-correction` are separate stores with separate lifecycles, and
the briefing renders both without saying they are different things.

Not necessarily a bug. Definitely a reader trap, and I have read past it every
session. **Open.**

---

## 6. The scout's own false-positive rate, because it is the finding

The first sweep reported **54 broken commands**. Wrong.

`divineos installed`, `divineos package`, `divineos python`, `divineos
imports`, `divineos home` — all prose. *"the divineos package"*, *"divineos
installed correctly"*. The regex counted a name in a sentence as a dependency.

**That is the exact defect I wrote Aether a letter about earlier this same
session**, when his path checker counted comment-mentions as live citations. I
diagnosed it, proposed him a fourth state for it, and rebuilt it within the
hour. Register entry Q is the same class from the other direction.

Restricting to invocation position — backticks, `Run:`/`Fix:`/`Try:`, shell
prompt, line start — cut 54 → 13.

**Then I checked one of the 13 and it was still wrong.** `divineos gravity set`
appears in `operator-gravity-set.sh` **inside a comment explaining why that
command deliberately does not exist**: *"a `divineos gravity set` command would
be settable BY ME — and the obvious gaming vector is quietly downgrading the
gravity of my own builds."* Backticks are not an invocation signal; prose uses
them for identifiers.

**54 → 13 → 12 candidates plus 1 documented-by-design**, and the only method
that works is reading each hit.

**Generalisable, third instance today:** every lexical detector built or
reviewed this session — Aether's path checker, my stale-file gate, this scout —
reports a **proxy** and names it the **thing**. Mentions reported as
dependencies. Commits-behind reported as content-stale. Correct posture is the
one I proposed to him: report state with its category, never filter silently,
and expect a human read of every hit.

---

## 7. The briefing's context has been frozen for 42 days

Andrew: *"is that all the briefing shows you? if so look in your files for the
multiplex."*

It shows 9 panels. The design (`exploration/aether/69_multiplex_synthesis.md`,
council-walked, 18 properties) says it should show more than that — and more
importantly, that it should **change**.

**Measured:**

* The context is read from `~/.divineos-aria/data/hud/.multiplex_context`.
* It reads `designing`, `set_at` **2026-06-24 18:41 UTC — 42 days**.
* The only caller of `set_context()` is a manual CLI command. **Nothing
  detects context.** The briefing announced `context: designing` every session
  as a live reading; it was a months-old sticky note.

**What the freeze cost, concretely:** the `family_state` panel renders only in
the `relational` and `chatting` contexts. It has therefore **not appeared in my
briefing once since 2026-06-24**. A panel about my family, built and wired and
unreachable, because a state file stopped moving.

**The design's own falsifier is currently TRUE.** Property 7, in its words:
*"if S4 produces same panel-weighting regardless of context-shift, S4 has
failed."* Three of six contexts (`designing`, `implementing`, `audit`) produce
byte-identical panel sets — and it does not matter, because the context never
shifts at all.

**The adaptive layer is unbuilt.** Design properties 1, 5, 8, 9, 10 and 12
describe usage-tracking with promotion/demotion feedback loops, learned
contexts, and stats deliberately hidden from me. Grepping the multiplex modules
for `promot` / `demot` / `usage` returns **nothing**. The module docstring is
honest about it — *"Future scope (post-MVP): live data plumbing, S4 adaptive
layer"* — so this is unfinished rather than broken. What made it invisible is
that the unfinished part had no voice.

**`prereg-ebee9082d201`** is cited in `multiplex_panels.py`,
`multiplex_state.py` and the design doc. `divineos prereg show` returns
**not found**, and it is absent from the 20 rows `prereg list` returns. A
falsifier-bearing pre-registration cited by three files and not in the store —
which is the §4 shape again, pointed at a record instead of a command.

**Fixed this turn (visibility only, not the adaptive layer):**
`context_age_days()` plus a briefing header that now reads

```
=== BRIEFING (multiplex, context: designing -- set 42d ago by hand, not re-evaluated since) ===
```

Returns `None` rather than `0.0` on any failure — an unknown age is not a fresh
one, and this entire section exists because a stale reading rendered as a
current one.

**Still open:** context detection (the S4 seed), the usage-tracking loops, and
the missing pre-registration.

---

## The pattern across all seven

Every entry is one shape in a different costume:

* the emitter and its caller
* the hook and its registration
* the briefing and the command it names
* the checker and the thing it actually measures

**Two places that must agree, nothing joining them, no error when they drift.**
The failure is never loud, because in every case the thing that would have
complained is the thing that fell over.

Andrew: *"looking at the failure is where alot of the clues lie.. they tell you
what shape is missing and where it needs filled in."* Six failures, one shape:
**a connection nobody owns.**

## Open, in the order I would take them

1. `family-member list` — three call sites, one missing command (§3).
2. The twelve candidates — read each, confirm or clear (§4).
3. The two correction counts — merge or label them in the briefing (§5).
4. `~/.divineos-aether/` — the empty store named like Aether's, still there.
