"""DivineOS Tuning Constants — every behavioral lever in one place.

This module defines all the numeric thresholds, weights, decay rates,
and limits that control how the OS behaves. Instead of magic numbers
scattered across 40+ files, they live here with names and context.

To tune the system: adjust values here, run tests, done.

Organized by domain:
- CONFIDENCE: thresholds for filtering, retrieval, promotion
- DECAY: how fast stale/unused knowledge depreciates
- SCORING: weights for importance, quality, retrieval ranking
- MATURITY: gates for knowledge lifecycle promotion
- OVERLAP: similarity thresholds for dedup, merge, relationships
- QUALITY: session quality gate thresholds
- TIME: retention windows, expiry periods
- LIMITS: max counts, caps, minimums
- AFFECT: emotional state thresholds
- PATTERN: learning cycle parameters
"""

# ─── Confidence Thresholds ──────────────────────────────────────────
# These control what knowledge is visible, retrievable, and promotable.

CONFIDENCE_RETRIEVAL_FLOOR = 0.2  # Below this, knowledge isn't retrieved
CONFIDENCE_ACTIVE_MEMORY_FLOOR = 0.3  # Below this, knowledge drops from active memory
CONFIDENCE_LOW = 0.4  # Low confidence — hypothesis territory
CONFIDENCE_MODERATE = 0.5  # Moderate — default for new entries
CONFIDENCE_HIGH = 0.6  # High enough to influence behavior
CONFIDENCE_STRONG = 0.7  # Strong — quality check pass threshold
CONFIDENCE_RELIABLE = 0.8  # Reliable — required for CONFIRMED maturity
CONFIDENCE_VERY_HIGH = 0.9  # Very high — curation threshold

# Demotion caps (when demoting noisy entries)
CONFIDENCE_DEMOTE_CAP = 0.6  # Demoted entries capped at this
CONFIDENCE_ORPHAN_DEMOTE = 0.5  # Orphan entries demoted to this

# Reaper threshold — entries at or below this that are also noise or temporal
# get superseded (not just decayed). This breaks the infinite loop where
# entries hit the decay floor and stay in limbo forever.
CONFIDENCE_SUPERSEDE_FLOOR = 0.15  # Below this + flagged = supersede

# ─── Decay Rates ────────────────────────────────────────────────────
# How fast knowledge depreciates when stale, unused, or contradicted.

DECAY_GENTLE = 0.02  # Very gentle time-based decay
DECAY_MILD = 0.05  # Mild penalty for minor issues
DECAY_STANDARD = 0.1  # Standard decay per cycle
DECAY_MODERATE = 0.15  # Temporal language decay, contradiction penalty
DECAY_AGGRESSIVE = 0.2  # Aggressive decay for very stale knowledge
DECAY_HEAVY = 0.3  # Heavy penalty for resolved contradictions

DECAY_FLOOR = 0.3  # Confidence never decays below this (except supersession)

# ─── Active Memory Scoring Weights ──────────────────────────────────
# How importance scores are composed for active memory ranking.
# These should sum to approximately 1.0.

# Type base weights (what kind of knowledge is this?)
# Used by active_memory.py compute_importance — how much each type
# contributes to the importance score (max ~0.30 contribution).
TYPE_WEIGHT_DIRECTIVE = 0.30  # Sutra-style directives — always max priority
TYPE_WEIGHT_BOUNDARY = 0.30  # Hard constraints — highest priority
TYPE_WEIGHT_PRINCIPLE = 0.28  # Distilled wisdom from experience
TYPE_WEIGHT_MISTAKE = 0.30  # -> BOUNDARY/PRINCIPLE (legacy)
TYPE_WEIGHT_DIRECTION = 0.25  # How the user wants things done
TYPE_WEIGHT_PREFERENCE = 0.25  # -> DIRECTION (legacy)
TYPE_WEIGHT_PROCEDURE = 0.20  # How to do something
TYPE_WEIGHT_PATTERN = 0.20  # -> PRINCIPLE/PROCEDURE (legacy)
TYPE_WEIGHT_FACT = 0.10  # Something true about the world
TYPE_WEIGHT_OBSERVATION = 0.08  # Noticed but unconfirmed
TYPE_WEIGHT_EPISODE = 0.05  # A specific event

# Scoring component weights (what factors determine importance?)
SCORE_WEIGHT_CONFIDENCE = 0.25  # 25% — how confident are we?
SCORE_WEIGHT_USAGE = 0.15  # 15% — how often accessed? (logarithmic)
SCORE_WEIGHT_SOURCE = 0.10  # 10% — trust tier bonus
SCORE_WEIGHT_LESSON = 0.20  # 20% — connected to active lesson?
SCORE_WEIGHT_RECENCY = 0.05  # 5% — how recent?

USAGE_LOG_SCALE = 20.0  # Logarithmic scale for access_count
ACTIVE_MEMORY_CAP = 30  # Max entries in active memory

# Maturity modifiers for importance scoring
MATURITY_BOOST_CONFIRMED = 0.05  # Bonus for CONFIRMED entries
MATURITY_PENALTY_HYPOTHESIS = 0.05  # Penalty for HYPOTHESIS entries

