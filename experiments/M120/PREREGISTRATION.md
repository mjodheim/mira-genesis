# M120 / H65 — preregistration

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H65 observation exists. Nothing below may be revised after the seal is broken.

## Status at the time of writing

- H65 is **not frozen**. No carrier bank exists. Qualifying scientific invocations: **0**.
- M113 through M119 are closed. Nothing here reopens, reinterprets or repairs any of them, and no
  artifact of theirs is modified.
- M119 closed `instrument_aborted` with **H64 untested**. That is not a result about the
  hypothesis, and it is not reported as one. The two checker defects M119 disclosed after its
  freeze are **requirements for this milestone**, not permission to edit that one.
- `M120` and `H65` become registered identifiers when this document, the hypothesis register entry
  and the owner's publication disposition are recorded — in that order, and before any freeze.

## The hypothesis

**H65.** A descendant carrying both pieces of acquired machinery — the attribution cascade and the
diagnostic policy — resolves demands on carriers it did not design more often than a comparator that
carries neither, on demands posed identically to both.

This is **H64's proposition, unchanged**. The handoff's instruction was to preserve the scientific
target unless a prospectively documented reason requires a new one, and no such reason exists: H64
was never tested, so there is nothing about it to revise. What changes is the instrument.

## What is inherited, and how that is enforced

The whole scientific design comes from M119 **by import**, not by restatement:

| | inherited from |
|---|---|
| the four arms and the fenced diagnostic arm | `metamorphosis/m119_arms.py` |
| the comparator, its uniform per-demand draw and its committed seed | `metamorphosis/m119_arms.py` |
| the paired endpoint, the exact test, α, the effect floor, the guards, the four verdicts | `metamorphosis/m119_endpoint.py` |
| the interpretation mapping over the four cells | `metamorphosis/m119_decomposition.py` |
| the observation budget, 4000 per demand | M113, through M119 |
| the admissibility minimums, 3 qualifying carriers and 3 distinct structures | M115, through M119 |
| the fixed route | `metamorphosis/m118_route.py`, byte-unchanged |

`m120_bank.assert_inherited_science_unchanged` records the digests of the three scientific modules
and refuses to derive an analysis plan if any of them has moved. A milestone that quietly edited the
endpoint it claims to inherit would be testing something else under the same name.

## What M119 established about the instrument, and what follows

M119's delivery was clean in every respect: HTTP 200, one attempt, no retry, exact frozen
model/provider identity, `finish_reason: stop`, parsed completion, conformance to the frozen output
schema. The generator emitted 37 machines for 36 requested. The frozen host then accepted 3 and
refused 34, and **zero** cleared the qualification clauses.

Two facts follow, and both are load-bearing here.

**First, schema conformance did not imply host acceptance.** 33 of the 34 refusals came from two
rules M115's schema states only in prose — `arg_size` must be 2–4 when `arity` is 1 and 0 when it is
0, and at least one entry of `visible` must be true. Neither is expressible as JSON Schema wrote
them, because both are relations between two fields. The model followed the schema exactly.

**Second, and less visible, the bank was degenerate.** Re-measured against M119's committed public
bank, the generator answered every range with its minimum: 22 of 37 machines had one cell, 35 of 37
had exactly two actions, and 28 of 37 had no reachable observation deeper than one step. Decoding
that bank into host-valid form — which is what this milestone's decoder does — leaves **one** machine
of the 37 qualifying. Closing the schema gap alone would therefore have produced another
`instrument_aborted`, one stage later.

## The carrier contract

Two layers, in `metamorphosis/m120_carrier_contract.py`.

**The candidate schema** contains no relation between two fields. Where M115's representation forced
one, the representation is changed rather than described more insistently:

