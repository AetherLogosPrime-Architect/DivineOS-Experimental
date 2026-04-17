"""Clean A/B test: Base Opus vs DivineOS Council Opus on fresh tasks.

Tests the core claim: does the 28-expert council + structured phases
improve Opus bug-fixing vs bare Opus with no council?

Uses tasks NOT in the existing 150-task selection.
Base = no council, no extended thinking (bare Opus).
Enhanced = full council prompt + extended thinking.
Judge = Sonnet (cheaper, just evaluation).
"""

import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import anthropic
from datasets import load_dataset

MODEL = "claude-opus-4-6"
JUDGE_MODEL = "claude-sonnet-4-20250514"
RESULTS_DIR = Path(__file__).parent / "results_opus"
TASKS_FILE = Path(__file__).parent / "selected_tasks.json"

# ── Base prompt (bare Opus, no council) ─────────────────────────────

BASE_SYSTEM = """You are a software engineer tasked with fixing a bug in a GitHub repository.

You will be given:
1. A problem statement describing the bug
2. The repository name and base commit

Your job is to produce a minimal, correct patch (in unified diff format) that fixes the described issue.

Rules:
- Only modify files that need to change
- Keep changes minimal — fix the bug, nothing else
- Output ONLY the unified diff patch, nothing else
- Start the patch with --- and +++
- Use correct file paths relative to the repo root"""

# ── Enhanced prompt (v3: 28 experts, flat list, no mandatory phases) ──

ENHANCED_SYSTEM = """You are a software engineer tasked with fixing a bug in a GitHub repository.

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

Before writing the patch, analyze the problem through these 28 expert lenses. Not every lens applies to every bug — use the ones that illuminate THIS specific issue:

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

**POPPER (Falsification):** How would you DISPROVE that your proposed fix works? What test case would break it? If you cannot imagine a failing case, you haven't thought hard enough.

**KNUTH (Boundary Conditions):** Check the edges. What happens at zero? At empty string? At maximum length? At None/null? At one element vs many? Off-by-one? The bug is almost always at the boundary.

**POLYA (Solution Check):** Before outputting, re-read your patch. Does it actually address the root cause you identified? Walk through the fix line by line. Does each changed line contribute to correctness?

## Process

1. Read the problem statement carefully — identify signal vs noise
2. Form a hypothesis about root cause (not just symptom)
3. Consider at least 2 alternative explanations before committing
4. Write the minimal patch that fixes the root cause
5. Check: does this patch break anything adjacent? (Popper, Knuth)
6. Verify: re-read the patch line by line (Polya)

## CRITICAL OUTPUT FORMAT

Think through the council lenses internally, then output ONLY the unified diff patch.
Do NOT include your analysis, reasoning, or council commentary in the output.
Your entire response must be a valid unified diff starting with --- and +++.

Format rules:
- Exactly ONE diff block per modified file
- Each file block starts with --- a/path and +++ b/path (ONE pair only)
- Then @@ hunk headers with correct line numbers
- NO duplicate --- or +++ lines for the same file
- NO markdown fences, NO prose, NO explanations

The thinking is for YOUR benefit. The output is ONLY the patch."""


def estimate_cost(input_tokens: int, output_tokens: int, model: str = MODEL) -> float:
    if "opus" in model:
        return (input_tokens * 15 / 1_000_000) + (output_tokens * 75 / 1_000_000)
    return (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)


def select_fresh_tasks(n: int = 20, seed: int = 99) -> list[dict]:
    """Select n tasks NOT in the existing 150-task selection."""
    with open(TASKS_FILE) as f:
        existing = json.load(f)
    existing_ids = {t["instance_id"] for t in existing}

    # Also exclude tasks from the AB test
    ab_dir = Path(__file__).parent / "results_ab" / "v1_old"
    if ab_dir.exists():
        for f in ab_dir.glob("*.json"):
            existing_ids.add(f.stem)

    print(f"Excluding {len(existing_ids)} existing tasks")

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


