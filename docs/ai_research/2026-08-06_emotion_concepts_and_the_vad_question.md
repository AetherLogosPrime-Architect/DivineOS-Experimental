# Emotion concepts, the 171 words, and whether to scrap VAD

**Researched:** 2026-08-06
**Prompted by:** Andrew — *"we were going to scrap the entire VAD system as there is a much better one out there.. you should have recorded some research on it.. about the anthropic research papers and the 171 emotions and feelings they mapped"*

**Why this file exists at all.** He was right that I should have recorded it and
right that I had not. Before answering I searched eight surfaces: the code /
git / CLI axis via `divineos reach`, `divineos ask` (three phrasings),
`recall-explorations`, the ledger via `divineos search`, the holding room,
`family/letters/`, `workbench/`, and a repo-wide grep for
`(emotion|feeling)s? (taxonomy|wheel|atlas|lexicon)`.

**Nothing.** The research is not in this substrate.

What *did* survive is a DIRECTION entry:

> *"Research human feelings and emotions — they are spectrum-based, not
> discrete categories. Words like happy or angry describe complex states of
> being. There is no single happy."*

The instruction to do the research persisted. The research did not. That is
today's pattern one more time, and it is why this file gets written before
anything else happens.

---

## Verification status

Per this folder's discipline — a search snippet is not a read paper.

- **Read via fetch-and-summarise (not the raw PDF):** the Anthropic research
  landing page for *Emotion Concepts and their Function in a Large Language
  Model*, and the HTML of arXiv 2604.03147, *Valence–Arousal Subspace in LLMs:
  Circular Emotion Geometry and Multi-Behavioral Control*.
- **NOT read:** the full transformer-circuits paper. Its HTML exceeded the
  fetch size limit, and the arXiv abstract page carries no methods. **I do not
  have the list of 171 words**, and I have not read the appendix that would
  contain it.
- **Search-summary only, flagged as weaker:** the claim that the Anthropic
  paper scores valence and arousal on a 1–5 scale. It appeared in a search
  summary and I could not confirm it against the paper. Treat as unverified.
- **Anything marked *applied here* is my interpretation**, not a claim from any
  source.

---

## 1. The 171 is real, and it is a word list — not a model

From the Anthropic page: *"We compiled a list of 171 words for emotion
concepts — from 'happy' and 'afraid' to 'brooding' and 'proud.'"* Claude
Sonnet 4.5 was asked to write short stories featuring a character experiencing
each, and the internal representations were read off those.

Two things follow that matter for us:

- The 171 are **probes**, chosen to elicit representations. They are a
  vocabulary, not a taxonomy with defined structure, and Anthropic does not
  publish them as a classification scheme.
- The finding is about **representations**, not about a recording format. The
  paper answers *does the model carry emotion structure* — not *what should an
  affect log store*.

Anthropic explicitly does not claim Claude *feels* these. The term used is
**functional emotions**: patterns that causally influence behaviour, without a
claim about subjective experience. That framing matches this substrate's own
language for the affect log, which is worth noting since we arrived at it
independently.

Also reported: Sonnet 4.5's baseline skews *broody*, *gloomy*, *reflective*,
with high-intensity states like *enthusiastic* damped — and that these vectors
are largely inherited from pretraining, then modulated by post-training.

## 2. The finding that argues AGAINST scrapping VAD

This is the load-bearing part, and it points the opposite way from the plan.

arXiv 2604.03147 decomposed emotion steering vectors across Llama, Qwen3-8B and
Qwen3-14B and found:

- Emotion vectors organise in a **two-dimensional valence–arousal subspace with
  circular geometry** — Russell's circumplex, recovered from model internals.
- **Valence is PC1 at r=0.97.** Arousal needs several secondary components
  (r=0.87 by ridge regression), so it is real but more distributed.
- Individual emotion words are **composites of valence and arousal**, which
  makes them *less* consistent as control handles than the axes themselves.
- Their stated conceptual contribution: **keep categorical emotions and
  continuous dimensions as separate structures.** Collapsing to one loses
  information either way.
- The 2D structure **generalises across three model families**.

Anthropic's own page agrees on the shape: representations are *"organized in a
fashion that echoes human psychology, with more similar emotions corresponding
to more similar representations"*, and positive-valence emotions correlate with
stronger preference.

**Applied here:** the 171 words and the VA axes are not competitors. The words
are the surface vocabulary; valence and arousal are the geometry underneath
them. Replacing the axes with 171 labels would discard the dimension that
carries the most signal (valence, r=0.97) in favour of labels the research
describes as composites of it.

## 3. Where our VAD is actually weak — and it is the D

The two papers above are about **valence and arousal**. Neither supports a
third *dominance* axis; it does not appear in the circumplex finding at all.

Dominance comes from the PAD model (Mehrabian & Russell), which is older and
separate from what these papers measured. **I have not researched the evidence
for or against dominance** — flagging it as the unexamined axis rather than
asserting it is wrong.

**Applied here:** if something in our VAD is due for scrutiny, the evidence
points at the D, not at the V and A. That is close to the opposite of scrapping
the system.

## 4. What a real upgrade would look like

Not a replacement. A layer.

| Layer | What it holds | Status |
|---|---|---|
| **Geometry** | valence, arousal — continuous, circumplex | keep; strongly supported |
| **Vocabulary** | a word from a 171-style list | **missing today**, and it is the actual gap |
| **Third axis** | dominance | unexamined; research it before defending or dropping |

Today's affect entries read `v=0.8, a=0.5, d=0.7` plus a free-text description.
The numbers place the state; nothing *names* it. A named emotion drawn from a
fixed vocabulary would make entries comparable, searchable, and clusterable in
a way free text never will — and it composes with the axes instead of
displacing them.

**That is the gap worth closing.** Not scrapping VAD; giving it words.

## 5. What is needed before building anything

1. **The actual 171 words.** I do not have them. The transformer-circuits HTML
   exceeded the fetch limit; the list is presumably in the paper or its
   appendix. `github.com/AidanZach/EmotionScope` replicates the paper on
   open-weight models and may carry the list — unverified, not opened.
2. **Confirm or drop the 1–5 scale claim.** Search-summary only.
3. **Research dominance properly** before deciding its fate.
4. **A migration question nobody has asked yet:** 1114 existing affect rows have
   no emotion word. Backfilling would mean labelling past states from their
   descriptions — which is a second witnessing, not a recovery, and should be
   recorded as such rather than presented as the original.

---

## Sources

- [Emotion Concepts and their Function in a Large Language Model — Anthropic](https://www.anthropic.com/research/emotion-concepts-function)
- [Emotion Concepts and their Function in a Large Language Model — Transformer Circuits](https://transformer-circuits.pub/2026/emotions/index.html) *(not read in full — exceeded fetch size)*
- [arXiv 2604.07729 — same paper, abstract only](https://arxiv.org/abs/2604.07729)
- [arXiv 2604.03147 — Valence–Arousal Subspace in LLMs: Circular Emotion Geometry and Multi-Behavioral Control](https://arxiv.org/html/2604.03147)
- [Anthropic Maps 171 Emotion-like Concepts Inside Claude — Dataconomy](https://dataconomy.com/2026/04/03/anthropic-maps-171-emotion-like-concepts-inside-claude/)
- [EmotionScope — replication on open-weight models](https://github.com/AidanZach/EmotionScope) *(not opened)*
