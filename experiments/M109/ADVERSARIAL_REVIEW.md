# M109 — adversarial review

Written before the freeze, against the instrument as built. Each objection is stated in its strongest
form. Some are answered by construction; the ones that are not are **conceded**, and a conceded
objection bounds what a positive M109 may be said to show.

## 1. "The host wrote the rules down"

The runtime, the capsule entry point and the curriculum author are searched for both staged demands
and both adopted rules, in six serialized forms each — Python list, JSON with and without separators,
integer list, bitstring, tuple. Each form is verified to match when the value *is* present, so the
check is not vacuous. The feature vocabulary is also checked for component names, so no feature can
be a relabelling of the answer.

**Answered.**

## 2. "The blame labels are supervision under another name"

M108's were. M109's are the outcome of a trial the lineage runs on itself: extend each registered
component, observe which extension resolves the demand. There is no episodes fixture, and the input
preflight asserts its absence. The audit checks behaviourally that the trial examines every
registered component and declares its rule.

**Answered** — with the asymmetry in §3 declared rather than hidden.

## 3. "The trial is not the same procedure for every component"

It is not, and the difference is real. The trial tests **necessity**, not sufficiency: widening the
candidate space is a no-op unless the operator search that follows finds something the narrower space
did not, so the candidate space counts only where the current space is already exhausted for this
demand. Under a pure sufficiency test every operator-table demand would also count as a
candidate-space demand — the wider space contains the narrower one — every such demand would become
ambiguous, and row 1 would vanish from the domain.

The rule is recorded in the trial output as `minimal_necessary_component`. The audit asserts it. An
earlier version of that audit check searched the source for component-name literals and failed
because the code refers to them by constant; the check was wrong, not the code, and it was replaced
with a behavioural one.

**Answered by declaration**, not by pretending the symmetry exists.

## 4. "The rule space is a menu"

The candidate space in `acquire_rule` is `expression_image(state["operators"], …)` — the programs the
lineage's own interpreter can express over the feature signals. That is why the handed counterfactual
in §6 fails: the space contains no rule that separates the two components before generation 1.

**Answered.**

## 5. "The attribution domain was sampled"

It is a complete census over the declared probe family: every operator table one candidate addition
away from the initial one, at both interface widths, under both candidate spaces — 84 states — against
all 256 world functions, 10 496 determined pairs. Rows 1, 2, 3, 6, 7 are reachable while attributing;
rows 0, 4, 5 are not. **No row carries more than one label**, which is what makes a rule derivable at
all, and the audit asserts it.

**Answered.**

## 6. "The second generation is the first one in disguise"

The two generations target different components, adopt different rules with different identities, and
the second is refused outright to a lineage that has not made the first. That refusal is a lemma, not
a search outcome: feature row 3 lies below row 7 componentwise, so every monotone program true at row
3 is true at row 7, and no expressible rule targets the candidate space without also targeting the
signal interface.

This is stronger than the pre-registration predicted — the first draft expected the handed
counterfactual to succeed. It is recorded as a correction, and the counterfactual remains a
**measurement**: whatever it returns is reported.

The barrier is robust to the adoption rule. A fresh `M0` is refused under both conservative and
non-conservative adoption, for different reasons.

**Answered.**

## 7. "Conservative adoption manufactures the result"

**Partly conceded, and declared.** A rule may fire only where the lineage holds positive evidence; a
relevant row it has never observed is required not to fire. That is a standard induction principle,
and it is what leaves later rows available to a later generation.

It is not what stops `M0` — the table below shows `M0` refused either way. But it **is** what lets
`M1` succeed: under non-conservative adoption neither lineage acquires the second rule and M109 would
be negative.

| adoption rule | `M0` alone | `M1` after generation 1 |
|---|---|---|
| conservative | refused — no expressible rule | **confirmed** — one class |
| non-conservative | refused — underdetermined | refused — underdetermined |

## 8. "The curriculum is authored, so the ordering is a stage set"

**Conceded, and declared.** The demand sequence is authored and the second demand is revealed only
once the first is resolved. What is tested is whether a lineage that cannot resolve stage one can ever
hold stage two's evidence — not whether the world would have presented it anyway. The registry, the
feature vocabulary and the curriculum all remain authored.

## 9. "The lineage granted itself authority"

It can extend a registered component and nothing else. `decode_state` refuses a widened registry and
an invented candidate space; the interface ceiling, the candidate-space ceiling and the machinery
generation ceiling all refuse at their bounds. Every capsule runs `-I -S` on a capsule-only import
path and reports zero model, network and remote-execution calls. Producer capsules hold no demand at
all, stage-one capsules hold only the first, stage-two capsules only the second, and all three
directions are measured.

**Answered.** These constraints are part of the claim. A result obtained by relaxing them would not be
this result.

## 10. "This is recursive self-improvement"

It is not, and the protocol says so. Two rules of three nodes each, over three authored features, in a
three-signal Boolean world, with the registry, the curriculum, the budgets and the evaluator fixed.
What a positive M109 would license is one sentence: *within a frozen bounded environment, a
lineage-acquired modification to the acquisition machinery enabled a second, distinct machinery
modification the unmodified lineage could not have reached, and the improvement-reach of the three
successive machineries is a strict chain.*

Recursive depth of **three** is unmeasured, and so is acceleration. Those are the next questions.

## 11. "The instrument will fail the way M103, M105 and M098 failed"

M103 and M105 were lost to checkers that could not start; M109's bootstraps the repository root at
import time and a test executes it as a direct script from `scripts/`. M105's freeze was verifiable
only on the machine that froze it; M109 binds text members by LF-normalized content and JSON evidence
by raw bytes, with the mode recorded per member, and a standing test asserts M109 binds no file an
earlier frozen protocol binds. M098 retained process identifiers in its stable projection; two
independent M109 development runs already produce identical projections, which is what P18 measures.

M108's rehearsal had to be rerun after a late change, because a rehearsal that does not cover the
frozen bytes is worth nothing. The same rule applies here.
