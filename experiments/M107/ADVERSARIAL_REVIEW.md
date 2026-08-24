# M107 adversarial pre-freeze review

**Date:** 25 August 2026
**Status:** apparatus complete; DEVELOPMENT evidence only; no protocol or canonical result exists

Every objection below is one an opponent would raise. Where the honest answer narrows the claim, the
claim is narrowed rather than the answer softened.

## The strongest objections

**1. The answer is coded in the world generator.** The host codes the *space* — all twenty one- and
two-ary Boolean operators — and never the answer. The audit checks mechanically that no negation
truth table is shipped as an argument to `operator_definition` anywhere in the runtime, that the
initial table is exactly `{AND, OR}`, and that the adopted operator's table and content address
appear nowhere in the demand fixture.

**2. This is selection among a handful of coded solutions.** It is selection from a complete generic
space of twenty, and the audit records the space as exhausted. What distinguishes it from M105/M106
is *what* is selected: there, one of sixteen classifiers the interpreter could already evaluate;
here, an entry in the interpreter's own operator table, which changes the set of expressible
functions from four to sixteen.

**3. The exclusion is a search bound in disguise.** It is not. Monotone operators compose to
monotone functions at every depth, so a non-monotone target is outside reach for **every** node
bound. The certificate records `budget_independent: true`, and the fresh control is re-run at bound
thirteen and still fails. `complete_image(S0)` is four at bounds nine, eleven and thirteen alike.

**4. The interpreter secretly knows negation.** `execute_expression` contains no operator semantics:
it indexes a truth table fetched from the state and raises when an expression names an operator the
state does not hold. A test asserts that an absent operator cannot be evaluated.

**5. The extension is host code, not lineage state.** The adopted operator is serialized into the
state, content-addressed, and survives an encode/decode cycle with an unchanged state digest. The
consumer process receives only the serialized bytes; its capsule contains no demand file and the
producer's capsule contains no target file.

**6. The ablation is decorative.** Removing the acquired operator returns the complete image to
exactly four functions and makes both targets unconstructible, and the ablated state is
**byte-identical** to S0. Mutating the acquired truth table loses the reach. Corrupting the state
fails closed on the digest.

**7. More budget would let the fresh control succeed.** The fresh control holds S0, the same
observations and the same exhaustive twenty-operator search, and fails at bound nine and again at
bound thirteen. By the lemma it fails at every bound.

**8. One demand already determines the extension, so the joint demand is theatre.** The opposite:
one demand leaves **two** reach classes and the lineage must refuse. This was found in DEVELOPMENT
and pre-registered as decisive condition P4 before any protocol existed. It is what distinguishes
inferring an extension from being handed one.

**9. This is recursive self-improvement.** It is not, and M107 must never be cited as such. One
operator is acquired once. The acquisition machinery, the search, the candidate space, the demands
and the evaluator are unchanged and authored. There is no second generation and no self-directed
choice of which mechanism to improve.

## Defects found before the freeze

1. **Acquisition took a single demand** where H52 requires joint demands to determine the extension.
2. **The isolation detector resolved `built-in` and `frozen` origins relative to the capsule working
   directory**, marking the entire standard library as a leak and making P15 false. Every isolated
   process reported a false violation.
3. Two **audit checks were themselves wrong**: a substring test matched the milestone's own schema
   name, and a literal test matched `SIGNAL_ROWS`, which legitimately contains `(True, False)` as a
   signal row. Both were made precise rather than loosened.

The first two would have been fatal in a canonical attempt. All were found by running the real
commands rather than assuming they worked — the discipline D072 and D074 were written to enforce.

## The ceiling this milestone cannot touch

Even a fully positive M107 leaves the **acquisition machinery** authored: the search, the candidate
space, the adoption rule, the demands and the evaluator. Nothing here modifies the mechanism that
performs later acquisitions. Recursive depth, measured acceleration and self-identification of the
bottleneck are all out of scope, and the successor must be derived from that ceiling.
