"""SWE-bench A/B Harness — Base Claude vs DivineOS-Enhanced Claude.

Runs SWE-bench Verified tasks through the Anthropic API twice:
  1. Base: minimal system prompt (Anthropic's own scaffold)
  2. Enhanced: DivineOS directives, lessons, and quality principles injected

Compares patch quality to measure whether DivineOS context improves coding.
"""

import json
import time
from pathlib import Path
from typing import Any

import anthropic
from datasets import load_dataset

# --- Config ---
MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
RESULTS_DIR = Path(__file__).parent / "results"
TASKS_FILE = Path(__file__).parent / "selected_tasks.json"


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


# --- System Prompts ---

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


def load_tasks(n: int = 20, seed: int = 42) -> list[dict[str, Any]]:
    """Load n tasks from SWE-bench Verified, deterministically sampled."""
    if TASKS_FILE.exists():
        with open(TASKS_FILE) as f:
            tasks = json.load(f)
        print(f"Loaded {len(tasks)} cached tasks from {TASKS_FILE}")
        return tasks

    print("Loading SWE-bench Verified dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    # Deterministic sample using hash-based selection
    all_ids = sorted([row["instance_id"] for row in ds])
    import random

    rng = random.Random(seed)
    selected_ids = set(rng.sample(all_ids, min(n, len(all_ids))))

    tasks = []
    for row in ds:
        if row["instance_id"] in selected_ids:
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

    # Cache for reproducibility
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)
    print(f"Selected and cached {len(tasks)} tasks")
    return tasks


def build_user_prompt(task: dict) -> str:
    """Build the user message for a task."""
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


