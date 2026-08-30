# M115 — instrument-aborted at strict-JSON admission; H60 untested

**Date:** 30 August 2026

**Hypothesis:** H60 — **untested**

**Verdict:** `instrument-aborted`

## What happened

The frozen M115 delivery sequence made one physical request and materialized one response. The
runtime identity gate passed for the requested alias `deepseek/deepseek-v4-flash-0731`, the required
canonical checkpoint `deepseek/deepseek-v4-flash-20260731`, and the selected provider `Alibaba`.
The response was sealed before the tested system was frozen and before reveal was authorized.

The single authorized reveal then decrypted the committed response in process memory. The runner
recomputed its provenance and runtime identity successfully, but the materialized completion was not
valid JSON. The frozen host therefore refused it before carrier-bank schema validation. No carrier
payload existed for the host, qualification did not begin, and no carrier content was printed or
written to the repository.

| quantity | observed value |
|---|---:|
| physical delivery attempts | 1 |
| bank materializations | 1 |
| accepted carriers | 0 |
| qualifying carriers | 0 |
| distinct qualifying structures | 0 |
| P1–P22 computed | 0 |

## Why this is not an insufficient-bank result

The frozen cardinality rule says that a payload the host refuses is not a carrier. The
insufficient-bank rule applies only after a valid carrier payload has entered the frozen
qualification machinery. Here, strict-JSON admission failed first. The minimum bank criteria were
therefore not met, but the pre-registered negative insufficient-bank verdict was not reached.

`invalid_json` is explicitly in `ANALYSIS_PLAN.json`'s `never_retried` set. The observation is
terminal: the completion was not repaired, selected, curated, regenerated, or retried. H60 remains
untested, and P1–P22 are all `not_computed`.

## Independent replay and custody

The one permitted independent checker replay revalidated the frozen reveal chain and reproduced the
same `invalid_json` terminal outcome. It printed no carrier content and wrote no plaintext generation
response. `GENERATION_RESPONSE.json` is absent; the ciphertext and public commitment remain the
preserved bank record.

No generality or completion gate moved. M113 and M114 remain unchanged.
