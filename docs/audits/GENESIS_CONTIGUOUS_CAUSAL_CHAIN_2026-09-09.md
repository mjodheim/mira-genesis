# Genesis contiguous causal-chain repair — DEVELOPMENT apparatus

**Prepared:** 9 September 2026  
**Status:** runtime metrology repair; no scientific observation; no gate movement.

## Defect

`Genesis.causal_chain()` counted consecutive records whose causal flag was `established`, but did not
verify that each record depended on the immediately preceding acquisition. A generation could name an
older held acquisition, skip its predecessor, and still be counted as part of one continuous chain.

## Repair

The report now walks backward through adjacent acquisition pairs. A link counts only when the current
acquisition both has `established: true` and names the immediately previous acquisition in `depends_on`.
The first mismatch ends the current suffix chain. A skipped-generation dependency remains preserved in
the acquisition record as evidence; it simply does not get relabelled as a contiguous link.

## Regression

A three-acquisition fixture first produces two genuine adjacent links. The last record is then changed
to point to acquisition 1 instead of acquisition 2 while retaining `established: true`. The chain
report must return zero current contiguous links rather than two.

## Boundary

No frozen experiment, result, protocol, sealed bank or scientific decision is changed. This only
narrows the DEVELOPMENT summary emitted by `Genesis.causal_chain()`.
