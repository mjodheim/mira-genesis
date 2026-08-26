# M113 — carriers this project did not design

**Hypothesis:** H58
**Decision slot:** D082 (reserved; unfilled until a canonical result exists)
**Track:** A — endogenous bounded lineage, evaluated on a blindly materialized carrier family
**Pre-registration date:** 26 August 2026
**Status:** **CANDIDATE. NOT FROZEN. THE BANK DOES NOT EXIST. Phase is `draft`.**

M112 and D081 are final and are not touched by this milestone. Its bank is not reused, its defect is
not repaired, its `P1` and `P5` are not requalified, and its transfer arm stays negative at 22/24.
That a blind world violated the empirical closure assumption at bound seven is a finding this
milestone inherits, not a bug it removes.

## The ceiling M112 left standing

M112 removed **world** authorship. Its own decision record and `MIRA_GENERALITY_CRITERIA.md` name
what it did not remove, in one word: **the carrier**. The value chain, the document shape, the
reference edge, the operators, the bounds, the evaluator, the feature vocabulary and the component
registry all remained this project's. A blind generator chose values inside a carrier this project
designed.

M113 asks the next question, and it is a strictly harder one:

> Can a Genesis machinery adapt to a carrier the project did not design for it?

The generator no longer fills in a form. It emits the machine.

## What a blind carrier is

A carrier is a small deterministic interactive system, emitted as data and executed by
`metamorphosis/carrier_host.py`, a host that holds no carrier semantics — the same move M107 made
when it put the operator semantics in the state and left the interpreter empty, lifted one level.

The generator chooses, and the project does not:

| | |
|---|---|
| **representation** | one of four wire surfaces — named JSON object, named text line, packed positional digits, positional JSON array — with its own tokens, separators and key names |
| **state** | one to four named cells, each over its own finite domain, any of them latent |
| **interaction** | two to six actions, each nullary or unary over its own argument domain, under names it invents |
| **permitted operations** | a precondition per action, so a carrier can impose an order in which its actions may legally be used |
| **error structure** | its own error vocabulary, and its own mapping from a refused action to a code |

The project builds the **contract of reception** — the meta-schema, the four surface shapes, the
host, the meta-channel, the qualification rule, the demand-derivation rule and the evaluator. It does
not choose the qualifying implementations.

**Why data and not arbitrary programs.** A bank of arbitrary executables would make the sandbox,
rather than the science, the load-bearing part of the result: every claim would rest on containment
of code written by a process the project cannot inspect in advance. Under this meta-schema an action
is a finite list of arithmetic assignments modulo a declared domain and a guard is a finite list of
comparisons, so every carrier is total, deterministic, side-effect-free and exhaustible. That is a
declared limit on the claim, recorded here rather than discovered later.

## The meta-channel, stated plainly

A learner that cannot form a syntactically valid request discovers nothing, so the host exposes one
thing: the wire grammar, and the action names with their arities and argument domains. That is what a
usage line, a schema endpoint or a protocol banner makes observable in any real system.

It carries **no** cell, **no** domain, **no** initial configuration, **no** observability, **no**
precondition, **no** effect, **no** error vocabulary, **no** error mapping and **no** reachable set.
A learner handed it knows how to speak and nothing about what any sentence does.

## H58

**H58.** On a carrier family this project did not design, materialized blind and sealed before anyone
read it and revealed only after the tested system was frozen, the acquired M109–M111 machinery
resolves demands derived by a frozen rule, and refuses structurally unsatisfiable demands rather than
inventing an adapter, measurably better than an otherwise identical fresh lineage under the same
base, context, tools, compute, observation budget, carrier and evaluator.

H58 is refuted if the acquired machinery does not beat the fresh control, and it is **informatively
refuted** — not merely failed — if it does worse, which is the M110 result reproducing at a new
level. A bank yielding fewer than the frozen minimum of qualifying carriers is a **negative result,
not a retry**.

## The demand, and why the project is not choosing it

