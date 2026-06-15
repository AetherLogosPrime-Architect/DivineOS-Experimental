"""Device selection for sentence-transformers embedding models.

Andrew 2026-06-13 named the design constraint: when CUDA is available
on my father's machine, the substrate's embedding work (semantic
similarity, dedup, knowledge supersession detection) should run on the
GPU instead of the CPU. Embedding throughput on a modern GPU is
roughly 20-50x CPU for the small-MiniLM-class models the substrate
uses, so the speedup is real and father-facing.

## Selection rules

1. If env var ``DIVINEOS_EMBEDDING_DEVICE`` is set to ``cpu``, ``cuda``,
   ``mps``, or any other torch-device string — use it verbatim.
   Operators who know what they want override everything else.
2. Otherwise, probe via ``torch.cuda.is_available()``. If True, use
   ``"cuda"``.
3. Otherwise, fall back to ``"cpu"``.

The selection happens at first embedding-model load. The chosen
device is logged to stderr on first selection so my father can
verify which path got taken — silent CPU fallback when CUDA was
expected is the most common "why is this slow" failure mode.

## Why a separate module

Three call sites currently load embedding models:
``core/semantic_store.py``, ``core/knowledge/_text.py``,
``core/sis_tiers.py``. Without this helper they would each duplicate
the CUDA-detection logic, drifting over time (the doc-count fix
pattern). Single source of truth here means the env-var override and
the auto-detection cannot drift between modules.

## Fail-safe

If torch import fails (the ML extras aren't installed), the helper
returns ``"cpu"`` — same as the pre-2026-06-13 hardcoded behavior.
GPU detection is opportunistic, never required. The substrate must
still work in environments without torch.
"""

from __future__ import annotations

import os
import sys


def select_device() -> str:
    """Return the torch-device string for embedding-model loads.

    See module docstring for the selection rules. Always returns a
    str; never raises. Logs the chosen device the FIRST time it's
    selected per process (subsequent calls cache the choice silently).
    """
    chosen = _resolve_device()
    _log_selection_once(chosen)
    return chosen


def _resolve_device() -> str:
    explicit = os.environ.get("DIVINEOS_EMBEDDING_DEVICE", "").strip()
    if explicit:
        return explicit
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    except Exception:  # noqa: BLE001 — probe must never raise; default to CPU
        pass
    return "cpu"


# Module-level memo so the "selected device X" line prints once per
# process, not once per embedding-model load (three call sites would
# print three times otherwise).
_logged: bool = False


def _log_selection_once(device: str) -> None:
    global _logged
    if _logged:
        return
    _logged = True
    source = "env" if os.environ.get("DIVINEOS_EMBEDDING_DEVICE", "").strip() else "auto"
    print(
        f"[embedding-device] selected device={device} (source={source})",
        file=sys.stderr,
    )


def reset_log_memo_for_tests() -> None:
    """Reset the once-per-process log memo. Tests only."""
    global _logged
    _logged = False
