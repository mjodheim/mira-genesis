# M124 complexity budget

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H69 observation exists.

M123 closed at `not_ready_stress`. Its sizing was correct, its delivery was clean, and its contract
held. **One rule killed it**, and that rule is the only thing this milestone is permitted to change.

## What may not grow

Inherited by import and forbidden to change:

| | |
|---|---|
| Arms, endpoint, exact test, α, effect floor, guards, verdicts, decomposition | M119 |
| Comparator and its committed seed | M119 |
| Observation budget, 4000 per demand | M113 |
| Admissibility minimums, 3 qualifying carriers and 3 distinct structures | M115 |
| Fixed route | M118, byte-unchanged |
| Threshold, 32,000 tokens | M118, unmoved for four milestones |
| Pre-seal adequacy gate and its information boundary | M120 |
| Carrier contract and its decoder | M122, route-validated |
| Stress schema shape | M122, route-validated |
| **Stress size, 109 stations** | **M123, and it predicted out of sample** |
| Delivery allowance and its cross-milestone ceiling | M123 |

The last two are new to this list. M123's sizing rule earned its place by making a prediction and
being right; re-deriving it would discard the only method in this line that has ever worked.

## What changes, and the failure it closes

**One.**

**A completion carrying no `finish_reason` is a delivery outcome, not a scientific one.**

*Closes:* M123 returned HTTP 200 with 50,232 tokens, a body that does not validate, and no
`finish_reason` at all. `holds` requires `finish_reason == "stop"`, so the verdict was
`not_ready_stress` — terminal — and the milestone died on a response the route never reported as
finished. The classification was left, deliberately and on the record, for a successor to decide
prospectively.

**Decided before any request is sent, and bound into the plan digest**, so it cannot be adjusted
after a result is seen.

### The boundary, which is the substance of the decision

| observed | classified | retryable |
|---|---|---|
| `finish_reason: "stop"` | scientific | no |
| `finish_reason: "length"` | **scientific** | **no — stays terminal** |
| `finish_reason` **absent** | **delivery** | yes, within the allowance |

Truncation stays terminal. It is a fact about the size this instrument asked for, and making it
retryable would let an oversized stress be re-run until it passed — the gate tuned to itself.

## What is refused

- No second route, no fallback, no provider substitution.
- **No change to the 32,000-token threshold.** Four milestones, unmoved.
- **No change to the stress size.** It worked.
- **No re-authoring of the contract.** M122 validated it twice.
- No re-running a verdict that is not `not_ready_delivery`.
- No additional arm, no second generation, no redraw, no repair, no resample.
- No repair of M115–M123. Their disclosed defects are requirements here.

## The running count

| | M120 | M122 | M123 | M124 |
|---|---|---|---|---|
| Array-of-object levels asked of the route | 8 | 5 | 5 | 5 |
| Capability probes conforming | 7 of 9 | 9 of 9 | **9 of 9, first ask** | inherited |
| Contract re-authored | yes | yes | no | **no** |
| Sizing observations | 0 | 1 | 3 | **4, two censored** |
| Model fitted to them | — | proportional | none | **none** |
| Stress stations | 24 | 74 | 109 | **109, unmoved** |
| Stress outcome | — | 30,957, short 3.3% | 50,232, **inside the predicted band** | *pending* |
| Verdict rules changed | — | — | — | **one** |

The instrument has stopped growing. M124 changes a single classification and nothing else.

## The limitation that outweighs this budget

At a fixed 109 stations the schema permits conforming completions spanning about **4×**, wider than
the **3.15×** pass window. Station count is not the only variable that decides the verdict.

Pinning the inner array cardinalities removes that freedom and leaves M122's validated census
**bit-identical** — verified, not assumed. It is not done here because every sizing observation was
measured unpinned: pinning would improve the instrument and discard its calibration in one edit.
**That is the next milestone's work, and it should budget for re-calibration rather than inherit a
size.**

## Order of operations

Unchanged, and for the reason four milestones have now demonstrated: the readiness gate runs
**before** the rest of the apparatus is written. M120 built everything and then learned its contract
was unserviceable. If this gate fails, almost nothing is wasted.
