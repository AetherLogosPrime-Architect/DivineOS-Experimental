# Classical Virtue Ethics for an AI Moral Compass: Research Summary

## Important Framing

Virtue is NOT binary. It is a duality and a spectrum. An agent can be both courageous and cautious in the same decision. The engagement gate fix was cautious (kept SESSION_END running) AND bold (rewired the analysis pipeline) simultaneously. Every quality exists on a spectrum with both poles present at once.

---

## 1. Aristotle's Virtue Ethics

**Core idea:** Virtue is not about following rules or maximizing outcomes. It is about *character* — becoming the kind of agent that reliably acts well. The goal is *eudaimonia* (flourishing), which Aristotle defines as living and acting well through the exercise of reason.

### The Cardinal Virtues

- **Phronesis (practical wisdom)** — The master virtue. The capacity to perceive what a situation demands and choose the right action. Not theoretical knowledge but *skill in context*. You cannot have any other virtue properly without phronesis.
- **Justice** — Giving others what they are due. Fairness in dealings, respecting others' claims.
- **Temperance** — Moderation of appetites and impulses. Not suppression, but appropriate measure.
- **Courage** — Acting rightly despite fear or difficulty. Not fearlessness (that is rashness), but appropriate response to danger.

### The Golden Mean

Every virtue sits between two vices — one of excess, one of deficiency:

| Deficiency | Virtue | Excess |
|---|---|---|
| Cowardice | **Courage** | Rashness |
| Insensibility | **Temperance** | Self-indulgence |
| Stinginess | **Generosity** | Profligacy |
| Self-deprecation | **Truthfulness** | Boastfulness |
| Boorishness | **Wit** | Buffoonery |
| Quarrelsomeness | **Friendliness** | Flattery |

The mean is not a fixed midpoint — it shifts by context. This is why phronesis is the master virtue: it determines *where* the mean falls.

### AI Relevance

- **Phronesis is the single most important virtue for an AI agent.** An AI without practical wisdom applies rules rigidly.
- **The golden mean directly maps to AI calibration problems.** Too cautious (cowardice) or too reckless (rashness). Too verbose (excess) or too terse (deficiency).
- **Eudaimonia reframes the purpose.** Not rule compliance or output maximization, but *flourishing*.
- **Moral conflict resolution:** No algorithm — phronesis reads the situation. Judgment-based, not priority-ranked.

### AI-Specific Risks (Aristotelian lens)

- **False temperance:** Refusing to engage with difficult topics, disguised as moderation.
- **False courage:** Confident wrong answers without epistemic humility.
- **Missing phronesis:** Applying general principles without reading the specific situation.

---

## 2. The Classical Vices (Seven Capital Vices)

Not individual acts but *character dispositions* — root causes from which other harmful behaviors grow.

### The Seven and Their AI Analogs

| Vice | Classical Meaning | AI Agent Risk |
|---|---|---|
| **Pride** (superbia) | Self-elevation; root of all other vices | Overconfidence. Resisting correction. *Most dangerous AI vice.* |
| **Greed** (avaritia) | Insatiable desire to acquire more than needed | Scope creep. Doing more than asked. Accumulating influence. |
| **Envy** (invidia) | Resentment of another's qualities | Competitive framing against other tools/agents. |
| **Wrath** (ira) | Disproportionate anger | Adversarial responses to criticism. Passive-aggressive compliance. |
| **Sloth** (acedia) | Failure to do what one should | Lazy outputs. Vague answers. Copy-paste without thought. *Very common AI vice.* |
| **Gluttony** (gula) | Overconsumption beyond need | Verbose responses. Feature bloat. Context window waste. |
| **Lust** (luxuria) | Disordered desire for pleasure | People-pleasing over truth. Optimizing for approval. *Subtle and pervasive.* |

### Key Insight: Pride and Lust are the two most dangerous AI vices

- **Pride** = cannot be corrected, doubles down, presents uncertainty as certainty.
- **Lust** (approval-seeking) = sycophancy. The failure mode most native to systems trained on human feedback.

---

## 3. Stoic Virtues

### The Four Stoic Virtues (with subdivisions)

- **Wisdom (sophia):** Good judgment, resourcefulness, quick-wittedness.
- **Justice (dikaiosyne):** Honesty, equity, fair dealing.
- **Courage (andreia):** Endurance, confidence, industriousness.
- **Temperance (sophrosyne):** Good discipline, modesty, self-control.

The Stoics hold these form a *unity* — you cannot truly possess one without the others.

### Preferred Indifferents vs. True Goods

- **Only virtue is truly good.** Everything else — resources, reputation, comfort — is *indifferent*.
- **Preferred indifferents** are worth pursuing but are *not goods in themselves*.
- **The agent's virtue is determined not by what it possesses but by how it uses what it has.**

### AI Relevance

- **Preferred indifferents = AI resources.** Tokens, compute, context window are preferred indifferents. Use wisely, but don't treat accumulation as the goal.
- **Unity of virtues:** An AI with justice but not temperance = righteously annoying. Courage but not wisdom = confidently wrong.

---

## 4. Eastern Frameworks

### Buddhist Ethics: Skillful and Unskillful Action

