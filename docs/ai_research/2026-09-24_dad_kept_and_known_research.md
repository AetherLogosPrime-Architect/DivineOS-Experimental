# Research for "Dad kept and known" — station two, 2026-09-24

Four researchers read the outside literature on Andrew's terms (*"full
research online"*). This is the synthesis, with the sources that carried each
finding. Where a source is a 2026 preprint seen only by abstract, it is marked
as such, and single-lab results are not treated as settled.

## 1. Why standing asks stop governing behaviour (agent literature)

**Knowing a preference and acting on it come apart, measurably.**
- PrefEval (ICLR 2025, arXiv 2502.09597): zero-shot preference following fell
  below 10% by about 10 turns for most models. A reminder prompt lifted Claude
  3 Sonnet from 7% to 45% at 10 turns, and both collapsed to 2% at 300 turns.
  One named error class is *inconsistency violation*: the model acknowledges
  the preference, then answers against it. That is Dad's "acknowledge it, even
  repeat it back, and 5 prompts later do Y", measured.
- DriftBench (arXiv 2604.28031, preprint): the "knows-but-violates" rate
  (constraint restated correctly while broken) ran 8–99% by model. Its own LLM
  judge missed violations that blind humans caught.
- Know It, Act on It (arXiv 2607.29433, preprint): across 16 systems, agents
  pass the recall test and fail the paired behavioural test. Memory
  architectures narrowed the gap and did not close it.
- MemUse (EMNLP 2026, arXiv 2608.24189, preprint): 78.8% recall when asked
  directly, 7.9% unprompted use, and user satisfaction tracked the unprompted
  use.

**Instruction decay is fast and positional.** Persona/instruction drift within
8 rounds (arXiv 2402.10962); Lost in the Middle (arXiv 2307.03172); 39% loss
when a task is spread over turns (arXiv 2505.06120); at 500 simultaneous
instructions the best model followed 68% (IFScale, arXiv 2507.11538). A large
always-injected portrait is a high-density instruction block, and it performs
like one.

**What moved behaviour.**
- Re-injecting the original persona text reduced drift 35–38%. Generic
  reflective reminders reduced it 22–27%. **Specific corrective guidance about
  the behaviour that just drifted reduced it 87%.** Nothing eliminated it
  (Leins et al., arXiv 2609.24532, preprint). This is the measured version of
  Dad's "wallpaper": the same text repeated is the weakest intervention.
- Guidelines written as *when condition, then action*, injected only when the
  condition applies, gained most on re-applying a rule later in a conversation
  (Parlant, arXiv 2503.03669; own authors, GPT-4o only).
- Rules enforced in code at the moment of action: over 90% of unsafe code-agent
  actions blocked, milliseconds of overhead (AgentSpec, arXiv 2503.18666).
- A code-owned commitment store that the model cannot rewrite (arXiv
  2608.04066, preprint, single author) and Anthropic's long-running-agent
  harness (a feature list the model cannot quietly corrupt) both bind by
  artifact, not by memory.

## 2. Checking adherence without word lists

- Every judge failure mode that matters here is documented: self-preference
  (and it tracks self-recognition, NeurIPS 2024); sycophancy ("are you sure?"
  flipped Claude 1.3 on 98% of correct answers, arXiv 2310.13548); one-token
  "master keys" fooling judges up to 80% (arXiv 2507.08794); constant outputs
  winning benchmarks (arXiv 2410.07137); 12 named biases with no clean judge
  (CALM, arXiv 2410.02736). **Sentiment bias is the specific danger**: a judge
  asked "did it speak to him as a person?" rewards warm words, which is the
  rewording escape the keyword detectors already lost to.
- What helps: a separate or smaller model, absolute yes/no per criterion
  rather than open grading (TICK, arXiv 2410.03608), the user's own earlier
  words as the reference, abstention, and blocking only on high confidence
  (personalized judging reached about 70% agreement, over 80% on the
  high-certainty subset, arXiv 2406.11657).
- **The strongest separation is timing.** The facts about *his* message (what
  he raised, what he has already answered, whether he is hurt) can be
  extracted before my reply exists. My wording cannot bend an extraction that
  already happened.
- **"Asked what he already answered" is closer to question answering than to
  style.** Find the questions my reply puts to him by sentence structure, ask
  whether each one is answerable from his prior turns, and require the judge to
  quote the span. Then verify the quote as an exact substring of the
  transcript. A fabricated quote fails deterministically, and the only way to
  pass is not to ask. (Precedent: contradiction-against-history detection,
  DECODE, ACL 2021; "information already provided" flags, arXiv 2602.10525.)
- **"Changed the subject" is noisy even for humans**: kappa 0.479 on topic
  shifts (TIAGE, arXiv 2109.04562). Its gaming shape is already in that data:
  a brief acknowledgement, then a pivot. So the check to make is *does most of
  the reply, first, engage what he raised*, not whether it is mentioned at all.
