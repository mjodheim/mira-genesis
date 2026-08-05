# M042 frozen protocol

**Status: frozen before the first canonical M042 execution.**

The consumed development run on commit `cefff2f302eb1019117a8b6450a10d9daab52386` completed successfully in workflow run `30945798437`. Its artifact digest is `sha256:ebff088049cf3e0995e357597f963705de117f665956f8203255ea8576dd0749`; the uncompressed result digest is `6ce6f6810c0b373dc9f8e6c2378cf2c367a00c41fc65b2921aa43474b3bd94b1`.

The immutable M040 base, M041 passive validator, bank-generation range, admission rules, controls, search depth, node budget and rollback rules are exactly those implemented and tested by the frozen M042 code. No M038–M041 input or result may be altered.

## Frozen bank

The bank is generated from seeds `420000` through the next 128 attempts, retaining exactly the first four entries satisfying every predeclared admission rule. Its ordered entry digests are:

1. `18b9c18828dbcd72fe91ca970cbdaebba59b5c6446b432642e70fc9b51fca0dd`
2. `9b6a201b642073aa76fc4639324f0bd20e5184346496d94a96b7599609fde9aa`
3. `732c5c86b67b13826cfb46dc1d839577ff32af8d3afc882f8abf0b0fe95a8442`
4. `60d30b5b35e2ff06f3735cfe4fe68196c9086959dd440769f66776eda43976d3`

The bank replayed identically, all four entries passed constructive availability, complete controls, native synthesis, exact rollback and passive isolated validation, and the complete continuous lineage satisfied gates 1–9. Gate 10 remains false during development because no canonical result has yet been observed.

## Canonical selection

The canonical index is fixed before execution by:

`uint64_be(sha256(selector_material)[0:8]) mod 4`

with selector material:

`M042 canonical selector v1|ebff088049cf3e0995e357597f963705de117f665956f8203255ea8576dd0749|cefff2f302eb1019117a8b6450a10d9daab52386`

The selector digest is `8a093e3bd5f7cb923cd4742fe4cb44232c88b4c51af5c9589836a795b8c83ed1`, fixing canonical index **2** and entry digest `732c5c86b67b13826cfb46dc1d839577ff32af8d3afc882f8abf0b0fe95a8442`.

## Immutable execution rule

The first canonical execution must use Python 3.11 and 3.13 guardrails, symbolic depth four, 4,096 nodes, 127 observations and the exact frozen selector. The first result is preserved regardless of sign. No threshold, seed, bank order, rule, control or validator may be changed after this freeze to alter the outcome.
