# M122 complexity budget

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H67 observation exists.

M120's budget said the instrument may grow only where growth is cheap, mechanical, and fails in
DEVELOPMENT rather than after a spend. That held: M120 died at a DEVELOPMENT gate for sixteen
requests rather than at a qualifying generation. The budget worked even though the milestone did
not.

So M122's budget is the same one, with the ledger carried forward and two entries added.

## What may not grow

Inherited from M119 by import, exactly as M120 inherited it, and forbidden to change:

| | |
|---|---|
| Arms | four, the same 2×2, plus the one fenced diagnostic arm |
| Primary comparison | `FULL` against `FRESH`, fixed in code |
| Endpoint | paired per-demand correctness, one way to win |
| Test | one-sided exact McNemar, α = 0.05, ten-point effect floor, both required |
| Guards | three, one direction each, veto only |
| Verdicts | four |
| Comparator seed | the committed constant, unchanged |
| Observation budget | 4000, inherited from M113 |
| Admissibility minimums | 3 qualifying carriers, 3 distinct structures, inherited from M115 |

## What M122 removes

This is the unusual entry, and it is the point of the milestone.

**One array, not two.** M120 split `actions` into `conditional_actions` and `actions` to express
"at least one action carries a precondition" without `contains`, which this route does not enforce.
The split duplicated the action subtree and took the census from five array-of-object levels to
eight, which this route also does not enforce.

The guarantee it bought was measured after the fact and was not worth its price: carriers with no
guarded action occur at 0.75% at the smallest shape and 0.00% across the family, and the
alternative — requiring *every* action to be guarded — costs yield rather than buying it, 36.5%
against 52.2%, because gating everything makes states unreachable.

**A budget that only ever adds is not a budget.** This is the first entry in this line that takes
something out, and it makes the instrument simpler, shallower and better-yielding at once.

## What is added, and the failure each closes

Two, and both come from M120's outcome rather than from ambition.

1. **`_assert_within_the_certified_census`** — the contract fails at import if its own census
   exceeds the nesting the route has been observed to enforce.
   *Closes:* M120's census drifted from five levels to eight as its representation changed, nothing
   in the apparatus said so, and a single-use readiness gate spent sixteen requests discovering it.
   A contract that cannot state its own serviceability will be found unserviceable later and at a
   worse price.

2. **Two corrections to the readiness gate**, both named in M120's outcome:
   - identity is attested only on responses that carry a completion, because a retry-exhausted 429
     is a delivery outcome and not a substituted route. M120's verdict said `not_ready_identity`
     when the finding was a feature class;
   - `finish_reason: length` on a probe is its own recorded class rather than folded into
     non-conformance, because 101,379 tokens against a fifty-token requirement is enforcement
     failing open and deserves to be named as such.

## What is refused

- No second route, no fallback, no provider substitution.
- No additional arm, ablation, rollback or budget cell beyond the one M119 already fenced.
- No second generation, no redraw, no repair, no resample, no selection among outputs.
- No threshold, minimum, guard or decision rule rewritten for M122.
- No DEVELOPMENT branch inside the qualifying scripts.
- No repair of M115–M120. M120's closure stands and its disclosed defects are requirements here.
- **No re-running the readiness gate until the route agrees.** It is single-use once committed, and
  a gate redrawn until it passes is not a gate.

## The running count

| | M118 | M119 | M120 | M122 |
|---|---|---|---|---|
| Principal arms | 9 | 4 | 4 | 4 |
| Diagnostic arms | 0 | 1 | 1 | 1 |
| Primary comparisons | 1 | 1 | 1 | 1 |
| Routes | 1 | 1 | 1 | 1 |
| Generations permitted | 1 | 1 | 1 | 1 |
| Reveals permitted | 1 | 1 | 1 | 1 |
| Candidate arrays of actions | 1 | 1 | **2** | **1** |
| Array-of-object levels asked of the route | 5 | 5 | **8** | **5** |
| Gates before the seal | admission | admission | admission, adequacy | admission, adequacy |
| Gates before the freeze | readiness | inherited | sizing, rehearsal, readiness | depth diagnostic, sizing, rehearsal, readiness |

The instrument gained one pre-freeze diagnostic and lost one array. That is the direction this
budget permits, and the only one.

## Order of operations, changed deliberately

M120 built its entire apparatus and then discovered at the readiness gate that its contract was
unserviceable. M122 inverts that: the route was asked about the contract's depth **first**, for two
requests, and the readiness gate runs **before** the rest of the apparatus is written.

A milestone that builds everything before checking whether the route will hold its schema is a
milestone that can waste all of it. This one is ordered so the cheapest disqualifying question is
asked first.
