# M084 status

**POSITIVE QUALIFIED DEVELOPMENT RESULT — TRACK A, MODEL-FREE, THREE REAL SUBSTRATES.**

**NO GATE ADVANCES. THIS IS AN INTEGRATION RESULT, NOT A CAPABILITY RESULT.**

- Target: whether the mechanisms qualified separately in M076–M083 can be the faculties of one
  persistent lineage, or whether their success depends on the isolation of their harnesses.
- Sequence: `shell → browser → desktop → shell`, four stages, three real containers, four separate
  operating system processes.
- `lineage`: **11/11** reachable goals reached from environment state, **5/5** unreachable refused,
  **0** false refusals, **0** unreachable goals recorded as reached.
- Returning stage: **0** diagnostic probes, **0** repair cycles, **0** affordance probes.
- `acquisition_ablated` — the same lineage minus what it learned: **1/1/1** in that stage, cost
  **85** against **46** over stages 1–3, and the same transformation re-adopted four times.
- `fresh_each_stage`: behaviourally identical to the ablated arm, four of five continuity proofs
  failed.
- Forced fault after stage 1 detected **by the stage-2 child** and restored to `81d9d437…`, the
  digest stage 1 recorded before the corruption existed.
- Bank commitment `a4081e5b…7f047`; first result `1cbeef8a…f830b`, attempt 1, no retry.
- Local suite: **1,623 passed, 10 skipped** in 2,309.73 s; 40 M084 regressions with
  `MIRA_RUN_DOCKER_TESTS=1`. Checker: `failures: []`. Integrity: clean.
- First CI run `31518942992`, attempt 1, no rerun: **1,624 passed, 9 skipped** on Python 3.11
  in 1,241.63 s and on Python 3.13 in 1,281.45 s, plus repository integrity. Attribution run
  `31518942706` passed.
- Gate advance: **none.** G2, G3, G5 and G6 all stay where M076–M083 left them.

## Frozen ordering

1. `ecb297c` froze `PROTOCOL.json` and `PROTOCOL.md` before any harness code existed.
2. `f19af86` added the harness and recorded amendments A1–A3 from the pre-materialization rehearsals.
3. `baba1f2` bound the bank and preserved the result in one pass, attempt 1, no retry.

## The finding that motivated the experiment

The agent M081, M082 and M083 carry across four real substrates is nine lines long and replays an
action list computed by the bank generator. It perceives nothing, plans nothing and detects no
failure. Those three experiments are **interface** results, and nothing in the registers said so.
M084 therefore does not import that agent — citing it would claim a reuse this experiment does not
have — and the protocol records the omission as deliberate.

Everything else is imported: M077's journal, M080's bounded table, M079's plan enumeration (extracted
into `bounded_search` so both use one copy), and the three environments unchanged.

## What persistence actually bought

Not correctness. Every arm reached every reachable goal and refused every unreachable one. What the
complete lineage bought was **cost and earliness**: 27 actions and 48 reads against 43 and 71, one
wasted action on an impossible goal instead of four, and a returning stage that needed no diagnosis
at all. Reporting this as a capability difference would be an overclaim.

## The rehearsal that produced amendment A1

The pipeline was rehearsed twice on throwaway salts, with no bank bound and no result preserved. The
first rehearsal produced a **false refusal** in the browser and desktop stages: the carrier-rejection
predicate generalized from one-sided evidence, and with no durable carrier yet observed the shortest
separating prefix collapsed from `sea` to `s`, which rejects the organism's own alternatives.

It was invisible in stage 0 only because the organism still verified at the end of the stage there,
so an affordance probe had already supplied durable evidence before it diagnosed anything. From stage
1 onward it verifies per goal and the diagnosis arrives first.

The clause that caught it is P2, which exists for exactly this. A1 and A2 were applied before any
artifact was materialized and no threshold, salt or goal grammar changed.

## What is deliberately absent

No cross-domain transfer: a fact learned in the shell is never offered to the browser, even though
both discard the same authored prefix. No desktop VM. No external suite. No private tasks. No model.
Eleven reachable goals over four stages is a small bank, and the goals, carriers, applications and
substrates are all project-authored.

The desktop's induced predicate is weaker than the other two: only one non-durable carrier is
observable there, so `r3` over-generalizes to cells no goal uses. Recorded rather than smoothed over.

## A limit on the evidence

Container-backed regressions skip in CI under the existing opt-in, so CI attests the structural half
only — the imports, the parent-never-executes-a-stage check, the induction, the restoration and the
recomputed threshold. The live half is reproducible locally with Docker running and the M082 and M083
images built. The checker's full live re-derivation is a second complete run across three substrates
and is opt-in behind `MIRA_M084_LIVE_CHECK=1`.

## What a successor would need

G4 — cross-domain transfer — with tasks maintained outside this project, and eventually independent
reproduction. M075's fail-closed pre-private boundary is the route and must not be bypassed. Adding a
fifth substrate under the same organism would repeat this instrument.
