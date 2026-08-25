# M108 — adversarial review

Written before the freeze, against the instrument as built. Each objection is stated in its
strongest form. Some are answered by construction; the ones that are not are **conceded**, and a
conceded objection bounds what a positive M108 may be said to show.

## 1. "The host wrote the answer into the runtime"

The runtime names no target, no rule and no component polarity. `scripts/audit_m108_boundaries.py`
searches both the runtime and the capsule entry point for the later demand's truth table and for the
adopted rule's truth table in six serialized forms each — Python list, JSON with and without
separators, integer list, bitstring, tuple — and the audit's own falsifiability is checked: each
form does match when the value is present.

The feature vocabulary is also checked for component names, so a feature cannot be a relabelling of
the answer. `operator_axis_progress_available` is computed from the state and the candidate space
alone and never inspects the demand; `demand_consistent_with_readable_signals` is computed from the
demand alone and never inspects the operator table.

**Answered.**

## 2. "The rule space was a menu the host supplied"

The candidate space in `acquire_attribution` is `expression_image(state["operators"], …)` — the
functions the lineage's own interpreter can express over the feature signals. That is why the
monotone control fails: its space holds four programs and none reproduces the blame record. The
audit asserts that `acquire_attribution` reaches for the lineage image and never for
`operator_space`.

**Answered.** This is also the load-bearing point of the milestone: the rule is a program in the
substrate the previous generation extended, which is what makes the dependency between generations a
lemma rather than a story.

## 3. "Determinacy is trivial — any one episode picks a rule"

It was, in the first draft, and that draft was wrong. Grouping consistent rules by their behaviour on
the *observed* rows makes a single episode sufficient. Determinacy is now judged on the rows
attribution can actually be asked about, established by complete census: every operator table
reachable by one candidate addition, at every interface width, against all 256 world functions —
14 303 unconstructible pairs. Row `(False, True)` is unreachable because a saturated operator table
plus a readable-consistent demand means the demand is already constructible, so no failure exists to
attribute.

P7 is the teeth: an episode set covering rows `{0, 3}` yields four consistent rules in **two**
attribution classes and the lineage refuses. The full set yields two rules in **one** class.

**Answered.**

## 4. "The hardwired baseline is a straw man"

`M0` is not weakened for the comparison. Its operator table is saturated at the base width — every
one of the sixteen functions of two signals is already constructible — so its refusal cannot be
"it needed a better operator". It exhausts the full twenty-operator candidate space, and it refuses
again at node bound 13. Both lineages get the same machinery-step budget and both use one step.

`M0` is exactly M107's `S1`: the operator table is obtained by replaying M107's own frozen
acquisition, not written by hand. `test_m108_starts_from_the_operator_table_m107_actually_acquired`
holds that continuity as a standing assertion.

**Answered.**

## 5. "The later capability was reachable all along; the interface extension is theatre"

Two independent structural certificates, both budget-independent:

- every expression at the base width reads only signals 0 and 1, so its world image is constant
  along axis 2. Sixteen liftable images out of 256 world functions; the intersection with the target
  is empty **for every operator set, arity and depth**;
- the target is non-monotone, so it is outside the complete image of the monotone fragment at *full*
  width by the monotonicity lemma.

The target therefore requires **both** generations. Neither the interface alone nor the operator
table alone reaches it.

**Answered.**

## 6. "The lineage granted itself authority"

It can extend a registered component and nothing else. The registry is fixed and `decode_state`
refuses a widened one; the interface ceiling is enforced and refuses at the world width; the node
bound, the candidate space, the machinery-step budget and the evaluator are host-held. Every capsule
runs `-I -S` on a capsule-only import path, reports zero model, network and remote-execution calls,
and the producer process is dead before the later demand exists.

**Answered.** These constraints are part of the claim. A result obtained by relaxing them would not
be this result.

## 7. "The blame labels are supervision — the lineage did not discover attribution"

**Conceded, and declared.** The episodes carry authored blame labels. M108 tests whether an acquired
attribution rule causally changes later acquisitions. It does **not** test whether a lineage can
invent the labels, the feature vocabulary, or the component registry. A positive M108 must not be
described as autonomous diagnosis.

## 8. "The rule is applied to a feature pattern it was trained on"

**Conceded, and declared.** The later demand's feature row is one the episode set covers. What is
demonstrated is generalization to a **new demand** with a recorded feature pattern, not extrapolation
into a feature region never observed. With this two-feature vocabulary the alternative is not
available honestly: rules consistent with the record are unconstrained off the observed rows, so a
claim of extrapolation would be a claim about an arbitrary tiebreak.

## 9. "Two rules survive; the adopted one is an arbitrary pick"

Two rules survive and they agree on every row attribution can be asked about — they are the same
machinery, in exactly the sense M107's reach classes were the same capability. The representative is
chosen canonically, by node count then canonical JSON, so the choice is a pure function of the
evidence. Both members are non-monotone, so the precondition on generation 1 does not depend on which
is picked.

## 10. "This is recursive self-improvement"

It is not, and the protocol says so. One rule, over two authored features, chosen from sixteen
programs, in a three-signal Boolean world, with the registry, budgets and evaluator fixed. What a
positive M108 would license is one sentence: *within a frozen bounded environment, a
lineage-acquired modification to the acquisition machinery causally expanded the set of later
improvements the lineage could construct under an equal budget.*

Recursive depth of two remains unmeasured. That is M109's question, not this one.

## 11. "The freeze is verifiable only on the machine that froze it"

That defect cost M105. M107 fixed it with milestone-local `.gitattributes` files and bound them —
which does not generalize, because git reads at most one attribute file per directory, so binding one
in a shared directory locks that directory for every later milestone. M108's sources sit in exactly
those directories and cannot be pinned without editing bytes M107's frozen protocol binds, which
M107's own live gate correctly refuses.

M108 therefore binds JSON evidence by raw bytes — digests are computed over those bytes, and the
repository-wide `experiments/M1*/*.json -text` rule already makes them identical everywhere — and
binds Python and Markdown members by SHA-256 over LF-normalized content. The mode is recorded per
member. This is strictly more portable than raw-byte binding: it is blind only to a difference that
cannot change what a Python module does, and `test_m108_binds_no_file_an_earlier_frozen_protocol_binds`
holds the non-overlap as a standing assertion.

**Answered, by changing the scheme rather than the claim.**

## 12. "The instrument will fail the way M103 and M105 failed"

Both were lost to a checker that could not start. M108's checker bootstraps the repository root at
import time, before anything can need it, and `test_the_checker_replay_import_resolves_as_a_direct_script`
executes it as a direct script from `scripts/`. Before any freeze the complete
`CANONICAL -> PRESERVE -> CHECK -> REPLAY` chain is rehearsed end to end in a throwaway clean
checkout against a materialized DEVELOPMENT result, with exit codes asserted for result-absent,
result-present, report-already-exists, corrupted result and tampered result carrying a recomputed
digest.

Two independent DEVELOPMENT runs already produce identical stable evidence projections, which is
what P16 will measure — and is the predicate M098 failed by retaining process identifiers.
