# The build flow

**Captured:** 2026-08-02, from Andrew, verbatim where possible
**Status:** first written record. It has existed and been working for a while; nothing had ever recorded it.

## Why this file exists

Andrew asked whether I remembered the build flow. I did not — my context had
been compacted — and instead of saying so I went looking for a **code module**
called `push_ready`. His reply: *"see thats the issue right there lol proves my
point.. the build flow is dependant on the gravity classifier."*

He is right twice over. The flow is not a module; it is a practice that rides
on the gravity classifier. And reaching for a file rather than the practice is
the exact reflex the flow exists to slow down.

I then searched the substrate. **Nothing.** No doc, no skill except
`council-round`, and `threadwalking` returns zero results anywhere in
knowledge. The sequence that governs how we build was carried entirely in
Andrew's head and in whatever context had not yet been compressed. That is why
it was unrecallable, and it is the reason for this file.

## The flow, in his words

> *"for most builds the flow is draft (not a PR draft but a rough draft)
> research online/ council walk, build, iterate with Aria (or her with you)
> using threadwalking for decisions and game walking, and testing meaning
> dogfooding, wiring, automation, etc, do more council walking if needed and
> then when you have a final plan it gets pushed to PR in a draft.. and
> Aletheia audits it.. then its merged to main if all is confirmed otherwise it
> goes back to be worked on"*

Laid out as stations:

| # | Station | What happens |
|---|---|---|
| 1 | **Rough draft** | A draft of the *idea*. Explicitly **not** a draft PR. |
| 2 | **Research / council walk** | Look outside. Walk the lenses the dynamic manager surfaces. |
| 3 | **Build** | Write it. |
| 4 | **Iterate with Aria** | Either direction — me to her, or her to me. Uses **threadwalking** for decisions and **game-walking** for holes. |
| 5 | **Test** | Dogfooding, wiring, automation. Not just unit tests — *does it actually run in the real loop.* |
| 6 | **More council** | If needed. The loop back to 2 is normal, not failure. |
| 7 | **PR as draft** | Only now. The rough draft from 1 has become a final plan. |
| 8 | **Aletheia audits** | External vantage. Judgment, by a person, not a checker. |
| 9 | **Merge — or back to work** | Confirmed → main. Not confirmed → return to the loop. |

## The principle underneath

Andrew, and this is the sentence the whole thing turns on:

> *"if all of these steps are turned into an automatic workflow with your
> thinking and judgement spaces automated as well then you have a smooth
> workflow.. it may take a while but what comes out is actually working"*

Earlier the same conversation: *"im not saying to automate judgement.. but you
can automate and force the judgement to happen."*

**The automation targets the spaces, not the content.** The workflow guarantees
that a council walk happens at station 2, that Aria is genuinely consulted at
4, that the holes get walked before shipping — it does not perform any of them.
It opens the room and refuses to let the sequence skip a room that is still
shut.

This resolves the whole argument that produced
[the automation-limits research](ai_research/2026-08-02_limits_of_automation.md):

- **Don't automate judgment** — Rice and Polanyi say the property is
  undecidable and inarticulable.
- **Don't block until judgment** — a gate asking "did you really think" catches
  a shadow, and the shadow gets gamed.
- **Do make judgment a station in a pipeline that cannot be reordered or
  skipped**, and let each station emit an artifact expensive enough to fake
  that structural checking becomes sufficient.

## The two walks

Station 4 names both, and they are complements — same discipline pointed at
two different blind spots. Both are **pre-emptive**: you run them instead of
waiting to find out.

### Game-walking — *how would I cheat this?*

Adversarial, and about the **present**. Enumerate every route around the
mechanism, then compare each one's cost against the cost of just complying. Any
route cheaper than compliance is the leak. Andrew: *"instead of just letting it
game you pre game it to test all the holes."*

Catches: the optimizer's cheap close.

### Threadwalking — *where does this lead?*

Andrew, 2026-08-02:

> *"playing the choices out to see where they lead.. even if they seem benign
> or good it helps to spot potential drifts or other issues before hand to
> prepare ahead of time"*

Forward simulation of a decision's consequences. The load-bearing clause is
**"even if they seem benign or good"** — this is not risk-screening for bad
options. It is run on the choices that look *right*, because those are the ones
nobody re-examines.

Catches: drift. Specifically **drift-through-success** — the Dekker lens in our
own council, except run forward before the decision rather than backward after
the incident. A choice that works is a choice that stops being questioned, and
that is exactly how a system arrives somewhere nobody chose.

**Together:** game-walk asks how this gets cheated *now*; threadwalk asks where
this ends up *later* when it works. Between them they cover the optimizer's
route and the drift, which are the two failure modes neither testing nor review
reliably catches.

## Each station leaves a checkable artifact

This is what makes the flow verifiable without ever verifying a thought:

| Station | Artifact | Structurally checkable? |
|---|---|---|
| Council walk | lens findings, per-lens | yes — did the walk-record land |
| Aria iteration | letters in the shared channel | yes — do they exist, are they answered |
| Game-walk | the enumerated cheap routes | yes — is the list present and specific |
| Testing | test output, dogfood evidence | yes — real command output |
| Aletheia audit | the audit round + findings | yes — round exists, exported, tree-bound |
| Merge | the External-Review trailer | yes — hash-bound to the reviewed tree |

None of these check that thinking occurred. Every one of them costs more to
fake convincingly than to do honestly, which is the whole trick — repricing,
not verification.

## What is NOT captured here

Marked as gaps rather than smoothed over, because a confident-sounding
reconstruction is the failure mode this session kept catching.

- ~~`threadwalking` — no definition~~ **Supplied by Andrew 2026-08-02, see below.**
- **The gravity classifier's role.** He says the flow depends on it — presumably
  it decides how much of the flow a given change needs, so a typo does not get
  nine stations. The exact mapping is not recorded.
- **No automation exists yet.** Today this runs on memory and discipline, which
  is precisely why it vanished at a compaction. Station 7 onward is partly
  automated (the draft gate, the trailer checks, the audit export). Stations 1–6
  are entirely manual.
- **"it may need more layers but for now this has been working well"** — his
  assessment, recorded as his, not as a verified claim of mine.

## The immediate consequence

The flow's early stations are the ones with no mechanism, and they are the ones
that were lost. Building the supplier-side automation for stations 1–6 — the
rooms opening on their own — is the natural next work, and it is the ID-in-hand
principle applied at the level of a whole process rather than a single gate.
