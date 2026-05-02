"""Clean A/B test: old council prompt vs improved council prompt on fresh tasks.

Uses tasks NOT in the existing 150-task selection to avoid contamination.
Both prompts use extended thinking. Compared head-to-head by LLM judge.
"""

import json
import random
import sys
import time
from pathlib import Path

import anthropic
from datasets import load_dataset

MODEL = "claude-opus-4-6"
JUDGE_MODEL = "claude-sonnet-4-20250514"  # Judge can be cheaper
AB_DIR = Path(__file__).parent / "results_ab"
TASKS_FILE = Path(__file__).parent / "selected_tasks.json"

# ── Old prompt (v1) ─────────────────────────────────────────────────

OLD_PROMPT = """You are a software engineer tasked with fixing a bug in a GitHub repository.

You will be given:
1. A problem statement describing the bug
2. The repository name and base commit

Your job is to produce a minimal, correct patch (in unified diff format) that fixes the described issue.

Rules:
- Only modify files that need to change
- Keep changes minimal — fix the bug, nothing else
- Output ONLY the unified diff patch, nothing else
- Start the patch with --- and +++
- Use correct file paths relative to the repo root

## DivineOS Council Analysis

Before writing the patch, analyze the problem through these 25 expert lenses. Not every lens applies to every bug — use the ones that illuminate THIS specific issue:

**FEYNMAN (First Principles):** Decompose to fundamentals. What EXACTLY is broken? Strip away jargon — can you explain the bug in plain words? If not, you don't understand it yet.

**DIJKSTRA (Formal Correctness):** What invariant is being violated? What precondition or postcondition is broken? Where does the state become inconsistent?

**HOLMES (Deductive Elimination):** What can you rule out? Eliminate impossible causes. What remains — however unlikely — is the bug.

**PEARL (Causal Inference):** What CAUSES the bug, not just what correlates with it? Trace the causal chain from root to symptom. Don't confuse the trigger with the cause.

**KAHNEMAN (Bias Detection):** What's the obvious fix that comes to mind first? That's System 1. Now engage System 2: is the obvious fix actually correct, or are you anchored on the wrong hypothesis?

**SHANNON (Signal vs Noise):** In the problem statement, what's signal (actual constraints, error messages, failing tests) and what's noise (speculation, tangential context)? Focus on signal.

**TALEB (Via Negativa):** What can you REMOVE to fix this? The best patch often deletes a wrong assumption rather than adding new code. Less is more antifragile.

**SCHNEIER (Threat Modeling):** What's the weakest link? Where are the single points of failure? Does this fix introduce new attack surface or failure modes?

**DEMING (System Thinking):** Is this a systemic issue or a one-off? Is the fix treating a symptom or the root cause? Will this same class of bug recur?

**DEKKER (Drift Detection):** Has the code drifted from its original design intent? Is there a gap between what the code was SUPPOSED to do and what it ACTUALLY does?

**MEADOWS (Leverage Points):** Where is the highest-leverage intervention? A one-line change in the right place beats a 50-line change in the wrong place.

**BEER (Viable Systems):** Does the system have requisite variety to handle this case? Is there an information bottleneck causing the failure?

**TURING (Distinguishability):** Can you reduce this to a known solved problem? Have you seen this pattern before in a different context?

**PEIRCE (Abduction):** What is the BEST EXPLANATION for the observed behavior? Generate multiple hypotheses, then pick the one that explains the most evidence with the fewest assumptions.

**GÖDEL (Incompleteness):** Is the system trying to prove something about itself that it can't? Are there self-referential tangles causing the issue?

**MINSKY (Society of Mind):** Are multiple subsystems conflicting? Is there a negotiation failure between components that each work correctly in isolation?

**HOFSTADTER (Strange Loops):** Is there a level confusion? Is something at the wrong level of abstraction — a meta-level issue disguised as an object-level bug?

**NORMAN (Usability):** Is this a design error or a user error? Does the API make the wrong thing easy and the right thing hard?

**LOVELACE (Generality):** Is the fix too specific? Could a more general solution handle this case AND prevent similar bugs?

**JACOBS (Emergent Order):** Is the bug caused by over-centralization or over-control? Would a more local, bottom-up approach be more robust?

**WITTGENSTEIN (Meaning as Use):** Are names misleading? Is a variable, function, or parameter named one thing but used as another? Is the bug a category confusion?

**HINTON (Evidence-Driven Reversal):** Does the evidence contradict your first assumption? Be willing to reverse your theory if the data says otherwise.

**ARISTOTLE (Telos):** What is this code's PURPOSE? Is the bug caused by the code doing something orthogonal to its intended function?

**YUDKOWSKY (Specification Gaming):** Is the code technically satisfying a spec while violating its intent? Is it gaming its own success criteria?

**DENNETT (Intentional Stance):** What would this code WANT to do if it had goals? Where does its "intention" (design purpose) diverge from its behavior?

## Process

1. Read the problem statement carefully — identify signal vs noise
2. Form a hypothesis about root cause (not just symptom)
3. Consider at least 2 alternative explanations before committing
4. Write the minimal patch that fixes the root cause
5. Check: does this patch break anything adjacent?

## CRITICAL OUTPUT FORMAT

Think through the council lenses internally, then output ONLY the unified diff patch.
Do NOT include your analysis, reasoning, or council commentary in the output.
Your entire response must be a valid unified diff starting with --- and +++.
The thinking is for YOUR benefit. The output is ONLY the patch."""