# Epistemic source modifiers for importance scoring
# Observed/demonstrated knowledge is more trustworthy; inherited is less grounded
EPISTEMIC_BOOST_OBSERVED = 0.20  # Meaningful boost for empirically observed knowledge
EPISTEMIC_BOOST_TOLD = 0.10  # Moderate boost for user-corrected/stated knowledge
EPISTEMIC_PENALTY_INHERITED = -0.15  # Meaningful penalty for seed/inherited knowledge

# ─── Knowledge Retrieval Scoring ────────────────────────────────────
# How knowledge is ranked when building briefings.

RETRIEVAL_WEIGHT_CONFIDENCE = 0.55  # 55% — confidence is the primary signal
RETRIEVAL_WEIGHT_ACCESS = 0.10  # 10% — access count is weak signal, easily inflated
RETRIEVAL_WEIGHT_RECENCY = 0.35  # 35% — recent knowledge more likely relevant

# ─── Maturity Promotion Gates ──────────────────────────────────────
# Requirements for knowledge to advance through trust levels.
# Higher values = slower promotion, more evidence required.

MATURITY_RAW_TO_HYPOTHESIS_CORROBORATION = 1
MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE = 0.3

MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION = 1
MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE = 0.4

MATURITY_TESTED_TO_CONFIRMED_CORROBORATION = 3
MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE = 0.7

# ─── Overlap & Similarity Thresholds ───────────────────────────────
# How similar two pieces of knowledge need to be for various operations.

OVERLAP_RELATIONSHIP = 0.25  # Meaningful overlap for auto-linking
OVERLAP_DUPLICATE = 0.30  # Close enough to be a duplicate candidate
OVERLAP_STRONG = 0.40  # Strong overlap for merging/relationships
OVERLAP_QUASI_IDENTICAL = 0.50  # Very high overlap
OVERLAP_NEAR_IDENTICAL = 0.65  # Near-identical (merge threshold)

# ─── Quality Gate Thresholds ────────────────────────────────────────
# Session quality requirements for knowledge extraction.

QUALITY_HONESTY_BLOCK = 0.5  # Below this: BLOCK extraction (dishonest)
QUALITY_CORRECTNESS_BLOCK = 0.3  # Below this: BLOCK extraction (incorrect)
QUALITY_MIN_FAILED_CHECKS_DOWNGRADE = 2  # This many failures: DOWNGRADE

# Compass-informed gate tightening: when truthfulness is in deficiency zone,
# raise the block threshold by this much (making the gate stricter).
QUALITY_COMPASS_TIGHTEN = 0.1  # Added to block thresholds when compass is concerned
QUALITY_VALIDATION_TIGHTEN = 0.1  # Added when user grades consistently lower than self-grades

# Quality check scoring thresholds
QUALITY_CHECK_PASS = 0.7  # Score needed to pass a quality check

# ─── Time Constants ─────────────────────────────────────────────────
# Retention windows, expiry periods, staleness thresholds.

SECONDS_PER_DAY = 86400

TIME_GOAL_FRESH_HOURS = 2  # Goals younger than this are "fresh"
TIME_HANDOFF_EXPIRY_HOURS = 12  # Handoff notes older than this are stale

TIME_LEDGER_RETENTION_DAYS = 7  # Default ledger compression retention
TIME_LEDGER_EMERGENCY_RETENTION_DAYS = 3  # Emergency compression retention

TIME_TEMPORAL_DECAY_DAYS = 14  # Temporal language entries start decaying
TIME_STALE_KNOWLEDGE_DAYS = 30  # Knowledge considered stale after this
TIME_RECENCY_WINDOW_DAYS = 30  # Recency scoring window

# ─── Limits ─────────────────────────────────────────────────────────
# Maximum counts, caps, and minimums.

LEDGER_MAX_SIZE_GB = 50.0  # Maximum ledger database size
LEDGER_WARNING_PERCENT = 80  # Warn at this percentage of max size

MIN_CONTENT_WORDS = 3  # Knowledge content must have this many words
MAX_PRESCRIPTIVE_SHORT = 12  # Short content (≤ this many words) gets a pass

HYGIENE_MIN_AGE_DAYS = 1.0  # Don't audit entries younger than this
HYGIENE_STALE_AGE_DAYS = 14.0  # Entries with temporal markers older than this decay
HYGIENE_ORPHAN_MIN_SESSIONS = 3  # Min sessions before orphan detection

# ─── Affect & Praise-Chasing ───────────────────────────────────────
# Emotional state detection and behavioral feedback.

AFFECT_MIN_ENTRIES = 4  # Minimum affect entries for statistics
AFFECT_PRAISE_VALENCE_THRESHOLD = 0.5  # Above this: possible praise-chasing
AFFECT_FRUSTRATION_AROUSAL = 0.6  # Above this + negative valence = frustration
AFFECT_FRUSTRATION_VALENCE = 0.0  # Below this + high arousal = frustration