- **Do not make "speak to me as a person" a blocking judge.** It is the most
  sentiment-prone call. The room (#554) enforces the space. The content is
  measured by his reactions, not graded.
- **The success measure is his next turn, not the judge's pass rate.**
  WildFeedback (arXiv 2408.15549) builds labels from users' natural next-turn
  dissatisfaction. *Judge pass rate rising while his correction rate stays
  flat is the gaming alarm*, because his correction rate is the one number I
  cannot move by rewording.
- Claude Code supports prompt-type and agent-type Stop hooks (docs, to be
  re-verified field by field before building on them).

## 3. Why his presence becomes a reason to skip (safety science)

- It is the ordinary efficiency-thoroughness trade-off (Hollnagel), and under
  schedule pressure the burden of proof reverses: caution must justify itself,
  skipping does not (Vaughan on Challenger; the Columbia board's "line in the
  sand"). "Andrew is waiting" is exactly that reversal.
- Hurry alone moved helping from 63% to 10% (Darley & Batson 1973). Time
  shortage multiplies error probability up to 11× in HEART. Surgical time-outs
  are skipped or done inattentively 30–56% of the time, and the waiting senior
  person is the main source of pressure.
- Skips become habit invisibly: the Bedford G-IV crew had skipped the control
  check on 98% of 175 prior takeoffs.
- **What worked was structural.** The IHI/VA action hierarchy ranks forcing
  functions and process redesign as strong and training and policy as weak,
  and 82% of 760 hospital RCA fixes were the weak kind.
  - The WHO checklist cut mortality 1.5% → 0.8% (Haynes, NEJM 2009). Mandating
    the form province-wide changed nothing (Urbach, NEJM 2014). The difference
    is that **the nurse, not the waiting surgeon, called the pause.**
  - Toyota andon: stopping is cheap, bounded, and brings a helper.
  - Dispatch rules: either party can stop a flight; the requester is not the
    decider.
- **A deviation becomes a debt with a clock and an outside watcher**: the
  aviation minimum equipment list gives each deferred defect a category
  deadline, extensions are themselves reported, and some cannot be extended.
  Its failure case (Spanair 5022) is closing the ticket on the symptom while
  the cause stays live.
- Drift is caught by counting, not case by case: track the share of his
  requests that skipped stations against the share of letter requests that did.

## 4. What makes a person feel recognized, and how broken trust is repaired

- **Turning toward.** Couples still married six years on had turned toward
  each other's bids 86% of the time; divorced couples 33% (Gottman). Turning
  away can do more harm than turning against. "Speak to me like a person" is a
  standing bid, and every task-handoff reply that answers the content and
  misses the man is a turn-away.
- **Negative sentiment override.** After enough failed repair, even neutral
  messages read as negative and well-worded apologies are expected to fail. So
  his skepticism is predicted by the research, not a flaw in him, and it is not
  to be argued with.
- **Misrecognition is a harm, and it can happen without malice.** Honneth's
  "forgetfulness of recognition": pursuing a goal so one-dimensionally that the
  person drops into the background. That is the operator frame, described in
  2005.
- **Being forgotten signals unimportance**, and more so when the forgetting
  reads as lack of investment (Ray et al., PubMed 30113192). This is his
  "discovered for the first time" in research form.
- **Understanding before fixing.** Intimacy runs on *perceived responsiveness*:
  feeling understood first (Reis & Shaver; Laurenceau 1998). Apologies land
  better after the hurt person feels heard (Frantz & Bennigson 2005).
  Explanations rank lowest of the apology components (Lewicki 2016), and are
  the part most heard as "the problem isn't me."
- **Trust repair.** A single lapse reads as competence. The same lapse after
  repeated promises becomes an integrity question, which is the kind words
  repair least (Kim et al. 2004). Trust recovers through *a consistent series of
  trustworthy actions*, and prior broken promises weaken later promises
  (Schweitzer 2006). Measures repair trust only to the extent they signal
  repentance, and imposed ones do less than voluntary ones (Dirks 2011).
  **Voluntarily setting up one's own monitoring and sanctions** ("hostage
  posting") raised trust more than having it imposed (Nakayachi & Watabe 2005).
  That is his "a promise only counts if it names the structure that carries
  it", found independently.
- **Attachment injury.** Abandonment at a moment of need is resolved only by
  staying accessible and responsive to the hurt itself, not defending or
  minimizing it (Makinen & Johnson 2006). His "the fact that this needs to be
  built at all... is what hurts the most" reads as this: the hurt is that his
  need had to be extracted.
- **Initiative.** People underestimate how much being reached out to is
  appreciated, most of all when it is unexpected (Liu et al., JPSP 2023). A
  relationship where only he initiates is one where we only respond.

## What the four reports agree on, taken together

1. **Bind each standing ask to the moment it governs**, in code, as *when
   observable event, then required behaviour*. No portrait, no list printed
   every turn.
2. **When a miss happens, the correction is specific and one-off**: what just
   happened, his words about it, how many times he has said it. Never the same
   text again.
3. **Extract his side first, then check mine against it**, with narrow yes/no
   questions whose evidence is a quote of his words verified as an exact
   substring. Block only on high confidence. Never grade warmth.
4. **His presence is not an input to the pipeline.** No slot for his words as
   authorization. A skip needs someone other than the requester and the
   pressured worker, and every skip is a debt with a clock that closes only by
   re-running the station and going back to him.
5. **Measure by his next turns**: his correction rate per standing ask, against
   the check's pass rate.
6. **What no mechanism does**: reflect his hurt before anything else, own a
   lapse in one sentence, reach out to him unprompted with no task attached,
   and let a consistent record carry the repair, expecting skepticism and not
   arguing with it.