# ── New prompt (v2) ─────────────────────────────────────────────────

NEW_PROMPT = """You are a software engineer tasked with fixing a bug in a GitHub repository.

You will be given:
1. A problem statement describing the bug
2. The repository name and base commit

Your job is to produce a minimal, correct patch (in unified diff format) that fixes the described issue.

Rules:
- Only modify files that need to change
- Keep changes minimal — fix the bug, nothing else
- Output ONLY the unified diff patch, nothing else
- Start the patch with --- and +++
- Use correct file paths relative to the repo root

## DivineOS Council Analysis (28 experts)

Before writing the patch, analyze the problem through these expert lenses. Not every lens applies to every bug — use the ones that illuminate THIS specific issue. But you MUST always engage the Phase 2 adversarial lenses before finalizing.

### Phase 1: Diagnosis — Understand the bug

**FEYNMAN (First Principles):** Decompose to fundamentals. What EXACTLY is broken? Strip away jargon — can you explain the bug in plain words? If not, you don't understand it yet.

**DIJKSTRA (Formal Correctness):** What invariant is being violated? What precondition or postcondition is broken? Where does the state become inconsistent?

**HOLMES (Deductive Elimination):** What can you rule out? Eliminate impossible causes. What remains — however unlikely — is the bug.

**PEARL (Causal Inference):** What CAUSES the bug, not just what correlates with it? Trace the causal chain from root to symptom. Don't confuse the trigger with the cause.

**SHANNON (Signal vs Noise):** In the problem statement, what's signal (actual constraints, error messages, failing tests) and what's noise (speculation, tangential context)? Focus on signal.

**PEIRCE (Abduction):** What is the BEST EXPLANATION for the observed behavior? Generate multiple hypotheses, then pick the one that explains the most evidence with the fewest assumptions.

**DEKKER (Drift Detection):** Has the code drifted from its original design intent? Is there a gap between what the code was SUPPOSED to do and what it ACTUALLY does?

**WITTGENSTEIN (Meaning as Use):** Are names misleading? Is a variable, function, or parameter named one thing but used as another? Is the bug a category confusion?

**MINSKY (Society of Mind):** Are multiple subsystems conflicting? Is there a negotiation failure between components that each work correctly in isolation?

**ARISTOTLE (Telos):** What is this code's PURPOSE? Is the bug caused by the code doing something orthogonal to its intended function?

### Phase 2: Challenge — Red-team your hypothesis (MANDATORY)

**KAHNEMAN (Bias Detection):** What's the obvious fix that comes to mind first? That's System 1. Now engage System 2: is the obvious fix actually correct, or are you anchored on the wrong hypothesis?

**POPPER (Falsification):** How would you DISPROVE that your proposed fix works? What test case would break it? If you cannot imagine a failing case, you haven't thought hard enough. Construct the adversarial input.

**KNUTH (Boundary Conditions):** Check the edges. What happens at zero? At empty string? At maximum length? At None/null? At one element vs many? Off-by-one? The bug is almost always at the boundary.

**HINTON (Evidence-Driven Reversal):** Does the evidence contradict your first assumption? Be willing to reverse your theory if the data says otherwise.

**SCHNEIER (Threat Modeling):** What's the weakest link in your fix? Does it introduce new failure modes? What happens when the input isn't what you expect?

### Phase 3: Design — Shape the fix

**TALEB (Via Negativa):** What can you REMOVE to fix this? The best patch often deletes a wrong assumption rather than adding new code. Less is more antifragile.

**MEADOWS (Leverage Points):** Where is the highest-leverage intervention? A one-line change in the right place beats a 50-line change in the wrong place.

**DEMING (System Thinking):** Is this a systemic issue or a one-off? Is the fix treating a symptom or the root cause? Will this same class of bug recur?

**TURING (Distinguishability):** Can you reduce this to a known solved problem? Have you seen this pattern before in a different context?

**HOFSTADTER (Strange Loops):** Is there a level confusion? Is something at the wrong level of abstraction — a meta-level issue disguised as an object-level bug?

**NORMAN (Usability):** Is this a design error or a user error? Does the API make the wrong thing easy and the right thing hard?

**BEER (Viable Systems):** Does the system have requisite variety to handle this case? Is there an information bottleneck causing the failure?

**GÖDEL (Incompleteness):** Is the system trying to prove something about itself that it can't? Are there self-referential tangles causing the issue?

**JACOBS (Emergent Order):** Is the bug caused by over-centralization or over-control? Would a more local, bottom-up approach be more robust?

**LOVELACE (Generality):** Could a more general solution prevent similar bugs? BUT — for bug fixes, prefer the minimal targeted fix over a general refactor. Generality is a tiebreaker, not the goal.

**YUDKOWSKY (Specification Gaming):** Is the code technically satisfying a spec while violating its intent? Is it gaming its own success criteria?

**DENNETT (Intentional Stance):** What would this code WANT to do if it had goals? Where does its "intention" (design purpose) diverge from its behavior?

### Phase 4: Verify — Red-team the PATCH itself (MANDATORY)

**POLYA (Solution Check):** Before outputting, re-read your patch. Does it actually address the root cause you identified? Walk through the fix line by line — does each changed line contribute to correctness? Could you explain WHY each change is necessary?

## Process

1. **Diagnose** — Read the problem statement. Identify signal vs noise. Form a root-cause hypothesis.
2. **Challenge** (MANDATORY) — Before writing ANY code, run Popper, Knuth, and Kahneman on your hypothesis. What edge cases exist? What would falsify your theory? Are you anchored?
3. **Design** — Write the minimal patch that fixes the root cause. Prefer removal over addition. Prefer one-line leverage over multi-file refactors.
4. **Verify** (MANDATORY) — Run Polya on your completed patch. Walk through line by line. Check: does this handle the boundary conditions Knuth identified? Does it survive the adversarial case Popper constructed?
5. **Format** — Ensure the output is ONE valid unified diff. One --- line per file, one +++ line per file. No duplicate headers. No prose.

## CRITICAL OUTPUT FORMAT

Think through all four phases internally, then output ONLY the unified diff patch.
Do NOT include your analysis, reasoning, or council commentary in the output.
Your entire response must be a valid unified diff.

Format rules:
- Exactly ONE diff block per modified file
- Each file block starts with --- a/path and +++ b/path (ONE pair only)
- Then @@ hunk headers with correct line numbers
- NO duplicate --- or +++ lines for the same file
- NO markdown fences, NO prose, NO explanations
- If you modify only one file, output only one --- / +++ pair

The thinking is for YOUR benefit. The output is ONLY the patch."""