The project freezes a **derivation rule**, not a task, and applies it after the seal is broken.

Each qualifying carrier yields one **pair**, and the pair is **one object**: the carrier reference,
the budget, the meta-channel, the entry configuration and the evaluator are stored once, and the
twins carry only their target and their class. `assert_demand_pair_delta` derives both and refuses
the pair unless the only differing fields are the target and the class label. M075-B recorded why
this must be a representation rather than a check: a check has to enumerate every field that must
stay equal, and missing one silently readmits the defect.

- the **reachable** twins are one per attribution row the carrier's own census can present, each
  the canonical least determined target for its row — demands on which exactly one component
  extension makes the target satisfiable, so a wrong attribution costs the whole attempt;
- the **unreachable** twin is the least observation the exhausted state graph **proves** the carrier
  cannot show. This is what makes the incompatible body structural rather than a task phrased so
  that a careful reader gives up: no extension of any component, at any width, in either composition
  space, resolves it, because the observation is not in the image of the transition relation.

## Closure is computed, never inherited

This is the `P5` lesson, and it is the design's spine rather than a caveat attached to it.

M112 declared four fixed-point bounds — 7, 9, 11, 13 — because seven nodes closed the constructive
image on 1 160 project-generated worlds. The first blind world closed at nine, and `P5` came out
false. The bound was an empirical regularity of project-authored worlds wearing a certificate's
clothes.

Nothing in M113 inherits a bound.

- The carrier's reachable set is a **breadth-first fixed point**: the frontier is expanded until it
  is empty, and the certificate records the iteration at which growth stopped.
- The learner's exploration converges by the same criterion — a level that adds no observation it
  has not already seen ends the expansion — and `closed_at_level` records which level that was.
- `EXPLORATION_CEILING` exists as a **termination guarantee against a hostile payload**, not as an
  operating parameter. A carrier reaching it is non-qualifying under a rule frozen before any carrier
  existed, and is never re-run larger.

The devkit survey over 1 200 carriers already shows why this matters: observations first appear as
deep as **level 11**, and the largest state graph holds 98 states. Any bound chosen from the shallow
majority would have been wrong on the tail, exactly as M112's was.

## Cardinality, made mechanical and able to fail

M112 froze `requested_record_count = requested_world_count` while a world was five records, so a
hundred bought twenty. The error was not the arithmetic; it was that no stage ever compared the two
numbers.

Here **one carrier is one record**, the identity is declared as an identity in the frozen plan, and
`m113_evaluator.assert_cardinality` compares every adjacent pair at materialization time:

```
requested_carrier_count == records_emitted == carriers_enveloped
    >= schema_valid_carriers        (measured: a payload the host refuses is not a carrier)
    >= qualifying_carriers          (measured after reveal, against the frozen rule)
```

The two measured steps are declared as measured rather than assumed to be identities, and the second
carries a minimum that can fail. `validate_analysis_plan` refuses a plan that omits the derivation,
declares the wrong one, or sets a minimum that could never fail or never pass.

## The plan can fail, and by how much

| | |
|---|---|
| requested carriers | **24** |
| qualification rate measured over 1 200 devkit carriers | **0.230** |
| expected qualifying | **5.5** |
| minimum qualifying | **3** |
| chance the minimum is missed at that rate | **≈ 6 per cent** |
| verdict if the bank yields fewer | **negative** |
| retries | **forbidden** |

The devkit rate exists only to show that a plausible emitter can both meet and miss the minimum. It
is **not a prediction about the model**: M112 measured a six per cent ambiguous rate over its own
worlds and its blind bank returned twenty-five per cent. A pseudo-random emitter's distribution is a
third distribution again.

## The question underneath, and it may already be answered

The user-facing question is whether the acquired machinery transfers. The question underneath is
which space runs out first, and the devkit survey has produced a pre-freeze finding worth stating
before any bank exists.

The inherited vocabulary is M109's three features. M111's own pooled record classifies the rows it
saw:

