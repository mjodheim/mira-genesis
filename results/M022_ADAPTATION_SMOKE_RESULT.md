# M022 — Seed-0 adaptation-stress control result

**Status: DEVELOPMENT CONTROL RESULT. Not frozen, canonical, or a selection-measure
comparison.**

## Run identity

- evaluated commit: `2296e778d443e57b44a533b143ea126cb6be3a97`;
- seed: 0;
- sequence: 12 episodes, three motifs repeated across four rounds;
- distinct source automata: 12;
- late rounds: 2 and 3, six episodes total;
- raw trace: [`M022_adaptation_smoke.json`](M022_adaptation_smoke.json);
- raw trace SHA-256: `1517ebebe8e27df26447238d002b7523e757a87e894eba27ebcfcd1c2aa8f9b6`.

The run used the gates already committed in
[`experiments/M022/PROTOCOL_DRAFT.md`](../experiments/M022/PROTOCOL_DRAFT.md). No gate
was changed after observing the result.

The raw trace contains every adaptive and frozen episode row in addition to the
aggregate diagnostics.

## Positive control — self-extending organism

- total solved: 12 adaptive, 12 frozen;
- late solved: 6 adaptive, 6 frozen;
- common late pairs: 6;
- adaptive late search nodes: **264**;
- frozen late search nodes: **59,358**;
- frozen/adaptive late cost ratio: **224,840 per mille (224.84×)**;
- learned macros after the adaptive sequence: **9**.

The positive control passed its 1,500-per-mille cost-separation gate by more than two
orders of magnitude without losing any late solves.

## Negative control — open search without absorption

- total solved: 12 adaptive, 12 frozen;
- late solved: 6 adaptive, 6 frozen;
- adaptive and frozen late search nodes: **59,358** each;
- frozen/adaptive late cost ratio: **1,000 per mille (1.00×)**;
- learned macros after the adaptive sequence: **0**.

The negative control remained exactly unchanged across the adaptive and reset
conditions, as required.

## Development conclusion

All seven pre-written gates passed. At seed 0, the M022 sequence detects state acquired
during the audit rather than merely measuring competence present before it. The
separation depends on absorption: an otherwise capable open-search organism receives no
benefit from persistence alone.

This result validates one deterministic smoke instance. It does not establish
cross-seed stability, compare M021-selected populations, or support a canonical claim.
