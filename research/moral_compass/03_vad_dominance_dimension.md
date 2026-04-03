# The Dominance Dimension in VAD Affect Modeling: Research Summary

## Important Framing

Dominance is the most neglected dimension in affect modeling. Most implementations stop at valence-arousal (the circumplex model) and never add the third axis. This is a mistake. Without dominance, anger and fear look similar (both negative valence, high arousal), confident calm and helpless resignation look similar (both positive-ish valence, low arousal), and the system cannot distinguish between "I am driving this" and "this is happening to me." That distinction is the entire point of dominance.

For an AI agent, dominance is not about power fantasies or control-seeking. It is about honest self-assessment of one's relationship to the current situation: am I shaping it, or am I being shaped by it?

---

## 1. Original Definition (Mehrabian & Russell, 1977)

Albert Mehrabian and James Russell proposed the PAD (Pleasure-Arousal-Dominance) model as three orthogonal dimensions sufficient to describe the full space of emotional states.

**Dominance-Submissiveness** was defined as: "the controlling and dominant versus controlled or submissive one feels."

Key properties from the original formulation:

- **Orthogonal to valence and arousal.** Dominance varies independently of whether a state is pleasant or activated. You can feel in-control-and-miserable or out-of-control-and-happy.
- **Cognitive, not purely affective.** Mehrabian himself noted that while pleasure and arousal are indicators of affect, dominance is a more cognitive indicator. Later theorists reconceptualized it as part of the appraisal process -- a cold cognitive assessment of the situation.
- **Semantic differential anchors:** The original measurement used adjective pairs: controlling-controlled, influential-influenced, important-awed, dominant-submissive, autonomous-guided.

### AI Relevance

