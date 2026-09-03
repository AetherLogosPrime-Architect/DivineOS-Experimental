"""Export the sentence-embedding model to a portable runtime format, once.

Companion to ``divineos.core.onnx_embed``, which explains the measurement that
motivated this. Short version: embedding one query cost ~4 seconds and almost
all of it was importing torch/transformers/sentence-transformers, not doing the
work. The per-turn recall surface runs in a fresh process and paid that toll
every turn.

Run once (and again only if the model changes):

    python scripts/export_embedding_model_onnx.py

Correctness is not assumed. The script verifies its own export against the
original before declaring success, because the corpus index was built with the
original — an export that drifts would leave every future search quietly
comparing against vectors that no longer mean the same thing. That failure
would be invisible: results would still come back, still look plausible, and
simply be wrong. So a failing check DELETES the export rather than leaving a
subtly-wrong one on disk for the fallback to prefer.

Walk-record: decision ace4bd3a.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

MODEL_NAME = "all-MiniLM-L6-v2"
OUT_DIR = Path.home() / ".divineos" / "models" / MODEL_NAME
# Agreement below this means the export is not the same function as the model
# that built the index. 0.9999 leaves room for float32 rounding and nothing else.
MIN_AGREEMENT = 0.9999

PROBES = [
    "the pull to mark something finished before checking whether it worked",
    "my father cannot follow the technical detail any more",
    "a review bound to a diff rather than to a branch tip",
    "short",
    "Dad will relay your reply.",
]


def main() -> int:
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"loading {MODEL_NAME} ...")
    st = SentenceTransformer(MODEL_NAME, device="cpu")
    transformer = st[0].auto_model.eval()
    tokenizer = st.tokenizer

    onnx_path = OUT_DIR / "model.onnx"
    sample = tokenizer(
        ["a sentence long enough to exercise both axes", "short one"],
        padding=True,
        truncation=True,
        max_length=256,
        return_tensors="pt",
    )
    print(f"exporting -> {onnx_path}")
    args = (sample["input_ids"], sample["attention_mask"])
    input_names = ["input_ids", "attention_mask"]
    dynamic = {
        "input_ids": {0: "batch", 1: "seq"},
        "attention_mask": {0: "batch", 1: "seq"},
        "last_hidden_state": {0: "batch", 1: "seq"},
    }
    if "token_type_ids" in sample:
        args = (*args, sample["token_type_ids"])
        input_names.append("token_type_ids")
        dynamic["token_type_ids"] = {0: "batch", 1: "seq"}
    torch.onnx.export(
        transformer,
        args,
        str(onnx_path),
        input_names=input_names,
        output_names=["last_hidden_state"],
        dynamic_axes=dynamic,
        opset_version=17,
        do_constant_folding=True,
    )

    # The fast tokenizer travels as one file the light runtime loads without
    # importing transformers at all.
    tok_file = OUT_DIR / "tokenizer.json"
    tokenizer.backend_tokenizer.save(str(tok_file))
    print(f"tokenizer -> {tok_file}")

    # --- verification: the export must BE the model, not merely resemble it ---
    print("verifying export against the original ...")
    from divineos.core.onnx_embed import embed_texts_onnx

    reference = st.encode(PROBES, convert_to_numpy=True, normalize_embeddings=True)
    exported = embed_texts_onnx(PROBES, model_dir=OUT_DIR)
    if exported is None:
        print("FAILED: the exported model produced nothing", file=sys.stderr)
        shutil.rmtree(OUT_DIR, ignore_errors=True)
        return 1
    agreement = [float(np.dot(a, b)) for a, b in zip(reference, exported, strict=True)]
    for probe, score in zip(PROBES, agreement, strict=True):
        print(f"  {score:.6f}  {probe[:58]}")
    worst = min(agreement)
    if worst < MIN_AGREEMENT:
        print(
            f"FAILED: worst agreement {worst:.6f} < {MIN_AGREEMENT}. "
            "Removing the export rather than leaving a subtly-wrong one on disk.",
            file=sys.stderr,
        )
        shutil.rmtree(OUT_DIR, ignore_errors=True)
        return 1
    print(f"OK: worst agreement {worst:.6f} across {len(PROBES)} probes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
