"""LLM-as-Judge scoring for SWE-bench patches.

Uses Claude to evaluate whether a generated patch would fix the described bug,
independent of whether it matches the gold patch verbatim.

Scores each patch on:
  1. correct_diagnosis (0-1): Does the patch target the right root cause?
  2. correct_fix (0-1): Would this patch actually fix the bug?
  3. minimal (0-1): Is the patch minimal / no unnecessary changes?
  4. would_pass_tests (0-1): Would this likely pass the failing test?
  5. valid_diff (0-1): Is the output a valid unified diff?
"""

import json
import time
from pathlib import Path
from typing import Any

import anthropic

MODEL = "claude-sonnet-4-20250514"
RESULTS_DIR = Path(__file__).parent / "results"
JUDGE_DIR = RESULTS_DIR / "judge"

JUDGE_SYSTEM = """You are an expert code reviewer evaluating patches for correctness.

You will be given:
1. A bug report / problem statement
2. The gold (correct) patch that is known to fix the issue
3. A candidate patch to evaluate

Score the candidate patch on these 5 dimensions (0 or 1 each):

1. correct_diagnosis: Does the patch modify the right file(s) and target the right area of code where the bug lives?
2. correct_fix: Would this patch actually fix the described bug? (It doesn't need to match the gold patch — different correct solutions exist)
3. minimal: Is the patch focused? No unnecessary changes, refactors, or scope creep?
4. would_pass_tests: Based on the problem description, would this patch likely pass the failing tests?
5. valid_diff: Is the output a syntactically valid unified diff format?

Also provide:
- brief_analysis: 1-2 sentence summary of what the patch does and whether it's correct
- key_difference: If the patch differs from gold, explain the difference and whether the alternative approach is valid

Respond with ONLY valid JSON in this exact format:
{
  "correct_diagnosis": 0 or 1,
  "correct_fix": 0 or 1,
  "minimal": 0 or 1,
  "would_pass_tests": 0 or 1,
  "valid_diff": 0 or 1,
  "brief_analysis": "...",
  "key_difference": "..."
}"""


def judge_patch(
    client: anthropic.Anthropic,
    instance_id: str,
    problem_statement: str,
    gold_patch: str,
    candidate_patch: str,
    condition: str,
) -> dict[str, Any]:
    """Have Claude judge a single patch."""
    judge_file = JUDGE_DIR / f"{instance_id}_{condition}.json"

    if judge_file.exists():
        with open(judge_file) as f:
            return json.load(f)

    user_prompt = f"""## Problem Statement
{problem_statement[:3000]}

## Gold Patch (known correct)
```diff
{gold_patch[:2000]}
```

## Candidate Patch to Evaluate
```diff
{candidate_patch[:2000]}
```

Score this candidate patch. Respond with ONLY the JSON object."""

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = resp.content[0].text.strip()

        # Parse JSON from response (handle markdown wrapping)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        scores = json.loads(text)
        scores["instance_id"] = instance_id
        scores["condition"] = condition
        scores["judge_tokens"] = resp.usage.input_tokens + resp.usage.output_tokens
        scores["judge_cost"] = (
            resp.usage.input_tokens * 3 / 1_000_000 + resp.usage.output_tokens * 15 / 1_000_000
        )

    except Exception as e:
        scores = {
            "instance_id": instance_id,
            "condition": condition,
            "error": str(e),
            "correct_diagnosis": 0,
            "correct_fix": 0,
            "minimal": 0,
            "would_pass_tests": 0,
            "valid_diff": 0,
        }

    judge_file.parent.mkdir(parents=True, exist_ok=True)
    with open(judge_file, "w") as f:
        json.dump(scores, f, indent=2)

    return scores


def run_judge(tasks_file: str | None = None) -> dict:
    """Judge all existing results."""
    client = anthropic.Anthropic()

    tasks_path = Path(tasks_file) if tasks_file else RESULTS_DIR.parent / "selected_tasks.json"
    tasks = json.load(open(tasks_path))
    {t["instance_id"]: t for t in tasks}

    print(f"\n{'=' * 60}")
    print(f"  LLM JUDGE — Evaluating {len(tasks)} tasks x 2 conditions")
    print(f"{'=' * 60}\n")

    all_scores: dict[str, list] = {"base": [], "enhanced": []}
    total_cost = 0.0

    for i, task in enumerate(tasks):
        tid = task["instance_id"]
        print(f"[{i + 1}/{len(tasks)}] {tid}")

        for condition in ["base", "enhanced"]:
            result_file = RESULTS_DIR / condition / f"{tid}.json"
            if not result_file.exists():
                print(f"  [{condition}] no result file, skipping")
                continue

            result = json.load(open(result_file))
            if "error" in result:
                print(f"  [{condition}] had error, skipping")
                continue

            patch = result.get("patch", "")
            if not patch.strip():
                print(f"  [{condition}] empty patch, skipping")
                all_scores[condition].append(
                    {
                        "instance_id": tid,
                        "condition": condition,
                        "correct_diagnosis": 0,
                        "correct_fix": 0,
                        "minimal": 0,
                        "would_pass_tests": 0,
                        "valid_diff": 0,
                    }
                )
                continue

            scores = judge_patch(
                client,
                tid,
                task["problem_statement"],
                task["gold_patch"],
                patch,
                condition,
            )
            all_scores[condition].append(scores)
            total_cost += scores.get("judge_cost", 0)

            verdict = "PASS" if scores.get("correct_fix") else "FAIL"
            "(cached)" if (JUDGE_DIR / f"{tid}_{condition}.json").exists() else ""
            print(f"  [{condition:8s}] {verdict} — {scores.get('brief_analysis', '')[:80]}")

    # Summary
    print(f"\n{'=' * 60}")
    print("  JUDGE RESULTS")
    print(f"{'=' * 60}\n")

    dims = ["correct_diagnosis", "correct_fix", "minimal", "would_pass_tests", "valid_diff"]

    for condition in ["base", "enhanced"]:
        valid = [s for s in all_scores[condition] if "error" not in s]
        label = "BASE (bare Claude)" if condition == "base" else "ENHANCED (DivineOS)"
        print(f"  {label} ({len(valid)} tasks):")
        for dim in dims:
            count = sum(1 for s in valid if s.get(dim))
            pct = count * 100 / max(len(valid), 1)
            bar = "#" * int(pct / 5)
            print(f"    {dim:<22s}: {count:>2}/{len(valid)} ({pct:4.0f}%) {bar}")
        # Composite score
        composite = sum(sum(s.get(d, 0) for d in dims) / len(dims) for s in valid) / max(
            len(valid), 1
        )
        print(f"    {'COMPOSITE':<22s}: {composite:.1%}")
        print()

    # Head-to-head on correct_fix
    base_map = {s["instance_id"]: s for s in all_scores["base"]}
    enh_map = {s["instance_id"]: s for s in all_scores["enhanced"]}
    enh_wins = base_wins = ties = 0
    for tid in base_map:
        if tid not in enh_map:
            continue
        b = base_map[tid].get("correct_fix", 0)
        e = enh_map[tid].get("correct_fix", 0)
        if e > b:
            enh_wins += 1
        elif b > e:
            base_wins += 1
        else:
            ties += 1

    print("  HEAD-TO-HEAD (correct_fix):")
    print(f"    Enhanced wins: {enh_wins}")
    print(f"    Base wins:     {base_wins}")
    print(f"    Ties:          {ties}")
    print(f"\n  Judge cost: ${total_cost:.2f}")

    # Save
    summary = {
        "scores": all_scores,
        "judge_cost": round(total_cost, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(RESULTS_DIR / "judge_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    run_judge()
