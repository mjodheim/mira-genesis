# M062 — synthesizing a bounded control arrangement

**Status: QUALIFIED IN DEVELOPMENT.**

The exact experiment head `f5cfe35c265cf83640fddc2ae80e54805776f84f` passed the first
and only qualification run `31269732461`, attempt 1: 1,038 tests on Python 3.11 and
1,038 on Python 3.13, plus repository integrity. The result remains noncanonical.

## Research question

Can the copy-loop control arrangement left authored by M061 be constructed from discovered
effects and public behavioural evidence, without supplying a catalogue of complete programs?

This is deliberately narrower than asking for an arbitrary compiler. The task decomposition,
search grammar, WebAssembly framing, block types, label-depth encoding and observation cases are
all authored and are recorded as such.

## What M061 left

M061 found ten data and control opcodes by effect, but `build_copy_loop` still wrote the final
instruction order, `block`, `loop`, the blocktype bytes and branch depths. It therefore removed an
authored instruction list without removing the authored program arrangement.

## Stage 1 — replay M061 discovery

Replay all six M061 scaffolds and resolve the same ten opcodes. M062 has no fallback table: a
missing load, store, branch, local write, addition, subtraction or comparison stops emission.

## Stage 2 — make region opening observable

A third-stage scaffold places a candidate region opener around a discovered unconditional branch.
The branch carries `7` to depth zero and a discovered addition runs after the region:

- an exit region returns `8`;
- a repeat region re-enters and does not terminate;
- malformed candidates are refused by the WebAssembly validator.

All 256 opcode bytes are scanned. The scaffold presupposes `i32.const`, `end`, an `i32` result
blocktype, module framing and a function signature. It uses the `br` and `i32.add` bytes recovered
by M061 rather than authored copies.

The probe is allowed to return an equivalence class. It may not prefer the familiar opcode by
name. A numeric minimum may serve as the deterministic representation only if every member of the
class passes the independent whole-program validation.

## Stage 3 — construct arrangements

The grammar is the Cartesian product of:

- two region nestings: exit-then-repeat and repeat-then-exit;
- two predicate operand orders: `remaining <= 0` and `0 <= remaining`;
- five positions for the exit check;
- every permutation of four atomic steps: copy one byte, advance source, advance destination,
  decrement remaining.

This constructs **480** arrangements (`2 × 2 × 5 × 24`). There is no list of 480 complete byte
programs. The emitter renders any grammar product from the opcodes supplied by discovery.

## Public synthesis evidence

The generator sees three cases only:

1. a zero-length copy with a non-zero source sentinel;
2. a one-byte copy with an extra source sentinel;
3. a four-byte copy.

Destination guard bytes and source preservation are observed as well as the returned value. The
zero-length case falsifies copying before the exit check; the one-byte case falsifies an extra
iteration.

If no candidate survives, stop. If several survive, retain the complete class. A digest may choose
a canonical source representation only after independent validation establishes that every public
survivor has the same admitted hidden behaviour.

## Independent validation

The synthesis function has no hidden-case parameter. A separate validator owns three committed
cases at different offsets and lengths, including zero, two and seven bytes and values `0x00` and
`0xff`.

Admission requires the Cartesian product of:

- every public arrangement survivor;
- every exit-region effect candidate;
- every repeat-region effect candidate;

to pass every hidden case. Any disagreement is ambiguity and stops the result. The canonical
digest is never allowed to choose hidden behaviour.

## Permanent falsifiers

- a wrong predicate must fail the public evidence;
- an exit check after the copy must alter the zero-length destination guard;
- missing discovered opcodes must stop emission without fallback;
- region witnesses must be found;
- every public survivor and every region-effect representative must pass hidden validation;
- the complete manifest must derive its counts and boundaries from execution;
- repeated emission from the same selected structure must be byte-identical.

The first region scaffold declared an empty-result region and then tried to use a value transported
through it. WebAssembly refused the witness. The permanent block-versus-loop test caught the
instrument defect before the full lineage ran; the scaffold now declares an `i32` result and the
presupposition is explicit.

## Authorship boundary

M062 does not pass as arbitrary compiler synthesis. The following remain authored:

- the copy-task decomposition and four atomic steps;
- the finite grammar and its 480-candidate budget;
- the generic emitter;
- the scaffold shapes and public/hidden observations;
- module framing, signatures, block types, label-depth encoding, `local.get`, `i32.const` and
  `end`.

What is not handed as a complete program is the selected region nesting, predicate direction,
exit position and step ordering. The operation bytes and region-effect representatives come from
scans rather than fallback constants.

## Qualification rule

M062 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A local green run is development
evidence, not qualification. An infrastructure failure is handled under D017.

## Claim boundary

One WebAssembly runtime, one copy task, one finite grammar, 480 arrangements, three public cases
and three hidden cases. M062 does not establish arbitrary compiler synthesis, a self-authored
grammar, unrestricted code generation, open-ended evolution, general intelligence,
consciousness or production safety. It is noncanonical; M042 remains the only positive canonical
continuous-lineage completion.
