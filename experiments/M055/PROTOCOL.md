# M055 — construction inside the migrated lineage

**Status: PROPOSED — unqualified.**

## Research question

Can the continuing M048 lineage, in its migrated Node runtime and carrying everything it
inherited, construct a capability its accepted module language cannot express, keep every
inherited capability, and reach a second task **because** of what it acquired?

## Why this experiment exists

Requirement 1 of issue #72 asked the language-extension line to continue the qualified M048
lineage. M053 and M054 do not: both import the frozen M051 catalogue and start from an empty
registry. Since M049 the line had run on integer sequences, separated from the executable
modular body M047 built and M048 migrated.

M055 puts the construction back inside that body. It is the only experiment in the line that
satisfies requirement 1.

## Inherited state

The lineage begins from the accepted M048 version-eight native state, **reconstructed rather
than asserted**: M048's own reconstruction, migration, proposal, validation and adoption path is
re-run, and the result is refused unless it reports version eight.

That state carries thirty-two retained capabilities, ten native modules including `tool_mean`
learned before the first migration and `tool_max` learned after it.

M048 is qualified, so under D003 nothing here modifies it. Its reconstruction helpers are read
and its Node runtime is left untouched; M055 ships `m055_node_runtime.mjs`.

## Declared parameters

| Parameter | Value |
|---|---:|
| Atoms | `previous`, `current` |
| Operators | `add`, `subtract`, `minimum`, `maximum`, `multiply` |
| Formation depth | 3 |
| Admissible space at that depth | 29,330,422 |
| Admissible space at depth 2 | 2,422 |
| Construction budget | 1,024 |
| Beam width | 12 |
| Behaviour domain | 81 integer pairs |

The budget is below the depth-two space, so enumeration is impossible by construction. The
number of candidates actually constructed is recorded.

## Construction, not template selection

M048 proposes by selecting a template: `renderTool(name, expressionId)` picks one of four
hard-coded expressions, chosen by a hard-coded branch on the unknown token. M055 builds the
tool body from formation rules, compiles it to JavaScript, and executes it in the migrated
runtime. The emitted module carries executable semantics; nothing interprets a data structure
handed to it.

## Inherited regression

Every one of the inherited capabilities must be **executed** in the candidate body before
adoption, not assumed. This is requirement 7 of issue #77 and the check that distinguishes a
lineage from a fresh experiment. The validator owns that bank, owns the hidden probes, and holds
no adoption authority.

## Reuse and the ablation

The acquired expression becomes an atom for the next construction, so what the lineage acquired
becomes material rather than an answer to replay.

Three arms under one budget:

| Arm | Recorded |
|---|---|
| Continued lineage, acquired expression available | candidates constructed |
| Empty acquisition, **same composition power**, same budget | candidates constructed, and whether it solves |
| Founder module language only | whether it solves |

The from-scratch arm is given the same composition power the continued lineage has. A control
denied what the treatment enjoys is a straw man and would make the claim unfalsifiable.

**The ablation is recorded, not asserted.** If it solves the reuse task, the capability-gain
claim is refuted and the manifest says so. The experiment does not raise, and the reuse task is
not replaced until an ablation agrees: choosing the task that flatters the hypothesis after
seeing the control is the tuning illusion recorded in CHANGELOG 0.33.0.

## Refusal, fault and rollback

Ambiguous public evidence must terminate without commitment, and neither budget nor depth is
widened afterwards.

The forced post-adoption fault tampers with the accepted body. It must be detected before
anything is restored, recovery rebuilds from a serialised snapshot rather than a retained
object, and the snapshot is refused unless its digest matches. Rollback counts as exact only
when the fault is detected, **the intact state reports no fault under the same detector**, and
the restored snapshot and digest match byte for byte.

## Identity

Recorded identities are computed per **D018**, over what was decided and never over the
environment. M055 is where that defect was found: M048's `validation_digest` covered a mapping
containing the Node worker pid, so the inherited state identity drifted between processes. Until
the repair, this experiment could publish only the body digest.

## Qualification rule

M055 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

Passing qualification means the experiment ran as specified. It does **not** mean the
capability-gain claim was supported; that is decided by the ablation and reported separately.

## Claim boundary

One bounded lineage, one formation language, fixed task families, one runtime. M055 does not
establish arbitrary code generation, unrestricted self-modification, open-ended evolution,
unknown-runtime discovery, general intelligence, consciousness or production safety. Network,
repository, credential, deployment and external-system authority remain human-controlled.

M055 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
