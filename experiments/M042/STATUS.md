# M042 status

## Current phase

**Canonical result: positive. Experiment closed.**

The unique frozen canonical execution completed on head `ae8b4dce2cb737fc51dc0fa3a9ffcae494ef1cdb` and its first result was preserved without re-execution or retuning. The selector chose index `2` with entry digest `732c5c86b67b13826cfb46dc1d839577ff32af8d3afc882f8abf0b0fe95a8442`.

## Canonical identities

- frozen protocol commit: `c75e57cfb23bcaccab98f449bfef0d83fe530ad4`;
- marker-only canonical head: `ae8b4dce2cb737fc51dc0fa3a9ffcae494ef1cdb`;
- first workflow run: `30958542929` (attempt `1`);
- frozen protocol SHA-256: `d3d2b60a23d5847238aaec87e0d04200b707761ba8e0eb1418632e59dd39a366`;
- exact raw result SHA-256: `2d6c75abf526f0b3a3edba381f6f7b820d4dd03ccc3276784301e3c6a65b7830`;
- exact first-result seal SHA-256: `bc39b5d494efcefa6fbfbf95170b2fe38436e90e4168fac9a347030a56e404b2`;
- GitHub artifact digest: `sha256:14abb40f77c5fe3821c7e87f3d3078e378e0763efa1cd4a68296d7224f30de38`.

The immutable raw result, raw seal and post-result audit are preserved under `results/artifacts/`; the report is `results/M042_CANONICAL_RESULT.md`.

## Verdict

The selected task was constructively available; the complete lineage reached 127/127 exact observations while every equal-budget ablation remained non-exact. Passive isolated validation, native synthesis and exact rollback all succeeded. Gate 10 is established by the separate first-result preservation record, leaving the raw payload and seal byte-identical. All ten audited gates are true.

## Closure boundary

No second M042 canonical run is permitted. M038–M041 identities and artifacts remain unchanged.