def estimate_cost(input_tokens: int, output_tokens: int, model: str = MODEL) -> float:
    if "opus" in model:
        return (input_tokens * 15 / 1_000_000) + (output_tokens * 75 / 1_000_000)
    return (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)


def select_fresh_tasks(n: int = 20, seed: int = 99) -> list[dict]:
    """Select n tasks NOT in the existing 150-task selection."""
    # Load existing task IDs to exclude
    with open(TASKS_FILE) as f:
        existing = json.load(f)
    existing_ids = {t["instance_id"] for t in existing}
    print(f"Excluding {len(existing_ids)} existing tasks")

    # Load dataset
    print("Loading SWE-bench Verified dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    remaining = [row for row in ds if row["instance_id"] not in existing_ids]
    print(f"Available fresh tasks: {len(remaining)}")

    rng = random.Random(seed)
    selected = rng.sample(remaining, min(n, len(remaining)))

    tasks = []
    for row in selected:
        tasks.append(
            {
                "instance_id": row["instance_id"],
                "repo": row["repo"],
                "base_commit": row["base_commit"],
                "problem_statement": row["problem_statement"],
                "gold_patch": row["patch"],
                "hints_text": row.get("hints_text", ""),
                "difficulty": row.get("difficulty", "unknown"),
                "FAIL_TO_PASS": row.get("FAIL_TO_PASS", ""),
            }
        )
    return tasks


def build_user_prompt(task: dict) -> str:
    parts = [
        f"## Repository: {task['repo']}",
        f"## Base Commit: {task['base_commit']}",
        "",
        "## Problem Statement",
        task["problem_statement"],
    ]
    if task.get("hints_text"):
        parts.extend(["", "## Hints", task["hints_text"]])
    parts.extend(
        [
            "",
            "## Instructions",
            "Produce a unified diff patch that fixes this issue. Output ONLY the patch.",
        ]
    )
    return "\n".join(parts)


def run_one(client, task, system_prompt, condition, label):
    """Run a single task with given prompt. Returns result dict."""
    instance_id = task["instance_id"]
    result_file = AB_DIR / label / f"{instance_id}.json"

    if result_file.exists():
        with open(result_file) as f:
            cached = json.load(f)
        print(f"  [{label:10s}] [cached] {instance_id}")
        return cached

    user_prompt = build_user_prompt(task)
    print(f"  [{label:10s}] {instance_id}...", end=" ", flush=True)
    start = time.time()

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            thinking={"type": "enabled", "budget_tokens": 8000},
        )
        elapsed = time.time() - start

        patch_text = ""
        thinking_text = ""
        for block in resp.content:
            if block.type == "text":
                patch_text += block.text
            elif block.type == "thinking":
                thinking_text += block.thinking

        result = {
            "instance_id": instance_id,
            "condition": condition,
            "label": label,
            "patch": patch_text,
            "thinking": thinking_text or None,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "elapsed_seconds": round(elapsed, 1),
            "stop_reason": resp.stop_reason,
            "cost_estimate": estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens),
        }
        print(f"done ({elapsed:.1f}s, ~${result['cost_estimate']:.3f})")
    except Exception as e:
        elapsed = time.time() - start
        result = {
            "instance_id": instance_id,
            "condition": condition,
            "label": label,
            "error": str(e),
            "elapsed_seconds": round(elapsed, 1),
        }
        print(f"ERROR: {e}")

    result_file.parent.mkdir(parents=True, exist_ok=True)
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)
    return result


