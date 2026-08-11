# M084 integrated persistent embodiment

**FROZEN BEFORE IMPLEMENTING THE HARNESS, THE ORGANISM OR THE GOAL BANK.**

## The question M076–M083 left open

M076 grounded three channels. M078 refused an under-determined body. M079 planned without a supplied
decomposition. M080 acquired six skills without losing an earlier one. M081, M082 and M083 put one
action vocabulary into four real isolated environments and scored it from environment state.

Every one of those results lives in its own harness. The register has never asked whether they can be
**faculties of one persistent lineage** rather than seven separate demonstrations.

There is a specific reason to doubt it. The agent that M081, M082 and M083 carry across four real
substrates is this:

```python
class Agent:
    def perform(self, task, environment):
        claimed = True
        for action in task.actions:
            claimed = environment.apply(action) and claimed
        return claimed
```

It replays an action list computed by the bank generator. It perceives nothing, plans nothing and
detects no failure. Those three experiments are **interface** results, and the fact that they are is
not visible from the registers. The mechanisms that perceive, plan, learn and refuse have never met a
real substrate; the real substrates have never met an agent.

**H30:** the mechanisms qualified separately in M076–M083 can become the faculties of one persistent
lineage that crosses several real environments while keeping one identity, one causal journal, one
bounded memory and the knowledge it acquired on the way.

## What crosses the environments

One **organism**, serialized to a file between stages, carrying:

| Component | Origin |
|---|---|
| lineage identity, body version, provenance | new to M084 |
| hash-chained causal journal | `Journal`, `GENESIS_DIGEST` imported from M077 |
| bounded shared memory of acquired facts | `Table`, `ExceptionEntry` imported from M080 |
| plan enumeration and replanning on a revealed obstacle | uniform-cost search extracted from M079 |
| the four real environments | `ShellEnvironment` (M081), `BrowserEnvironment` (M082), `DesktopEnvironment` (M083) |

M081's `Agent` is **deliberately not imported**. Importing it would be an empty citation: it cannot
perceive, so it cannot be the subject of this experiment. That replacement is a recorded finding about
M081–M083, not an oversight.

## The stage sequence

`shell → browser → desktop → shell`

Four stages over three substrates, ending where it began. The return to the shell is the point: the
knowledge acquired in stage 0 must still be causally useful in stage 3 after crossing two materially
different substrates and three serialization boundaries.

Each stage opens a **fresh container**. Nothing about the previous container survives except what the
organism carries in its own bytes.

## The harness must not be the state holder

M082 nearly recorded a result where a fresh browser profile per action would have left the harness
holding the state while every test stayed green. That failure mode is structural, so the defence is
structural:

1. every stage runs in a **separate operating-system process**, invoked with a file path;
2. the child loads the organism from that file, acts, and writes the organism back;
3. the parent reads only a metrics report and never calls a perception, planning or action function;
4. the organism records **inside itself** the SHA-256 of the file it loaded, so the chain of
   serializations is carried by the organism rather than asserted by the harness.

A checker and a regression fail the result if the parent executes a stage in-process.

## What the organism does per goal

A goal is a set of **desired carrier states**, with no decomposition supplied. Carriers have declared
costs. The organism:

1. observes the goal's carriers from the environment;
2. discovers, by effect rather than by return value, which affordances actually work in this substrate;
3. enumerates satisfying plans by uniform-cost search over the discovered affordances, excluding
   carriers already known to be non-durable — the same role that `known_blocks` plays in M079;
4. executes the cheapest plan, cheapest carrier first;
5. verifies from environment state;
6. on a shortfall, retries the failing carrier once and re-reads — the **diagnostic probe** that
   separates a transient write failure from a carrier that permanently discards;
7. records the carrier as non-durable and replans through an alternative — a **repair cycle**;
8. **refuses** when no plan over the remaining carriers satisfies the goal, rather than claiming it.

## What is acquired, and where it must pay

Two kinds of acquisition, with two distinct predicted effects.

**T1, a transformation of the body.** The organism begins with `verification: end_of_stage`, which is
the M081 stance: trust what the action returned and audit once at the end. The first audit-revealed
divergence causes it to propose `verification: per_goal`, validate the proposal on a **disposable
descendant** run against a separate probe goal in the same environment, and adopt it with a version
increment, a journal entry naming the causing evidence, and a checkpoint. Rejected proposals are
journaled and change no version.

Predicted effect: end-of-stage verification must re-observe and re-plan every unsatisfied goal in a
repair pass; per-goal verification repairs inside the goal that failed. The cost difference appears in
**environment actions and state reads in stages 1, 2 and 3**.

**F\*, facts.** Carrier non-durability and affordance effectiveness are stored per **substrate class**
in the bounded table. Predicted effect: in stage 3, which returns to the shell substrate of stage 0,
the lineage performs **zero** diagnostic probes, **zero** repair cycles and **zero** affordance probes,
because it already knows both.

Facts are keyed by substrate. A fact learned in the shell is **not** offered to the browser, even
though both discard the same authored prefix. Carrying it would be the relabelling this repository
forbids; the register must not read this as cross-domain transfer.

## Arms

| Arm | What it removes | Predicted loss |
|---|---|---|
| `lineage` | nothing | — |
| `acquisition_ablated` | facts and adopted policy cleared at every stage boundary; identity, version and journal preserved | must re-derive everything in every stage |
| `fresh_each_stage` | a new genesis organism at every stage | the same behavioural loss, plus every continuity proof fails |
| `self_report_scored` | derived view, not a re-execution | over-reports where the substrate accepts and discards |

