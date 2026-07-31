# M012 — Implementation notes

## Increment 1 — Generic finite constraint synthesizer

The first implementation increment introduces:

- declarative primitive catalogues;
- one catalogue-driven expression synthesizer;
- native-body serialization;
- exact abstention when a contract cannot be expressed under a catalogue;
- no use of evaluation seeds and no M012 acceptance result.

This increment receives explicit finite transition constraints. It does **not** yet discover latent behavioural states from the black-box contract. Consequently it is infrastructure for M012, not a successful M012 experiment.

## Development observation

A quantized threshold catalogue without a primitive XOR can still synthesize XOR by composing OR, NAND and AND. The initial test assumption that this catalogue must abstain was therefore wrong; the control was replaced by a genuinely monotone restricted catalogue.

## Next increment

Add active behavioural-state discovery and connect it to the generic synthesizer without exposing a target DFA or calling the M010 compilers.
