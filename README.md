# Mira Genesis — Adaptive Embodiment

Mira Genesis is a public, auditable research program on **adaptive software lineages**: systems that
can diagnose limitations in their own executable body, construct and validate changes, adopt them
transactionally, preserve useful state across substrate changes, and continue adapting under strict
measurement boundaries.

The project is deliberately narrower than the phrase “self-improving AI” usually suggests. It does
not treat a model rewriting source code as proof that a lineage owns the improvement process. The
research question is instead whether progressively more of the machinery for diagnosis,
transformation, validation, adoption and later improvement can become **lineage-owned, causal and
replayable**.

> **Current frontier:** M094 is a positive qualified real-software result. M095 is an active,
> heavily audited development mechanism asking whether one adopted improvement can change what later
> improvements are reachable. M095 is **not frozen, not qualified and has no scientific verdict**.

For the detailed current snapshot, see
[`docs/CURRENT_RESEARCH_FRONTIER.md`](docs/CURRENT_RESEARCH_FRONTIER.md).

## What the project is trying to establish

The long-term research target is not “make the benchmark number go up”. It is a causal chain in
which improvements become part of the machinery that makes later improvements possible:

```text
S0
  -> acquire A
S1 has new reach
  -> acquire B using that reach
S2 has new transformation capability
  -> acquire C
...
```

A stronger successor would show that earlier acquisitions improve the **ability to discover later
acquisitions** — for example by exposing missing prerequisites, reducing search cost, improving
selection or extending the transformation language itself.

The current staged objective is:

1. **real self-repair** — diagnose and repair a real repository component without being handed the
   target or finished patch;
2. **improvement enabling improvement** — show that adopting A causally changes whether B is
   reachable;
3. **endogenous language extension in the real-software line** — show that a needed transformation
   lies outside the inherited operation language and that the lineage acquires an extension rather
   than receiving it;
4. **hard persistence** — kill the process and prove the acquired transformation capability returns
   from lineage-owned persisted state;
5. **repeated cumulative cycles** — repeat the causal chain across fresh tasks and eventually across
   materially different domains.

M091 already demonstrated endogenous extension of a state-owned transformation language in a bounded
abstract setting. The next frontier is not to relabel M091, but to bring that kind of ownership into
the current cumulative **real-software** line.

## Where the project stands now

| Milestone | Status | Current reading |
|---|---|---|
| M042 | **Positive canonical** | First bounded Genesis completion in deterministic finite DFAs; all ten frozen completion gates passed together. |
| M066 | **Positive canonical** | The same bounded gate structure was confirmed on a CPython → Node ESM → whole-WebAssembly lineage. |
| M091 | **Positive scientific result** | A state-owned transformation language was extended endogenously beyond the inherited language's constructive image. |
| M092 | **Aborted without verdict** | Canonical exhaustive search was stopped voluntarily before terminal candidate, reproduction or qualification. |
| M093 | **Engineering rehearsal** | Real repository transformation, sandbox validation, adoption, persistence and rollback worked, but the target, diagnosis and patch were substantially authored. |
| M094 | **Positive qualified scientific result** | The lineage measured the limiting real component, selected the tied top targets and assembled an executable repair from composable operations; 12/12 conditions passed. |
| M095 | **Development mechanism under adversarial audit** | One adopted repair changes later reach, and a failed search can descend to an enabling prerequisite. No protocol, qualification pool, armed run or verdict exists yet. |

`main` currently contains the M094 qualified result. The active M095 development work is being
reviewed separately and must not be described as a scientific result until its own protocol and
qualification boundary exist.

## M094 — current qualified anchor

M094 is the strongest qualified result on the active real-software line.

Its preserved second attempt produced a **positive** verdict with **12/12 protocol conditions
computed and true**. The mechanism used **zero model calls and zero network calls**. Diagnosis
selected `mira_core/contracts.py` by measurement and repaired both classes tied at the highest
demand, `Goal` and `Observation`.

Qualification was drawn after adoption from the adopted mechanism digest and passed **2/2
cross-component requirements**:

- `AgentResult`, including a computed `@property` alongside declared fields;
- `ContainerSpec`, including a key mapped to a differently named field.

Random-selection and template-only controls closed nothing. More budget over the same operation set
recovered the same mechanism.

M094 also preserves a withdrawn first positive-looking attempt. A post-verdict audit discovered that
rollback had been tested over decoded text and missed CRLF → LF byte normalization. The attempt was
withdrawn instead of retroactively repaired into a success, the storage mechanism was corrected to
adopt and restore bytes, and the second attempt reused the same mechanism and qualification draw.

See `experiments/M094/` and PR #177 for the full evidence.

## M095 — why the current work matters

M095 does not ask whether the lineage can perform two repairs in sequence. It asks whether the first
repair changes the **constructive reach** of the second.

In the development world, the outer repair requires a renderer on an inner value object. At S0 that
renderer does not exist, so the outer repair cannot be built. The lineage repairs the inner object;
after adoption, the **same operation set** can construct the outer repair.

The active audit then found a more interesting selection problem: when the needed enabler was ranked
below the blocked target, a greedy strategy stalled. The failed search already named the operation it
could not apply, and that operation identified the missing supplier. The lineage can now use that
failure as evidence, descend to the lower-ranked enabler, repair it, and retry the blocked target.

That development relation now holds across all six tested demand-bearing arrangements, including
cases where the enabler is initially outranked. Two deliberately negative arrangements remain where
no inner demand exists and therefore no visible enabler exists to descend to.

This is promising **development evidence only**. The current M095 line has recorded 19 defects across
five adversarial audit passes, with 18 repaired at the latest snapshot. Several controls that looked
positive were shown not to test what their names implied. No M095 hypothesis is frozen, no protocol
exists, no qualification pool exists, no run is armed and no verdict exists.

