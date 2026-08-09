# M071 pre-target governed model transport

## Why M071 exists

M070 correctly preserved a negative external result. Both selected tasks received official reward
`0.0`, as did both `nop` controls. The frozen model transport failed before useful task work because
Windows text mode attempted to encode a true `U+2011` through `cp1252`; parent-only timeout cleanup
then left descendants retaining inherited pipes.

M071 is a separately named corrected design. It does not reinterpret, retry or overwrite M070.
Its narrow hypothesis will be whether this already-frozen composed system can earn an external
reward on a fresh blind pair under the same evaluator-owned success boundary.

## Frozen correction

All policy-adjacent host processes now share one supervisor:

- no host shell;
- bytes-mode standard streams;
- explicit strict UTF-8 encoding and decoding;
- a separate process group/session;
- whole-tree termination on timeout or bounded-output cleanup;
- fail-closed errors when the tree cannot be stopped.

The model adapter and Docker control path use the UTF-8 runner. Docker task execution and the
governed terminal use the same start/termination primitives. On a Docker timeout, the container is
stopped before the host-side `docker exec` process tree is cleaned.

Real Windows regression tests pass `U+2011`, accented text and an emoji through the transport and
prove that a delayed descendant cannot create a marker after timeout. A complete local Python 3.14
suite passed 1,215 tests with two platform/optional skips, and repository integrity passed. A live
`gpt-5.6-sol` smoke call containing the same Unicode probe produced the valid bounded action
`container_submit` through `StructuredModelPolicy`.

## Identity and attribution

The Harbor bridge now emits `m071-harbor-agent-manifest-v1`, goal `m071-external-task`, policy
`m071-governed-model-policy-v1` and agent name `mira-m071`. This prevents later evidence from being
mistaken for M070.

The named external model is a declared proposal component. Model availability and model behavior
are operational dependencies even though the Python package has no provider SDK dependency. Any
benchmark reward belongs to the complete named system. Evidence about Mira governance itself
requires a direct control or ablation that isolates that layer.

## Pre-target boundary

The runtime commit and bridge commit are already immutable. At the commit introducing the freeze:

- no benchmark revision is pinned;
- no fresh task identifier is selected;
- no fresh task package, instruction, solution or verifier test is opened;
- no M071 benchmark attempt or result exists.

The next step may pin an independently maintained benchmark tree and an identifier-only selection
rule. That rule must exclude the two closed M070 identifiers before ranking, use a new committed
salt, select exactly two fresh tasks without replacement, and be committed before the inventory is
enumerated. No agent or bridge blob may change after that boundary; a new defect is negative M071
evidence and any correction requires M072 or later.