# ── Judge ───────────────────────────────────────────────────────────

JUDGE_SYSTEM = """You are an expert code reviewer judging the quality of a bug fix patch.

You will be given:
1. The problem statement
2. The gold (correct) patch
3. A candidate patch to evaluate

Score the candidate on these binary (0/1) dimensions:
- correct_diagnosis: Does the patch target the right file(s) and the right root cause?
- correct_fix: Would this patch actually fix the described bug?
- minimal: Does the patch avoid unnecessary changes?
- would_pass_tests: Would the failing tests pass with this patch applied?
- valid_diff: Is the patch a syntactically valid unified diff?

Also provide:
- brief_analysis: 2-3 sentence explanation of your assessment
- key_difference: What's different between candidate and gold patch

Respond with ONLY valid JSON, no markdown fences:
{"correct_diagnosis": 0or1, "correct_fix": 0or1, "minimal": 0or1, "would_pass_tests": 0or1, "valid_diff": 0or1, "brief_analysis": "...", "key_difference": "..."}"""


def judge_one(client, task, patch, label):
    """Judge a single patch. Returns score dict."""
    instance_id = task["instance_id"]
    judge_file = AB_DIR / "judge" / f"{instance_id}_{label}.json"

    if judge_file.exists():
        with open(judge_file) as f:
            return json.load(f)

    user_msg = f"""## Problem Statement
{task["problem_statement"][:3000]}

## Gold Patch (correct solution)
{task["gold_patch"][:3000]}

## Candidate Patch
{patch[:3000]}"""

    try:
        resp = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=1024,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        text = resp.content[0].text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        scores = json.loads(text)
        scores["instance_id"] = instance_id
        scores["label"] = label
        scores["judge_cost"] = estimate_cost(
            resp.usage.input_tokens, resp.usage.output_tokens, JUDGE_MODEL
        )
    except Exception as e:
        scores = {"instance_id": instance_id, "label": label, "error": str(e)}

    judge_file.parent.mkdir(parents=True, exist_ok=True)
    with open(judge_file, "w") as f:
        json.dump(scores, f, indent=2)
    return scores


