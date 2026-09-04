# M122 / H67 — preregistration

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H67 observation exists. Nothing below may be revised after the seal is broken.

## Status at the time of writing

- H67 is **not frozen**. No carrier bank exists. Qualifying scientific invocations: **0**.
- M113 through M120 are closed. Nothing here reopens, reinterprets or repairs any of them.
- M120 closed at its DEVELOPMENT readiness gate with **H65 untested**. Its two disclosed instrument
  defects are **requirements for this milestone**, not permission to edit that one.
- **No publication disposition is recorded for M122.** The proposed row remains the owner's to
  write or refuse.

## The hypothesis

**H67.** A descendant carrying both pieces of acquired machinery — the attribution cascade and the
diagnostic policy — resolves demands on carriers it did not design more often than a comparator that
carries neither, on demands posed identically to both.

This is **H64's proposition, unchanged**, and H65's before it. Neither was ever tested, so there is
nothing about the target to revise. What changes, again, is the instrument.

## What M120 established, and what follows

M120's contract was mechanically host-safe: every schema-valid candidate decoded into a carrier the
frozen host accepts, established over 240 exhaustive corners, 1,200 fuzzed draws and M119's own
committed bank. That property is inherited here intact.

What it lost on was depth. Its candidate schema needed **eight** array-of-object levels; the route
enforces five. The probe that measures that class returned HTTP 200 with `finish_reason: length`
after **101,379 completion tokens**, where enforcement would have produced roughly fifty.

The eight came from one place, and naming it precisely is what makes M122 a correction rather than
a guess. The frozen host requires that at least one action carry a precondition. JSON Schema says
that with `contains`, this route has no evidence of enforcing `contains`, and M120's workaround was
to split one `actions` array into two — duplicating the action subtree, and the census with it.

## The correction, and the measurement that justified it

M122 keeps **one** `actions` array, with `guard` at `minItems: 0`.

The guarantee that forced the split was measured rather than assumed:

| | |
|---|---|
| carriers with no guarded action, at the smallest shape the contract admits | **0.75%** |
| carriers with no guarded action, across the family | **0.00%** |
| requiring *every* action to be guarded instead — the other single-array option | **36.5%** qualification against 52.2% |

Requiring every action to be guarded makes states unreachable and the reachability clauses fail, so
it costs yield rather than buying it. M120 spent three nesting levels, and about sixteen points of
qualification rate, insuring against a 0.75% risk that the pre-seal adequacy gate would have caught
anyway.

So the guarantee is dropped and `the_carrier_imposes_a_protocol` is left to fail honestly on the
rare carrier that earns it. That clause exists to be able to fail.

## What the flattening bought, measured before anything was spent

| | M120 | M122 |
|---|---|---|
| array-of-object levels | 8 | **5** |
| decoded candidates the frozen host accepts | 400/400 | **400/400** |
| qualification, pessimistic corner | 28.75% | **33.5%** |
| qualification, uniform | 41.75% | **49.5%** |
| qualification, ceiling | 58.25% | **62.0%** |

Flatter, simpler and higher-yielding at once. That is unusual and is stated plainly rather than
dressed up: it happened because the thing removed was costing more than it was worth, not because
the redesign was clever.

## The route was asked, not inherited

M120's outcome instructs a successor to establish the depth on the route **before** adopting a
schema that needs it. Five levels was otherwise backed only by inheritance — M115's schema sat
there, M116 and M119 ran under it, M118's readiness gate certified that census — and inheriting a
measurement across a schema change is precisely the reasoning M120 existed to stop.

`scripts/audit_m122_route_depth.py` therefore asked directly, for two requests, before any more of
this milestone was built:

| depth | result |
|---|---|
| eight levels, M120's run | HTTP 200, `finish_reason: length`, 101,379 tokens, did not conform |
| **five levels, this run** | HTTP 200, **`stop`, 75 tokens, conformed**, identity held |

Recorded at `experiments/M122/ROUTE_DEPTH_DIAGNOSTIC.json`. The `combined` probe returned 429 and is
unresolved; that is rate limiting, not a capability finding, and the record says so rather than
reading a transient rejection as evidence.

This diagnostic is **not** the readiness gate. It consumes no single-use budget, it is repeatable,
it sends no qualifying input and it produces no carrier. Its result is design evidence.

## What is inherited, and how that is enforced

The whole scientific design comes from M119 by import, exactly as M120 took it:

| | inherited from |
|---|---|
| the four arms and the fenced diagnostic arm | `metamorphosis/m119_arms.py` |
| the comparator, its uniform per-demand draw and its committed seed | `metamorphosis/m119_arms.py` |
| the paired endpoint, the exact test, α, the effect floor, the guards, the verdicts | `metamorphosis/m119_endpoint.py` |
| the interpretation mapping over the four cells | `metamorphosis/m119_decomposition.py` |
| the observation budget, 4000 per demand | M113, through M119 |
| the admissibility minimums, 3 qualifying carriers and 3 distinct structures | M115, through M119 |
| the fixed route | `metamorphosis/m118_route.py`, byte-unchanged |
| the pre-seal adequacy gate and its information boundary | `metamorphosis/m120_adequacy.py` |

