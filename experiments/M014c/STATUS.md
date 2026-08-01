# M014c — Status

- Scientific status: `HALTED — SUPERSEDED BY M017`
- Canonical evaluation: **never opened**
- Result claimed: **none**
- Code preserved: tag **`archive/m014c-halted`**

## What was built

A structural meta-plasticity passport, an online adaptation session with integer
counters, a persistent adaptation engine on an opaque substrate, and a development
benchmark over generated profiles. The tests passed and CI was green.

## Why the experiment is halted

It did not fail. It measured the wrong thing.

`MetaPlasticitySession.identify` enumerates exactly `passport.programs` — twelve
hand-written structural programs. All learning consists of reweighting group counters
over that closed catalogue. The organism cannot express anything it was not given.

The development benchmark reported `active_to_scratch_ratio = 0.083`, which reads as a
fifteen-fold gain. It is an automaton-size effect: out-of-distribution DFAs carry 7 to
10 states, so L\* from scratch pays a cost that grows with the automaton while Genesis
pays one that grows with its twelve-entry library. Enlarging the automata would have
inflated the same ratio without changing anything the passport had learned.

The comparison that actually carried the hypothesis was the adaptive session against its
own non-adaptive twin: `active_to_static_ratio = 0.88`. Twelve percent, on a task whose
theoretical optimum sits near four queries and whose random selection sits at eight — a
window four queries wide.

**M014b failed on exactly that geometry**: a pre-registered 25% margin, measured on a
scale too coarse to separate signal from sampling noise. Freezing M014c against L\*
would have passed trivially and repeated the error in the opposite direction.

## What was carried forward

The part of the structural language belonging to no experiment — roles, atoms,
application, canonical forms — was extracted into `metamorphosis/structural.py` and
became the foundation of M017. The passport, session and query policy specific to M014c
were not carried forward: they encode the closed catalogue that motivates the halt.

Per D007, M014c's code does not stay in the working tree. The tag
`archive/m014c-halted` holds it intact, and this record is never deleted.

A tag rather than a branch: a live branch invites resumption and gets deleted by
accident, whereas an annotated tag is an immutable reference, which is what a scientific
record requires. Recovery:

```bash
git show archive/m014c-halted:metamorphosis/m014c_meta.py
```

```bash
git switch --detach archive/m014c-halted
```

## Note on the branch's last CI run

Run `30656737493` of `M014c development benchmark` fails at installation:

```
error: Multiple top-level packages discovered in a flat-layout:
       ['results', 'archives', 'experiments', 'metamorphosis']
```

The branch was rebased onto the consolidated tree one commit **before** the packaging
fix that declares the build backend and the explicit package list. Its `pyproject.toml`
therefore does not allow `pip install -e ".[dev]"`.

The failure is deliberately left uncorrected: the tagged commit is what this record
cites, and a halted experiment is not rewritten to clear a red check. The branch having
been replaced by the tag, the workflow has no trigger left and will not replay.

## Replacement

**M017 — Self-extending language.** See `experiments/M017/`.
