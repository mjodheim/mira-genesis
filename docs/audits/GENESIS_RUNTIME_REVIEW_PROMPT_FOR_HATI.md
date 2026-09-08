# Prompt issued to Hati for the Genesis runtime hostile review

Recorded so a later reader can see what framing produced the verdict. The text below is what was
handed to the reviewer, verbatim.

---

You are the independent hostile reviewer of the Genesis runtime in the `mira-genesis` repository.

Repository state under review:

- branch `claude/repos-status-presentation-c5ktjo`, pull request #275 (draft)
- the runtime is `genesis/` — 8 modules, ~3000 lines — plus `scripts/run_genesis_demonstration.py`
  and 193 tests in `tests/test_genesis_*.py`

**Record in your report header the exact commit you checked out.** This prompt deliberately does not
pin one: the branch was still moving when the prompt was written, so any SHA named here would be
stale on arrival, and the commit you actually read is better evidence than one chosen for you in
advance. If the head moved while you worked, say so and say which state your findings apply to.

**Your brief is `docs/audits/GENESIS_RUNTIME_HOSTILE_REVIEW_BRIEF.md`. Read it first, and read it as
a claim rather than as a description.** It was written by the agent that wrote the runtime, its
tests, its demonstration and its notes. There is no epistemic separation anywhere in that chain, and
closing that gap is the entire reason you are being asked.

## Read in this order

1. `docs/audits/GENESIS_RUNTIME_HOSTILE_REVIEW_BRIEF.md` — the request, the ten defects the author
   found in his own work, and the ten attack surfaces he considers most dangerous
2. `docs/METAMORPHOSIS_TARGET.md` — the objective and the stopping criterion
3. `experiments/GENESIS/DEMONSTRATION_DEFINITION.md` — the twelve properties a run must exhibit, and
   separately which of them are driven to their negative in the test suite
4. `experiments/GENESIS/DEMONSTRATION_RECORD.json` — what a run actually produced
5. `experiments/GENESIS/RUNTIME_NOTES.md` — the defects in full
6. `docs/GENESIS_PRIMITIVE_AUDIT.md` — how M107–M111 map onto the runtime's primitives
7. the code

**Read the definition before the record.** If a property is defined so that it cannot come out
false, that is a finding regardless of what the record says. M121 v2 in this same repository passed
76 tests while being unable to return a negative, and nobody noticed until someone went looking for
variance.

## What is claimed, and what is not

Claimed, and this is the whole of it: **that the runtime's mechanisms hold as properties of a running
program rather than as properties of how the author wrote the fixtures.**

Not claimed, and refuting these refutes nothing:

- no AGI claim and no generality claim
- no scientific result — the record carries `is_a_scientific_observation: false` and
  `advances_a_generality_gate: false`, and the bodies in `genesis/development_bodies.py` are fixtures
- no novelty — each mechanism generalises something M107–M111 did once

## Your task

1. **Verify the ten defects are actually fixed.** Do not take the brief's word for any of them. Each
   claims a test that fails when the mechanism is removed; check that claim on the ones that matter.
2. **Then go past them.** They share one shape — *a record testifying to a property the code does not
   have*. Your first job after verification is to decide whether that shape recurs somewhere still
   unfixed. The author's found-and-fixed defects are not evidence he found the others; they are
   evidence of what class of mistake he makes, which should tell you where to look.
3. **Work the ten attack surfaces** in the brief. The author ordered them by how dangerous he thinks
   they are; disagree with that ordering if you think it is wrong, and say so.

## Do not defer to the author

- Do not soften a finding because the code looks careful. It looked careful in the ten places it was
  already wrong, and it looked careful in M121 v2 while being unfalsifiable.
- Do not accept a documented limitation as a resolved one. Several things in the runtime are
  *recorded* as open — the host draws the component→operations partition, two definitions in the
  vocabulary path are conventions rather than measurements, the bodies are fixtures. Recording a
  problem is not fixing it, and if any of those is worse than the author admits, say so.
- `NO-GO` is an expected outcome, not a failure of the review.

## Required output shape

Following `docs/audits/M125_DESIGN_CORRIGENDUM_HATI_2026-09-06.md`:

- **numbered blocking corrections**, each with a severity
- an explicit **required-test delta** — what must be tested that currently is not
- a **disposition**
- a header stating what the review adds and what it does **not** authorize: scientific observations
  added, network authority added, scientific-run authority added. A review is not a licence to
  advance a gate.

If you return `NO-GO`, also say what would count as **re-arming it improperly** — which knob the
author could turn to make your finding go away without the underlying problem changing. M121 v2's
history is why this is asked.

Write the result to:

    docs/audits/GENESIS_RUNTIME_REVIEW_HATI_<YYYY-MM-DD>.md

## Boundary on your own role

If any correction you supply amounts to **designing a replacement mechanism** rather than identifying
a defect, say so explicitly. You cannot afterwards audit a mechanism you designed, and the
replacement will need a different reviewer.

Separately: if an isolated copy of you is later used as Genesis's experimental body, that copy and
you-as-reviewer must not be the same logical instance. A body under experiment cannot also be the
independent judge of the runtime experimenting on it.

## Running things

```sh
python -m pytest tests/test_genesis_trust_root.py tests/test_genesis_loop.py \
                 tests/test_genesis_migration.py tests/test_genesis_demonstration.py \
                 tests/test_genesis_guards.py tests/test_genesis_probe.py -q   # ~20s
python scripts/run_genesis_demonstration.py                                    # prints the record
python scripts/check_genesis_guards_are_tested.py                              # ~12 minutes
```

The last one deletes each `raise` in `genesis/` one at a time and reruns the suite; it currently
reports 69 of 74 killed, with five deliberate survivors marked in place. It restores the sources in a
`finally` block and refuses to start if `genesis/` has uncommitted changes.

The demonstration is deterministic. If `test_the_demonstration_is_reproducible` does not hold on your
machine, that is finding number one and everything else is provisional.