See [`docs/CURRENT_RESEARCH_FRONTIER.md`](docs/CURRENT_RESEARCH_FRONTIER.md) and
`experiments/M095/` for the current boundary.

## What has already been completed — and what “complete” means

The project has a frozen **bounded Genesis completion definition** in
[`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md).

M042 was the first continuous lineage to satisfy all ten gates together in the deterministic
binary-DFA laboratory. M066 later supplied a separate bounded real-substrate confirmation.

Those results are complete **inside their declared task, substrate and budget families**. They do
not imply unrestricted self-modification, general intelligence or open-ended evolution.

The active M094 → M095 → M096 → M097 line deliberately asks a stronger question: how much of the
improvement process can become endogenous in a continuing real-software lineage, and whether one
acquisition can become a real prerequisite or tool for the next.

## What Mira Genesis does not currently claim

Mira Genesis does **not** currently establish:

- AGI;
- consciousness or sentience;
- unrestricted or open-ended recursive self-improvement;
- arbitrary self-modification;
- superiority to frontier language models;
- autonomous authority over production systems, credentials, networks or deployment;
- that competence supplied by an external model belongs to the endogenous lineage.

Generality language is governed separately by
[`MIRA_GENERALITY_CRITERIA.md`](MIRA_GENERALITY_CRITERIA.md). A bounded mechanism or benchmark score
cannot be promoted into an AGI claim by wording alone.

## Two epistemic tracks

The repository separates two kinds of evidence:

**Endogenous lineage track**

Studies capabilities that belong to lineage state, transformation machinery and executable body.
This is the track relevant to M091 and the current M094/M095 frontier.

**Model-mediated governed-agent track**

Allows a named external model to propose actions while Mira supplies authority control, isolation,
budgets, audit and evaluator-owned success. External-model competence remains attributed to the
composed system, not silently reassigned to Mira.

See [`docs/EPISTEMIC_TRACKS.md`](docs/EPISTEMIC_TRACKS.md).

## Scientific discipline

The repository is intentionally designed so that a failed experiment can remain useful evidence.
Its operating rules include:

- freeze protocols, thresholds and decision rules before the evidence they decide exists;
- keep hidden qualification material outside the mechanism being evaluated;
- execute candidates rather than infer success from structure where behaviour matters;
- preserve negative, withdrawn and disqualified results instead of replacing them;
- distinguish development demonstrations from qualified scientific results;
- use causal controls and ablations that can genuinely come out the other way;
- replay from preserved artifacts and keep provenance resolvable;
- keep release authority outside the self-modifying lineage.

The failure history is not cleanup debt; it is part of the research record. See
[`FAILURE_LOG.md`](FAILURE_LOG.md).

## Safety and authority boundary

Even a scientifically autonomous lineage remains inside an externally controlled release boundary.
Candidate code runs in disposable environments with explicit limits. Scientific autonomy inside a
sandbox does not grant permission to modify production systems, credentials, external networks or
deployment infrastructure.

The long-term research goal does not require making Genesis impossible for humans to stop, inspect or
contain.

## Quick navigation

| If you want to know... | Read... |
|---|---|
| Where the active research stands today | [`docs/CURRENT_RESEARCH_FRONTIER.md`](docs/CURRENT_RESEARCH_FRONTIER.md) |
| The long-form authoritative project record | [`PROJECT_STATE.md`](PROJECT_STATE.md) and [`PROJECT_STATE.yaml`](PROJECT_STATE.yaml) |
| The historical construction path | [`ROADMAP.md`](ROADMAP.md) |
| The bounded Genesis finish line | [`GENESIS_COMPLETION_CRITERIA.md`](GENESIS_COMPLETION_CRITERIA.md) |
| What would justify stronger generality language | [`MIRA_GENERALITY_CRITERIA.md`](MIRA_GENERALITY_CRITERIA.md) |
| The endogenous/model-mediated attribution boundary | [`docs/EPISTEMIC_TRACKS.md`](docs/EPISTEMIC_TRACKS.md) |
| Preserved failures and disqualifications | [`FAILURE_LOG.md`](FAILURE_LOG.md) |
| Scientific hypotheses | [`SCIENTIFIC_HYPOTHESES.md`](SCIENTIFIC_HYPOTHESES.md) |
| Project decisions | [`DECISIONS.md`](DECISIONS.md) |
| Current qualified real-software experiment | [`experiments/M094/`](experiments/M094/) |
| Active improvement-enabling-improvement work | [`experiments/M095/`](experiments/M095/) |

## Reproducing the repository checks

The normal development verification path is:

```bash
python -m pip install -e ".[dev]"
pytest -q
python scripts/check_repository_integrity.py
```

Individual frozen experiments may require additional commands, runtimes, artifacts or checkers.
Follow the experiment-local protocol rather than treating the generic test suite as a scientific
verdict.

## Licensing and contributions

Project-controlled software intentionally published in this repository is available under
**AGPL-3.0-only** according to [`LICENSE_POLICY.md`](LICENSE_POLICY.md). Public AGPL use and separate
commercial permissions are compatible; see [`COMMERCIAL_LICENSING.md`](COMMERCIAL_LICENSING.md).

Externally authored copyrightable contributions are currently subject to the temporary rights
boundary in [`CONTRIBUTING.md`](CONTRIBUTING.md). Issues, reproducibility reports and technical
criticism remain welcome.

## Citation and provenance

Use [`CITATION.cff`](CITATION.cff) for citation metadata and [`PROVENANCE.md`](PROVENANCE.md) for the
repository's provenance policy.

Mira Genesis treats the ability to resolve the exact commits behind scientific claims as part of
reproducibility, not as optional repository hygiene.
