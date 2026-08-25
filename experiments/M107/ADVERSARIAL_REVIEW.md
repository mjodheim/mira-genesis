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

## The rehearsal, and the fourth defect it caught

The complete `CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain was rehearsed end to end in a throwaway
clone with its own rehearsal freeze, using exactly the commands the canonical chronology will use. It
consumed no canonical attempt and wrote nothing to the repository's evidence path.

**The first full rehearsal returned `verdict: negative`, P16 false, 15/16, `replay_equal: false`.**
The stable projection excluded `pid` but not `producer_pid` or `later_pids`, so two runs of the same
deterministic experiment produced different projections. **This is exactly the defect that made M098
negative** — a frozen projection retaining process identifiers that clean replay cannot reproduce.
The raw identifiers are pure process accident; the derived boolean `producer_pid_absent_from_later`
carries the claim and stays. Orchestration and checker now share one key set.

After the correction the rehearsal returns `verdict: positive`, **16/16 computed and true, zero
uncomputed, replay equal, exit 0**.

Four defects were therefore found before any freeze, two of them fatal to a canonical attempt:

| defect | consequence if unfound |
|---|---|
| acquisition took a single demand | H52's joint-determination claim untestable |
| isolation detector resolved `built-in` relative to the capsule | **P15 false** — every process reporting a false leak |
| protocol bound M106's inherited pool identity | freeze unbuildable |
| process identifiers inside the stable projection | **P16 false** — M098's exact failure mode |

## A structural defect in the repository's freeze design, found by M107

Every milestone binds its apparatus by raw-byte SHA-256, and every milestone must pin those bytes in
`.gitattributes` or inherit M105's checkout-dependent defect. But the root `.gitattributes` is itself
a bound member of M105's and M106's protocols. **Pinning milestone N+1 therefore necessarily breaks
milestone N's binding.** The design is self-defeating at the second freeze.

M107 hit it immediately: adding its entries to the root file made M106's frozen-apparatus test
report `['.gitattributes']` and both CI test jobs fail. M105's binding turned out to have been broken
already — by M106's own pinning, and by the two bound members edited to record M105's verdict — but
that only surfaces on the exact canonical runtime, because `require_frozen` refuses on the runtime
check first everywhere else.

The fix is architectural, not local. Git applies `.gitattributes` per directory, so each milestone
pins its own members in files no earlier protocol binds:

- `experiments/M107/.gitattributes`, `metamorphosis/.gitattributes`, `scripts/.gitattributes`,
  `tests/.gitattributes` — bound by M107;
- the root file restored to its frozen bytes, so M106's binding digest matches the freeze again.

Two rules follow for every future milestone, both now enforced by tests:

1. **Never bind a file an earlier frozen protocol binds.** Pin bytes in milestone-local attribute
   files.
2. **Never record a verdict inside a bound member.** M106 keeps its result summary outside the bound
   list for this reason; M105 predates the lesson and its binding is permanently drifted.

A drifted apparatus is a defect *before* the canonical attempt, because the freeze would be
unverifiable and the run must not proceed. *After* the attempt the protocol is spent and the freeze
tag is the authoritative byte record.
