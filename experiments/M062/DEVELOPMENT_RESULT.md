# M062 — development result

## Status

**POSITIVE ON THE BOUNDED CENTRAL QUESTION — QUALIFIED IN DEVELOPMENT.**

The final copy-loop arrangement was selected from a constructed grammar using public evidence,
then every public survivor and every observationally equivalent region representative passed
independent hidden validation. This is a qualified, noncanonical development result.

## Observed result

| Observation | Value |
|---|---:|
| M061 scaffolds replayed | **6** |
| Region opcode space scanned | **256** |
| Region outcomes | 253 refused, 2 observed, 1 non-terminating |
| Exit-region effect class | `0x02`, `0x06` |
| Repeat-region effect class | `0x03` |
| Arrangements constructed | **480** |
| Public survivors | **16** |
| Hidden cases | **3** |
| Survivor/region programs admitted | **32 / 32** |
| Selected module | **97 bytes** |

## Qualification

The exact experiment head is `f5cfe35c265cf83640fddc2ae80e54805776f84f`.

GitHub Actions run [`31269732461`](https://github.com/mjodheim/mira-genesis/actions/runs/31269732461),
attempt 1, passed without a failed job or rerun:

- **1,038 tests on Python 3.11** in `889.83` seconds;
- **1,038 tests on Python 3.13** in `914.03` seconds;
- repository integrity: clean imports, no orphan modules and dependency consistency.

The separate human-only attribution workflow also passed. Warnings about GitHub Actions moving
their JavaScript action runtime from Node 20 to Node 24 are infrastructure annotations, not
scientific failures and not a change to the pinned native target runtime used by the tests.

The deterministic selected arrangement is:

```text
topology:      block_then_loop
condition:     remaining_le_zero
exit_position: 0
step_order:    copy_byte, decrement_remaining, advance_source, advance_destination
```

## The new observation

M061 said `block` and `loop` could not be exposed by placing one inside the other without assuming
what the experiment sought. M062 instead uses neither opener as the scaffold. A branch recovered
by M061 targets depth zero inside the candidate region. With the same surrounding bytes, an exit
region transports `7` and returns `8` after a discovered addition; a repeat region starts again
and hits the process deadline.

The scan did not uniquely name the exit opener. Node accepts both `0x02` and `0x06` with the
required bounded effect. That ambiguity is preserved as a class rather than resolved by opcode
familiarity. `0x03` is the only repeat-region candidate.

## The arrangement was not supplied as a finished program

The search constructs 480 products from two nestings, two predicate operand orders, five exit
positions and twenty-four permutations of four atomic state transitions. Sixteen satisfy all
public observations. A digest chooses one reproducible source representation only after the
validator establishes that all sixteen survivors pass all hidden cases.

The same check is repeated with both exit-region representatives. The admission matrix is
therefore 16 survivors × 2 exit representatives × 1 repeat representative = **32 complete
programs**, each passing all three hidden cases.

This matters because choosing the lowest digest before checking the class would allow the digest
to decide hidden behaviour while appearing to perform harmless canonicalisation. D021 records the
rule produced by this result.

## What failed during construction

The first scaffold declared an empty-result region. Its branch placed `7` on the stack and the code
after the region attempted to add one, but an empty block cannot transport that value. WebAssembly
refused `0x02`, the witness disappeared and the permanent block-versus-loop falsifier failed.

The correction was to declare an `i32` result blocktype, not to loosen the resolver. The authored
blocktype is now named in the presupposed floor. This was an instrument defect found before the
complete development lineage, not a negative scientific result.

## Falsification results

- reversing the predicate to `0 <= remaining` fails the public cases;
- placing the exit after `copy_byte` corrupts the zero-length destination sentinel;
- removing `br_if` or the repeat-region opcode stops emission;
- both `0x02` and `0x06` pass the whole-program hidden validation;
- all sixteen public survivors pass all hidden cases;
- repeated selected emission is byte-identical;
- the manifest records the remaining authorship explicitly.

## Digests

| Artifact | SHA-256 |
|---|---|
| Protocol | `3780dc998a5df0cee783ba435671e1b349b27e9cd96315130ae7a34f41e7b97e` |
| Public evidence | `89b3d76501648f7ca08c2dd564d4ed3d2c6c175fca0493ddc8fd127c2414fd8f` |
| Selected hidden evidence | `91f0047e268b24f1cf39e19a0cdc7143e3a8c93c30b84a39c532c96c7f8dad9b` |
| `0x02` survivor-class evidence | `6d69aaaab05130fa7cab97c76c57c51a838a9356e12fbffaa37baaf235d62ed2` |
| `0x06` survivor-class evidence | `c52776a858acdf53966ce3bf2ed638554572041e5f1b18a423455106a04cd67c` |
| Manifest | `752fecdc5891911038ef04813a57f736a7f65c14c62c41a907269500fe88b03b` |

## What remains authored

This does **not** finish the general compiler question. The copy-task decomposition, atomic
operations, finite grammar, generic emitter, blocktypes, label encoding, module framing, scaffold
shapes and evidence cases are authored. The result removes one complete literal arrangement; it
does not generate its own task language or compiler architecture.

The second project frontier is untouched. Nothing here supplies the four-arm post-migration
plasticity comparison, three accepted cycles across new held-out families or a protocol frozen
and hashed before a canonical real-substrate run.

## Claim boundary

One substrate, one copy task, 480 grammar products, three public cases and three hidden cases.
M062 is noncanonical and qualified in development. It does not establish arbitrary compilation,
open-ended evolution, general intelligence, consciousness or authority over repositories,
credentials, networks, deployments or production systems.
