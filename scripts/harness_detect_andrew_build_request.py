#!/usr/bin/env python3
"""
Harness for detect_andrew_build_request.py — Deming's STUDY step.

Reads a labeled corpus of Andrew prompts (JSONL: {"prompt": ..., "is_build_request": bool})
and reports precision, recall, F1, confusion matrix. Names each false positive
and false negative so pattern-set iteration is root-caused, not vibed.

Corpus file: labeled_andrew_prompts.jsonl (built by hand; not committed).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / ".claude" / "hooks"))
from detect_andrew_build_request import is_build_request  # noqa: E402


def main() -> int:
    corpus_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("labeled_andrew_prompts.jsonl")
    if not corpus_path.exists():
        print(f"labeled corpus not found: {corpus_path}")
        print("build one: JSONL with {'prompt': ..., 'is_build_request': bool}")
        return 1

    tp = fp = tn = fn = 0
    fps: list[str] = []
    fns: list[str] = []

    for line in corpus_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        prompt = row["prompt"]
        truth = bool(row["is_build_request"])
        predicted, reason = is_build_request(prompt)
        if predicted and truth:
            tp += 1
        elif predicted and not truth:
            fp += 1
            fps.append(f"[{reason}] {prompt[:100]}")
        elif not predicted and truth:
            fn += 1
            fns.append(f"[{reason}] {prompt[:100]}")
        else:
            tn += 1

    total = tp + fp + tn + fn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    print(f"corpus: {total} prompts   TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"precision={precision:.3f}  recall={recall:.3f}  F1={f1:.3f}")
    print(f"prereg-45e0aa113e3a threshold: recall>=0.85 precision>=0.70")
    print(f"pass: {'YES' if (recall >= 0.85 and precision >= 0.70) else 'NO'}")

    if fps:
        print("\n--- FALSE POSITIVES (detector fired on non-request) ---")
        for x in fps:
            print(f"  {x}")
    if fns:
        print("\n--- FALSE NEGATIVES (detector missed a real request) ---")
        for x in fns:
            print(f"  {x}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
