# M124 / H69 — preregistration

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H69 observation exists. Nothing below may be revised after the seal is broken.

## Status at the time of writing

- H69 is **not frozen**. No carrier bank exists. Qualifying scientific invocations: **0**.
- M113 through M123 are closed. Nothing here reopens, reinterprets or repairs any of them.
- M123 closed at `not_ready_stress` with **H68 untested**. Its disclosed defect is a **requirement**
  for this milestone, not permission to edit that record.
- **No publication disposition is recorded for M124.** Nor for M120, M121, M122 or M123.

## The hypothesis

**H69.** A descendant carrying both pieces of acquired machinery — the attribution cascade and the
diagnostic policy — resolves demands on carriers it did not design more often than a comparator that
carries neither, on demands posed identically to both.

H64's proposition, unchanged, for the fifth time. It has never been tested. Nothing about the target
has been revised because nothing about it has ever been measured.

## The one thing this milestone changes

M123's outcome recorded a question and refused to answer it retroactively:

> A successor must decide, **prospectively and before any request is sent**, whether a 200 carrying
> content with no `finish_reason` and unparseable JSON is a delivery outcome or a scientific one.

**The answer, decided here, before any request:** it is a **delivery outcome**.

`finish_reason` is how this API reports that generation terminated and why. A response that omits it
is not a completed generation record — it does not say the model stopped, and it does not say the
model was cut off. There is no finished artifact to judge, so there is nothing for a scientific
verdict to be about.

### The boundary matters more than the rule

The decision is deliberately narrow:

| observed | classified as | retryable |
|---|---|---|
| `finish_reason: "stop"` | scientific | no — final on first occurrence |
| `finish_reason: "length"` | **scientific** | **no** — terminal |
| `finish_reason` **absent** | **delivery** | yes, within the allowance |

**Truncation stays terminal.** The model reaching the cap is a fact about the size this instrument
asked for, and it is exactly the evidence a stress exists to produce. Making truncation retryable
would let an oversized stress be re-run until it passed, which is the gate tuned to itself — the
failure this whole line of records exists to prevent.

Evidence that absence is anomalous rather than routine: across M122's and M123's runs, **every one
of the eighteen probe responses that carried a completion reported `finish_reason: "stop"`**. The
only response ever observed without one is the stress that closed M123.

The rule is bound into `plan_sha256`, so it cannot be adjusted after a result is seen. That is the
only thing that makes it prospective rather than convenient.

## What is deliberately not changed

### The sizing, because it worked

M123's stress was not what failed:

    predicted band at 109 stations   45,598 – 65,698 tokens
    observed                         50,232
    implied rate                     460.8 per station

The empirical rate envelope made an out-of-sample prediction and the route landed inside it, after a
two-point linear fit had failed the same test by at least 57%. That is the first sizing in this line
that worked.

M123's own observation is folded in and **changes nothing**, which is why it is worth recording:

| stations | tokens | rate | |
|---|---|---|---|
| 24 | 13,118 | 546.6 | |
| 74 | 30,957 | 418.3 | |
| 167 | ≥100,657 | ≥602.7 | censored — truncated |
| **109** | **≥50,232** | **≥460.8** | censored — no `finish_reason` at all |

460.8 sits inside the envelope [418.3, 602.7] the first three already described, so the window stays
[77, 141] and the midpoint stays **109**. A rule whose answer is stable when new evidence arrives is
behaving the way a rule should.

**The 32,000 threshold is inherited from M118 and is not touched.** It has now not moved for four
milestones. The stress moves; the bar does not.

### The contract, because M122 validated it

Inherited by import, not re-authored. Nine of nine capability classes enforced on the live route,
confirmed again in M123 attempt 2 — nine of nine on the first ask, no retries, no rate limiting.

## The limitation that outweighs everything above

At a fixed 109 stations the inherited schema permits conforming completions spanning about **4×**,
wider than the **3.15×** pass window, because every station carries arrays whose length the model
picks freely. **Station count is not the only variable that decides the verdict, and it is not the
largest.**

Pinning the inner array cardinalities would remove that freedom, and it leaves the census M122
validated **bit-identical** — verified mechanically, not assumed.

It is **not done here**, and the reason is a trade rather than an oversight: every observation in the
table above was measured on the unpinned schema. Pinning would improve the instrument and discard
its entire calibration in the same edit, leaving a better-designed gate with no basis for choosing
its size. That belongs to a milestone that budgets for re-calibration, not to a successor whose
purpose is to correct one verdict rule.

The empirical mitigation, stated for what it is worth and no more: the four observations sit inside a
narrow slice of the permitted band, so the model has never gone near either extreme.

## Chronology

Unchanged:

    M123 closed at readiness
      → this preregistration and the complexity budget
      → DEVELOPMENT route readiness for the inherited contract at 109 stations
      → **only if ready:** bank sizing, the rest of the apparatus, the rehearsal
      → plan, spec, qualifying input and nonce frozen
      → tested-system freeze committed
      → unique H69 qualifying generation
      → machine-only admission
      → machine-only pre-seal adequacy gate, or terminal abort
      → seal → reveal authorization → one reveal
      → frozen scoring → independent replay

The readiness gate runs **before** the rest of the apparatus is written.

## The delivery allowance

Inherited unchanged: only `not_ready_delivery` may be superseded, at most three times per
instrument, counted from the attempt archive by result digest and scoped by plan digest, with a
ceiling of six across every instrument — **three of which are already spent** (M122 ×2, M123
attempt 1). Every other verdict is final on its first occurrence.

## Stop conditions

H69 stops without a scientific verdict if the readiness gate does not return `ready`; if the route
cannot serve the frozen request or identity is not exactly that route on a response carrying a
completed generation; if the one completion is not admissible; if the pre-seal adequacy gate does
not clear the bank; if the tested system does not match its freeze; if the recovered plaintext is
not the plaintext sealed; or if the pre-seal and post-reveal adequacy counts disagree.

In every case the outcome is `instrument_aborted`: H69 **untested**, never converted into a negative
result.

## What a positive result would and would not mean

It would mean the descendant resolved more demands than a symmetric comparator on carriers this
project did not design, by a margin unlikely under the null and at least ten points wide, without
harming refusal calibration or inventing adapters.

It would **not** mean AGI, recursive self-improvement, open-ended intelligence, the closing of any
generality gate, provider invariance, generality beyond this carrier family, independence of the
generator's training data, human independence, or external reproduction.

## Stated limitations

1. Provider and model are confounded with the effect.
2. The carrier family is narrower than M115's, and that narrowing was informed by closed records.
3. The decoder cannot make a carrier qualify.
4. `FRESH` is symmetric, not strong.
5. The observation budget is 4000 per demand, inherited unchanged.
6. One bank, one generation, one model.
7. **The schema permits a wider spread than the pass window**, so the stress size is evidence and
   not a guarantee. See above; this limitation dominates the sizing rule.
8. **Two of the four sizing observations are censored** — both are floors, not measurements.
9. No statistical test has been performed anywhere on this chain. H59, H60, H62, H63, H64, H65, H67
   and H68 are all recorded untested. H69 would be the first, and a first test is not a multiple
   comparison.

## Amendment log

*No amendments.*
