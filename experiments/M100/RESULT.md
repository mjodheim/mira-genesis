# M100 scientific result — positive

M100 attempt 1 is a **positive qualified scientific result**. H45 is supported inside the frozen
bounded affine-operation domain. The independent checker recomputed all twelve conditions true,
with no failed or uncomputed condition.

## Cumulative chain

The canonical local run began from clean freeze commit `c4214d6` and used zero model, network or
remote calls.

```text
S0: 0 operations — B absent
S1: A = subtraction
S2: A + acquired B = addition
S3: A + B + acquired C = left + 2×right
```

B was acquired only after A registration: 780 programs assembled, 28 well formed, two accepted,
shortest length four. C was acquired only after B registration: 9,330 assembled, 202 well formed,
six accepted, shortest length five. Building B without registering it left S1 unchanged and C
absent. Every S1 definition remained byte-identical in S2, and every S2 definition remained
byte-identical in S3.

After S3, A, B and C each passed three fresh real-Python worlds and four cases per world: 9/9 worlds
and 36/36 cases. All 24 migration, acquisition, control and execution invocations used fresh base
Python `-I` processes, imported no project module and exposed no repository import path.

## Causal controls

- B was absent without A; C was absent without registered B.
- A digest-valid semantic mutation broke B.
- A digest-valid B mutation broke C.
- Removing A or B and corrupting state failed closed.
- A live digest-valid S2 fault suppressed C acquisition.
- Restoring the exact original S2 bytes reproduced the exact original S3 in a fresh process.
- Clean replay changed process identifiers but no retained scientific field.

## Boundaries

This result demonstrates bounded cumulative constructive reach, hard process separation,
conservation, reuse and live transitive dependency across one authored affine-operation family. It
does not demonstrate unbounded expressivity, open-ended evolution, AGI, arbitrary self-modification,
a self-hosting interpreter, endogenous objective choice, cross-domain transfer, independent human
reproduction or production authority.

The next ceiling is transfer of the cumulative relation to materially different operation families
and observed demands, rather than another authored affine signature inside the same interpreter.

## Immutable evidence

- protocol/pool/mechanism freeze: `c4214d6`;
- source commit recorded by the run: `c4214d6bdaeb1326c9dcd6d336ff1d4173c96c98`;
- result digest: `241292fc81e64c8e0ec4620e72304889f52ae2185033e056b787f1b27c6c1475`;
- stable evidence digest: `4bdb1aa8f7a85108eac4e92f8cff90f05a12520462e5ea2b358fc9b5886b19da`;
- checker digest: `d8e945a595571505d9c2a44568029208f41f05010e36d8e7b3f5937016529654`;
- preservation tag: `experiment/m100-positive-result`.

Post-result repository integration added `scripts/m100_runtime.py` as an import-only relay so the
global module/dependency audit can inspect the isolated entry point in place. It is not copied into
the capsule, is absent from the frozen mechanism and apparatus bindings, and does not alter the
canonical run or replay.
