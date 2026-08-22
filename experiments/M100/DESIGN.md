# M100 — repeated cumulative operation acquisition

## Question

Can the current real-Python lineage repeat the acquisition/persistence causal chain so that one
registered operation makes a second operation constructible, and that second registered operation
makes a third operation constructible, while every earlier definition remains live and reusable
after complete process boundaries?

M100 is the direct successor required by D068. It combines the contract-safe composition boundary
qualified by M096, the bounded operation acquisition qualified by M097, and the process-death
persistence qualified by M099. It does not relabel any of those results.

## Fixed cumulative chain

The inherited M097 acquisition is operation A:

```text
A(left, right) = left - right
```

M100 migrates both the exact pre-acquisition M097 state and the exact extended M097 state into a
closed cumulative registry. New M100 definitions may contain only:

- `PUSH_LEFT`, `PUSH_RIGHT`, `NEG`, `SWAP`;
- `CALL:<operation-id>` for an operation already registered earlier in the same state.

They may not contain host `ADD`, `SUB` or `MUL` instructions. Only the preserved M097 definition may
contain its original legacy instruction. A new definition therefore cannot combine two operands at
all unless a prior registered binary operation supplies that ability.

The two successor targets are fixed before qualification:

```text
S0: no A
S1: A is registered
    acquire B(left, right) = left + right       with bound 4
S2: A and B are registered
    acquire C(left, right) = left + 2 * right   with bound 5
S3: A, B and C are registered
```

The target is the exact affine signature, not merely agreement on a weak sample. Public cases reject
most candidates; a separate exact symbolic calculation must also prove the signature. Selection is
shortest program first and canonical digest second.

## Why the chain is cumulative

The expected shortest B program invokes A. The expected shortest C program invokes B, which still
invokes A. Definitions store live content-addressed references; the runtime expands those references
at execution. It does not cache the resulting Python expression or host function.

The frozen controls distinguish cumulative acquisition from three authored answers:

1. B must be absent in the migrated pre-A state.
2. C must be absent in S1.
3. Building B without registering it must leave S1 byte-identical and C absent.
4. Registration must grow the operation census `0 → 1 → 2 → 3` and conserve every earlier
   definition byte-for-byte.
5. A digest-valid semantic mutation of A must break B.
6. A digest-valid semantic mutation of B must break C.
7. Removing A or B, or corrupting state, must fail closed.
8. A live semantic fault in S2 must suppress C acquisition; restoring the exact original S2 bytes
   must reproduce the exact original S3 in another fresh process.

These controls test a bounded extension of constructive reach. They do not establish unbounded
expressivity: the target operations all remain affine combinations over two inputs, and the host
interpreter, stack primitives, bounds and targets remain authored.

## Process boundary

The qualification apparatus copies exactly two files into a temporary capsule: the generic M100
runtime and a minimal entry point. Every migration, acquisition, control and world execution starts
the base Python interpreter with `-I`. The capsule cannot import Mira packages or use the repository
as an import path.

The key chronology uses distinct processes:

```text
fresh process: M097 extended state -> S1, terminate
fresh process: S1 -> acquire/register B -> S2, terminate
fresh process: S2 -> acquire/register C -> S3, terminate
fresh processes: execute A, B and C from S3 on qualification worlds
```

## Qualification population

The complete population contains nine new real-Python structures: three subtraction demands for A,
three addition demands for B, and three weighted-addition demands for C. All M097, M098 and M099
worlds are excluded. Each entry has two independent caller files and four constructor/execution
cases. Before freeze the authoring preflight may only build and parse source and case records; it may
not invoke migration, acquisition, registration, isolated execution, mutation, ablation or
rollback.

After S3, all nine worlds execute from the same persisted state. This tests conservation as well as
new reach: A and B must still solve fresh demands after C exists.

## Stable replay boundary

The only recursively excluded evidence keys are `pid`, `process_pids` and `search_path`. Process
counts, isolation flags, module-import census, return codes, state bytes/digests, operation bodies,
accepted counts, execution results, fault outcomes and rollback equality remain scientific evidence.
The checker reruns the complete 24-process experiment and compares the stable projection.

## Claim boundary

A positive result would demonstrate three bounded cumulative operation states, two new acquisition
cycles enabled in order by prior registered operations, hard process separation, conservation,
live transitive dependency and exact rollback across the frozen nine-world population.

It would not demonstrate AGI, open-ended evolution, recursive self-improvement without a fixed
bound, arbitrary self-modification, a self-hosting interpreter, endogenous choice of objectives,
cross-domain transfer, independent human reproduction, hostile-code containment or production
authority.

## Publication

The project owner recorded `PUBLIC_AGPL_COMMERCIAL_OPTION` for M100 on 22 August 2026 before the
first enabling implementation was created. The disposition is recorded in `IP_ASSET_REGISTER.md`.
Public project-controlled software remains AGPL-licensed; separate commercial permissions may be
granted by the rights holder.