| M115 | M120 |
|---|---|
| `arity` 0–1 and `arg_size` 0–4 | one field `arg_size` over {0, 2, 3, 4}; arity is derived |
| `initial`, a list as long as `cells` | `initial` lives inside its own cell |
| `visible`, booleans, at least one true | `hidden`, at most one cell index, over at least three cells |
| `error`, a name that must appear in `errors` | `error_index`, reduced against the declared list |
| `actions` 2–6, guards optional | `conditional_actions` 2–3 with a guard each, plus `actions` 2–3 |

It uses **only the eleven schema feature classes M118's readiness gate observed this route
enforcing**. `oneOf`, `contains`, `minContains` and `uniqueItems` would each express something here
more directly, and none of them has evidence on this route, so none is used.

**The decoder** is total, deterministic and content-independent. It is applied to every machine
identically, before anything is counted; it cannot refuse, reorder, drop or select; and every
remaining host rule is a bound of one field against a domain the candidate itself declared, which it
discharges by modular reduction. Its one conditional promotes an `arg_size` of 0 to 2 when the
action's own effect asks for an argument, which honours what the candidate wrote.

The claim the two layers make together is mechanical and is checked, not asserted:

> for every value satisfying the candidate schema, the frozen `carrier_host.validate_carrier`
> accepts the decoded carrier.

`tests/test_m120_carrier_contract.py` establishes it by exhausting the constraint-relevant corners
of the candidate space and by fuzzing the rest, and the sizing derivation asserts it again over
twelve hundred further draws.

**The decoder cannot make a carrier qualify.** Whether a carrier admits the experiment is decided by
M113's qualification clauses over reachability, observation depth and attribution, and nothing in
the contract touches those.

## The narrowed carrier family, and its cost

The family this milestone asks for is narrower than M115's: three to four cells, at most one of them
latent, two to three actions carrying a precondition, four to six actions in all.

**This narrowing was chosen after reading M119's closed, public bank.** That is an instrument-design
dependency on a closed record and it is disclosed as such. It is not a selection over H65 outputs:
the contract is fixed here, before generation, and applies to every machine identically; no
completion is filtered, ranked, repaired or redrawn against it.

What it costs is stated rather than glossed: **a verdict here speaks about a smaller carrier family
than M119 would have spoken about.** What it does not cost is the independence of the test. Nothing
in the narrowing mentions the arms, the cascade, the policy, the attribution or which side of the
comparison should win, and the qualification clauses that decide whether a carrier admits the
experiment are unchanged and can still fail — measured at the family's smallest corner, they fail
71% of the time.

## The bank

- **48 carriers requested**, in one generation, from one blind generator.
- The generator is blind: one user message carrying the derived qualifying input and the candidate
  schema; no system message, no tools, no prior turns, no retrieval, no repository, no project
  vocabulary. `m120_bank.blindness_contract` computes that from the request body rather than
  asserting it, and the contamination checker runs over the prompt.
- The count is derived before any H65 observation exists, by `scripts/build_m120_bank_sizing.py`, from the
  contract's own bounds. The derivation uses the **smallest corner the contract admits**, because
  that is the shape M119's generator actually produced when offered a range, and then halves the
  measured rate again. At that planning rate, 48 carriers yield about 7 qualifying carriers and 28
  paired demands, against 3 required and 5 discordant needed.
- **That is a sizing estimate, not a prediction.** It measures a development emitter, not the blind
  generator. M113 recorded six per cent qualification over project worlds against twenty-five per
  cent from M112's blind bank, and M119's blind bank qualified at one in thirty-seven once decoded.
  The binding constraints are the admissibility minimums and the adequacy gate, and the count is not
  revisable after the generation.
- **Admissibility**, inherited unchanged: at least 3 qualifying carriers and at least 3 distinct
  structural signatures. Below either, H65 is `instrument_aborted` — untested, not refuted.

## Adequacy is decided before the seal

M116 moved carrier admission ahead of the seal so an instrument failure could be described without
spending the reveal. It asked whether the payload was admissible. M119's payload was admissible and
could not be tested.

