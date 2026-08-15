# M092 criterion freeze notes

This branch is still pre-search infrastructure. It must not contain a canonical M092 target result,
qualification material, an adopted target operation or a scientific verdict.

Before the first target search is consumed, the branch must freeze:

- path-wise candidate ghost-policy enumeration with real attempt accounting;
- deterministic first-accepted-candidate selection over the frozen M092-B program stream;
- integrity-checked resumable search state, implementation bindings and canonical prefix replay;
- structural/anti-cheating validation before global proof validation;
- no candidate execution or qualification access during correctness selection;
- exact per-program and global program/certificate budgets;
- all protocol certificate bounds (`-4..4` affine coefficients, at most 8 constraints per loop,
  at most 2 ghost counters and exactly the single-loop candidate surface);
- neutral development rehearsal only;
- a canonical-run entry point with no reroll or result-saving correction path.

## Resume provenance boundary

The SHA-256 values carried inside a serialized search state are integrity checks, not signatures. A
party able to rewrite the JSON can also recompute those hashes. They therefore must not be described
as authenticating the scientific history by themselves.

For the canonical M092 run, every supplied resume state is first parsed and bound to the frozen
theorem and implementation digests, then the complete claimed search prefix is deterministically
replayed from genesis. The fully serialized replayed state must equal the supplied state before a
single new proposal is consumed. This recomputes the cursor position, program and certificate
attempt counts, refusal tallies, selected payload and both event chains rather than trusting them.

Consequently resumability is a cache/checkpoint optimization only: it may reduce recovery storage,
but it cannot change which prefix the frozen criterion computation says occurred. Direct library use
that bypasses `scripts/run_m092_criterion_search.py` is not a canonical scientific run.

## Certificate-language boundary

The independent verifier accepts the frozen normalized integer-affine certificate language described
by `experiments/M092/PROTOCOL.json`. The candidate-side generator is a deterministic **bounded
template search inside that accepted language**. It proposes sparse invariant, inequality, variant,
step-bound and ghost-policy templates; it is not itself an impossibility prover for the full accepted
certificate language.

The criterion runner counts every real template-policy attempt and selects the first exact
program/certificate pair accepted by the independent scanner and verifier. Verifier refusal is a
terminal observation for that pair and is never used to repair or complete it.

A bounded search failure is therefore a preserved negative about this precommitted program stream,
certificate-template family and budget only. It is not an impossibility proof for K1, for the full
accepted affine certificate language, or for endogenous substrate extension in general.
