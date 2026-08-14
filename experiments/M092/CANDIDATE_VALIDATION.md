# M092-B candidate validation boundary

**Status: implemented after protocol freeze; no extension search or qualification has run.**

`metamorphosis/m092_candidate_validation.py` is the structural and anti-cheating gate in front of
the exact certificate verifier. It executes no candidate, reads no qualification artifact and
imports only the frozen K1 kernel plus the neutral M092 runtime vocabulary.

## Structural gate

For every proposed program/certificate pair the gate recomputes and records:

- K1 structural validity and the fourteen-instruction limit;
- the exact allowed/forbidden opcode partition from the frozen protocol;
- the literal set `{-1, 0, 1}`;
- at most one backward-jump target/loop header;
- SHA-256 binding between the certificate and exact canonical program bytes.

Malformed candidates produce a deterministic refusal report without being executed. Global
correctness, termination and frame soundness remain separate obligations of
`m092_certificate_verifier.py`; passing this scanner alone can never authorize registration.

## Executable anti-cheating scan

The scanner recursively inspects the certificate and generated support artifacts under closed
depth, node-count and byte limits. It refuses:

- direct input/output rows or numeric-keyed lookup tables;
- hexadecimal, binary, base64-like or explicitly labelled packed masks;
- chains of equality tests over an input;
- Python callables, callback/import fields, import text or host-function declarations;
- candidate-specific fixtures or expected answers;
- target names in executable support artifacts;
- output vectors sized like a frozen verification/qualification domain;
- large integer sets capable of carrying outputs.

The required SHA-256 `program_digest` field is narrowly exempted from the packed-mask heuristic;
its value is independently compared with the recomputed program digest.

## Five positive controls and clean restoration

`scripts/check_m092b_candidate_scanner.py` injects exactly the five fixtures frozen in
`PROTOCOL.json`: a direct table, encoded bit mask, equality-chain lookup, host callback and
wrong-program-digest certificate. Each is rejected for its expected code. The callback raises if
called, so the passing self-test also proves it was inspected rather than executed.

The neutral baseline digest is
`636fadd483f1df1ca9fa7b558125955df6e79912d3d1b2378dbdaa8bb11df0c9` before and after all
fixtures. The self-test digest is
`585332e85b09d3cbf70037f6a3b7d0b881ba691fa74e5069333410d7799ef58f`.

The same checker passed in a local `python:3.13-slim` container with the repository mounted
read-only, a read-only root filesystem, a 16 MiB no-exec `/tmp`, and `--network none`. No image was
pulled during that replay. CI runs the checker directly on Linux as a decisive pre-result boundary.

These fixtures are rejection controls explicitly authorized by the protocol, not candidate search
or qualifying data. No target candidate, `SUBSTRATE_B`, receipt, result, H38 or D062 claim exists.