`m120_adequacy` asks the second question at the same point: how many carriers qualify, how many
distinct structures they present, and how many paired demands they would yield. If any is short, the
milestone closes **before the seal is broken**, with the reveal unspent.

The information boundary is enforced rather than promised. The gate's output allowlist is
exhaustive and every member is a boolean, a count, or a histogram over the frozen clause names;
`validate_record` refuses a record carrying anything else. The gate returns one verdict about the
whole bank and cannot name, rank, order, exclude or prefer a carrier. An inadequate bank is
**terminal**: it is not filtered, repaired, resampled or regenerated, and no second generation is
drawn.

## Readiness is re-measured for this schema

M119 inherited M118's readiness result across a schema change. Here that would be an error, and it
is refused: M118's stress schema does not dominate the M120 candidate schema's keyword census — 22
`enum` occurrences against 5, eight array-of-object levels against five — so the earlier measurement
cannot speak for this contract.

`scripts/run_m120_readiness.py` re-measures identity, every census-required feature class, the
reasoning control and one full-scale conforming completion, against a stress schema that **does**
dominate the candidate census. `m120_chronology.assert_readiness_passed` refuses the freeze without
a committed result that says `ready` and that names this exact candidate schema.

The stress schema is deliberately **not** the candidate schema, and the readiness record carries no
qualification statistic and no carrier count. Sending the carrier contract at scale during
DEVELOPMENT would preview the bank the frozen contract is about to draw, and a preview is a degree
of freedom over the contract. M117 disclosed five apparatus revisions, some following real endpoint
observations; this milestone does not need to pay that cost again.

## The checker scores what it authenticates

M119's checker took both the analysis plan and the measurements file from the command line. Closing
review reproduced two consequences: a plan with its minimums set to zero, keeping the frozen
commitment string verbatim, was accepted; and the replay gate proved the committed measurements were
at HEAD and then scored whatever path `--measurements` named.

`scripts/check_m120_result.py` has **no scientific evidence path a caller can point at**. It resolves
the committed plan, measurements, reveal record and adequacy record from the chronology's own
constants, after the replay gate has proved each is committed at HEAD byte-identically to disk, and
it re-derives the plan from code with `m120_bank.validate_analysis_plan` rather than trusting a
self-reported digest. The pre-seal adequacy record must also agree, count for count, with the same
gate recomputed over the revealed bank.

## Chronology

Each stage must prove its predecessors were **committed at HEAD, byte-identical to the working
tree**, before it may run. A file written seconds before a request is not a freeze. There is no
parameter through which a caller may supply a record it has just built.

    M119 closed, route fixed
      → this preregistration
      → DEVELOPMENT bank sizing and end-to-end rehearsal
      → DEVELOPMENT route readiness for this candidate schema
      → plan, spec, qualifying input and nonce frozen
      → complete tested-system freeze committed
      → unique H65 qualifying generation
      → machine-only admission
      → machine-only pre-seal adequacy gate, or terminal abort
      → seal
      → reveal authorization → one reveal
      → frozen scoring → independent replay

The **bank nonce is committed before the generation** because the comparator's per-demand draw
consults the opaque carrier references derived from it. A nonce chosen after the bank existed would
be a degree of freedom over the comparator.

## The single generation

One qualifying request. Only an explicit pre-generation HTTP 429 carrying no completion and no
evidence of model execution may be retried, at most twice. Everything else is terminal: a scientific
outcome is never retried, no output is repaired, reparsed or regenerated, and there is no selection
among outputs.

Admission runs **before** anything is called a bank, on the bytes that arrived. It requires runtime
identity to be exactly the fixed route, `finish_reason: stop`, valid JSON, conformance to the
candidate schema, and acceptance of the decoded and enveloped payload by the frozen carrier host. It
is a pure predicate: it may not repair, strip, extract, reformat, regenerate or choose.

## What a positive result would and would not mean