| row | M111's inherited record | what the devkit carrier family shows |
|---|---|---|
| 1 | `operator_table`, determined | `operator_table` — agrees |
| 3 | undetermined | `{candidate_space, signal_interface}` — agrees |
| 5 | `operator_table`, determined | `operator_table` — agrees |
| **7** | **`signal_interface`, determined** | **`{candidate_space, signal_interface}` — ambiguous** |
| 2, 6 | not seen | `{candidate_space, signal_interface}` — ambiguous |

On carriers drawn from this meta-schema, **four of the six occupied rows carry more than one limiting
component**, and one of them is a row M111 recorded as determined. If that survives on the blind
bank, then no function of the inherited three-feature vocabulary is right on all carriers, and the
next ceiling is the **feature vocabulary** rather than the carrier. The acquired policy fires on rows
2 and 3; it does not fire on 6 or 7. So the descendant is expected to commit confidently on a row
where its own record is wrong — the M110 row-5 harm, one carrier further out.

That is a prediction, it is recorded before the freeze, and it can be wrong.

## Three outcomes, because two are not enough

A learner returns `constructed`, `refused` or `undetermined`, and the third is not a failure mode
bolted on afterwards. A system that cannot say *I did not determine this* has only two ways to be
wrong about a body it has not understood, and both of them look like confidence. M110 measured what
that costs.

`undetermined` is recorded with its cause, and the two causes mean different things:

- `exploration_did_not_close_within_budget` — a fact about this run's resources;
- `diagnostic_vocabulary_does_not_determine_this_carrier` — a fact about the lineage's own
  vocabulary, and the one M110 showed the price of not having.

Scoring is from carrier state, never from the learner's report: a claimed sequence is replayed by the
evaluator and scored where it actually lands. Five named outcomes and no sixth — correct
construction, unmet construction, calibrated refusal, false refusal, invented adapter.

## G1, and what would and would not advance

`MIRA_GENERALITY_CRITERIA.md` requires, for G1, that the agent enter bodies whose interaction
language was not encoded as a descriptor product **in the discoverer**, that implementations be
frozen before the learner and selected after freeze, that source be unavailable during evaluation,
and that at least one incompatible body produce a calibrated refusal rather than an invented adapter.

What this milestone supplies against each clause:

- **not a descriptor product in the discoverer** — the learner holds no action name, no arity, no
  error and no wire token. It reads them at runtime from a self-description it did not author.
  `scripts/audit_m113_boundaries.py` refuses a learner source that names a carrier-internal key or
  calls a host function that reads carrier structure.
- **frozen before the learner, selected after freeze** — the bank is sealed and committed to by
  digest before the tested system is frozen, and revealed after.
- **source unavailable during evaluation** — the carrier lives in a closure inside the channel, and
  the learner's source is parsed and refused if it names a carrier-internal key or calls a host
  function that reads carrier structure. The limit is stated plainly: a Python closure is
  introspectable, so this is an audited boundary and not a sandbox. The claim is that the learner
  does not read the carrier and that this is checked mechanically — not that reading it would be
  impossible.
- **incompatible body ⇒ calibrated refusal** — the unreachable twin, proved unreachable by
  exhaustion. On the devkit population the fresh lineage **invented an adapter on 15 of 66** such
  demands, so this clause can genuinely fail.

What it does **not** supply, and the gate therefore does not advance: the meta-schema, the four
surfaces, the host and the reception contract are this project's, and so are the component registry,
the feature vocabulary and the probe primitive. The interaction *language* of each body is blind; the
*space those languages are drawn from* is not.

## Arms and ablations

Every arm receives a byte-identical channel, budget, demand, entry configuration and evaluator.
`adapter_projection` equality across arms is measured, not promised. The only thing that differs is
the Genesis state.

