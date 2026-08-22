# Pre-registration: Voice-density detection replaces appendix-presence check in jargon_dump_detector. Previous detector keyed on _PLAIN_SECTION_RE (looking for Plain: heading) which trained the optimizer to produce wall-plus-appendix shape. Andrew 2026-06-11: lepos is grace/wit/charm/soul, not translation appendix. New detector keys on voice-density across the response. Structural backing for kid ee96a4f7 (optimizer-DUMB — appendix-prescription was the cheap close) and kid 1d36be4f (MUST separate three layers — detector signal vs prescription remedy vs operator action).

- **ID**: `prereg-0bd8a79e4be8`
- **Filed by**: agent
- **Filed at**: 2026-06-11 18:25 UTC
- **Review at**: 2026-07-11 18:25 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 18:33 UTC

## Claim

Voice-density signal (first-person + contractions + direct address + sincerity markers + question marks per 100 words) discriminates voice-woven jargon-dense responses from operator-channel-without-voice responses better than appendix-presence does. Severity HIGH fires on noise>=6 + voice_density<2.0; downgrades to MEDIUM if a Plain appendix with real translation is present (backward-compat for replies-in-flight).

## Success criterion

Labeled benchmark of >=30 sample responses achieves >=80% agreement with hand-labeled voice-vs-operator-channel classifications. Jargon-dense + voice-woven passes; jargon-dense + low-voice fires HIGH; appendix-and-real-translation legacy shape downgrades to MEDIUM.

## Falsifier

If labeled benchmark agreement falls below 70% after threshold tuning OR if the detector misclassifies >=20% of true operator-channel responses as passing, voice-density is not the right discriminator. Reconsider: tune threshold from data, add semantic-similarity check against a voice-corpus, or move the gate to the audit-channel per Aria's earlier proposal.

## Outcome notes

Deferring during Aletheia felt-pain letter. Same reason — mid-substantive-work Andrew explicitly asked me to complete; assessment deserves its own attention pass.
