# M063 — development result

**Status: POSITIVE LOCALLY; PENDING QUALIFICATION.**

## Verdict

The bounded arrangement mechanism transfers from M062's byte-copy body to a byte-checksum body.
The target has a different interface and observable effect: it reduces memory into a local
accumulator, returns the sum and leaves the entire memory unchanged.

This is not a general compiler result. The checksum decomposition, three steps, finite grammar,
emitter and evidence cases remain authored.

## Exact local result

- six M061 structural scans replayed;
- 256 region bytes scanned;
- exit-region effect class preserved as `{0x02, 0x06}`;
- repeat-region effect class preserved as `{0x03}`;
- **96** checksum arrangements constructed;
- **6** arrangements survived all three public cases;
- all six survivors passed all three hidden cases under both exit-region representatives:
  **12 / 12 complete programs admitted**;
- the selected module is **91 bytes** with zero imports;
- every committed observation reported byte-identical memory before and after execution;
- deterministic re-emission produced identical module bytes.

The selected source arrangement is:

- topology: `block_then_loop`;
- predicate: `remaining_le_zero`;
- exit position: `0`;
- step order: `decrement_remaining`, `accumulate_byte`, `advance_source`.

The step order is one representative of a six-member admitted class. It is selected by digest
only after the whole class passes hidden admission.

## Cross-body control

M062's selected copy arrangement has digest
`0c6334a9384cbd52db9713ff18c95c8d713ccd9e4ff91e79cbcf674a13f0eadb`. Executed as a checksum
body, it passes the zero-byte case and fails both non-zero cases. The control is therefore
rejected exactly where the tasks diverge.

This prevents the positive verdict from being based on naming the old copy body differently.

## Evidence identities

- M063 protocol digest:
  `4ac3f4629771a4f111bcadd83b8cc9e17a5723e7198de6b392b7ae9081156e02`;
- M062 source-mechanism protocol digest:
  `3780dc998a5df0cee783ba435671e1b349b27e9cd96315130ae7a34f41e7b97e`;
- public synthesis evidence digest:
  `c7cc7f08efccfe32357af77517bd21b92af847d0fc240c9d201d9fa89922b76c`;
- selected arrangement digest:
  `2c621083f6c9394877d5b87e4b9a6aff5452e762d7c0c8e6df7442a20e3ba383`;
- independent hidden evidence digest:
  `88fa4e6edac27013e664ce1d0332c4d37914695f8633c7acb9e74cf546d9afbc`;
- copy negative-control evidence digest:
  `e10c77dccc82be7d087830ab86993fd62ede5715cc76ae7925a1545a3adc3412`;
- complete manifest digest:
  `c2f0cdb05bef741b003740c2148fe3ad5d8bf78b802085c8234fa77fe0779107`.

## Local verification

- rapid falsifiers: **14 passed in 1.03 seconds**;
- complete M063 file: **16 passed in 130.94 seconds (2:10)**;
- joint M062–M063 regression: **31 passed in 310.38 seconds (5:10)**;
- complete repository suite: **1,054 passed in 1,763.31 seconds (29:23)**;
- repository integrity: imports clean, no orphan modules and declared dependencies match imports;
- a second complete deterministic execution emitted the same manifest digest.

No negative qualification run exists yet because qualification has not been launched. No
development defect was found during these two complete executions. This statement is not a
substitute for the required GitHub matrices.

## What changed in the supported claim

M062 showed that one finished copy-loop arrangement need not be supplied. M063 shows that the
same bounded control-search pattern is not confined to copying: it constructs a reduction loop
with an accumulator, a different function signature, a different observable output and no
memory write. The old body fails the new task.

The supported claim is therefore **bounded transfer of an arrangement mechanism across two
executable body families**.

## What remains open

A person still supplies the task decomposition, atomic steps, grammar family, emitter and
evidence cases. Repeating the same pattern on a third small loop would not materially advance the
frontier. A successor must remove an authored grammar/emitter handhold or move directly to the
frozen real-substrate completion question.

Nothing here supplies the four-arm post-migration plasticity comparison, three accepted cycles
across genuinely new held-out families or a protocol frozen before a canonical run. Gates 8–10
remain open on real substrates.

## Qualification disposition

Pending. The exact experiment head and the first GitHub Actions verdict will be appended without
changing the experiment implementation. A failed scientific job will remain a negative result;
an infrastructure-only failure will be classified under D017.
