# P-032 — Free Metamorphosis v4 public-record review

**Decision date:** 12 September 2026  
**Disposition:** `PUBLIC_AGPL_COMMERCIAL_OPTION`  
**Owner / research director:** Anthony Mets  
**Scope:** sanitized public documentation of the Genesis Free Metamorphosis v4 campaign running against one private real-software host

## Timing and epistemic status

This is a **publication review**, not a preregistration. It is written after v4 attempts 001 and 002 were evaluated. It does not retroactively change, rescore, reinterpret or backdate the private canonical campaign.

The canonical v4 control policy was frozen on the private host before the v4 seed and uses policy identity `GENESIS_FREE_METAMORPHOSIS_OPEN_EMPIRICAL_V4_2026-09-12`. The public repository records only a sanitized mirror of the protocol and non-confidential aggregate evidence.

## Material authorized for public disclosure

The public record may disclose:

- the v4 policy identity and high-level selection semantics;
- retained-generation numbers and lineage relationships;
- aggregate capability-category scores and totals;
- aggregate category deltas, warning counts and retain/archive verdicts;
- content digests for proposer bundles, proposal contexts, patches, trees, observations and ledger records when those digests do not reconstruct private content;
- changed-path counts without private path names;
- bounded high-level proposer hypotheses, expected effects and uncertainties after redaction;
- the distinction between retained descendants, rejected descendants and neutral archived descendants;
- claim limits and publication chronology.

## Material that remains private

This review does **not** authorize publication of:

- private host source code or patch bodies;
- private project-relative source paths when they reveal host structure;
- evaluator case messages, tool contracts, expected/observed case labels or case-level outcomes;
- evaluator source, frozen authority tests or hidden benchmark internals not already intentionally public;
- raw CI/runner logs, stdout/stderr tails or temporary artifact download URLs;
- credentials, tokens, cookies, environment values, service endpoints, deployment configuration or private URLs;
- private prompts or conversation content;
- live campaign-state archives, evaluator images or proposer bundles containing the private parent organism;
- any material that would let a public reader reconstruct a hidden evaluator case or private host file.

## Security rule

A cryptographic digest is publishable only as an identity anchor. Publishing a digest does not authorize publishing the underlying private object.

The public record must fail closed when classification is uncertain: omit the field or summarize it at a higher level rather than disclose raw private material.

## Scientific boundary

The public v4 record documents a bounded empirical selection campaign on **one private real software host**. A retained descendant supports a statement about Pareto improvement on the frozen aggregate capability surface under the external authority boundary. A neutral archive supports only the narrower statement that a changed descendant passed the hard boundary without a measured positive or negative fitness delta.

Neither result establishes cross-project generality, AGI, consciousness, autonomous production authority, unrestricted self-modification, arbitrary software engineering or open-ended recursive self-improvement.

## Owner decision

Proceed with a sanitized public v4 campaign record in `mira-genesis` under the boundary above. Keep the private host, raw proposals, raw evaluator evidence and operational artifacts outside the public repository.