`acquisition_ablated` is the falsifier that matters: it is the **same lineage** minus what it learned.
If the complete lineage does not beat it, persistence bought nothing and M084 is negative.

`fresh_each_stage` exists to show that the continuity proofs are not vacuous. It is re-executed rather
than derived because its behaviour must be **identical** to `acquisition_ablated`; if the two differ,
the ablation is leaking and the result is negative.

`self_report_scored` is a scoring view of the `lineage` arm's own records and is not a separate
execution, because re-running would resample a live environment for no scientific gain. It scores each
goal by whether every action of the **first** executed plan reported success, ignoring state.

## The forced fault

After stage 1 the parent corrupts the serialized organism outside its checkpoint blob. The **stage-2
child** must detect the broken journal chain and restore from the last checkpoint, and the restored
live digest must equal the pre-corruption digest recorded independently in the stage-1 report. The
comparison is never against the checkpoint's own digest: that is the tautology M080 recorded.

## Positive threshold

All of the following, on the first materialized bank, with no retry:

- **P1** `lineage` reaches **11/11** reachable goals, scored from environment state.
- **P2** `lineage` refuses **5/5** unreachable goals, with **0** false refusals and **0** unreachable
  goals recorded as reached.
- **P3** `lineage` stage 3: diagnostic probes **0**, repair cycles **0**, affordance probes **0**.
- **P4** `acquisition_ablated` stage 3: diagnostic probes **≥ 1**, repair cycles **≥ 1**, affordance
  probes **≥ 1**.
- **P5** `lineage` actions plus state reads over stages 1–3 strictly fewer than `acquisition_ablated`.
- **P6** `lineage` adopts **≥ 1** transformation, ends at body version **≥ 1**, its journal verifies
  from the genesis anchor to the head and grows strictly at every stage, a checkpoint exists at every
  stage boundary, and the serialization chain is unbroken.
- **P7** the forced fault is detected by the stage-2 child and the restored digest equals the recorded
  pre-corruption digest.
- **P8** `fresh_each_stage` fails at least three continuity proofs.
- **P9** `acquisition_ablated` and `fresh_each_stage` agree on every behavioural metric per stage.
- **P10** `self_report_scored` over-reports **≥ 1** in each of stages 0, 1 and 2.
- **P11** no stage was executed in the parent process.

## Failure classification

**Negative** — any of P1–P11 false, or a stage exceeding its 60-action safety bound.

**Inconclusive** — Docker, the browser image or the desktop image unavailable, or an environment that
never starts. Not runnable is not negative.

## If it is negative, where is the rupture?

Named in advance so that a negative is informative rather than merely disappointing:

1. **serialization** — an acquisition does not survive the file boundary;
2. **carrier space** — screen coordinates and resource names do not fit one abstract space;
3. **affordance discovery** — removal really is absent on the desktop and the organism cannot find out
   by effect;
4. **capacity** — the 24-slot shared table saturates across four stages;
5. **refusal calibration** — refusal generalizes to a reachable goal in a real substrate;
6. **state ownership** — the harness turns out to hold what the organism was supposed to carry;
7. **substrate regression** — a transformation adopted in one substrate is harmful in another.

## Claim boundary

A positive result establishes **one persistent lineage integrating previously separate mechanisms
across three real substrates and four stages**, with verifiable descent.

It does **not** establish AGI, general autonomy, open-ended evolution, cross-domain transfer, a closed
G4, a closed G6, a closed G7, general desktop competence, structural retention without replay, or any
behaviour on privately maintained external tasks. The goals, carriers, applications and substrates are
all project-authored. M080's retention remains replay-dependent and nothing here changes that. The
M075 pre-private boundary is untouched.

No external model is called. No network is opened. No repository, credential, deployment or permission
authority is granted to the organism.

## Amendments, recorded before materialization

The complete pipeline was rehearsed once on a throwaway salt, with no bank bound and no result
preserved, so that the recorded run could be attempt 1 with no retry. It found two defects and one
harness bug, all corrected here **before** any artifact existed. No threshold, salt or goal grammar
changed.

**A1 — the induction was unsound on one-sided evidence.** The shortest separating prefix is only
defined against durable carriers. With none observed yet, it collapsed to a single character and
rejected the organism's own alternatives: the lineage **falsely refused a reachable goal** in the
browser and desktop stages. That is a false refusal manufactured by the induction rather than by the
substrate, and it is precisely what P2 exists to catch. The rule now names the observed non-durable
carriers exactly until there is something to separate them from.

The order of events is what made it visible only there. In stage 0 the organism still verifies at the
end of the stage, so the affordance probe has already supplied a durable observation by the time it
diagnoses. From stage 1 onward it verifies per goal, and the diagnosis arrives first.

**A2 — a verified carrier is evidence.** The organism read the goal value back from the environment
and discarded the observation. Recording it is what makes the induction two-sided, and not recording
it is what made A1 necessary.

**A3 — a harness bug.** The rehearsal path skipped the bank-sealing step and then read a digest it
had never computed.

## Additive changes to qualified modules

Recorded here because they are made **before** the harness and must not be discovered later:

1. `metamorphosis/bounded_search.py` extracts M079's uniform-cost plan enumeration verbatim;
   `satisfying_plans` becomes a thin wrapper over it. Behaviour-preserving; M079's checker re-derives
   its arms live and must still reproduce its preserved result.
2. `DesktopEnvironment.colour_at(label)` is added to M083 as a targeted single-carrier read. Reading
   the whole grid costs 8.9 s against 0.3 s for one cell, and this experiment observes far more often
   than M083 did. Additive only; `state()` is unchanged.
