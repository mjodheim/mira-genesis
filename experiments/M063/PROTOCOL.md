# M063 — transfer of bounded control arrangement to a checksum body

**Status: QUALIFIED IN DEVELOPMENT.**

The exact experiment head `d4eb5ed981727fd1343e6e1031494771d9dec220` passed the first
and only qualification run `31275085485`, attempt 1: 1,054 tests on Python 3.11 and
1,054 on Python 3.13, plus repository integrity. Human-only attribution also passed. The
result remains noncanonical.

## Research question

Does M062's bounded control-arrangement mechanism transfer from byte copying to a genuinely
different executable body, without passing a complete checksum program to the emitter?

The new body reduces memory bytes into a local accumulator. It has two parameters rather than
three, returns the computed checksum rather than a constant, and performs no memory write. This
is a transfer test, not an arbitrary compiler claim: the checksum decomposition, its atomic
steps, the finite grammar and the task-specific emitter remain authored.

## Source mechanism

M063 replays the six M061 structural scans and M062's 256-byte region-effect scan. It consumes
the resulting operation mapping and the observed region classes rather than a fallback opcode
table. The exact M062 source-mechanism protocol digest is
`3780dc998a5df0cee783ba435671e1b349b27e9cd96315130ae7a34f41e7b97e`.

The arrangement dimensions transferred from M062 are:

- two region nestings;
- two predicate operand orders;
- an exit position among the task's atomic steps;
- every permutation of those steps;
- public synthesis followed by class-wide independent hidden admission.

## Target body and grammar

The target function is `(source: i32, count: i32) -> i32`. It declares one `i32` accumulator
local and constructs a loop from three atomic effects:

1. load one unsigned byte and add it to the accumulator;
2. advance the source pointer;
3. decrement the remaining count.

The finite product contains **96** candidates:

`2 topologies × 2 predicates × 4 exit positions × 3! step orders`.

No complete checksum byte program is stored in the candidate catalogue. The emitter renders a
grammar product using the opcodes supplied by discovery and the selected region representatives.

## Public synthesis evidence

The generator receives three cases only:

1. zero bytes with a non-zero sentinel;
2. one byte followed by a distinct sentinel;
3. five bytes followed by another sentinel.

The runtime records the return value, the source payload and whether the entire one-page memory
remained byte-identical. A zero-length case falsifies accumulation before the exit check. Distinct
adjacent values falsify advancing before loading. The generator API has no hidden-case parameter.

## Independent validation

A separate call owns three committed cases at different offsets:

- two bytes including `0x00` and `0xff`;
- seven ASCII bytes;
- zero bytes at a shifted source address.

Every public survivor must pass every hidden case under every member of the region-effect
Cartesian product. D021 applies again: no digest or minimum opcode may choose hidden behaviour.

## Cross-body negative control

M062's selected copy arrangement is re-emitted from the same discovered effects and executed by
the checksum observer. It must fail at least one public checksum case. The zero case may pass
because both tasks return zero there; both non-zero checksum cases must expose the mismatch.

If the copy body passes all checksum cases, M063 stops rather than calling relabelling a transfer.

## Permanent falsifiers

- the grammar contains exactly 96 distinct source arrangements;
- a wrong predicate fails public evidence;
- advancing before loading fails the distinct-byte case;
- accumulating before the exit check fails the zero-length case;
- a missing discovered opcode or region opener stops emission;
- public synthesis has no hidden-case parameter;
- every public survivor and region-effect representative passes independent hidden validation;
- the selected module writes no memory and returns each committed checksum exactly;
- M062's selected copy body is rejected by the checksum task;
- repeated emission of the selected structure is byte-identical.

## Authorship boundary

M063 leaves authored:

- the checksum-task decomposition and three atomic steps;
- the finite transferred Cartesian grammar;
- the checksum WebAssembly emitter;
- local declarations, blocktypes and label-depth encoding;
- module framing and function signature shape;
- public and hidden cases.

The result can support bounded mechanism transfer from copy to reduction. It cannot support a
self-authored grammar, general compiler synthesis or unrestricted program generation.

## Frozen development constants

- protocol digest: `4ac3f4629771a4f111bcadd83b8cc9e17a5723e7198de6b392b7ae9081156e02`;
- candidate budget: `96`;
- public cases: `3`;
- hidden cases: `3`;
- opcode space per scan: `256`;
- region probe timeout: `2.0` seconds;
- arrangement process timeout: `30.0` seconds.

## Qualification rule

M063 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and
repository-integrity job pass on the exact documented experiment head. A local green run is
development evidence, not qualification. Infrastructure failure is handled under D017.

## Claim boundary

One WebAssembly runtime, one checksum body, one 96-product authored grammar, three public cases,
three hidden cases and one previous-body negative control. M063 is noncanonical and does not
discharge Genesis gates 8–10. M042 remains the only positive canonical continuous-lineage
completion.
