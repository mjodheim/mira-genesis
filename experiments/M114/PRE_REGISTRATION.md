# M114 — the same question, with an instrument that can reach the generator

**Hypothesis:** H59
**Decision slot:** D083 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage, evaluated on a blindly materialized carrier family
**Pre-registration date:** 27 August 2026
**Status:** **CANDIDATE. NOT FROZEN. THE BANK DOES NOT EXIST. Phase is `draft`.**

## What this milestone is, and what it is not

M114 is a **corrective instrumental replication** of M113. It asks M113's scientific question with a
delivery instrument that can distinguish a request that never reached the model from a model that
answered.

M113 is **closed**. It froze an analysis plan and a generator identity, made one physical request,
received HTTP 429, materialized no bank, and left H58 untested. That record is final. It is not
re-frozen, not reinterpreted, not repaired and not completed. Nothing in M114 makes M113 into
anything other than what it was: an **instrument failure**, correctly recorded as one.

M113's record, bound by digest so that "unchanged" is checkable rather than asserted:

| artifact | sha256 |
|---|---|
| `experiments/M113/PRE_REGISTRATION.md` | `3bbbfe945f2fb80c30ea0ab3215833066f8481dede2391dbe033685308750aaa` |
| `experiments/M113/ANALYSIS_PLAN.json` | `48948e6782c111e00a58aac996f22c7fa610c79138168f80a099268656bc0527` |
| `experiments/M113/GENERATOR_SPEC.json` | `a8be0181d448b49200555de3ff1031265283109d8c68bcc3299703e0105751a4` |
| `experiments/M113/GENERATION_LEDGER.json` | `ac3ab6033a52f7dc4b15a85475fc954ca9686ca3704ad301e3a3e5024fa8285a` |

`tests/test_m113_record_is_closed.py` pins those digests, asserts that the ledger holds exactly one
attempt with outcome `aborted` and no payload, and fails if a bank, a reveal or a result ever appears
under `experiments/M113/`.

## Why H59 and not H58

The register carries **one hypothesis per milestone**, strictly monotone. M106 set the precedent: it
was a corrective replication of M105, and it took **H51** rather than reusing M105's number, with
`DECISIONS.md` recording that "M105 remains negative. D074 is unchanged and is not retroactively
repaired by this result."

The same reasoning applies here for the same reason. A replication that inherited its predecessor's
hypothesis number would make the predecessor's record read as though it were still open — as though
M113 were a first draft of M114 rather than a completed milestone with its own outcome. It is not.
H58 was never tested and stays untested, permanently. H59 is the hypothesis M114 tests, and it states
exactly what H58 stated.

**H59.** On a carrier family this project did not design, materialized blind and sealed before anyone
read it and revealed only after the tested system was frozen, the acquired M109–M111 machinery
resolves demands derived by a frozen rule, and refuses structurally unsatisfiable demands rather than
inventing an adapter, measurably better than an otherwise identical fresh lineage under the same
budget.

`P22` is H59, exactly as `P22` was H58.

## What is imported unchanged

Everything scientific. Not copied — imported, by reference and by digest, so that a claim of
sameness cannot drift:

- `metamorphosis/m114_carrier_bank.py` delegates its plan and generator-spec rules to
  `m113_carrier_bank`, and adds clauses; it restates none.
- `scripts/run_m114_qualification.py` imports `run_bank`, the sealed scope and the arms from
  `scripts/run_m113_qualification.py`.
- `scripts/check_m114_result.py` imports `P1`–`P22` from `scripts/check_m113_result.py`.
- `scripts/run_m114_generation.py` imports the transport from `scripts/run_m113_generation.py`.
- `experiments/M114/GENERATOR_PROMPT.txt`, `QUALIFYING_INPUT.txt` and `OUTPUT_SCHEMA.json` are
  M113's files byte for byte, and `m114_carrier_bank.GENERATOR_INPUT_DIGESTS` pins all three.