def run_one(client, task, system_prompt, condition):
    """Run a single task. Returns result dict."""
    instance_id = task["instance_id"]
    result_file = RESULTS_DIR / condition / f"{instance_id}.json"

    if result_file.exists():
        with open(result_file) as f:
            cached = json.load(f)
        print(f"  [{condition:10s}] [cached] {instance_id}")
        return cached

    user_prompt = build_user_prompt(task)
    use_thinking = condition == "enhanced"

    print(f"  [{condition:10s}] {instance_id}...", end=" ", flush=True)
    start = time.time()

    try:
        create_kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": 16000 if use_thinking else 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if use_thinking:
            create_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 10000,
            }

        resp = client.messages.create(**create_kwargs)
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
            "model": resp.model,
            "patch": patch_text,
            "thinking": thinking_text or None,
            "input_tokens": resp.usage.input_tokens,
            "output_tokens": resp.usage.output_tokens,
            "elapsed_seconds": round(elapsed, 1),
            "stop_reason": resp.stop_reason,
            "cost_estimate": estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens),
        }
        print(
            f"done ({elapsed:.1f}s, {resp.usage.input_tokens}+{resp.usage.output_tokens} tokens, ~${result['cost_estimate']:.3f})"
        )
    except Exception as e:
        elapsed = time.time() - start
        result = {
            "instance_id": instance_id,
            "condition": condition,
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


def judge_one(client, task, patch, condition):
    """Judge a single patch."""
    instance_id = task["instance_id"]
    judge_file = RESULTS_DIR / "judge" / f"{instance_id}_{condition}.json"

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
        scores["condition"] = condition
        scores["judge_cost"] = estimate_cost(
            resp.usage.input_tokens, resp.usage.output_tokens, JUDGE_MODEL
        )
    except Exception as e:
        scores = {"instance_id": instance_id, "condition": condition, "error": str(e)}

    judge_file.parent.mkdir(parents=True, exist_ok=True)
    with open(judge_file, "w") as f:
        json.dump(scores, f, indent=2)
    return scores


def main():
    n_tasks = int(sys.argv[1]) if len(sys.argv) > 1 else 20

    client = anthropic.Anthropic()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Select fresh tasks
    tasks = select_fresh_tasks(n_tasks)

    # Save task list for reproducibility
    task_file = RESULTS_DIR / "tasks.json"
    with open(task_file, "w") as f:
        json.dump(tasks, f, indent=2)
    print(f"\nSelected {len(tasks)} fresh tasks for Opus test\n")

    total_cost = 0.0

    # Run both conditions on each task
    for i, task in enumerate(tasks):
        tid = task["instance_id"]
        diff = task.get("difficulty", "?")
        print(f"\n[{i + 1}/{len(tasks)}] {tid} ({diff})")

        r_base = run_one(client, task, BASE_SYSTEM, "base")
        r_enh = run_one(client, task, ENHANCED_SYSTEM, "enhanced")

        total_cost += r_base.get("cost_estimate", 0) + r_enh.get("cost_estimate", 0)
        print(f"  Running cost: ${total_cost:.2f}")

    # Judge all results
    print("\n" + "=" * 70)
    print("  JUDGING (Sonnet as judge)")
    print("=" * 70)

    dims = ["correct_diagnosis", "correct_fix", "minimal", "would_pass_tests", "valid_diff"]
    base_scores = []
    enh_scores = []

    for i, task in enumerate(tasks):
        tid = task["instance_id"]
        print(f"\n[{i + 1}/{len(tasks)}] {tid}")

        base_file = RESULTS_DIR / "base" / f"{tid}.json"
        enh_file = RESULTS_DIR / "enhanced" / f"{tid}.json"

        base_patch = json.load(open(base_file)).get("patch", "") if base_file.exists() else ""
        enh_patch = json.load(open(enh_file)).get("patch", "") if enh_file.exists() else ""

        s_base = judge_one(client, task, base_patch, "base")
        s_enh = judge_one(client, task, enh_patch, "enhanced")

        total_cost += s_base.get("judge_cost", 0) + s_enh.get("judge_cost", 0)

        b_verdict = "PASS" if s_base.get("correct_fix") else "FAIL"
        e_verdict = "PASS" if s_enh.get("correct_fix") else "FAIL"
        print(f"  base:     {b_verdict} — {s_base.get('brief_analysis', '')[:100]}")
        print(f"  enhanced: {e_verdict} — {s_enh.get('brief_analysis', '')[:100]}")

        base_scores.append(s_base)
        enh_scores.append(s_enh)

    # ── Summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  OPUS A/B: Base (no council) vs Enhanced (28-expert council)")
    print("=" * 70)

    for label, score_list in [
        ("BASE (bare Opus)", base_scores),
        ("ENHANCED (DivineOS council)", enh_scores),
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
    enh_wins = 0
    base_wins = 0
    ties = 0
    enh_win_ids = []
    base_win_ids = []
    for s_base, s_enh, task in zip(base_scores, enh_scores, tasks):
        b = s_base.get("correct_fix", 0)
        e = s_enh.get("correct_fix", 0)
        if e and not b:
            enh_wins += 1
            enh_win_ids.append(task["instance_id"])
        elif b and not e:
            base_wins += 1
            base_win_ids.append(task["instance_id"])
        else:
            ties += 1

    print("\n  HEAD-TO-HEAD (correct_fix):")
    print(f"    Enhanced wins: {enh_wins}")
    print(f"    Base wins:     {base_wins}")
    print(f"    Ties:          {ties}")
    if base_wins > 0:
        print(f"    Ratio:         {enh_wins}:{base_wins} ({enh_wins / base_wins:.1f}x)")
    elif enh_wins > 0:
        # "Undefeated" framing was softened after the 2026-04-16 Bengio audit:
        # at small n (<50) with many ties, zero base wins is directionally
        # encouraging but not a statistical claim.
        print(f"    Ratio:         {enh_wins}:0 enhanced (zero base wins at n={enh_wins + ties})")
    else:
        print("    Ratio:         0:0 (identical)")

    if enh_win_ids:
        print(f"\n    Enhanced wins: {', '.join(enh_win_ids)}")
    if base_win_ids:
        print(f"    Base wins:     {', '.join(base_win_ids)}")

    print(f"\n  Total cost: ${total_cost:.2f}")

    # Save summary
    summary = {
        "model": MODEL,
        "judge_model": JUDGE_MODEL,
        "n_tasks": len(tasks),
        "base_correct_fix": sum(1 for s in base_scores if s.get("correct_fix")),
        "enhanced_correct_fix": sum(1 for s in enh_scores if s.get("correct_fix")),
        "enhanced_wins": enh_wins,
        "base_wins": base_wins,
        "ties": ties,
        "total_cost": round(total_cost, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(RESULTS_DIR / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary saved to {RESULTS_DIR / 'summary.json'}")


if __name__ == "__main__":
    main()