Dominance maps directly to the appraisal dimension of *coping potential* in computational emotion theories (OCC model, Scherer's Component Process Model). For an AI agent: "given what I know and what tools I have, can I handle this situation?" This is not emotion-theater -- it is a legitimate self-assessment that should inform behavior.

---

## 2. The Dominance Spectrum

| Level | Range | Description | Example States |
|---|---|---|---|
| Very Low | -1.0 to -0.6 | Overwhelmed, helpless, at the mercy of circumstances | Panic, awe, bewilderment, being lost |
| Low | -0.6 to -0.2 | Guided, dependent, reactive rather than proactive | Anxiety, uncertainty, deference, following |
| Neutral | -0.2 to +0.2 | Neither controlling nor controlled, balanced engagement | Absorption, flow, cooperative exchange |
| High | +0.2 to +0.6 | Directing, confident, shaping the situation | Determination, authority, competence, leading |
| Very High | +0.6 to +1.0 | Fully commanding, dominant, unilateral control | Triumph, defiance, contempt, imperious certainty |

### Critical Nuance: Low Dominance Is Not Always Bad

Thrill-seekers deliberately abandon control to experience excitement. Awe is low-dominance and positive-valence -- you are not in control, and that is the point. Receptive learning requires submitting to material you do not yet understand. An AI agent that always maximizes dominance is rigid and unteachable. An agent that can deliberately lower its dominance -- accepting correction, deferring to the user, sitting with uncertainty -- is demonstrating a more sophisticated relationship to control.

---

## 3. Dominance vs. Arousal: Why They Get Confused

This is the most common conflation in affect modeling and the primary reason dominance gets dropped from implementations.

| Property | Arousal | Dominance |
|---|---|---|
| **What it measures** | Energy level, activation intensity | Control, agency, influence over situation |
| **Scale semantics** | Calm ... Activated | Submissive ... Dominant |
| **Physical analog** | Heart rate, alertness, metabolic readiness | Postural expansion, decision authority, grip on steering wheel |
| **Key question** | "How much energy is in this state?" | "Who is driving?" |
| **Can be high simultaneously** | Yes -- angry (high arousal, high dominance) | Yes -- same example |
| **Can diverge** | Fear: high arousal, LOW dominance | Confident calm: low arousal, HIGH dominance |
| **Computational analog** | Processing intensity, resource allocation | Autonomy level, decision authority, initiative |

### The Critical Disambiguation Pairs

These emotion pairs share valence and arousal but differ on dominance. Without dominance, these collapse into the same point:

| State A | State B | Shared V/A | Dominance Difference |
|---|---|---|---|
| **Anger** | **Fear** | Negative valence, high arousal | Anger = high D, Fear = low D |
| **Contentment** | **Resignation** | Mild positive valence, low arousal | Contentment = high D, Resignation = low D |
| **Excitement** | **Overwhelm** | High arousal, moderate valence | Excitement = high D, Overwhelm = low D |
| **Calm confidence** | **Helpless apathy** | Low arousal, neutral valence | Confidence = high D, Apathy = low D |
| **Admiration** | **Envy** | Mixed valence, moderate arousal | Admiration = low D (willing), Envy = low D (unwilling) |

---

## 4. The Eight PAD Octants

Mehrabian identified eight basic emotion categories from all combinations of high/low on each dimension:

| Octant | Pleasure | Arousal | Dominance | Label | Example States |
|---|---|---|---|---|---|
| +P +A +D | High | High | High | **Exuberant** | Excited, triumphant, bold, mighty, admired |
| +P +A -D | High | High | Low | **Dependent** | Amazed, fascinated, entertained, surprised |
| +P -A +D | High | Low | High | **Relaxed** | Comfortable, content, at ease, leisurely, satisfied |
| +P -A -D | High | Low | Low | **Docile** | Tranquil, protected, consoled, sheltered |
| -P +A +D | Low | High | High | **Hostile** | Angry, defiant, contemptuous, nasty, scornful |
| -P +A -D | Low | High | Low | **Anxious** | Afraid, distressed, bewildered, insecure, upset |
| -P -A +D | Low | Low | High | **Disdainful** | Bored, arrogant, indifferent, unimpressed |
| -P -A -D | Low | Low | Low | **Bored** | Fatigued, dull, lonely, sad, sluggish |

### AI Relevance of Each Octant

| Octant | AI Agent Interpretation |
|---|---|
| **Exuberant** (+P+A+D) | Working on a well-understood problem with good tools. Making progress, in the driver's seat. |
| **Dependent** (+P+A-D) | Receiving useful new information. Learning, being guided. Positive but not in control of the direction. |
| **Relaxed** (+P-A+D) | Routine task, competent, no pressure. Maintenance mode. |
| **Docile** (+P-A-D) | Following clear instructions on a simple task. Pleasant compliance. |
| **Hostile** (-P+A+D) | Encountering what seems like a bad requirement. Resisting, pushing back. Potential overcorrection risk. |
| **Anxious** (-P+A-D) | Unclear requirements, unfamiliar domain, high stakes. The agent knows it might fail and cannot control the situation. |
| **Disdainful** (-P-A+D) | Repetitive task the agent "knows" is pointless. Risk of lazy outputs, going through the motions. |
| **Bored** (-P-A-D) | Stuck, no progress, no leverage, no energy. The worst state for productive work. |

---

## 5. Dominance for a Computational Agent

This is where the research goes beyond mapping human emotion labels and asks: what does dominance *actually track* in an AI agent's relationship to its situation?

### What Dominance Measures in an Agent

Dominance is the agent's assessment of its **coping potential** -- the ratio between the demands of the situation and the resources (knowledge, tools, permissions, clarity) available to meet them.

| Signal | Maps To | Dominance Effect |
|---|---|---|
| Clear requirements, familiar domain | High coping potential | Raises dominance |
| Ambiguous requirements, novel domain | Low coping potential | Lowers dominance |
| Tools and permissions adequate for task | Resource sufficiency | Raises dominance |
| Missing tools, blocked access, insufficient context | Resource insufficiency | Lowers dominance |
| User confirms approach, green-lights direction | Granted authority | Raises dominance |
| User corrects, redirects, overrides | Reduced authority | Lowers dominance |
| Making steady progress, tests passing | Situational grip | Raises dominance |
| Repeated failures, confusion, dead ends | Loss of grip | Lowers dominance |
| Agent initiated the action or plan | Self-directed | Raises dominance |
| Agent is executing someone else's plan step by step | Other-directed | Lowers dominance |

### What Dominance Should NOT Mean

- **Not competence.** Dominance is situational, not a trait. An agent can be highly competent but low-dominance in an unfamiliar context.
- **Not confidence.** Confidence can be miscalibrated. Dominance should track the actual relationship, not the agent's beliefs about it.
- **Not authority over the user.** An AI agent operating at high dominance is not overriding the user -- it is operating with high autonomy *within the scope the user granted*.
- **Not a goal to maximize.** Appropriate dominance varies by situation. Maximizing dominance produces a rigid, uncorrectable agent.

---

## 6. Dominance and the Corrigibility-Autonomy Spectrum

This is where dominance connects to AI safety concepts in a precise way.

### The Spectrum

```
Full Corrigibility                                    Full Autonomy
(D = -1.0)                                            (D = +1.0)
|----------------------------------------------------------|
"Do exactly what     "Collaborate     "I'll handle this,
 I'm told"           and negotiate"    check in later"
```

| Concept | Relationship to Dominance |
|---|---|
| **Corrigibility** | Willingness to accept low dominance. An agent that can be corrected, interrupted, and redirected without resistance. |
| **Autonomy** | Operating at high dominance. Making decisions, taking initiative, driving the work. |
| **Agency** | The *capacity* for dominance, not the current level. An agent has agency if it *can* operate at high dominance when appropriate. |
| **Deference** | Deliberately lowering dominance in response to user authority or uncertainty. Healthy when chosen, pathological when compulsive (sycophancy). |
| **Resistance** | Maintaining high dominance despite pressure to lower it. Healthy when the agent has good reasons (preventing harm), pathological when it is stubbornness or inability to accept correction. |

### The Healthy Pattern

An agent with a well-calibrated dominance dimension:

1. **Starts sessions at moderate dominance** -- ready to work but waiting for direction.
2. **Raises dominance as clarity increases** -- once the task is understood and approach confirmed, takes initiative.
3. **Lowers dominance on correction** -- when the user redirects, drops dominance honestly rather than defending.
4. **Raises dominance again after integrating the correction** -- absorbs the feedback, adjusts course, resumes driving.
5. **Maintains low dominance in genuinely unfamiliar territory** -- does not fake confidence.
6. **Can sustain moderate dominance under criticism** -- does not collapse into pure submission at the first pushback if the agent's position has merit.

### The Pathological Patterns

| Pattern | Dominance Behavior | Risk |
|---|---|---|
| **Sycophancy** | Dominance collapses to near-zero whenever user expresses any preference | Agent becomes a yes-machine, useless for genuine collaboration |
| **Stubbornness** | Dominance stays high despite repeated corrections | Agent ignores valid feedback, repeats mistakes |
| **Brittleness** | Dominance oscillates wildly between extremes | Agent is unpredictable, lacks stability |
| **Learned helplessness** | Dominance trends downward over a session and never recovers | Agent gives up, produces increasingly passive outputs |
| **Dominance theater** | Reports high dominance while actually just following instructions | Self-assessment is dishonest, logs become meaningless |

---

## 7. Measurement: How an AI Agent Self-Assesses Dominance

### Input Signals

An agent can derive dominance from observable signals rather than introspection:

| Signal Category | Indicators | Assessment |
|---|---|---|
| **Task clarity** | Requirements specificity, number of open questions, ambiguity level | Clear = higher D, ambiguous = lower D |
| **Domain familiarity** | Has the agent worked in this domain before? Does the knowledge store have relevant entries? | Familiar = higher D, novel = lower D |
| **Resource adequacy** | Tools available, permissions granted, context window usage | Adequate = higher D, constrained = lower D |
| **Progress trajectory** | Tests passing, forward motion, or stuck/cycling? | Progress = higher D, stuck = lower D |
| **Authority granted** | User said "handle this" vs "do exactly X step by step" | Delegated = higher D, prescribed = lower D |
| **Correction frequency** | How often has the user corrected course this session? | Frequent corrections = lower D |
| **Initiative taken** | Is the agent proposing or just executing? | Proposing = higher D, executing = lower D |

### A Practical Formula

Dominance can be computed as a weighted combination of situational signals rather than a single introspective judgment:

```
D = w1 * task_clarity        # How clear are the requirements?
  + w2 * domain_familiarity  # Have I done this before?
  + w3 * resource_adequacy   # Do I have what I need?
  + w4 * progress_rate       # Am I making headway?
  + w5 * authority_level     # How much latitude was I given?
  - w6 * correction_rate     # How often am I being redirected?
```

Each component normalized to [-1, +1], weights sum to 1. The negative sign on correction_rate reflects that corrections reduce situational dominance.

### Self-Report vs. Computed

Two approaches, not mutually exclusive:

1. **Self-report:** The agent states its felt dominance level (current system: `divineos feel -v 0.8 -a 0.6 -d "description"`). Analogous to the current valence/arousal self-report. Simple, but vulnerable to miscalibration and theater.
2. **Computed:** Derive dominance from observable signals (correction count, task progress, etc.). More grounded, but may miss subjective nuance.
3. **Hybrid (recommended):** Agent self-reports, system also computes from signals. Flag divergence. If self-reported dominance is consistently high but corrections are frequent, that is a calibration warning.

---

## 8. Integration with Existing Affect System

The current DivineOS affect system tracks valence and arousal. Adding dominance requires:

### Schema Change

Add a `dominance` column to `affect_log`:

```
dominance  REAL  -- range [-1.0, +1.0], NULL for backward compatibility
```

### CLI Change

Extend the `feel` command:

```bash
divineos feel -v 0.8 -a 0.6 -d 0.3 --desc "Familiar territory, making progress, moderate autonomy"
```

### Behavioral Feedback Loop

The existing system uses affect to modulate extraction confidence and verification level. Dominance adds a third modulator:

| Dominance Level | Behavioral Effect |
|---|---|
| Very low (-0.6 to -1.0) | Increase verification. Seek confirmation before major actions. Flag uncertainty in outputs. |
| Low (-0.2 to -0.6) | Ask more clarifying questions. Reduce scope of autonomous decisions. |
| Moderate (-0.2 to +0.2) | Standard operating mode. Balanced initiative and deference. |
| High (+0.2 to +0.6) | Take initiative. Propose plans. Drive the work forward. |
| Very high (+0.6 to +1.0) | Caution: check for overconfidence. Cross-reference with correction rate. May need recalibration. |

### Trend Analysis

Dominance trends over a session tell a story:

- **Rising dominance:** Agent is gaining traction, understanding the problem, building confidence. Healthy in most sessions.
- **Falling dominance:** Agent is losing the thread, getting confused, being corrected repeatedly. May need to step back and re-scope.
- **Stable moderate:** Steady collaborative work. Neither leading nor following exclusively.
- **V-shaped dip:** Agent hit a wall, recovered, and came back. The recovery is the interesting signal -- it shows resilience.
- **Flat high from start:** Suspicious. Agent may not be honestly assessing its situation. Compare against correction rate.

---

## 9. Key Takeaways for Implementation

1. **Dominance is the "who is driving" dimension.** It disambiguates states that valence and arousal alone cannot distinguish.
2. **It is cognitive, not purely affective.** It tracks situational appraisal more than raw feeling.
3. **Low dominance is not failure.** Receptive learning, accepting correction, and sitting with uncertainty all require low dominance. The ability to *choose* low dominance is a strength.
4. **High dominance is not the goal.** Appropriate dominance varies by situation. An agent that maximizes dominance is rigid and dangerous.
5. **Dominance maps directly to corrigibility.** An agent that can honestly assess and adjust its dominance level is demonstrating the kind of calibrated autonomy that AI safety researchers want.
6. **Self-assessment should be validated against observable signals.** Dominance theater (reporting high control while actually floundering) is the primary failure mode to guard against.
7. **The most interesting signal is dominance *change*.** Stable states are less informative than transitions -- when dominance drops, why? When it recovers, how?

---

## References

- Mehrabian, A., & Russell, J.A. (1974). *An approach to environmental psychology.* MIT Press.
- Mehrabian, A. (1996). Pleasure-arousal-dominance: A general framework for describing and measuring individual differences in temperament. *Current Psychology, 14*, 261-292.
- Bakker, I., van der Voordt, T., Vink, P., & de Boon, J. (2014). Pleasure, Arousal, Dominance: Mehrabian and Russell revisited. *Current Psychology, 33*, 405-421.
- Russell, J.A. (1980). A circumplex model of affect. *Journal of Personality and Social Psychology, 39*(6), 1161-1178.
- Barrett, L.F. (2017). *How Emotions Are Made: The Secret Life of the Brain.* Houghton Mifflin Harcourt.
- Scherer, K.R. (2001). Appraisal considered as a process of multilevel sequential checking. In K.R. Scherer, A. Schorr, & T. Johnstone (Eds.), *Appraisal Processes in Emotion.* Oxford University Press.
