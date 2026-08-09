# M070 external-task selection protocol

**SELECTION RULE CANDIDATE — NO TASK IDENTIFIER OR TASK CONTENT HAS BEEN READ.**

## Fixed predecessors

- frozen agent design: `41ebe791605f55e7a44df8f0939d730139cf219a`;
- agent-design commitment: `14f6c17ea9c88a4e967b317e167e45d76f4700f5a5d91c4f017edb0add179a46`;
- independently maintained task repository:
  `https://github.com/harbor-framework/terminal-bench-2.git`;
- task-repository revision observed by `git ls-remote`:
  `2fd12b88aafdd04a52c298e3940bcb189f9766d6`;
- official Harbor v0.20.0 tag commit:
  `f75477f2ad0b04fad199b0cb80689cc23a06c72d`;
- selection count: exactly two tasks;
- selection salt: UTF-8 bytes `mira-m070-selection-v1\0`.

## Deterministic rule

After this rule is committed, clone the task repository at the exact pinned revision. Enumerate
the parent POSIX paths of every tracked regular file whose basename is `task.toml`. A task
identifier is the final component of that parent path.

For every identifier compute:

```text
sha256(b"mira-m070-selection-v1\0" + identifier.encode("utf-8"))
```

Sort by `(digest, identifier)` ascending and select the first two identifiers. Do not filter by
topic, apparent difficulty, build size, expected score, known model performance or local
compatibility. Do not replace a selected task if its image cannot build, the infrastructure fails,
the agent refuses, a budget expires or the evaluator score is zero. Such events are preserved.

The complete ordered inventory, digest for every identifier and selected pair must be written to a
machine-readable selection artifact before any selected instruction, environment, solution or
test file is opened.

## Contamination and evidence boundary

General Harbor and Terminal-Bench documentation was consulted to choose the benchmark family and
harness. No task identifier or task content was consulted while designing the agent or this rule.
Terminal-Bench is public, so even a positive result is development evidence and may reflect model
pretraining contamination. Reference solutions must never enter the model context. Evaluator tests
must remain hidden from the policy and may be run only by the external evaluator.

## Failure preservation

Once the selected identifiers are committed, the M070 task pair is immutable. A code defect found
after task-content access makes M070 negative or incomplete under this frozen design; a corrected
agent must use a separately named attempt with a new pre-target freeze and new blind selection.
