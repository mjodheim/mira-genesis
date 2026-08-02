# M031 — Structural transport of component guidance

M031 tests whether M030's uniform component signal transports from pair-reversal tasks
to a split-scaffold generator of eight cyclic and permuted triads.

- [`PROTOCOL_DRAFT.md`](PROTOCOL_DRAFT.md) freezes the generator, seed boundary and
  decision gates.
- [`STATUS.md`](STATUS.md) records implementation and result status.

All unit and smoke validation uses seeds 64 and above so primary seeds 0–63 remain
unobserved until the pre-result commit is frozen.
