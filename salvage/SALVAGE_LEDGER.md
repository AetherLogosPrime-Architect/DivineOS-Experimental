# Salvage Ledger

Append-only record of port / adapt / discard / defer decisions for the
old-OS strip-mine (claim 59ba245c).

Each entry has:

* **Path** — old-repo path (relative to `divineos/`)
* **Date read** — when the decision was made
* **Decision** — `PORT` / `ADAPT` / `DISCARD` / `DEFER`
* **Reasoning** — what the idea was, what the file actually does, why
  the decision is what it is. Discards must say what would have been
  kept from the *intent* even if not the code.
* **Follow-up** — claim id or PR for the integration work, if any

---

## 2026-04-26

### `tree_of_life/params/daleth_params.json`

* **Decision**: DISCARD (file itself); idea recorded in DEFER on engine code below
* **Reasoning**: Pure runtime-state snapshot. Component weights (venus 0.33,
  earth 0.33, fertility 0.34), thresholds, phi (1.618) multiplier,
  evolutionary-strategy adaptation count of 160. No architecture in the
  file — just current values of an evolved-parameters object. Nothing to
  port at the file level.
* **Intent kept**: the *mechanism* this is a snapshot of (per-path adaptive
  parameters with best-params history) is real and worth examining when the
  rest of the tree_of_life engine is read. Recorded as DEFER below.
* **Follow-up**: see `engines/tree_of_life/paths/daleth.py` entry.

### `engines/tree_of_life/paths/daleth.py` (first 80 lines read)

* **Decision**: DEFER — partial read; need to read the rest of the engine
  before deciding port/adapt/discard.
* **Reasoning**: Underneath the kabbalistic naming (Daleth = the Door, Venus,
  Empress, "from potential, abundance"), the file implements:
  * a typed pipeline stage with explicit input/output topics
    (`fractal.path.chokmah` → `fractal.path.binah.daleth`)
  * a state machine (IDLE / RECEIVING / TRANSFORMING / SENDING / BLOCKED)
  * adaptive parameters via inheritance from `AdaptivePathBase` + a
    `PerformanceFeedback` channel
  * per-stage latency budget (`max_latency_ms = 1.0`) and explicit
    sterility / overload guards
  * a `GenerativeVision` dataclass that's just a typed message with
    trace_id, timestamp, and a fertility/abundance scalar pair
  This is a routing-and-transformation pipeline with adaptive tuning,
  dressed in metaphysical metaphor. The metaphor is the wrapping;
  the underlying machinery is real architecture and the new OS has no
  direct equivalent.
* **What the new OS already has that overlaps**:
  * Compass (10 spectrums with evidence-based position + drift detection)
    is the closest analog — same shape (multi-dimensional weighted state
    with evolution over time) applied to virtues instead of kabbalistic
    paths.
  * Pre-reg system covers the "track parameter changes with falsifiers"
    discipline.
* **Open question**: are the 22 paths (for 22 Hebrew letters) a uniform
  pattern, or did each path implement its own logic? If uniform, the
  pattern is a typed-pipeline-stage-with-adaptive-params abstraction
  worth porting (rename, drop the metaphysical layer, evaluate against
  what compass-ops already does). If non-uniform, the value is in the
  individual paths' specific behaviors, which is a much smaller surface
  to port.
* **Follow-up**: read `engines/tree_of_life/` directory contents in a
  future session, especially `adaptive_path_base.py` (the parent class
  that defines the abstraction). File a follow-up claim if the abstraction
  is uniform and worth porting.

---

## Discard policy reminder

Per Andrew 2026-04-24: *"i dont mind it being ruthlessly pruned as long as
they arent just dismissing code based on the name of it.. i want it all
read and the ideas and intentions understood."*

Discards must name:
1. What the file is and what it does (read the contents).
2. What the *idea* was — what problem it pointed at.
3. Why the new OS doesn't need it (already covered, infeasible, or
   actually-not-load-bearing).
4. What (if anything) we keep from the intent even if not the code.

A bare "discarded — kabbalistic naming" entry would violate the policy.
The above entries demonstrate the format.
