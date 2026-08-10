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
statements drawn from the eleven-member repair language and never inspects `sys.modules`. There is
no evidence that this learner exploited the reachable data. The diagnostic observations — one
uniform policy recovered four repairs and each selected source passed 3/3 hidden cases — and every
reported reward remain exactly as recorded.

## What this does change

M069 falsifier 10 is stated as "source inspection checks confirm that the learner does not read the
evaluator implementation". That check verifies the learner's text. It does not establish that the
interface *prevented* hidden-evidence access, and M069 reported no falsifier that did. The
non-reachability property was therefore never established by construction; it holds for this frozen
learner by audit, not for the design. Because evaluator isolation was part of the validity boundary,
auditing one benign learner after the run cannot repair the experiment.

## Verdict decision

`PHASE_8_ADAPTIVE_EMBODIMENT_AGENDA.md` lists as a phase falsifier that "hidden evidence is
reachable by the discovery API". The governed body's admitted write/evaluate/output path is part of
that API. The condition therefore fires: **M069 is post-hoc disqualified as a positive development
result by the evaluator-isolation falsifier.** Its recorded task outcomes remain useful diagnostics,
but they do not qualify H15 or advance a generality gate. This decision is additive and does not
rewrite the frozen protocol, learner, evaluator, task bank or result bytes.

## Constraint on successors

Any future evaluator that executes candidate code must run it in a separate process that never
holds hidden evidence in memory, passing cases in and results out over a pipe. Static inspection of
a learner's source is not a substitute for an interface that cannot leak.