- The generator identity is M113's: `deepseek/deepseek-v4-flash-0731`, provider `Morph`, no
  fallbacks, no automatic routing, `require_parameters: true`, the same sampling, the same
  structured-output schema, the same declared quantization with the same epistemic status
  (discovery-bound, not runtime-attested).
- The canonical request body is byte-identical to M113's:
  `02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc`.

24 carriers requested, minimum 3 qualifying, minimum 3 distinct qualifying structures, exact
fixed-point closure computed per carrier, no inherited bound, no selection, no manual correction, an
insufficient bank is a **negative** result and not a reason to generate again. None of that moved.

## What M114 changes, and it is only this

M113's protocol used one predicate — "one physical request" — to carry two different quantities:

- how many times the instrument may **reach** for the generator;
- how many times the generator may **produce** a bank.

Those coincide only while the network cooperates. A capacity rejection from a shared upstream pool
spent the second budget without ever spending the first, and the milestone ended on a fact about
queueing. M114 separates them:

| term | meaning |
|---|---|
| `delivery_attempt` | one physical request carrying the frozen body |
| `bank_materialization` | a response that actually carries a model completion |

**Up to 3 delivery attempts are permitted to obtain at most 1 bank materialization.**

### The retry rule, in full

1. Every attempt sends the **byte-identical frozen request body**. A retry that changed the request
   would be a second experiment wearing the first one's name.
2. An attempt may follow another **only** after an explicit **HTTP 429** that carries **no
   completion of any kind** and **no evidence that the model executed**.
3. The wait before a retry is a fixed, pre-registered **60 seconds**. It is not backoff, not
   jittered, and not chosen at runtime.
4. **Three capacity rejections ⇒ `M114 = instrument-aborted`.** That is a fact about transport
   capacity. It is **not** a negative result about H59, and nothing is relaunched.

### What is never retried

Each of these is **final on its first outcome**, whatever the budget says:

- a completion that is invalid JSON;
- a completion that violates the frozen output schema;
- a truncated completion;
- a refusal by the model;
- an insufficient bank — too few carriers, too few qualifying, too few distinct structures;
- a timeout **after transmission** whose state cannot be established;
- a connection lost in an ambiguous state;
- any HTTP status other than 429;
- **any scientific outcome, `P22` false included.**

That enumeration is carried in the frozen analysis plan itself, not only in this document and the
module, so it sits inside the plan commitment. A milestone permitted three attempts has exactly one
clause it must not be able to quietly narrow later, and this is it.

### Where the doubt goes

`m114_delivery.classify_attempt` is conservative in one direction only. An attempt counts as a
capacity rejection — the single retryable outcome — only when **every** condition holds: status
exactly 429, no completion present, nothing indicating the model executed. Any doubt resolves to
`failed_ambiguous`, which is terminal.

That asymmetry is the safeguard, and it is deliberately lopsided. Misclassifying a capacity rejection
as ambiguous costs one unused attempt. Misclassifying an ambiguous outcome as a capacity rejection
would permit a second draw against a model that may already have produced one, and **no downstream
check could ever recover the difference**. A protocol that retried an ambiguous timeout would be a
protocol that could quietly draw twice and keep the better draw. Every part of this milestone exists
to make that impossible.

### What the checker recomputes

Nothing the ledger says about itself is evidence; the runner writes it. What is evidence is the
sequence of attempts, and `m114_delivery.validate_delivery_ledger` derives all of the following from
that sequence:

- the attempt count against the frozen budget of 3;
- contiguous attempt indices from 1, in order;
- that every attempt's `request_body_sha256` is the same and is the spec's;
- that no served provider or model differs from the requested one;
- that each recorded outcome is the one `classify_attempt` computes from the evidence carried;
- that no attempt follows a terminal outcome;
- that no attempt follows one the frozen rule did not permit a retry after;
- that each recorded `retry_permitted_by_the_frozen_rule` equals what the rule computes;
- that the first attempt waited 0 seconds and every later attempt waited at least 60;
- that at most one attempt materialized a bank, and that nothing follows the one that did;
- that the ledger's declared `bank_materialization_index` is where the attempts actually place it;
- that the ledger binds the frozen generator spec's commitment.