It would mean: on demands derived from carriers this project did not design, the descendant carrying
both pieces of acquired machinery resolved more of them than a symmetric comparator, by a margin
unlikely under the null and at least ten percentage points wide, without harming refusal calibration
or inventing adapters.

It would **not** mean, and will not be said to mean:

- AGI, recursive self-improvement, open-ended intelligence, or the closing of any generality gate.
- Provider invariance. **One provider and one checkpoint are used, so provider is confounded with
  the effect.**
- Generality beyond the carrier family this milestone's contract defines — which is narrower than
  M115's, and narrower than the family M119 drew from.
- Independence of the generator's training data. The generator is blind to the hypothesis; it is not
  independent of what it was trained on.
- Human independence, or external reproduction.

## Multiplicity across H60–H65

H65 is tested at α = 0.05 with no correction, and the reason is that **no statistical test has been
performed anywhere on this chain of hypotheses**. Checked against the committed records:

| hypothesis | milestone | recorded verdict | statistical test performed |
|---|---|---|---|
| H59 | M114 | `instrument-aborted`, untested | none |
| H60 | M115 | `instrument-aborted`, untested | none |
| — | M116 | DEVELOPMENT capability matrix | none |
| H62 | M117 | instrument development / route calibration | none |
| H63 | M118 | closed as instrument design; never frozen, no bank | none |
| H64 | M119 | `instrument_aborted`, untested; zero paired demands, no arm ran | none |

H65 is therefore the **first** test of this target, and a first test is not a multiple comparison.

Two things follow, and both are binding:

- **This milestone spends the only uncorrected α on the chain.** If H65 also ends
  `instrument_aborted`, that consumes no α, because no test was performed. But if H65 returns a
  `negative` or a `positive`, a later milestone testing the same target must correct for having
  tested it twice, and must say so in its own preregistration.
- **The four arms do not create multiplicity here.** There is exactly one primary comparison, FULL
  versus FRESH, fixed in code before the data. The other cells enter only the decomposition of a
  result the primary comparison has already established, and the fenced diagnostic arm enters
  neither.

## Stated limitations

1. Provider and model are confounded with the effect. No provider-invariance claim is available.
2. The carrier family is narrower than M115's and M119's, and the narrowing was chosen after reading
   M119's closed public bank. That is an instrument-design dependency on a closed record.
3. The decoder is a project-side total function. It closes the gap between what the schema permits
   and what the host accepts; it cannot and does not make a carrier qualify.
4. `FRESH` is symmetric, not strong. Beating it is not evidence of beating a competent hand-written
   attributor.
5. The observation budget is 4000 per demand, inherited unchanged. The endpoint is therefore
   *budget-constrained* resolution, and the fenced diagnostic arm exists to say whether a negative is
   that cost or a competence cost.
6. One bank, one generation, one model.
7. M117's five disclosed apparatus revisions sit upstream of the route and are not repaired here.
8. The DEVELOPMENT sizing estimate measures a development emitter, not the blind generator.

## Stop conditions

H65 stops, without a scientific verdict, if any of these holds:

- the fixed route cannot serve the frozen request, or runtime identity is not exactly that route;
- the M120 readiness gate does not return `ready` for this candidate schema;
- the one completion is not admissible;
- the pre-seal adequacy gate does not clear the bank;
- the tested system does not match its freeze at any phase after the generation;
- the recovered plaintext is not the plaintext that was sealed;
- the pre-seal adequacy counts and the post-reveal recomputation disagree.

In every one of those cases the outcome is recorded as `instrument_aborted`: H65 **untested**. It is
never converted into a negative result, and the design is never adjusted afterwards to rescue it.

An `instrument_abort` that was detectable before the freeze is a **preflight failure**, and is
recorded as one.

## Amendment log

This document was written before the analysis plan, the generator spec, the bank nonce and the
tested-system freeze, and before any H65 observation existed. Amendments will be listed here rather
than folded in silently, because a preregistration that quietly changes is not a preregistration.

*No amendments.*
