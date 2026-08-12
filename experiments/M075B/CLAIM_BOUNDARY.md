# M075-B claim boundary

Five different things get called "independent". They are not interchangeable, and conflating any
two of them would turn this instrument into a way of announcing a stronger result than it earned.
They are separated here, and the separation is enforced in code: `BLIND_CLAIM_BOUNDARY` is a
frozen constant that both the analysis plan and the system protocol must carry byte-for-byte, and
a generator descriptor recording `training_data_independence_proven: true` is rejected outright.

## The five levels

### 1. Procedural independence — **claimed, and provable**

The bank's contents were fixed before the tested system's protocol was frozen, and the selection
rule was committed publicly by digest before any task existed. Nothing about the bank was chosen
after observing how the system behaves.

*Proved by:* `GENERATOR_SPEC.json` and `ANALYSIS_PLAN.json` committed at F1; the frozen
`assembly` record; `GENERATION_LEDGER.json` admitting exactly one materialization; the validator's
import graph containing no path to the tested system.

### 2. Generator context blindness — **claimed, and provable**

The process that emitted the bank received one hashed input file, in a container with no
repository mount, no network, an allowlisted environment and a fresh working filesystem. It was
shown nothing about this project.

*Proved by:* `ISOLATION_ATTESTATION.json`, whose recorded argv is independently audited — mount
sources are resolved against the repository root rather than string-matched, and environment
values are checked even when the variable name is allowlisted.

*Not proved:* that the model is ignorant of this project. Only that it was not told.

### 3. Training-data independence — **NOT claimed, and not provable**

Nobody controls what a checkpoint was trained on. The strongest available argument is
**antecedence**: a checkpoint published before this research line became publicly accessible
cannot have memorized *these* specific tasks or results.

That argument is narrow, and its limits are recorded rather than glossed:

- it bounds memorization of this repository's content, nothing more;
- the *ideas* involved — capability-absent tasks, matched pairs, budget-aware stopping — are
  ordinary machine-learning concepts present in any large corpus, and antecedence says nothing
  about them;
- for an API-hosted generator it cannot be demonstrated at all, and the descriptor may then not
  record a weights digest either.

The sentence this repository may never write is **"the generator does not know about this
project"**. The sentence it may write, when the isolation attestation supports it, is **"the
generator was supplied no context about this project"**. `validate_generator_descriptor` enforces
the difference by refusing any descriptor that records the first as proven.

### 4. Human independence — **NOT claimed, and not obtained**

No person outside the project chose the subject matter, wrote a task, held the payload or signed
an independence attestation. M075's boundary requires all four, and this milestone supplies none
of them. A model prompted by the project is not a second party; it is the project's instrument.

This is why [issue #112](https://github.com/mjodheim/Mira-Genesis/issues/112) stays open.

### 5. External reproduction — **NOT claimed, and not obtained**

One generator, one bank, one run. Reproduction requires a second generator differing in family
and runtime, a separate bank and a separate protocol version — and even that reaches only the
cross-generator tier, not the human one.

## The evidence ladder

| Tier | Name | Reached by | Supports H21? |
|---|---|---|---|
| 0 | `project_authored_public_bank` | M075's public comparison | No — the project wrote the tasks |
| 1 | `blind_generated_sealed_bank` | **M075-B, if it runs and passes** | No |
| 2 | `cross_generator_reproduced_sealed_bank` | M075-B plus a second, materially different generator | No |
| 3 | `human_maintained_sealed_bank` | M075's original protocol — still open, still #112 | Not alone |
| 4 | `independently_reproduced_human_maintained_sealed_bank` | M075 plus a second maintainer and bank | **Yes** |

Tiers 1 and 2 do not entail tier 3. A blind generator removes the risk that the project's
expectations shaped the tasks; it does not supply the outside judgement that tier 3 is about. The
ladder is not a queue in which reaching 2 advances you toward 3 — 3 requires a person, and no
number of generators becomes one.

## The phrase to use for a positive result

> Blind externally materialized sealed-bank evidence for H21, at the
> `blind_generated_sealed_bank` tier: one bank emitted by a context-isolated generator, sealed
> before inspection, scored against thresholds frozen before the bank existed, on a single
> execution with no retry.

And the sentence that must accompany it:

> This is not independent human reproduction. H21 remains untested at the tier its own protocol
> requires, and M075's independent-maintainer requirement is unmet.

## What a positive result would still not establish

Not AGI. Not Genesis Gate 2 or 3. Not mathematical impossibility of the impossible tasks. Not
general safety. Not that the agent refuses correctly outside the bank's domains. Not that the
epistemic context is the only cause of any difference observed — the conditions use independent
model samples, as M075 already records, and no provider seed or snapshot changes that here.
