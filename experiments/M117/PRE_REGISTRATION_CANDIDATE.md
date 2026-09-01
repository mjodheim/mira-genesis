# M117 — H62 candidate: route qualification before the carrier-blind test

**Hypothesis:** H62
**Status:** **CANDIDATE. NOT FROZEN. DRAFTED FOR OWNER REVIEW.** No route is selected, no generator
specification exists, no qualifying input has been sent, no bank exists. **Qualifying invocations: 0.**

## Why M117 exists

M116 is closed. Its DEVELOPMENT capability matrix established that the fixed route enforces **none**
of the nine schema feature classes the frozen carrier schema relies upon: every probe returned HTTP
200 with `finish_reason=stop` and well-formed JSON shaped entirely by the prompt, and every one
violated exactly the constraint under test. Under the precommitted rule the M116 instrument family
is unsuitable for H61, H61 is preserved untested, and the corrective-replication path is closed.

M117 is **not** a repair of H61 by provider substitution. That is the failure mode the M116 decision
rule was written to prevent, and it is the failure mode this document exists to keep preventing. The
distinction is procedural and enforceable: **route selection is a preregistered, mechanically applied
rule that runs and commits its answer before any H62 generator specification is frozen.** The route
is not chosen because it "worked best" informally, and it is never chosen after seeing a carrier.

## The scientific proposition

H62 states the **same scientific proposition** as H60 and H61 — unchanged. It receives a new number
because hypothesis identity in this project is bound to a frozen instrument, and M117 changes the
instrument's most consequential component: which endpoint generates the blind carrier bank.

M113/H58, M114/H59, M115/H60 and M116/H61 remain closed historical records. None is reinterpreted,
repaired, retried or relabelled by anything here.

## Stage 1 — route qualification (DEVELOPMENT, preregistered, before anything else)

Committed **before** the first candidate is probed:

**Eligibility.** The candidate set is derived mechanically from the provider catalogue by a
committed rule, not hand-picked. A candidate must expose the model under an explicit
alias-to-canonical-checkpoint relation, permit `allow_fallbacks: false` and `require_parameters:
true`, and report router metadata sufficient for the inherited identity attestation.

**Reliability threshold.** The inherited reliability ordering (uptime over 1 day, uptime over 30
minutes, median latency over 30 minutes, provider name) with a committed minimum, applied before any
capability probe.

**Capability matrix.** The M116 matrix, unchanged and reused: the same probes, derived from the same
census of the same frozen carrier schema, with the same underspecified-prompt design and the same
outcome vocabulary. Reusing it verbatim is deliberate — a matrix rewritten for M117 could be
rewritten to let a preferred route through.

**Minimum structural capability.** A candidate qualifies only if it enforces **every** feature class
the census marks required. Partial enforcement does not qualify. This threshold may not be lowered
after any candidate is observed.

**Token-budget capability.** A candidate must also complete a schema-conforming output exceeding the
volume the carrier request demands, measured by the existing stress instrument under the new
diagnostic classification.

**Identity attestation and no fallback.** Exact requested alias, exact canonical checkpoint, exact
provider, direct routing, one selected endpoint, one router attempt, no fallback, no pipeline
intervention — inherited unchanged.

**Scoring, ordering and tie-break.** Qualifying candidates are ordered by the committed reliability
ordering. Ties break by provider name ascending. **Carrier quality plays no part**, and cannot: no
carrier exists at this stage.

**Budget ceiling.** A committed maximum number of DEVELOPMENT requests per candidate and in total;
exceeding it ends qualification without a selection rather than widening the budget.

**Outcome.** The selection, the full ordering and every candidate's capability profile are committed
together, before Stage 2 begins. If no candidate qualifies, M117 stops with no route selected and no
H62 freeze — a legitimate and recordable outcome, not a reason to relax a threshold.

## Stage 2 — H62 freeze, only after the selection is committed

Only once the route selection is committed may the H62 analysis plan and generator specification be
frozen. Everything else is inherited from M116's merged apparatus without modification:

- the scientific proposition, qualifying input, generator prompt and output schema, byte-for-byte;
- the minimum 3 qualifying carriers and 3 distinct qualifying structures, and exact fixed-point
  closure;
- M113 demand derivation, qualification, scoring and P1–P22;
- machine-only pre-seal admission as a pure predicate, and the positional content-independent
  carrier envelope under a nonce committed before generation;
- the one-shot rule: the first completion carrying evidence of model execution consumes the
  scientific generation opportunity; no content-dependent redraw, no repair, no selection among
  completions;
- the deterministic terminal classifier over preserved non-carrier telemetry;
- the tested-system freeze **before** the qualifying generation, re-proved at admission, sealing,
  reveal and scoring;
- seal before inspection, single authorized reveal, fail-closed consumption, independent replay.

## What must not happen

The route may not be changed after the H62 freeze. The carrier schema may not be weakened to
accommodate any provider. Thresholds may not be lowered after observing a candidate. No candidate
may be added to the eligible set after the matrix has run. The qualifying input may never be used as
a DEVELOPMENT probe. H61 is not revived, and M116 is not reopened.

## Stopping rule

If Stage 1 qualifies no route, M117 stops there and the record says so. The proposition is then not
testable by any endpoint reachable under the committed eligibility rule, which is a finding about
the available instrument family and is recorded as one — not a licence to widen eligibility until
something passes.

## Claim boundary

Inherited unchanged. A successful H62 would be bounded evidence from one blind generated and sealed
carrier bank: it would not close G1, G4 or any generality gate, and would not support an AGI claim.
Stage 1 is instrument qualification and is not evidence for H62 at all.

## Chronology at drafting

M113/H58, M114/H59, M115/H60, M116/H61: closed, untouched, all four hypotheses untested. M117/H62:
candidate only; no route selected; no plan frozen; no spec frozen; no bank; **qualifying
invocations 0**; G1–G10 unmoved.
