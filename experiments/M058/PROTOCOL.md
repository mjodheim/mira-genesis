# M058 — a discovered instruction set

**Status: PROPOSED — unqualified.**

## Research question

Can the lineage discover **which instructions exist** in a substrate, rather than being handed a
list and discovering only what they do?

## What this removes

M057 removed the authored compiler and kept an authored list. Six handles were exposed, and its
result named what remained:

> The set of available operations remains authored by a human. What the lineage discovers is
> what they do and how to build its tools from them.

M058 removes the list.

## The scan

The lineage is told only the **shape** it needs: a function taking two `f64` values and returning
one. It then emits one candidate module for **every single-byte opcode** — all 256 — and asks the
substrate to compile each.

**Validation is the answer.** A byte that is not a binary `f64` operation refuses to compile, and
that refusal is the information. Nothing narrows the space in advance, and nothing says how many
operations will be found or where they sit.

The set the scan returns is whatever the substrate accepted. It is not compared against a
reference list before use; an authored list is retained only so the result can report what
discovery added, and a permanent test asserts it never reaches the scan or the synthesis.

## Synthesis

As in M057: bottom-up by expression size, deduplicating by observed behaviour, evaluating every
candidate by calling the discovered operations. Nothing holds a table of what an opcode means.

The atoms are the tool's own parameters plus a constant equal to its arity.

## Declared parameters

| Parameter | Value |
|---|---:|
| Opcode space scanned | 256 |
| Scan pairs | 4 |
| Maximum expression size | 7 nodes |
| Synthesis budget | 200,000 |

## Required lineage

1. begin from the accepted M048 version-eight state, reconstructed rather than asserted;
2. scan the whole opcode space and keep what the substrate accepts;
3. observe its own tools, and synthesize a body for each from the discovered operations;
4. reach at least one tool that **no single operation satisfies**;
5. verify every synthesized body on a hidden domain the synthesis never saw;
6. execute every inherited capability through the discovered instruction set;
7. record what discovery added beyond what a human had written down.

## The falsifier

M058 fails, informatively, if the scan returns exactly what a human would have listed. Discovery
would then be a more expensive way of receiving the same thing, and the experiment would have
established nothing beyond M057.

## Ablation

| Arm | Required outcome |
|---|---|
| Discovered set, full composition | constructs a working path |
| Discovered set, composition denied | fails on the tool no single operation satisfies |

## Anti-cheating

M058 does not pass if any opcode list is supplied to the scan or the synthesis, if the scan is
narrowed to a subrange chosen for containing the answer, if a synthesized body delegates to the
source runtime, or if a capability is served from a lookup table.

A permanent test reads the discovery module's source and asserts that no specific opcode is
named in it.

## The boundary that remains

**The signature shape is authored by a human**: two `f64` in, one out. The lineage discovers
which operations exist *in that shape*, not that the shape exists.

This is stated rather than blurred, and it is the next thing to remove. An operation of another
arity, another type, or with side effects on linear memory would not be found by this scan, and
M058 does not claim otherwise.

## Qualification rule

M058 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One lineage, one substrate, one signature shape, fixed tools. M058 does not establish arbitrary
runtime discovery, unrestricted code generation, open-ended evolution, general intelligence,
consciousness or production safety. Network, repository, credential, deployment and
external-system authority remain human-controlled.

M058 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
