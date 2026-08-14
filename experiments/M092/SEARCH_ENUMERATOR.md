# M092-B deterministic search enumerator

**Status: pre-search infrastructure only. No target search or qualification has run.**

`metamorphosis/m092_search_enumerator.py` turns the frozen K1 candidate grammar into a bounded,
reproducible proposal stream. It has no target postcondition, executes no K1 program, constructs no
certificate and cannot import qualification material.

## Frozen surface

The implementation re-declares and tests against `PROTOCOL.json`:

- seed `9202`;
- raw-proposal cap `2,000,000`;
- maximum program length `14`;
- literals `{-1, 0, 1}`;
- the exact twelve allowed and seven forbidden K1 opcodes;
- in-program jump targets and no more than one loop header for a structurally surviving proposal.

Lengths 6 through 14 are visited breadth-first. M092-P already proves that a loop-free K1 program
cannot meet the global requirement, so spending the frozen cap on straight-line programs would add
no information. The grammar therefore emits a single structured loop. Within one length,
domain-separated SHA-256 of the frozen seed, layout, position, register frontier and typed
instruction fixes the order. Register identifiers are alpha-normalised by first occurrence; because
K1 initializes all eight registers identically and cannot observe a register name, this removes
renaming duplicates rather than behaviours.

The first pass uses the stack contract as a target-neutral canonical frame: `SPOP r0`, zero or more
literal initialisations, a conditional exit, one or more affine updates, one fixed back edge,
optional exit updates, then `SPUSH r; HALT`. A finite control-flow abstraction rechecks that paths do
not pop the opaque prefix, grow above entry depth, halt at the wrong depth, make code unreachable or
introduce multiple loop headers. This is a deliberately bounded search grammar, not an impossibility
proof about programs outside that canonical frame.

A naive Cartesian layer contains 2,838,822 length-seven programs and more than three billion at
length eight, so exhausting each shorter length would consume the two-million cap before later
lengths existed. The enumerator therefore derives a target-neutral breadth-layer quota from only the
remaining frozen budget and number of remaining lengths. Length six is exhausted at 3,324 programs;
the unused allocation carries forward, and every length through fourteen receives roughly 249,584
ordered proposals. The exact cardinality, quota, emitted count and truncation flag for all nine
layers are part of every audit snapshot. This is a deterministic beam over breadth layers, disclosed
before target search; truncation can never support an impossibility claim.

## Resume and provenance

Every raw emitted proposal receives:

- a one-based ordinal counted against the frozen cap;
- exact canonical program bytes and SHA-256 digest;
- the recomputed loop headers and structural refusal reasons;
- a digest-bound cursor containing the program length and typed decision path;
- an order-sensitive event-chain commitment linked to the previous proposal.

The cursor resumes directly inside the current length instead of replaying earlier sibling
subtrees. The audit refuses a forged program digest, classification, ordinal or cursor. Its JSON
snapshot carries its own digest and explicitly records that no target postcondition, candidate
execution or qualification material was loaded.

`python -m scripts.check_m092b_search_enumerator` reproduces the first 512 raw proposals both in one
pass and across a serialized split at ordinal 137. Both routes end at event-chain digest
`ec345bf1...3268a`, with zero structural refusals from the typed normal form and exact resume
equivalence.

These raw programs are **not candidates** under the frozen protocol: a candidate is an exact K1
program paired with a candidate-supplied global certificate. No certificate generation, semantic
observation, behaviour deduplication, validator receipt, `SUBSTRATE_B`, result, H38 claim or D062
decision exists at this stage.
