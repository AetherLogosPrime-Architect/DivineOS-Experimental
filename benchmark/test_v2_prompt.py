"""Quick A/B test: v1 council prompt vs v2 (with Popper/Knuth/Polya + phases).

Runs on the tasks where v1 lost or failed, to see if v2 fixes the issues.
Saves results to results/enhanced_v2/ for comparison.
"""

import json
import time
from pathlib import Path

import anthropic

# Import the new prompt from the harness
from swe_harness import ENHANCED_SYSTEM, MODEL, estimate_cost

RESULTS_DIR = Path(__file__).parent / "results"
TASKS_FILE = Path(__file__).parent / "selected_tasks.json"

# Tasks where v1 lost to base (base wins)
BASE_WINS = [
    "astropy__astropy-14508",
    "django__django-16032",
    "matplotlib__matplotlib-25479",
]

# Tasks where v1 had right diagnosis but wrong fix
RIGHT_DIAG_WRONG_FIX = [
    "django__django-12325",
    "django__django-13158",
    "django__django-13401",
    "django__django-13741",
    "django__django-14034",
    "sphinx-doc__sphinx-11510",
    "astropy__astropy-13398",
]

TEST_TASKS = BASE_WINS + RIGHT_DIAG_WRONG_FIX


def run_v2_test():
    client = anthropic.Anthropic()

    with open(TASKS_FILE) as f:
        all_tasks = json.load(f)
    task_map = {t["instance_id"]: t for t in all_tasks}

    print(f"\n{'=' * 60}")
    print(f"  V2 COUNCIL PROMPT TEST — {len(TEST_TASKS)} tasks")
    print("  Testing Popper/Knuth/Polya + mandatory phases")
    print(f"{'=' * 60}\n")

    v2_dir = RESULTS_DIR / "enhanced_v2"
    v2_dir.mkdir(parents=True, exist_ok=True)

    total_cost = 0.0
    results = []

    for i, tid in enumerate(TEST_TASKS):
        task = task_map.get(tid)
        if not task:
            print(f"[{i + 1}] {tid} — NOT IN TASK SET, skipping")
            continue

        result_file = v2_dir / f"{tid}.json"
        if result_file.exists():
            print(f"[{i + 1}] {tid} — cached")
            with open(result_file) as f:
                results.append(json.load(f))
            continue

        # Build user prompt
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
        user_prompt = "\n".join(parts)

        print(f"[{i + 1}/{len(TEST_TASKS)}] {tid}...", end=" ", flush=True)
        start = time.time()

        try:
            resp = client.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=ENHANCED_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
                thinking={
                    "type": "enabled",
                    "budget_tokens": 10000,  # Slightly more budget for mandatory phases
                },
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
                "instance_id": tid,
                "condition": "enhanced_v2",
                "model": resp.model,
                "patch": patch_text,
                "thinking": thinking_text if thinking_text else None,
                "input_tokens": resp.usage.input_tokens,
                "output_tokens": resp.usage.output_tokens,
                "elapsed_seconds": round(elapsed, 1),
                "stop_reason": resp.stop_reason,
                "cost_estimate": estimate_cost(resp.usage.input_tokens, resp.usage.output_tokens),
            }
            cost = result["cost_estimate"]
            total_cost += cost
            print(f"done ({elapsed:.1f}s, ${cost:.3f})")

        except Exception as e:
            elapsed = time.time() - start
            result = {
                "instance_id": tid,
                "condition": "enhanced_v2",
                "error": str(e),
                "elapsed_seconds": round(elapsed, 1),
            }
            print(f"ERROR: {e}")

        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        results.append(result)

    # Quick comparison
    print(f"\n{'=' * 60}")
    print("  V2 RESULTS COMPARISON")
    print(f"{'=' * 60}\n")

    for tid in TEST_TASKS:
        v1_file = RESULTS_DIR / "enhanced" / f"{tid}.json"
        v2_file = v2_dir / f"{tid}.json"

        if not v1_file.exists() or not v2_file.exists():
            continue

        v1 = json.load(open(v1_file))
        v2 = json.load(open(v2_file))

        v1_patch = v1.get("patch", "")
        v2_patch = v2.get("patch", "")

        # Check for obvious improvements
        v1_valid = v1_patch.strip().startswith("---") and "+++" in v1_patch[:500]
        v2_valid = v2_patch.strip().startswith("---") and "+++" in v2_patch[:500]

        v1_lines = len(v1_patch.splitlines())
        v2_lines = len(v2_patch.splitlines())

        # Check thinking for phase markers
        v2_thinking = v2.get("thinking", "") or ""
        has_popper = "popper" in v2_thinking.lower() or "falsif" in v2_thinking.lower()
        has_knuth = "knuth" in v2_thinking.lower() or "boundar" in v2_thinking.lower()
        has_polya = (
            "polya" in v2_thinking.lower()
            or "solution check" in v2_thinking.lower()
            or "verify" in v2_thinking.lower()
        )

        category = "BASE WIN" if tid in BASE_WINS else "DIAG OK FIX BAD"

        print(f"  {tid} ({category}):")
        print(f"    v1: {v1_lines} lines, valid_start={v1_valid}")
        print(f"    v2: {v2_lines} lines, valid_start={v2_valid}")
        print(f"    v2 engaged: Popper={has_popper} Knuth={has_knuth} Polya={has_polya}")
        print(f"    v2 thinking: {len(v2_thinking)} chars")
        print()

    print(f"  Total v2 test cost: ${total_cost:.2f}")
    print(f"  Results in: {v2_dir}")
    print("\n  Next: run llm_judge on enhanced_v2 to compare scores")


if __name__ == "__main__":
    run_v2_test()