A milestone that quietly edited the endpoint it claims to inherit would be testing something else
under the same name, and the derivation refuses to build a plan if those bytes have moved.

## The two readiness-gate corrections M120's outcome requires

1. **Identity is attested only where there is a completion to attest.** M120's gate computed
   runtime identity on every response including HTTP 429s, which carry no router metadata, so two
   rate-limited requests made `identity_held_on_every_request` false and the verdict ladder reported
   `not_ready_identity` when the finding was a feature class. A retry-exhausted 429 is a delivery
   outcome.
2. **`finish_reason: length` on a probe is its own recorded class.** Folding it into
   non-conformance loses the distinction between "the route emitted something the schema refuses"
   and "the route emitted 101,379 tokens because enforcement failed open."

Neither correction changes a threshold, and neither is applied to M120's record.

## Chronology

Each stage must prove its predecessors were committed at HEAD, byte-identical to the working tree,
before it may run. The order is deliberately different from M120's.

    M120 closed at readiness
      → route-depth diagnostic, before the contract is committed to
      → this preregistration and the complexity budget
      → DEVELOPMENT route readiness for this candidate schema
      → **only if ready:** bank sizing, the rest of the apparatus, the rehearsal
      → plan, spec, qualifying input and nonce frozen
      → complete tested-system freeze committed
      → unique H67 qualifying generation
      → machine-only admission
      → machine-only pre-seal adequacy gate, or terminal abort
      → seal → reveal authorization → one reveal
      → frozen scoring → independent replay

**M120 built its entire apparatus and then learned its contract was unserviceable.** M122 asks the
disqualifying question first and builds the rest only if the answer survives. That reordering is
the main procedural lesson of M120's closure and it is binding here.

## The single generation

One qualifying request, if the milestone ever reaches one. Only an explicit pre-generation HTTP 429
carrying no completion and no evidence of model execution may be retried, at most twice. Everything
else is terminal: a scientific outcome is never retried, no output is repaired, reparsed or
regenerated, and there is no selection among outputs.

## Stop conditions

H67 stops, without a scientific verdict, if any of these holds:

- the M122 readiness gate does not return `ready` for this candidate schema;
- the fixed route cannot serve the frozen request, or runtime identity is not exactly that route on
  a response that carries a completion;
- the one completion is not admissible;
- the pre-seal adequacy gate does not clear the bank;
- the tested system does not match its freeze at any phase after the generation;
- the recovered plaintext is not the plaintext that was sealed;
- the pre-seal adequacy counts and the post-reveal recomputation disagree.

In every case the outcome is recorded as `instrument_aborted`: H67 **untested**. It is never
converted into a negative result, and the design is never adjusted afterwards to rescue it.

An `instrument_abort` that was detectable before the freeze is a **preflight failure**, and is
recorded as one.

## What a positive result would and would not mean

It would mean: on demands derived from carriers this project did not design, the descendant carrying
both pieces of acquired machinery resolved more of them than a symmetric comparator, by a margin
unlikely under the null and at least ten percentage points wide, without harming refusal calibration
or inventing adapters.

It would **not** mean, and will not be said to mean:

- AGI, recursive self-improvement, open-ended intelligence, or the closing of any generality gate;
- provider invariance — one provider and one checkpoint, so provider is confounded with the effect;
- generality beyond the carrier family this contract defines, which is **narrower than M115's**;
- independence of the generator's training data;
- human independence, or external reproduction.

## Multiplicity across H60–H67

No statistical test has been performed anywhere on this chain. H59, H60, H62, H63, H64 and H65 are
all recorded untested, and none computed a p-value. H67 is therefore the **first** test of this
target, and a first test is not a multiple comparison.

If H67 returns a `negative` or a `positive`, a later milestone testing the same target must correct
for having tested it twice and must say so in its own preregistration. An `instrument_aborted`
consumes no α, because no test was performed.

## Stated limitations

1. Provider and model are confounded with the effect.
2. The carrier family is narrower than M115's, and the narrowing was informed by M119's closed
   public bank and by M120's closed readiness result. Both are disclosed instrument-design
   dependencies on closed records.
3. The decoder is a project-side total function. It closes the gap between what the schema permits
   and what the host accepts; it cannot and does not make a carrier qualify.
4. `FRESH` is symmetric, not strong.
5. The observation budget is 4000 per demand, inherited unchanged.
6. One bank, one generation, one model.
7. The DEVELOPMENT sizing estimate measures a development emitter, not the blind generator.
8. The route-depth diagnostic establishes that one feature class holds at five levels on one date.
   It is not a readiness result and does not stand in for one.

## Amendment log

Amendments will be listed here rather than folded in silently.

*No amendments.*