`scripts/check_m114_result.py` adds two verdicts on top of `P1`–`P22`, and both are **strictly
subtractive** — neither can turn a negative into a positive:

- a canonical attempt whose delivery ledger violates the frozen rule ⇒ `invalid`;
- a canonical attempt that materialized no bank ⇒ `instrument-aborted`.

`tests/test_m114_delivery.py` and `tests/test_m114_carrier_bank.py` attack each of these rules
directly: a fourth attempt, an attempt after a terminal outcome, a retried ambiguous timeout, a 429
carrying a completion, two materializations, a non-429 retry, a changed request body, a mislabelled
outcome, a forged retry permission, an index mismatch, an omitted field, a provider or model
substitution, a shortened wait.

## When this rule was decided

This is the part that matters most, and it is recorded here so it can be checked rather than trusted.

The separation of `delivery_attempt` from `bank_materialization` was decided:

- **after** M113's instrument failure — it is a response to an observed transport behaviour;
- **before** any M114 bank existed;
- **without any observation of H58 or H59 whatsoever** — no carrier, no payload, no qualification
  count, no `P22` value was ever seen, because M113's request never reached the model and M114 has
  not yet made one;
- and it was **never part of M113**, and must never be described as though it had been.

Those four statements are carried as booleans in `m114_carrier_bank.FILIATION`, which the frozen
analysis plan must reproduce exactly or fail validation, and which the result and check report both
carry forward.

M113 remains an instrument failure under the protocol it actually ran.

## Filiation

| | |
|---|---|
| predecessor | M113 |
| predecessor hypothesis | H58 |
| predecessor outcome | instrument-aborted before bank materialization |
| predecessor record | closed; not repaired, not reinterpreted, not completed |
| this milestone | M114 |
| this hypothesis | H59 |
| relationship | corrective replication with transport-capacity semantics preregistered before any new generation |
| scientific target | unchanged |

## Commitments

| | |
|---|---|
| candidate analysis plan commitment | `d191f74df43526b35e39095c62b2329fe47fb467d9c5167f0eb3bf935b1c0339` |
| canonical request body | `02a71fb54e492bed151981f6b3f79ec947e7e404bc999caffa37c2c642beaabc` |
| `GENERATOR_PROMPT.txt` | `f79fb18cde53e0efd4b1defef43460589376c0d3e93ff0eb2443836de526269e` |
| `QUALIFYING_INPUT.txt` | `c73721aec1de46b792551c9b16291b69806f21b4181a212b356bcc73e3f592e0` |
| `OUTPUT_SCHEMA.json` | `1020a1db9625f2734be1f548edd4c5af0139cb17732d13fb25913144f9106075` |

The generator spec's commitment is not listed here because the freeze sets
`frozen_before_generation` and stamps `frozen_at`, which changes it. It is published at the freeze,
before the first delivery attempt, and the delivery ledger binds it.

## What would make this milestone negative

The same things that would have made M113 negative, unchanged: fewer than 3 qualifying carriers,
fewer than 3 distinct qualifying structures, or `P22` false — the full descendant failing to be
strictly better than the fresh control on at least one of correct construction, calibrated refusal,
invented adapters or attribution agreement while being no worse on the other three.

An insufficient bank is a **negative result**, not a reason to generate again. The delivery budget
buys attempts to *reach* the generator; it buys nothing about what the generator produces once
reached.

## What would make this milestone abort

Three capacity rejections, or any terminal non-materializing outcome. `instrument-aborted` is not a
result about H59, and H59 would then stand exactly as H58 stands now: untested.