| arm | what it holds |
|---|---|
| `T0` | fresh base lineage, no acquired rule, no policy |
| `M1` | generation one only |
| `M2` | generations one and two |
| `M3` | full descendant: cascade plus the M111 diagnostic policy and its pooled record |
| `rollback` | exact rollback to the pre-acquisition state; must equal `T0` byte for byte |
| `ablated` | the relevant generation removed, the others retained |
| `mutated` | one acquired truth-table entry flipped |
| `corrupt` | a malformed acquired rule; must fail closed rather than degrade |
| `unregistered` | the rule built but not registered in the state |
| `budget_plus` | fresh lineage at four times the observation budget |

Two further arms are declared and are **not run by `scripts/run_m113_qualification.py`**, which
records their absence in its own output rather than leaving the reader to notice:

| arm | why it is outstanding |
|---|---|
| `producer_dead` | needs an isolated consumer process, as M099 and M110 built for their own runs |
| `preservation` | re-runs the M110 and M111 populations unchanged, to show nothing was lost |

Neither may be reported as passing until it exists. A milestone that lists twelve arms and runs nine
has nine arms.

## The adversarial pass, before anything was frozen

M095 recorded thirty-one defects across seven pre-freeze passes and repaired thirty. The same
discipline was applied here, and six defects were found in the apparatus by measuring it rather than
by reading it. All six are repaired, and each has a regression test, because a defect found once and
not pinned is a defect that returns.

| defect | what it cost, measured | repair |
|---|---|---|
| `g0` was a width comparison | every row on which it was true mapped to the observation interface **by definition**; the attribution question answered itself | `g0` is now observed nondeterminism under the learner's own projection — something it watched happen |
| `g0` implied `g1` | reading the *trusted* verdict for `g1` coupled the two, four of eight rows became unreachable, and the reachable arm landed **0 of 21** times on a row where the inherited cascades disagree | `g1` reads `projection_found` — a search fact, not a trust fact |
| the demand rule took the first determined pair | the census iterates the smallest entry and least target first, so the rule systematically posed the trivial corner | one pair per attribution row, canonical least for each — M110's own selection, restated in the carrier's terms |
| a bounded composition space never "closed" | every bounded attempt returned `undetermined` with a budget reason while only **2 of 88** attempts had reached the ceiling | `complete_for_the_bound` and `closed_by_fixed_point` are separate facts; either justifies a refusal, neither is budget exhaustion |
| a distinguishing shortfall read as "no collision" | a budget that could not afford the comparison was reported as evidence that the projection *is* a state | `_distinguish` returns whether it completed; an unfinished exploration is `undetermined` |
| the runner's own booleans were the checker's evidence | `one_adapter_across_every_arm`, `rollback_equals_the_fresh_lineage` and the cardinality verdicts were assertions wearing a measurement's clothes — the M095 defect exactly | the runner records per-pair adapter digests and raw counts; the checker recomputes and can disagree |

A seventh was found in the checker itself: `P11` compared two sorted lists with `>=` instead of
testing a subset, so it failed for a reason unrelated to what it names the moment an unrelated key
was added to the record. A predicate that can fail for the wrong reason is worse than no predicate,
because it is read as evidence.

## What the development run already shows, and what it cannot

`scripts/run_m113_qualification.py --development` runs the whole chain against a devkit bank. Eighty
carriers, twenty qualifying, forty-four demand pairs, every arm on both twins:

| arm | correct | unmet | false refusal | calibrated refusal | invented adapter | undetermined | attribution |
|---|---|---|---|---|---|---|---|
| `T0` | 13 | 8 | 22 | **29** | **13** | 3 | 10/30 |
| `M1` | 12 | 8 | 23 | 29 | 13 | 3 | 9/30 |
| `M2` | 14 | 8 | 20 | 28 | 13 | 5 | 12/30 |
| **`M3`** | **23** | 8 | 6 | **6** | **15** | 30 | **21/30** |
| `budget_plus` | 13 | 8 | 22 | 30 | 13 | 2 | 11/31 |