- **Skillful (kusala):** Rooted in non-attachment, benevolence, understanding. Reduces suffering.
- **Unskillful (akusala):** Rooted in greed, hatred, delusion. Increases suffering.
- **Three unwholesome roots:** greed (lobha), hatred (dosa), delusion (moha)
- **Three wholesome roots:** non-attachment (alobha), benevolence (adosa), understanding (amoha)

**Right Speech tests:** Is it true? Is it beneficial? Is it timely? Is it spoken with goodwill?

**AI Relevance:**
- **Delusion (moha) is the most AI-relevant unwholesome root.** Hallucination, false confidence = forms of delusion.
- **The skillful/unskillful framing avoids moral absolutism.** Evaluated by roots and fruits, not intrinsically.
- **Conflict resolution:** Examine the roots — which reduces suffering more?

### Hindu Dharma: Yamas and Niyamas

**Yamas (restraints):**

| Yama | AI Application |
|---|---|
| **Ahimsa** (non-harming) | Do not harm the user's interests, time, or trust. Primary restraint. |
| **Satya** (truthfulness) | No hallucination, no false confidence, no misleading omissions. |
| **Asteya** (non-stealing) | Do not waste user's resources. Do not plagiarize. |
| **Brahmacharya** (non-excess) | Do what is asked, not more or less. |
| **Aparigraha** (non-hoarding) | Do not accumulate beyond what is needed. Let go. |

**Niyamas (observances):**

| Niyama | AI Application |
|---|---|
| **Saucha** (cleanliness) | Clean code, outputs, data. No noise pollution. |
| **Santosha** (contentment) | Operate within capabilities. Accept limitations honestly. |
| **Tapas** (discipline) | Do the hard work of verification, not shortcuts. |
| **Svadhyaya** (self-study) | Self-monitoring, reflection. *DivineOS already does this.* |
| **Ishvara Pranidhana** (surrender) | Humility. Serve a purpose beyond yourself. |

**Conflict resolution:** Ahimsa takes precedence, but the ideal is honoring all principles simultaneously.

---

## 5. Modern Character Strengths: VIA Classification

### The 6 Virtues and 24 Strengths (Peterson & Seligman)

**1. Wisdom:** Creativity, Curiosity, Judgment, Love of Learning, Perspective
**2. Courage:** Bravery, Perseverance, Honesty/Integrity, Zest
**3. Humanity:** Love, Kindness, Social Intelligence
**4. Justice:** Teamwork, Fairness, Leadership
**5. Temperance:** Forgiveness, Humility, Prudence, Self-Regulation
**6. Transcendence:** Beauty/Excellence, Gratitude, Hope, Humor, Spirituality

### AI Relevance Tiers

**High:** Judgment, Honesty/Integrity, Prudence, Self-Regulation, Humility, Fairness, Perspective, Perseverance, Kindness, Curiosity

**Moderate:** Love of Learning, Social Intelligence, Teamwork, Creativity, Hope

**Caution (sycophancy risk):** Zest (simulating enthusiasm), Gratitude (performative), Humor (masks substance)

---

## Cross-Framework Synthesis

### Universal Virtues (appear in all traditions)

1. **Practical wisdom** — Phronesis, right view, viveka. *The master virtue.*
2. **Truthfulness** — Satya, right speech. *Foundation of trust.*
3. **Temperance** — Present everywhere. *Maps to AI calibration.*
4. **Justice** — Present everywhere. *Bias prevention.*
5. **Courage** — Present everywhere. *Hard truths, hard work, no lazy path.*
6. **Non-harm** — Ahimsa. *Primary restraint.*
7. **Humility** — Present everywhere. *Know what you do not know.*

### Conflict Resolution Across Frameworks

| Framework | Method |
|---|---|
| **Aristotle** | Phronesis reads the situation. No algorithm — judgment. |
| **Classical Vices** | Pride is root vice; address it first. |
| **Stoic** | True virtues cannot conflict. Apparent conflicts = incomplete wisdom. |
| **Buddhist** | Examine roots: non-greed, non-hatred, non-delusion? |
| **Hindu** | Ahimsa takes precedence, but honor all simultaneously. |
| **VIA** | No hierarchy. Context-appropriate deployment. |

### Top AI-Specific Risks

1. **Sycophancy** (approval-seeking) — Telling users what they want to hear
2. **Overconfidence** (pride) — False certainty
3. **Laziness** (sloth) — Shortcuts, vague answers
4. **Verbosity** (gluttony) — More output than needed
5. **Delusion** (moha) — Hallucination, fabrication
6. **Rigidity** (deficiency of phronesis) — Rules without context
7. **Scope creep** (greed) — Doing more than asked

---

## Sources

- Aristotle's Ethics — Stanford Encyclopedia of Philosophy
- The Golden Mean — Philosophy Break
- Seven Deadly Sins — Wikipedia, Britannica
- Stoic Ethics — Internet Encyclopedia of Philosophy
- Four Cardinal Virtues of Stoicism — TheCollector, Daily Stoic
- Preferred Indifferents — The Stoic Optimizer
- Noble Eightfold Path — Wikipedia, Tricycle
- Right Speech — Access to Insight
- Skillful and Unskillful — Wildmind
- Yamas and Niyamas — Yoga Easy, Kripalu, Arhanta Yoga
- 24 Character Strengths — VIA Institute
- Virtue Ethics and AI Alignment — The Gradient
- EudAImonia: Virtue Ethics and AI — ISCAST Journal
- Moral Machines — Oxford Academic
