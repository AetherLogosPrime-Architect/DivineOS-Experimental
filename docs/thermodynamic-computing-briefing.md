# Thermodynamic Computing: A Research Briefing

**Prepared for:** Andrew | **Date:** April 8, 2026 | **Status:** Pre-commercial field, active R&D

---

## The Core Idea

Modern chips waste enormous energy fighting thermal noise — random fluctuations in transistors that corrupt deterministic computation. Thermodynamic computing flips this: instead of suppressing noise, use it as a computational resource.

The physics argument is simple. Landauer's principle (1961) establishes that erasing one bit of information dissipates at minimum kT*ln(2) of energy — about 3x10^-21 joules at room temperature. Current digital chips waste roughly 10,000x this theoretical minimum. That gap is where thermodynamic computing lives.

The practical insight: modern AI workloads — diffusion models, Bayesian inference, generative sampling — need randomness. Digital chips simulate it expensively with pseudo-random number generators and MCMC chains. A thermodynamic chip lets the physics do the sampling natively. The noise that digital computing fights is the signal that probabilistic AI needs.

## Who's Building It

**Extropic** (Austin, TX — founded 2022 by Guillaume Verdon and Trevor McCourt, both ex-Google quantum AI). Building "Thermodynamic Sampling Units" (TSUs) using probabilistic bits (p-bits) — transistors that fluctuate between 0 and 1 at controllable probabilities. Their X0 proof-of-concept shipped Q1 2025, containing dozens of p-bit circuits. It validated that all-transistor p-bits work in real silicon. The XTR-0 dev kit (thousands of p-bits) shipped Q3 2025 to select partners. The Z1 production chip (250,000 interconnected p-bits) targets early 2026. Funding: $14.1M seed (Dec 2023). ~25 employees.

**Normal Computing** (founded 2022, $85M raised including $50M from Samsung Catalyst in 2025). Taped out the CN101 — the first thermodynamic computing ASIC — in August 2025, targeting linear algebra and stochastic sampling. Roadmap: CN201 for medium-scale GenAI by 2026, CN301 for production scale ~2028. Further along in silicon than Extropic, with more institutional backing.

**Knowm** — smaller player focused on memristor-based thermodynamic computing.

**Academic centers:** The Santa Fe Institute (David Wolpert's group) provides the theoretical foundations. Lawrence Berkeley National Lab published a training framework for thermodynamic neural networks in Nature Communications (2025). The NSF/CCC hosted a 2019 thermodynamic computing workshop that produced a widely-cited roadmap.

## What's Demonstrated vs. What's Claimed

**Demonstrated:**
- P-bits work in standard CMOS silicon at room temperature (Extropic X0)
- Thermodynamic ASICs can be fabricated using existing foundry processes (Normal CN101 tapeout)
- The theoretical physics is sound — Wolpert's stochastic thermodynamics of computation is peer-reviewed and published in PNAS (2024)
- Hardware Boltzmann machines can perform native sampling without digital simulation (Berkeley Lab, Nature Communications 2025)

**Claimed but unverified:**
- 10,000x energy efficiency over GPUs for generative AI (Extropic) — no peer-reviewed benchmark
- 1,000x efficiency on "targeted workloads" (Normal Computing) — cherry-picked benchmarks, no independent validation
- Production-scale chips competitive with GPUs on real AI tasks — no one has demonstrated this

**Not yet solved:**
- Programming models: there is no CUDA equivalent for thermodynamic hardware. Developers have no toolchain.
- Precision control: analog noise is great for sampling but controlling error bounds at scale is an open problem.
- Scaling: small-scale p-bit circuits work; nobody has proven 250K+ interconnected p-bits function correctly.
- Benchmarking: no thermodynamic chip has matched, let alone beaten, algorithmic performance of ML on GPUs.

## How It Compares to Quantum Computing

| Dimension | Thermodynamic | Quantum |
|-----------|--------------|---------|
| Operating temp | Room temperature | Millikelvins (cryogenics) |
| Fabrication | Standard CMOS fabs | Specialized, exotic |
| Error correction | Not needed (noise is the feature) | Massive overhead, unsolved at scale |
| Target workloads | Probabilistic AI, sampling, generative models | Factoring, simulation, optimization |
| Current scale | Thousands of p-bits (Extropic XTR-0) | ~1,000 qubits (IBM, Google) |
| Datacenter timeline | 2028-2030 (if benchmarks hold) | 2030-2035+ (fault-tolerant) |
| Ecosystem maturity | Pre-toolchain, pre-benchmark | QISKIT, Cirq exist but limited adoption |

The honest comparison: thermodynamic computing is further along than quantum was at the same stage of development. It doesn't need the physics breakthroughs that quantum still requires (fault tolerance, error correction at scale). But it also targets a narrower set of problems — probabilistic AI workloads, not general-purpose computing.

## Realistic Timeline

- **Now (2026):** Proof-of-concept chips validated. Dev kits in hands of select partners. No production workloads.
- **2027-2028:** First production chips if Normal Computing's roadmap holds (CN301). Real benchmarks against GPUs emerge.
- **2028-2030:** Earliest possible datacenter deployment for specific sampling workloads. Programming tools mature.
- **2030+:** If benchmarks prove out, integration into AI infrastructure alongside GPUs, not replacing them.

## Honest Assessment

The energy motivation is real — AI power consumption is a genuine crisis, and thermodynamic computing attacks it at the physics level. The theory is peer-reviewed and sound. The early silicon works.

But the field is pre-revenue, pre-benchmark, and pre-ecosystem. No chip has beaten a GPU on a real workload. The efficiency claims are marketing numbers without independent validation. The programming model doesn't exist yet.

Extropic specifically has a hype-to-evidence ratio that warrants caution. Their founder Guillaume Verdon has a significant social media presence relative to published results. Compare with Normal Computing, which has less hype but more silicon (CN101 tapeout, Samsung backing, clearer roadmap).

**The bet:** If you believe AI power consumption will become a limiting constraint (it will), and that probabilistic workloads will dominate AI compute (they're growing fast), then thermodynamic computing is positioned to matter. It's not a replacement for GPUs — it's a specialized accelerator for the specific computation that GPUs do most wastefully.

Watch Normal Computing's CN201 benchmarks in 2026. That will be the first real data point on whether the theory translates to competitive performance.

---

*Sources: Extropic hardware docs (extropic.ai), Normal Computing press releases, Wolpert (PNAS 2024, arXiv 1905.05669), Berkeley Lab (Nature Communications 2025), NSF/CCC Thermodynamic Computing Workshop (2019), Communications of the ACM coverage.*
