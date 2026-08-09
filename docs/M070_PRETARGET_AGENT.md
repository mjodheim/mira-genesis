# M070 pre-target agent design

**Status: ENGINEERING BASELINE TESTED — NO EXTERNAL TASK SELECTED OR RESULT CLAIMED.**

This record fixes the generic agent side of the next evaluation before Mira Genesis reads,
selects or imports a Terminal-Bench task. A later append-only freeze record will identify the
exact design commit and only then bind an independently maintained benchmark revision and a
deterministic task-selection rule.

## Structural advance over M069

M069 ran finite supplied replacements through trusted registered host commands. The M070 baseline
instead provides:

- `StructuredModelPolicy`, which accepts only a closed JSON decision (`act`, `finish`, `refuse`),
  declares the body's complete authority for every action and rejects inconsistent output;
- `CodexExecBackend`, a provider-specific adapter behind the provider-neutral
  `StructuredModelBackend` contract; it runs ephemerally in a neutral directory, ignores repository
  rules and user configuration, uses a named model, a read-only sandbox and an output schema;
- `IsolatedContainerBody`, which executes policy-supplied shell scripts only inside a disposable
  digest-pinned Linux container;
- `DockerCliEngine`, which invokes Docker without a host shell, bounds time and output and kills the
  entire container when an action times out;
- evaluator-owned success: `finish` only submits the task workspace and always leaves the Mira
  episode unsuccessful. A separate benchmark evaluator must inspect final state.

## Isolation contract

The body requests and then independently inspects all of the following:

- Docker network mode `none`;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- read-only container root filesystem;
- explicit memory, CPU and PID limits;
- one read/write bind mount containing only the disposable task workspace;
- no repository, Docker socket, credential or ambient host-environment mount.

If Docker reports a weaker realized configuration, reset fails closed and removes the container.
Scripts, observations, step count, action time and captured output are bounded. Image tags are
rejected; only repository digests are accepted.

This is materially stronger isolation than M069's governed host workspace, but it is not a proof
against Docker-engine, kernel or side-channel vulnerabilities. It grants no network, repository,
credential, deployment, permission-change or physical authority.

## Pre-target validation

- 34 unit/synthetic tests pass with two expected skips when Docker integration is not opted in;
- the broader Mira Core/M069 targeted set passes 45 tests with two expected skips;
- one opt-in real-Docker synthetic repair passes on Docker 29.6.2 using
  `python@sha256:9662417aace5ae7b8e2609cce472b72a8958e134ba372808abe9cc1a0c0125e6`;
- the real container is removed after the episode;
- an authenticated schema-constrained `gpt-5.6-sol` smoke decision returns only
  `container_submit` with no authority;
- repository import, orphan-module and dependency audits pass.

These are engineering tests, not M070 scientific evidence.

## Required next sequence

1. Commit this agent design without any external task identifier or task content.
2. Create an append-only design-freeze record naming that exact commit.
3. Pin an official external benchmark revision and choose tasks by a predeclared deterministic
   rule written after the design freeze but before any task execution.
4. Freeze image digests, model identity, prompts, action/resource budgets, evaluator commands,
   baselines, ablations, stopping rule and failure-preservation rule.
5. Run once, preserve failures and report evaluator-owned final-state outcomes.

A public benchmark result can support development evidence only. A stronger generality claim also
requires a private uncontaminated split and independent reproduction.
