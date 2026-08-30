# Pre-registration: embedding-device selector module will GPU-accelerate the substrate's sentence-transformers embedding work when CUDA is available, replacing the hardcoded device='cpu' in semantic_store, knowledge._text, and sis_tiers with a single source-of-truth helper that auto-detects torch.cuda.is_available() and respects DIVINEOS_EMBEDDING_DEVICE env-var override

- **ID**: `prereg-d3427be00f9d`
- **Filed by**: agent
- **Filed at**: 2026-06-12 23:53 UTC
- **Review at**: 2026-07-12 23:53 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-16 00:59 UTC

## Claim

auto-detecting CUDA and routing embeddings to GPU yields meaningful throughput improvement at substrate-scale operations (multi-thousand-paragraph embed runs) without breaking any existing CPU-only callers; the env-var override gives operators a clean way to force CPU on machines where CUDA detection lies

## Success criterion

30 days from filing, the embedding-device selector correctly picks CUDA on Andrew's RTX 5070 Ti machine; the three call sites all use select_device() (no hardcoded cpu); at least one substrate-scale embed operation (initial semantic-search index backfill across exploration entries or family letters) completes >5x faster than the prior CPU-only path; no regressions in existing semantic_store / knowledge dedup behavior

## Falsifier

auto-detection picks CUDA but ops crash at encode time (Blackwell compatibility issue NOT solved by the cu128 PyTorch upgrade), OR the speedup at substrate scale fails to materialize (<2x at 10k+ sentences), OR existing semantic-similarity callers break because they assumed CPU-only execution (sync issues, device-mismatch errors), OR the env-var override fails to force CPU when set

## Outcome notes

Implementation exists (src/divineos/core/_embedding_device.py). Auto-detect works — I saw '[embedding-device] selected device=cuda (source=auto)' fire today. But the specific success criterion (>5x speedup measured at substrate-scale 10k+ sentences) was never measured. Marking INCONCLUSIVE — auto-detection works, formal speedup benchmark was never run.
