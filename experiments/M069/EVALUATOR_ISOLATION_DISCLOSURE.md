# M069 evaluator isolation disclosure

This append-only disclosure was recorded after M069 was qualified and merged. No frozen M069
artifact is rewritten: `PROTOCOL.md`, `FROZEN_PROTOCOL.json`, `DEVELOPMENT_RESULT.md`, the task
bank and the learner keep their exact recorded bytes and digests.

## The defect

The frozen evaluator loads each candidate in its own interpreter:

```text
metamorphosis/m069_terminal_task_bank.py:129   spec.loader.exec_module(module)
```

`evaluate` is reached through `main`, so the task-bank module is `__main__` and `TASKS` — including
every hidden case — is resident in that process while the candidate executes. The candidate is
imported before any case is run.

## Why it was reachable through the governed interface

The policy owns `write_text` and may place arbitrary bytes in `solution.py`. The public evaluator
is registered without `expose_output=False`
(`metamorphosis/m069_governed_terminal_repair.py:283`), so process output returns to the policy
inside an observation. A candidate containing
`print(sys.modules["__main__"].TASKS)` would therefore have transported the hidden cases back
across the body interface using only admitted actions.

## What this does not change

The recorded M069 learner is frozen at `c603dd5` and its source is auditable. It writes only
statements drawn from the eleven-member repair language and never inspects `sys.modules`. The
positive finding — one uniform policy recovered four repairs and each selected source passed 3/3
hidden cases — stands, and every reported reward remains exactly as recorded.

## What this does change

M069 falsifier 10 is stated as "source inspection checks confirm that the learner does not read the
evaluator implementation". That check verifies the learner's text. It does not establish that the
interface *prevented* hidden-evidence access, and M069 reported no falsifier that did. The
non-reachability property was therefore never established by construction; it holds for this frozen
learner by audit, not for the design.

## Open question for the project owner

`PHASE_8_ADAPTIVE_EMBODIMENT_AGENDA.md` lists as a phase falsifier that "hidden evidence is
reachable by the discovery API". Under a strict reading the governed body *is* that API and the
condition fires, which would bar a positive verdict. Under a narrow reading the leak runs through
candidate code executed by the evaluator rather than through a body affordance that returns hidden
evidence directly. The verdict label is a scientific judgement reserved to the project owner; this
file only records the fact and does not reclassify M069.

## Constraint on successors

Any future evaluator that executes candidate code must run it in a separate process that never
holds hidden evidence in memory, passing cases in and results out over a pipe. Static inspection of
a learner's source is not a substitute for an interface that cannot leak.
