# M123 / H68 — preregistration

Written before the analysis plan, the generator spec, the bank nonce and the tested-system freeze,
and before any H68 observation exists. Nothing below may be revised after the seal is broken.

## Status at the time of writing

- H68 is **not frozen**. No carrier bank exists. Qualifying scientific invocations: **0**.
- M113 through M122 are closed. Nothing here reopens, reinterprets or repairs any of them.
- M122 closed at its readiness gate with **H67 untested**. Its two disclosed defects are
  **requirements for this milestone**, not permission to edit that one.
- **No publication disposition is recorded for M123.**

## The hypothesis

**H68.** A descendant carrying both pieces of acquired machinery — the attribution cascade and the
diagnostic policy — resolves demands on carriers it did not design more often than a comparator
that carries neither, on demands posed identically to both.

H64's proposition, unchanged, for the fourth time. It has never been tested. Nothing about the
target has been revised because nothing about it has ever been measured.

## What M122 established, and why the contract is not touched

M122's readiness run answered nine of nine capability probes and **all nine conformed**: HTTP 200,
`finish_reason: stop`, schema valid, zero enforcement failures, identity holding on every request.
That includes the two that had never been cleanly answered before:

- **`nested_arrays`** — the class that closed M120. At eight array-of-object levels it free-ran to
  101,379 tokens and truncated; at five it conforms in **76**.
- **`combined`** — every class exercised at once. Conformed in **582**.

**So the contract is validated against the live route**, and M123 inherits it by import rather than
re-authoring it. Rebuilding a validated schema to carry a new milestone number would discard the
only thing M122 bought and re-open a question already answered. The same applies to the stress
schema's *shape*, which is inherited unchanged; only its size moves.

This is the first milestone in this line that does not redesign the carrier contract.

## What closed M122, and the correction

The stress produced a conforming completion of **30,957 tokens against a 32,000 threshold** — short
by 3.3%.

Its size had been derived from a **single** observation, 546.6 tokens per station at 24 stations,
on the assumption that the rate is constant. It is not: at 74 stations the observed rate was 418.3,
and the single-point model overshot its own prediction by 31%. **A single point is a line through
the origin**, and this relationship has an intercept — a fixed cost per completion that a
proportional model charges to every station.

### Amended after attempt 1: the fit was falsified, and there is no model any more

**The two-point fit below was wrong and is abandoned.** It is left on the record because a
preregistration that quietly replaces its own reasoning is worthless.

What it predicted, and what happened:

| stations | predicted | observed | rate |
|---|---|---|---|
| 24 | — | 13,118 | 546.6 |
| 74 | — | 30,957 | 418.3 |
| 167 | 64,137 | **≥ 100,657, truncated** | **≥ 602.7** |

The fit under-predicted by at least 57% on its first out-of-sample test. The rates go **down and
then up**: the relationship is not linear, not monotonic, and not identified by three points.
Fitting a fourth model would repeat the same mistake with more arithmetic.

**The replacement rule fits nothing.** It takes the envelope of the rates actually observed and
requires the stress to sit inside the admissible window under *every* one of them:

    floor    > 32,000 tokens at the LOWEST observed rate (418.3)   ->  >= 77 stations
    ceiling  < 85,000 tokens at the HIGHEST observed rate (602.7)  ->  <= 141 stations
    chosen   the midpoint of [77, 141]                             ->  109 stations

At 109 the prediction is a **range, not a number**: 45,599 tokens at the lowest observed rate,
65,698 at the highest. Both sit inside the window with room on each side. The midpoint is taken
because it is the one point in the window that no observation argues for, it is maximally far from
both edges, and it is computed rather than picked — a size chosen because it looked likely to pass
would be the gate tuned to itself.

### 100,657 is a truncation that was observed, not a ceiling that is known

The request asked for 131,072 tokens and the route stopped at 100,657 with `finish_reason:
"length"`. That is a **censored observation**, and it bounds two things in the unhelpful direction:

- the route's real output limit is *at most* about 100,657, and may be lower;
- the true rate at 167 stations is *at least* 602.7 per station, because the object was cut off
  before it closed. **The upper edge of the envelope is itself a lower bound**, so the real worst
  case can be worse than the worst case this rule can see.

That is the honest weakness of the envelope rule, and it is the reason for the operational bound
rather than an argument against it.

**85,000 is a choice, not a derivation** — roughly 15.6% below the single truncation ever seen. It
buys headroom against three things this project cannot measure from here: that the true limit may
sit below the one truncation observed, that the censored rate understates the real rate, and that
this route's yield has already moved by 44% between two sizings with nothing in the schema changing.

