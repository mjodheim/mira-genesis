# M064 — whole-WebAssembly development result

**Status: POSITIVE IN DEVELOPMENT — CANONICAL RUN NOT YET ARMED.**

## Verdict

The same reconstructed lineage crosses CPython v6 → Node ESM v8 → whole WebAssembly v9 and then
accepts three complete native rewrites to v12. Across every one of four precommitted bank entries,
the complete arm passes 18/18 hidden observations while the fresh, unchanged-parent and
learned-state-ablated controls each pass 0/18 under the same per-cycle budget.

This closes the development work for gates 8 and 9 on a real complete-body substrate. Gate 10 is
not claimed here: the unique marker-only run and independent reproduction remain to be executed.

## Development-bank results

| Bank | Manifest SHA-256 | Complete | Fresh B | Parent | Ablated |
|---:|---|---:|---:|---:|---:|
| 0 | `fc663fa6f0eebb73238cff1e9338db37e9d95dbc8e07fd99888a93402a65f6e6` | 18/18 | 0/18 | 0/18 | 0/18 |
| 1 | `5557da22e075cf7226ad56e59da5010b8abd8c8cc6b7660f0605e598f532a2e3` | 18/18 | 0/18 | 0/18 | 0/18 |
| 2 | `156768e27e23208be8f52bc7638e00e1cc736545ecde9e8612229474c29e928a` | 18/18 | 0/18 | 0/18 | 0/18 |
| 3 | `988d46a3e7d6ad64e0fa4b437f8d8e5c4f3d3ec19d73bdeea0c690583b47432a` | 18/18 | 0/18 | 0/18 | 0/18 |

The manifests differ because each bank commits different immutable tokens and case values. Their
decision structure is identical.

## Native migration evidence

- 256 arithmetic opcode bytes scanned;
- four required arithmetic operations uniquely resolved: `add=0xa0`, `mul=0xa2`, `div=0xa3`,
  `max=0xa5`;
- six M061 structural shapes replayed and ten effects recovered;
- initial complete module: 1,834 bytes, zero imports, 32/32 inherited capabilities;
- zero semantic modules left in Node;
- final selected modules: 1,887, 1,962 and 2,037 bytes;
- all 68 final retained cases pass.

The compiler and block structure remain authored. That boundary is recorded in the manifest next
to the discovery evidence.

## Search and admission evidence

The complete arm constructs 740, 1,496 and 2,668 expressions. The public evidence leaves 12, 8
and 8 survivors. Every one is independently recompiled, inspected for zero imports and executed
against retained, public and hidden evidence before a digest selects a representative.

The selected route references are:

1. `max`, `mean`;
2. `add`, the learned cycle-1 route, `max`;
3. the learned cycle-1 route, the learned cycle-2 route, `mul`.

Each control constructs 200 expressions per cycle and has no public survivor. Fractional public
targets expose the missing learned `mean`; a control is not rejected by a label or a manifest
constant.

## Transaction and continuity evidence

- patch records: 3;
- exactly archived parents: versions 9, 10 and 11;
- final version: 12;
- one causal-memory episode appended per accepted rewrite;
- forced provisional version 10 rejected after journal corruption;
- state bytes and retained behaviour restored exactly;
- deterministic replay from version 9 reproduces the final state digest.

## Cost accounting for the complete arm

- expressions constructed: 4,904;
- public candidate processes: 28;
- independent inspection processes: 28;
- independent admission executions: 28;
- total bounded native-host invocations: 95;
- accepted rewrites: 3.

Every arm receives the same ceiling of 8,192 expressions per cycle. M064 claims higher exact
quality, not lower realised cost.

## Permanent falsifiers

- protocol or task-bank drift raises at construction;
- the task bank must be selected after all four migration events;
- the proposal signature has no hidden evidence;
- a corrupted module byte fails compiler-trace replay;
- an import-bearing module cannot pass independent safety admission;
- every public survivor, not only the selected digest, must pass hidden admission;
- a tied control falsifies strict advantage;
- a broken journal-to-patch link triggers exact rollback;
- final state, body archive, patch registry, memory and journal counts must remain continuous;
- the passive validator has no adoption state;
- the marker guard binds one exact parent, protocol file and task-bank commitment.

## Development execution note

The first four-bank WebAssembly test invocation completed every scientific run. Nineteen tests
passed; one fixture assertion expected intermediate
module sizes of 1,903/1,970 rather than the observed 1,887/1,962. The final 2,037-byte module and
all scientific outputs matched. The assertion was corrected without changing the engine,
protocol, bank, threshold or result. The clean rerun passed **26/26 tests in 274.65 seconds** and
emitted the four final manifest digests above. Fields binding the later canonical marker were
added before that rerun; no executable or scientific commitment changed.

The exact pre-freeze tree then passed the complete repository suite: **1,085 tests in 2,035.10
seconds**. The portable historical `FROZEN_PROTOCOL.json` now has SHA-256
`f05f0fdda2f9de03eee149b5a83dde290e576d164b4e2226333fbe10f45c7a4b`.

## Qualification outcome

Exact parent `ec92af78b57203d32c2ee504db91b4166ec83fdf` failed GitHub run
`31281234286`, attempt 1. Python 3.11 passed 1,084/1,085 tests in 1,037.15 seconds and Python 3.13
passed 1,084/1,085 in 1,094.43 seconds; both rejected a checkout-dependent source hash. Integrity
and attribution passed. Review also showed that the rollback receipt compared the untouched saved
input to itself. No marker was created. M064 is closed as negative pre-canonical qualification;
the required scientific correction is M065.
