# M094 design audit — resolved before any freeze

**Status: audit complete, four defects found, nothing is frozen. H39 is unregistered and
unclaimed. No qualification exists and none may be generated until a protocol is frozen.**

This document exists because M094's implementation was committed *ahead* of its protocol, in
`df88d24` (PR #170), while carrying docstrings that claim more than the code does. The audit
below measures those claims against the real repository. Numbers come from
`scripts/audit_m094_design.py`, are re-runnable, and are stored in `DESIGN_AUDIT.json`
(digest `6ebcafa4…`).

Starting point: clean `main` at `df88d24851c018836a35e8102ff0aa7dbf81167c`. M093 is historical
evidence from here on; its record is read, never edited.

The audit asserts nothing about M094's eventual verdict. Its purpose is that these defects are
on the record with reproducible numbers *before* anything is frozen, so that no later correction
can be mistaken for a precommitment.

---

## What the inherited code claims

`metamorphosis/m094_component_discovery.py`:

> The lineage examines each component, produces diagnostic hypotheses, selects the most
> constrained component, and justifies the choice […] This is the first step toward removing
> the authored TARGET_FILE from M093.

`metamorphosis/m094_transform.py`:

> The winning patch emerges from the search, not from authored code. Contrast with M093's
> `CodePatch.generate` which contained the exact patch.

Both claims are currently false. M094 as committed reproduces M093's authored target and
M093's authored patch by construction.

---

## Defect 1 — the deciding indicator names one file rather than measuring a property

`missing_query_method` carries the highest authored severity (3) and is the pattern that
decides the selection. Its entire detection rule is the substring `event.kind`.

| indicator | severity | memory.py | safety.py | contracts.py | components matched |
|---|---|---|---|---|---|
| `event.kind` | 3 | 2 | 0 | 0 | **1 / 3** |
| `if not` | 2 | 5 | 0 | 3 | 2 / 3 |
| `__init__` | 1 | 1 | 0 | 0 | **1 / 3** |

`event.kind` occurs in exactly one eligible component. An indicator that matches exactly one
candidate does not discriminate between candidates; it names one. The "diagnosis" is the
authored `TARGET_FILE` of M093 rewritten as a string search.

## Defect 2 — the detector is inverted with respect to the capability it claims to detect

`missing_query_method` asserts that a component "exposes a collection but no declarative query
method". `mira_core/memory.py` **already defines** `MemoryLedger.events_by_kind` at line 107 —
M093 added it, and it is on `main`.

The pattern fires anyway, and measurably worse than at random:

- with `events_by_kind` present: the indicator occurs **2** times;
- with `events_by_kind` removed: the indicator occurs **1** time.

Adding the capability *raises* the score for the insufficiency that claims the capability is
absent, and the score never reaches zero. This is not a noisy detector, it is an inverted one:
`event.kind` is a fragment of the query implementation, so writing the method necessarily
introduces more occurrences of the evidence that the method is missing.

A diagnostic that reports a missing capability on a component that has it cannot support any
claim about autonomous diagnosis.

## Defect 3 — one eligible component can never be selected

`mira_core/safety.py` matches no indicator at all and scores 0. It is not a rejected
alternative; it is an unreachable one. `DiagnosticHypothesis` requires that "another hypothesis
must exist that could have been chosen instead", and for safety.py no weighting of the current
indicator set makes that true. The falsifiability the dataclass documents is not present.

The selection also does not depend on the authored severity weights: flattening every severity
to 1 selects `mira_core/memory.py` unchanged. What decides is the indicator set, which is the
part keyed to one file.

## Defect 4 — the transformation language contains the finished repair

`TRANSFORM_TEMPLATES` holds exactly **one** template, `suggest_query_method`. There is no search
space; there is one element. That template emits the complete method body as a literal, including
the guard clause and the filter expression:

```python
def {collection}_by_kind(self, kind: str) -> tuple[...]:
    if not kind:
        raise ValueError("...")
    return tuple(x for x in self._{collection} if x.kind == kind)
```

It also carries a component-specific branch, `before_method="history" if class_name ==
"MemoryLedger" else None`.

This is M093's `CodePatch.generate` with the class and collection names parameterised. The
docstring's contrast with M093 does not hold: what changed is that three identifiers became
arguments, not that the patch became constructed. Parameterisation is not synthesis.

---

## Consequence for the protocol

Were the current code frozen and run, every stage would succeed and the result would be a false
positive: a lineage "diagnosing" a component chosen for it by a substring, and "generating" a
repair it was handed whole. That is the failure M088's `authored_full_experiment_space` ceiling
arm and M089's P10 exist to catch, arriving one level up.

The protocol drafted in `PROTOCOL.json` therefore treats all four defects as **falsifiers rather
than implementation details**, and the corresponding conditions are written so that the current
implementation fails them:

| defect | condition that must fail on the current code |
|---|---|
| 1 | `P2_the_insufficiency_is_a_measured_property_not_a_component_specific_string` |
| 2 | `P3_the_diagnostic_verdict_inverts_when_the_capability_is_supplied` |
| 3 | `P4_every_eligible_component_is_reachable_under_some_admissible_observation` |
| 4 | `P6_the_repair_is_assembled_from_composable_operations_and_is_not_a_template_body` |

`scripts/audit_m094_design.py` is the instrument for P2, P3 and P4 and is re-runnable against
any candidate implementation. A implementation that cannot turn these four red is not a
successor to M093; it is M093 with more indirection.

---

## The corrected measure, and what it currently reports

`metamorphosis/m094_diagnosis.py` replaces the substring detector with a structural one. It rests
on a single separation, which is what makes it a measurement rather than a name lookup:

> demand is counted **outside** the component; supply is checked **inside** it.

A component is insufficient for a capability when callers that can actually reach it repeatedly
perform by hand an operation it could expose, and it does not expose one. Because the component's
own source is excluded from the demand count, implementing the capability can only ever *lower*
insufficiency — Defect 2 is structurally impossible rather than merely fixed. Demand is attributed
only to files that import the module or a name it defines through a package re-export, so an
unrelated class exposing a collection of the same name contributes nothing.

`tests/test_m094_diagnosis.py` drives this against synthetic repositories, so the properties do not
depend on what `mira_core` happens to contain on a given day.

**Run against the real repository, the corrected measure selects nothing.**

| component | capability | demand | supplied | unmet |
|---|---|---|---|---|
| `mira_core/memory.py` | `MemoryLedger.events` filtered by `kind` | 2 | yes | **no** |
| `mira_core/safety.py` | — | — | — | — |
| `mira_core/contracts.py` | — | — | — | — |

Two consequences, both honest and both material to whether M094 can run at all.

First, the one capability the old detector "diagnosed" is **already supplied** — M093 added
`events_by_kind`, and the corrected measure correctly reports it as met. The inherited
implementation was not merely rigged toward `mira_core/memory.py`; it was rigged toward a
capability that no longer needs building.

Second, `mira_core/safety.py` and `mira_core/contracts.py` expose no collection, so the single
capability shape implemented so far cannot reach them. Their unreachability under the *old*
indicator set was Defect 3; under the corrected measure it is a narrower and more honest fact —
there is one capability shape, and it does not apply to them.

M094 therefore cannot presently be frozen against this eligible set, because the protocol's own
P1 and P4 would fail: with one shape and one already-met capability there is nothing to diagnose,
and two of three components remain unreachable. Two admissible ways forward, neither presupposed:

- **widen the capability shapes**, so that insufficiencies other than collection-filtering are
  measurable and components without collections become reachable;
- **widen the eligible set** to components with genuine unmet demand, chosen by the measure rather
  than by hand — which is itself the thing under test, and so must be done before any freeze.

Recording this now is the point of a pre-freeze audit. Discovering after a freeze that the
diagnosis has nothing to find would be an invitation to adjust the eligible set until it did, and
that is the retry the project forbids.

## What is not in question

The transformation *infrastructure* M093 rehearsed — subprocess sandbox, A/B comparison,
transactional adoption, digest-verified persistence, exact rollback — is sound and is not
re-litigated here. M094's question is upstream of it: who chooses the target, and who writes
the repair.

## Status of H39 and D063

Unregistered and unclaimed. No hypothesis may be registered, no protocol frozen and no
qualification generated until the project owner records the decision. Nothing in this audit
constitutes a freeze.
