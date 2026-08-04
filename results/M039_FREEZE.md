# M039 — canonical freeze record

**Status: frozen before task derivation.**

This record freezes the tested M039 mechanism and exact protocol bytes before the unique
marker-only arming commit. At the parent tested below:

- no canonical marker existed;
- no canonical master nonce or task seed had been derived;
- no canonical founder, target, observation, candidate or result had been observed;
- all development tasks were already consumed and excluded from canonical evidence.

## Frozen identities

| Identity | Value |
|---|---|
| Pull request | `#54` |
| Tested mechanism parent | `28ca27b33c5ef661e01b28828bc59f8fb52369fd` |
| Protocol path | `experiments/M039/PROTOCOL.md` |
| Protocol bytes | `11688` |
| Protocol SHA-256 | `007d0dcb7581e3e4a8adb25605b103036d1c4b2d9eb933e1973fe1de5c698625` |
| Protocol Git blob | `34c9cba11b3c09ada2739365e20d8dff30c4ae6b` |
| Freeze-identity workflow run | `30907036238` |
| Freeze-identity artifact | `8891453915` |
| Freeze archive digest | `sha256:e5ef6d9b4650ffe220652175a4736dc1ce3e54847319d9db2e68222a76e77bf6` |
| Permanent CI run | `30907174460` |
| Canonical workflow | `.github/workflows/m039-canonical.yml` |
| Exact arming message | `m039(canonical): arm first immutable run` |

The freeze-candidate workflow calculated the identity directly from the repository bytes and
asserted both `canonical_marker_absent = true` and `sealed_seed_not_derived = true`.

## Permanent verification before freeze

The complete repository, including all historical experiments and permanent M039 tests,
passed on the exact tested parent:

| Check | Result |
|---|---|
| Repository integrity | pass |
| Python 3.11 | **498 passed** in 493.85 seconds |
| Python 3.13 | **498 passed** in 497.10 seconds |
| M039 guard on ordinary commit | pass; install/run/upload skipped |

The M039-specific suite covers:

- contiguous F0 → F1 → F2 → F3 manifests;
- protocol-supplied versus lineage-constructed provenance;
- construction inputs that must predate the macro;
- later adopted reuse and equal-budget ablation dependency;
- exact `ToolConstructed` and `ToolReused` verification from persisted bytes;
- multi-cycle journal ordering, state continuity, tampering, deletion and reordering;
- cycle-zero relabelling attacks;
- rollback without audit erasure;
- seed-only replay input boundaries;
- exhaustive evidence-rejected search transcripts and registry ordering;
- marker-only arming and domain-separated sealed seed derivation.

## Consumed development evidence

The final development artifact remains diagnostic only:

| Identity | Value |
|---|---|
| Consumed seed | `390039` |
| Development head | `8bcd8dccf1fd34934d452b518b2b979caa95029a` |
| Workflow run | `30906574031` |
| Artifact | `8891290506` |
| Artifact SHA-256 | `935dbebc773394881e46405f3dcb923ee246c555b61ba2a41d6aa456e816fffa` |
| Manifest digest | `faa418a69ea5e8f00b78f2e8add82c8647e758fd4700cbf3d357e074c3328207` |

That seed revealed three tasks and exposed three mechanism defects that were repaired before
this freeze: semantic cycle membership, self-reported provenance and uncommitted hidden
search rejections. It cannot support the canonical result.

## Frozen first-run rule

The child of this freeze record must change exactly:

```text
experiments/M039/CANONICAL_ARMED.json
```

with the exact commit message:

```text
m039(canonical): arm first immutable run
```

The marker must name this freeze-record commit as its direct parent and the protocol digest
above. The SHA of that child and the frozen protocol digest reveal the task seed for the
first time.

The resulting scientific outcome—positive, negative, generator exhaustion or bounded search
failure—will be preserved as the unique first canonical artifact. No replacement seed,
budget widening or second first run is permitted.