"""Expand task selection by adding more tasks from SWE-bench Verified."""

import json
import random
from pathlib import Path
from datasets import load_dataset

TASKS_FILE = Path(__file__).parent / "selected_tasks.json"


def expand_tasks(target_n: int = 150, seed: int = 42):
    # Load existing tasks
    with open(TASKS_FILE) as f:
        existing = json.load(f)
    existing_ids = {t["instance_id"] for t in existing}
    print(f"Existing tasks: {len(existing)}")

    # Load dataset
    print("Loading SWE-bench Verified dataset...")
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    # Get all IDs not already selected
    remaining_ids = sorted(
        [row["instance_id"] for row in ds if row["instance_id"] not in existing_ids]
    )
    print(f"Available remaining tasks: {len(remaining_ids)}")

    # Sample additional tasks deterministically
    need = target_n - len(existing)
    if need <= 0:
        print(f"Already have {len(existing)} >= {target_n}, nothing to add")
        return

    rng = random.Random(seed + 1)  # Different seed to avoid correlation
    new_ids = set(rng.sample(remaining_ids, min(need, len(remaining_ids))))
    print(f"Adding {len(new_ids)} new tasks")

    # Build new task entries
    new_tasks = []
    for row in ds:
        if row["instance_id"] in new_ids:
            new_tasks.append(
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

    combined = existing + new_tasks
    with open(TASKS_FILE, "w") as f:
        json.dump(combined, f, indent=2)
    print(f"Saved {len(combined)} total tasks to {TASKS_FILE}")


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    expand_tasks(n)
