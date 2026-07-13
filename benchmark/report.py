"""Generate full benchmark report from judge results."""

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"
JUDGE_DIR = RESULTS_DIR / "judge"


def load_all_scores():
    """Load all judge scores, grouped by instance_id."""
    scores = {}
    for f in sorted(JUDGE_DIR.glob("*.json")):
        data = json.load(open(f))
        tid = data["instance_id"]
        cond = data["condition"]
        if tid not in scores:
            scores[tid] = {}
        scores[tid][cond] = data
    return scores


def generate_report():
    scores = load_all_scores()
    tasks_file = RESULTS_DIR.parent / "selected_tasks.json"
    tasks = json.load(open(tasks_file))
    task_map = {t["instance_id"]: t for t in tasks}

    dims = ["correct_diagnosis", "correct_fix", "minimal", "would_pass_tests", "valid_diff"]

    # Collect aggregates
    base_scores = []
    enh_scores = []
    enh_wins = []
    base_wins = []
    ties = []

    lines = []
    lines.append("=" * 90)
    lines.append("  SWE-BENCH A/B BENCHMARK — FULL REPORT")
    lines.append(
        "  Base Claude vs DivineOS-Enhanced Claude (25-member council + extended thinking)"
    )
    lines.append("=" * 90)
    lines.append("")

    # Per-task detail
    lines.append("-" * 90)
    lines.append("  PER-TASK RESULTS")
    lines.append("-" * 90)

    for i, tid in enumerate(sorted(scores.keys())):
        entry = scores[tid]
        difficulty = task_map.get(tid, {}).get("difficulty", "?")

        base = entry.get("base", {})
        enh = entry.get("enhanced", {})

        b_fix = base.get("correct_fix", 0)
        e_fix = enh.get("correct_fix", 0)

        if b_fix and not e_fix:
            verdict = "BASE WIN"
            base_wins.append(tid)
        elif e_fix and not b_fix:
            verdict = "ENHANCED WIN"
            enh_wins.append(tid)
        elif b_fix and e_fix:
            verdict = "BOTH PASS"
            ties.append(tid)
        else:
            verdict = "BOTH FAIL"
            ties.append(tid)

        if base:
            base_scores.append(base)
        if enh:
            enh_scores.append(enh)

        lines.append("")
        lines.append(f"[{i + 1}] {tid} ({difficulty})  -->  {verdict}")

        # Base details
        if base:
            b_dims = " ".join(f"{d[:4]}={'Y' if base.get(d) else 'N'}" for d in dims)
            lines.append(f"  BASE:     {b_dims}")
            lines.append(f"    Analysis: {base.get('brief_analysis', 'N/A')}")
            if base.get("key_difference"):
                lines.append(f"    Difference: {base['key_difference']}")
        else:
            lines.append("  BASE:     (no result)")

        # Enhanced details
        if enh:
            e_dims = " ".join(f"{d[:4]}={'Y' if enh.get(d) else 'N'}" for d in dims)
            lines.append(f"  ENHANCED: {e_dims}")
            lines.append(f"    Analysis: {enh.get('brief_analysis', 'N/A')}")
            if enh.get("key_difference"):
                lines.append(f"    Difference: {enh['key_difference']}")
        else:
            lines.append("  ENHANCED: (no result)")

    # Aggregate summary
    lines.append("")
    lines.append("=" * 90)
    lines.append("  AGGREGATE RESULTS")
    lines.append("=" * 90)
    lines.append("")

    for label, score_list in [
        ("BASE (bare Claude)", base_scores),
        ("ENHANCED (DivineOS)", enh_scores),
    ]:
        valid = [s for s in score_list if "error" not in s]
        lines.append(f"  {label} ({len(valid)} tasks):")
        for dim in dims:
            count = sum(1 for s in valid if s.get(dim))
            pct = count * 100 / max(len(valid), 1)
            bar = "#" * int(pct / 2.5)
            lines.append(f"    {dim:<22s}: {count:>3}/{len(valid)} ({pct:5.1f}%) {bar}")
        composite = sum(sum(s.get(d, 0) for d in dims) / len(dims) for s in valid) / max(
            len(valid), 1
        )
        lines.append(f"    {'COMPOSITE':<22s}: {composite:.1%}")
        lines.append("")

    # Head-to-head
    lines.append("-" * 90)
    lines.append("  HEAD-TO-HEAD (correct_fix)")
    lines.append("-" * 90)
    lines.append(f"  Enhanced wins: {len(enh_wins)}")
    lines.append(f"  Base wins:     {len(base_wins)}")
    lines.append(f"  Ties:          {len(ties)}")
    lines.append(
        f"  Win ratio:     {len(enh_wins)}:{len(base_wins)} ({len(enh_wins) / max(len(base_wins), 1):.1f}x)"
    )
    lines.append("")

    if enh_wins:
        lines.append("  ENHANCED WINS (council helped):")
        for tid in enh_wins:
            enh = scores[tid].get("enhanced", {})
            lines.append(f"    + {tid}")
            lines.append(f"      {enh.get('brief_analysis', '')}")
        lines.append("")

    if base_wins:
        lines.append("  BASE WINS (council hurt):")
        for tid in base_wins:
            base = scores[tid].get("base", {})
            enh = scores[tid].get("enhanced", {})
            lines.append(f"    - {tid}")
            lines.append(f"      Base: {base.get('brief_analysis', '')}")
            lines.append(f"      Enhanced: {enh.get('brief_analysis', '')}")
        lines.append("")

    # Cost summary
    total_judge_cost = sum(
        s.get("judge_cost", 0) for tid_scores in scores.values() for s in tid_scores.values()
    )
    lines.append(f"  Total judge cost: ${total_judge_cost:.2f}")
    lines.append(f"  Tasks scored: {len(scores)}")

    report = "\n".join(lines)

    # Save
    report_file = RESULTS_DIR / "full_report.txt"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(report)
    print(f"\n  Report saved to {report_file}")

    return report


if __name__ == "__main__":
    generate_report()