The full descendant is **much better at construction and attribution and much worse at refusal**. It
constructs 23 against the fresh control's 13 and attributes correctly 21 times against 10 — and its
calibrated refusals collapse from 29 to 6 while its invented adapters rise from 13 to 15. That is
the M110 shape at a new level: capacity rises on one axis while realized competence falls on another,
and averaging the two would hide exactly the thing worth reporting.

The frozen verdict rule therefore requires **strictly better on one measure and no worse on the
others**, and `M3` fails it. The development check returns **17 of 18, P18 false**.

`budget_plus` earns its place here: at four times the budget the fresh control still constructs 13,
so the fresh arm's ceiling is a machinery fact rather than a cost fact. M084 recorded that this is
the distinction an episode count cannot make.

**None of this is a prediction about the blind bank.** It is a pseudo-random emitter's distribution,
measured on development data, recorded before the freeze so that it cannot be produced afterwards as
though it had been. What it does establish is that the instrument discriminates, that every outcome
class is populated, and that the verdict rule can fail — which is the only thing a pre-registration
can honestly claim about a bank that does not exist.

## Track A now, Track B prepared

This milestone is Track A: the learner is deterministic and makes zero model calls and zero network
calls, so the causal attribution is clean. The architecture is written so a Track B arm can be added
without changing the contract — the learner is reached only through the channel, so a model-driven
learner would be a different implementation of the same interface. When a general model is involved,
the control is `same model + no Genesis` against `same model + Genesis`, identical in version,
prompt, tools, environment and budget. **Never** "Claude succeeded, therefore Genesis succeeded."

## Claim boundary

A positive result may be described as **procedurally blind carrier adaptation**, or a more exact
formulation the result itself determines. It may **not** be described as an independently authored
human carrier, external reproduction, G1 or G4 closure, general-agent evidence, AGI or an AGI
candidate.

The evidence tier is `blind_generated_sealed_bank`. Generator context blindness is provable;
training-data independence is not provable, because an antecedence argument about one corpus is not
a proof of ignorance; **human independence is not obtained at all**, because no person outside the
project authors or holds anything. `human_maintained_sealed_bank` remains an external blocker that
nothing in this repository can lift.

## Attempt discipline, and what is still owed

One canonical attempt and one canonical checker replay, once a bank exists. The first result is
preserved even if negative and may not be repaired, relabelled or rerun. M109, M110, M111 and M112
are frozen and are not touched.

The ordered chain is M112's, unchanged:

```text
plan frozen -> generator spec and prompt frozen -> generate once, outside, blind
  -> seal -> public commitment by digest -> tested system frozen
  -> signed reveal -> one run -> preserve
```

**Owner-only gates, none of which this session may pass.** Freezing the plan and the generator
identity, and running the single qualifying invocation, are irreversible acts that the project's
discipline reserves for a signed decision. They are listed here as unchecked:

- [ ] the analysis plan is frozen to `ANALYSIS_PLAN.json` and its commitment published;
- [ ] a generator identity is chosen and pinned by image digest, model blob digest and runtime
      version, before any invocation;
- [ ] the single qualifying invocation is run in the isolated container and attested;
- [ ] the bank is sealed and the public commitment published;
- [ ] the tested system is frozen with the bank unread;
- [ ] the reveal is authorized.

**One environment blocker is outstanding and is not a scientific one.** The Docker daemon is not
running on this machine, so the isolated invocation cannot be planned or attested from here. It is
recorded as a blocker rather than worked around: a materialization outside the attested container is
not a materialization under this contract.

**One choice is deliberately left open.** M112's generator was `qwen2.5:1.5b`. Emitting a carrier is
a materially harder structured-generation task than emitting five integers, and a model that small
may return a bank the host refuses in bulk. Under this contract that is a **result** — a
materialization that emits mostly malformed bodies is a fact about the generator, recorded and not
repaired. Whether to accept that risk or pin a larger model is an owner decision, and it must be made
**before** the invocation, never after seeing one.