def run_task(
    client: anthropic.Anthropic,
    task: dict,
    system_prompt: str,
    condition: str,
) -> dict:
    """Run a single task and return the result."""
    instance_id = task["instance_id"]
    result_file = RESULTS_DIR / condition / f"{instance_id}.json"

    # Skip if already done
    if result_file.exists():
        with open(result_file) as f:
            cached = json.load(f)
        print(f"  [cached] {instance_id} ({condition})")
        return cached

    user_prompt = build_user_prompt(task)

    print(f"  [running] {instance_id} ({condition})...", end=" ", flush=True)
    start = time.time()

    try:
        # Enhanced condition uses extended thinking so council analysis
        # happens in the thinking block and only the patch comes out
        use_thinking = condition == "enhanced"

        create_kwargs: dict[str, Any] = {
            "model": MODEL,
            "max_tokens": 16000 if use_thinking else MAX_TOKENS,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if use_thinking:
            create_kwargs["thinking"] = {
                "type": "enabled",
                "budget_tokens": 8000,
            }

        resp = client.messages.create(**create_kwargs)
        elapsed = time.time() - start

        # Extract text (skip thinking blocks)
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
            "thinking": thinking_text if thinking_text else None,
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

    # Save result
    result_file.parent.mkdir(parents=True, exist_ok=True)
    with open(result_file, "w") as f:
        json.dump(result, f, indent=2)

    return result


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost in USD for Sonnet 4.6."""
    # Sonnet: $3/M input, $15/M output
    return (input_tokens * 3 / 1_000_000) + (output_tokens * 15 / 1_000_000)


def score_patch(generated: str, gold: str) -> dict:
    """Basic patch similarity scoring.

    Full SWE-bench scoring requires Docker + running tests.
    This is a lightweight proxy: checks if the generated patch
    touches the same files and has overlapping content.
    """

    def extract_files(patch_text: str) -> set[str]:
        files = set()
        for line in patch_text.split("\n"):
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                f = line.split("/", 1)[-1] if "/" in line else line[4:]
                if f and f != "/dev/null":
                    files.add(f.strip())
        return files

    def extract_changes(patch_text: str) -> set[str]:
        changes = set()
        for line in patch_text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("+") and not stripped.startswith("+++"):
                changes.add(stripped[1:].strip())
            elif stripped.startswith("-") and not stripped.startswith("---"):
                changes.add(stripped[1:].strip())
        return changes

    gen_files = extract_files(generated)
    gold_files = extract_files(gold)
    gen_changes = extract_changes(generated)
    gold_changes = extract_changes(gold)

    file_overlap = len(gen_files & gold_files) / max(len(gold_files), 1)
    change_overlap = (
        len(gen_changes & gold_changes) / max(len(gold_changes), 1) if gold_changes else 0
    )

    # Exact match (normalized whitespace)
    def normalize(s: str) -> str:
        return "\n".join(line.rstrip() for line in s.strip().split("\n"))

    exact = normalize(generated) == normalize(gold)

    return {
        "exact_match": exact,
        "file_overlap": round(file_overlap, 3),
        "change_overlap": round(change_overlap, 3),
        "files_correct": gen_files == gold_files,
        "gen_files": sorted(gen_files),
        "gold_files": sorted(gold_files),
    }


def run_benchmark(n_tasks: int = 20) -> dict:
    """Run the full A/B benchmark."""
    client = get_client()
    tasks = load_tasks(n_tasks)

    print(f"\n{'=' * 60}")
    print(f"  SWE-bench A/B Benchmark: {len(tasks)} tasks")
    print(f"  Model: {MODEL}")
    print("  Conditions: base vs enhanced (DivineOS)")
    print(f"{'=' * 60}\n")

    all_results = {"base": [], "enhanced": []}
    total_cost = 0.0

    for i, task in enumerate(tasks):
        print(f"\n[{i + 1}/{len(tasks)}] {task['instance_id']} ({task['difficulty']})")

        # Run base
        base_result = run_task(client, task, BASE_SYSTEM, "base")
        all_results["base"].append(base_result)

        # Run enhanced
        enhanced_result = run_task(client, task, ENHANCED_SYSTEM, "enhanced")
        all_results["enhanced"].append(enhanced_result)

        # Track cost
        for r in [base_result, enhanced_result]:
            total_cost += r.get("cost_estimate", 0)

        print(f"  Running cost: ${total_cost:.2f}")

    # Score
    print(f"\n{'=' * 60}")
    print("  SCORING")
    print(f"{'=' * 60}\n")

    scores = {"base": [], "enhanced": []}
    for condition in ["base", "enhanced"]:
        for result in all_results[condition]:
            task = next(t for t in tasks if t["instance_id"] == result["instance_id"])
            if "error" in result:
                scores[condition].append({"instance_id": result["instance_id"], "error": True})
                continue

            s = score_patch(result.get("patch", ""), task["gold_patch"])
            s["instance_id"] = result["instance_id"]
            scores[condition].append(s)

    # Summary
    print(f"\n{'=' * 60}")
    print("  RESULTS")
    print(f"{'=' * 60}\n")

    for condition in ["base", "enhanced"]:
        valid = [s for s in scores[condition] if "error" not in s]
        exact = sum(1 for s in valid if s["exact_match"])
        files_correct = sum(1 for s in valid if s["files_correct"])
        avg_file_overlap = sum(s["file_overlap"] for s in valid) / len(valid) if valid else 0
        avg_change_overlap = sum(s["change_overlap"] for s in valid) / len(valid) if valid else 0

        label = "BASE (bare Claude)" if condition == "base" else "ENHANCED (DivineOS)"
        print(f"  {label}:")
        print(
            f"    Exact match:     {exact}/{len(valid)} ({exact * 100 / max(len(valid), 1):.0f}%)"
        )
        print(
            f"    Files correct:   {files_correct}/{len(valid)} ({files_correct * 100 / max(len(valid), 1):.0f}%)"
        )
        print(f"    Avg file overlap:   {avg_file_overlap:.1%}")
        print(f"    Avg change overlap: {avg_change_overlap:.1%}")
        print()

    print(f"  Total cost: ${total_cost:.2f}")
    print(f"  Total tasks: {len(tasks)} x 2 conditions = {len(tasks) * 2} API calls")

    # Save summary
    summary = {
        "model": MODEL,
        "n_tasks": len(tasks),
        "total_cost": round(total_cost, 2),
        "scores": scores,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n  Summary saved to {summary_file}")

    return summary


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_benchmark(n)