**The 32,000 threshold is inherited from M118 and is not touched.** A threshold rewritten to fit a
stress is a gate tuned to pass itself. The stress moves; the bar does not.

## The second correction: unanswered is not unenforced

`conforms` is false for an HTTP 429 exactly as it is for a completion the schema refuses. M120 and
M122 both therefore listed feature classes as *unenforced* when their probes had only ever been
rate-limited — M122's attempt 2 named `pattern` and `required`, and attempt 3 named three classes,
none of which had ever been measured.

The verdict ladder checks delivery before features, so no headline verdict was wrong. But a reader
trusting `unenforced_feature_classes` would conclude the route lacks a capability nobody measured,
and that is a false record rather than a cosmetic one.

From M123, a class is recorded unenforced **only if its probe was answered and the answer did not
conform**. Classes whose probes never answered are reported separately, as
`feature_classes_never_answered`.

## The third correction: the ceiling counted only its own directory

M122 wrote the total delivery ceiling as "across every instrument" and then counted it by globbing
its own experiment directory. A successor milestone is a new directory, so the ceiling reset on
exactly the move it exists to bound: revising the apparatus and opening a successor are the same
move at two different sizes, and the larger one escaped.

The scan now crosses milestones. M123 therefore opens at **two of six spent**, not zero — M122's
two distinct delivery attempts, deduplicated by result digest across the three files that hold
them. The per-instrument allowance is unaffected and remains scoped by plan digest.

## Chronology

Unchanged from M122, including the ordering that milestone introduced:

    M122 closed at readiness
      → this preregistration and the complexity budget
      → DEVELOPMENT route readiness for the inherited contract at the corrected stress size
      → **only if ready:** bank sizing, the rest of the apparatus, the rehearsal
      → plan, spec, qualifying input and nonce frozen
      → tested-system freeze committed
      → unique H68 qualifying generation
      → machine-only admission
      → machine-only pre-seal adequacy gate, or terminal abort
      → seal → reveal authorization → one reveal
      → frozen scoring → independent replay

The readiness gate runs **before** the rest of the apparatus is written. M120 built everything and
then learned its contract was unserviceable.

## The delivery allowance

Inherited from M122 with the counting corrected above: only a `not_ready_delivery` verdict may be
superseded, at most three times per instrument, counted from the attempt archive by result digest
and scoped by plan digest, with a ceiling of six across every instrument — now including earlier
milestones, of which two are already spent. Every other verdict is final on its first occurrence.

## Stop conditions

H68 stops without a scientific verdict if the readiness gate does not return `ready`; if the route
cannot serve the frozen request or identity is not exactly that route on a response carrying a
completion; if the one completion is not admissible; if the pre-seal adequacy gate does not clear
the bank; if the tested system does not match its freeze; if the recovered plaintext is not the
plaintext sealed; or if the pre-seal and post-reveal adequacy counts disagree.

In every case the outcome is `instrument_aborted`: H68 **untested**, never converted into a
negative result.

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
7. **The stress size is bounded by an envelope of three observations, one of them censored.** No
   model is fitted, because the fitted model was falsified on its first out-of-sample test. The
   envelope's upper edge is a lower bound — the truncated run's true rate is unknown and larger —
   so the operational ceiling carries the margin that the envelope itself cannot.
8. No statistical test has been performed anywhere on this chain: H59, H60, H62, H63, H64, H65 and
   H67 are all recorded untested. H68 would be the first, and a first test is not a multiple
   comparison.

## Amendment log

**Amendment 1 — 4 September 2026, after readiness attempt 1, before any H68 observation exists.**

Attempt 1 returned `not_ready_delivery` (two probes rate-limited) and, separately, its stress
truncated at 100,657 tokens. The two-point sizing model that this preregistration described was
falsified by that run and has been replaced by the empirical rate envelope documented above.

What changed: the sizing rule, the station count (167 -> 109), the admissible window (newly
declared as [77, 141] and recomputed from the envelope at import), and the addition of the observed
truncation and the operational ceiling as bound, named quantities.

What did not change: the hypothesis, the endpoint, the 32,000-token threshold inherited from M118,
the carrier contract inherited from M122, the verdict rules, the delivery allowance and its
ceiling, and the stop conditions. **No scientific parameter moved.** The stress size is instrument
calibration; the threshold is the bar, and the bar did not move.

Accounting: the revision moves `plan_sha256` from `9d317afc…` to `6655a4fc…`, so the per-instrument
allowance starts at **0 of 3** for the new instrument while the cross-milestone ceiling stands at
**3 of 6** — M122's two delivery attempts plus M123 attempt 1. Verified mechanically before the
revision was run, not asserted.

Attempt 1 and its falsification are preserved in full and were committed before this amendment was
written.