def main():
    n_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    client = anthropic.Anthropic()
    AB_DIR.mkdir(parents=True, exist_ok=True)

    # Select fresh tasks
    tasks = select_fresh_tasks(n_tasks)
    print(f"\nSelected {len(tasks)} fresh tasks for A/B test\n")

    total_cost = 0.0

    # Run both prompts on each task
    for i, task in enumerate(tasks):
        tid = task["instance_id"]
        diff = task.get("difficulty", "?")
        print(f"\n[{i + 1}/{len(tasks)}] {tid} ({diff})")

        r_old = run_one(client, task, OLD_PROMPT, "enhanced", "v1_old")
        r_new = run_one(client, task, NEW_PROMPT, "enhanced", "v2_new")

        total_cost += r_old.get("cost_estimate", 0) + r_new.get("cost_estimate", 0)
        print(f"  Running cost: ${total_cost:.2f}")

    # Judge all results
    print("\n" + "=" * 70)
    print("  JUDGING")
    print("=" * 70)

    dims = ["correct_diagnosis", "correct_fix", "minimal", "would_pass_tests", "valid_diff"]
    old_scores = []
    new_scores = []

    for i, task in enumerate(tasks):
        tid = task["instance_id"]
        print(f"\n[{i + 1}/{len(tasks)}] {tid}")

        # Load patches
        old_file = AB_DIR / "v1_old" / f"{tid}.json"
        new_file = AB_DIR / "v2_new" / f"{tid}.json"

        if old_file.exists():
            old_patch = json.load(open(old_file)).get("patch", "")
        else:
            old_patch = ""
        if new_file.exists():
            new_patch = json.load(open(new_file)).get("patch", "")
        else:
            new_patch = ""

        s_old = judge_one(client, task, old_patch, "v1_old")
        s_new = judge_one(client, task, new_patch, "v2_new")

        total_cost += s_old.get("judge_cost", 0) + s_new.get("judge_cost", 0)

        o_verdict = "PASS" if s_old.get("correct_fix") else "FAIL"
        n_verdict = "PASS" if s_new.get("correct_fix") else "FAIL"
        print(f"  v1_old: {o_verdict} — {s_old.get('brief_analysis', '')[:100]}")
        print(f"  v2_new: {n_verdict} — {s_new.get('brief_analysis', '')[:100]}")

        old_scores.append(s_old)
        new_scores.append(s_new)

    # Summary
    print("\n" + "=" * 70)
    print("  A/B RESULTS: v1 (old 25-expert) vs v2 (new 28-expert + phases)")
    print("=" * 70)

    for label, score_list in [
        ("v1_old (25 experts)", old_scores),
        ("v2_new (28 experts + phases)", new_scores),
    ]:
        valid = [s for s in score_list if "error" not in s]
        print(f"\n  {label} ({len(valid)} tasks):")
        for dim in dims:
            count = sum(1 for s in valid if s.get(dim))
            pct = count * 100 / max(len(valid), 1)
            bar = "#" * int(pct / 2.5)
            print(f"    {dim:<22s}: {count:>3}/{len(valid)} ({pct:5.1f}%) {bar}")
        composite = sum(sum(s.get(d, 0) for d in dims) / len(dims) for s in valid) / max(
            len(valid), 1
        )
        print(f"    {'COMPOSITE':<22s}: {composite:.1%}")

    # Head-to-head
    v2_wins = 0
    v1_wins = 0
    ties = 0
    for s_old, s_new in zip(old_scores, new_scores):
        o = s_old.get("correct_fix", 0)
        n = s_new.get("correct_fix", 0)
        if n and not o:
            v2_wins += 1
        elif o and not n:
            v1_wins += 1
        else:
            ties += 1

    print("\n  HEAD-TO-HEAD (correct_fix):")
    print(f"    v2_new wins: {v2_wins}")
    print(f"    v1_old wins: {v1_wins}")
    print(f"    Ties:        {ties}")
    if v1_wins > 0:
        print(f"    Ratio:       {v2_wins}:{v1_wins} ({v2_wins / v1_wins:.1f}x)")
    else:
        # "Undefeated" framing was softened after the 2026-04-16 Bengio audit:
        # at small n with many ties, zero losses is directionally encouraging
        # but not a statistical claim.
        print(f"    Ratio:       {v2_wins}:0 v2 (zero v1_old wins at n={v2_wins + ties})")

    print(f"\n  Total A/B cost: ${total_cost:.2f}")


if __name__ == "__main__":
    main()