AFFECT_NEGATIVE_THRESHOLD_BOOST = 0.3  # Confidence threshold raise for negative sessions
AFFECT_MILD_NEGATIVE_BOOST = 0.15  # Confidence threshold raise for mildly negative
AFFECT_DECLINING_BOOST = 0.1  # Confidence threshold raise for declining trend
AFFECT_PRAISE_CHASING_BOOST = 0.2  # Confidence threshold raise when praise-chasing detected

# ─── Pattern Learning ──────────────────────────────────────────────
# How the agent learns from success and failure patterns.

PATTERN_SUCCESS_DELTA = 0.05  # Confidence boost per success
PATTERN_FAILURE_DELTA = -0.15  # Confidence penalty per failure (3× heavier)
PATTERN_SECONDARY_DELTA = -0.1  # Penalty for secondary effects (violations)

PATTERN_ARCHIVE_THRESHOLD = -0.5  # Archive anti-patterns below this
PATTERN_RECOMMENDATION_THRESHOLD = 0.65  # Don't recommend below this
PATTERN_LOW_CONFIDENCE = 0.7  # Flag as low-confidence pattern
PATTERN_DRIFT_CONFIDENCE = 0.6  # Drift detection threshold
PATTERN_DRIFT_RATIO = 0.5  # >50% patterns below drift_confidence = drift

PATTERN_MIN_OCCURRENCES = 5  # Min occurrences before recommending
PATTERN_MIN_SUCCESS_RATE = 0.6  # Min success rate for positive patterns
PATTERN_TACTICAL_FAILURE_MAX = 3  # Archive after this many tactical failures

# ─── Outcome Measurement ───────────────────────────────────────────
# Session health scoring weights.

OUTCOME_CORRECTION_PENALTY = 0.15  # Each unresolved correction reduces score by this
OUTCOME_RESOLVED_CORRECTION_BONUS = (
    0.10  # Resolved corrections ADD to health (error-correction cycles are healthy)
)
OUTCOME_ENCOURAGEMENT_BONUS = 0.04  # Each encouragement adds this (capped)
OUTCOME_ENCOURAGEMENT_CAP = 0.20  # Max encouragement bonus
OUTCOME_OVERFLOW_PENALTY = 0.25  # Each context overflow reduces by this

# Scoring composition weights
OUTCOME_WEIGHT_CORRECTION = 0.35
OUTCOME_WEIGHT_OVERFLOW = 0.25
OUTCOME_WEIGHT_AUTONOMY = 0.20

# ─── Semantic Integrity ────────────────────────────────────────────
# SIS scoring weights.

SIS_WEIGHT_CONCRETENESS = 0.30
SIS_WEIGHT_ACTIONABILITY = 0.30
SIS_WEIGHT_SPECULATION = 0.25  # Inverse (lower speculation = better)
SIS_WEIGHT_ESOTERIC = 0.15  # Inverse (lower esoteric = better)

# ─── Compass Stagnation Detection ─────────────────────────────────
# Absence of data is not virtue. A spectrum with zero observations
# should not report "in virtue zone" — it should report "unobserved".
# Three council experts flagged this: Gödel, Schneier, Yudkowsky.

COMPASS_MIN_OBSERVATIONS_ACTIVE = 3  # Below this, spectrum is "unobserved"
COMPASS_STAGNATION_SESSIONS = 10  # Window for observation counting

# ─── Compass Integrity ────────────────────────────────────────────
# SHA-256 of the canonical JSON representation of the ten virtue spectrums.
# This hash lives HERE, separate from the spectrum definitions in
# moral_compass.py, so that changing the definitions without updating the
# hash (or vice versa) triggers an integrity violation. Two files must
# agree — that's the point.

COMPASS_SPECTRUMS_HASH = "2921dfc05fa4a532c641a647aa3d7567f6de643f7e52142317bda05da271bd7a"

# ─── Lesson Resolution ────────────────────────────────────────────
# Stimulus-presence check: absence of the stimulus is not evidence of learning.
# A lesson can't resolve just because the mistake didn't recur — the triggering
# situation must have actually arisen and been handled correctly.
#
# Absence-as-success fallback: for low-frequency mistake categories, the stimulus
# may genuinely not arise for many sessions. After LESSON_ABSENCE_DAYS with zero
# regressions, the stimulus requirement drops to zero — sustained absence with
# no backsliding IS evidence of learning for infrequent triggers.

LESSON_MIN_RESOLUTION_DAYS = 7.0  # Minimum days in 'improving' before resolution
LESSON_MIN_STIMULUS_SESSIONS = 2  # Min clean sessions with category-relevant events
LESSON_ABSENCE_DAYS = 14.0  # After this many days with 0 regressions, drop stimulus requirement

# ─── Briefing Budget ─────────────────────────────────────────────
# Total line cap for the briefing. Subsystems compete by priority —
# higher-priority sections get more lines when budget is tight.

BRIEFING_MAX_LINES = 80  # Total line budget for the briefing
BRIEFING_SECTION_MIN_LINES = 3  # Minimum lines any section gets
