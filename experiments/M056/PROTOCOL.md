# M056 — a second migration

**Status: PROPOSED — unqualified.**

## Research question

Does a capability learned **after** a migration survive the **next** one?

M048 changed substrate once and then learned `tool_max` in the new runtime. Its compiler was
written by a human who knew the nine M047 modules it had to translate; `tool_max` did not exist
yet. If a second migration carries the twenty-eight capabilities inherited from before migration
one and loses the one acquired after it, then each hop transports only what its compiler already
knew, and the lineage cannot accumulate across substrates.

That is the distinction between continuity and translation, and it has never been tested.

## Target substrate

WebAssembly, executed by the already-pinned Node runtime through its built-in engine.

- a genuinely different execution model: stack machine over linear memory, `f64` operands, no
  closures, no objects, no prototype chain. The body's JavaScript semantics do not survive by
  accident;
- the emitted module **declares no imports**, so it cannot call back out for its arithmetic.
  This is verified through `WebAssembly.Module.imports()` rather than promised;
- no new runtime, no `setup-*` step, no change to the pinned environment that forms part of
  M048's experimental identity.

`f64` is chosen because a JavaScript number is an IEEE-754 double and `mean` divides. The
migration is therefore semantically exact rather than approximate.

## Scope of the migration

**The tools migrate; the request shell does not.** Tokenising, routing, planning, critique and
orchestration remain in JavaScript. What moves is where the capabilities live.

This is stated rather than dressed up as a whole-body migration. The claim it supports is
bounded and checkable: removing the WebAssembly module must break **every** migrated capability.
If the shell still answers, the semantics never left JavaScript and the migration claim is false.

The calling convention that spreads an argument array into positional `f64` values performs no
arithmetic and is named as convention, not semantics.

## The compiler must not know the answer

The compiler works from what each accepted module **declares**, never from its name.
`tool_mean` was learned before the first migration and `tool_max` after it; both declare
`kind: synthesized_tool`, so both take the identical path.

This is the requirement that makes the falsifier honest. A compiler with a hand-written case for
the post-migration tool would carry it across while proving nothing. Permanent tests pin the
property directly: a module named `tool_zzz` declaring `expression_id: maximum` compiles, and a
module named `tool_max` declaring an unknown expression is refused.

## Required lineage

1. begin from the accepted M048 version-eight state, reconstructed rather than asserted, with
   its thirty-two retained capabilities;
2. compile the declared tools to one WebAssembly module with no imports;
3. execute every inherited capability in the new substrate and pass;
4. **verify the capability learned after the first migration, isolated from those that predate
   it**. This is the point of the experiment;
5. verify that removing the module breaks every capability;
6. diagnose a new limitation and learn a capability **in the migrated substrate**, emitting a
   module that declares itself the way its predecessors do;
7. validate independently: inherited regression bank, then public probes, then hidden probes.
   The validator holds no adoption authority;
8. adopt transactionally; detect a forced post-adoption fault; restore the exact state, with the
   detector shown able to report no fault on an intact state;
9. replay deterministically, with identities computed per **D018**.

## The falsifier

M056 fails, informatively, if step 4 fails while step 3 otherwise passes: migration would then
transport only what the compiler was written against. That outcome must be recorded as a
negative result, not repaired by teaching the compiler about the post-migration tool.

Requirement 2's indifference to names exists to keep that failure possible.

## Anti-cheating

M056 does not pass if the module calls back into JavaScript for its semantics, if any capability
is served from a lookup table, if the compiler special-cases a tool by name, or if a capability
still answers with the module removed.

## Qualification rule

M056 may pass in development only when the complete Python 3.11 and Python 3.13 matrices and the
repository-integrity job pass on the exact documented head. A run that fails before the
experiment's code executes is an infrastructure event under D017 and is not a verdict.

## Claim boundary

One lineage, one hand-written compiler, one target substrate, fixed task families. M056 does not
establish arbitrary runtime discovery, unrestricted code generation, open-ended evolution,
general intelligence, consciousness or production safety. Network, repository, credential,
deployment and external-system authority remain human-controlled.

**The compiler is written by a human.** In M048 and in M056 alike, the lineage carries its
capabilities across a substrate boundary but does not perform the crossing. Migration remains
something done to it. M056 does not close that gap and does not claim to.

M056 is noncanonical. M042 remains the only positive canonical continuous-lineage completion.
