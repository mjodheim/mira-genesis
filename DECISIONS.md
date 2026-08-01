# Decision register

## D001 — The repository is the official memory

Project continuity rests on versioned files, not solely on conversational context.

## D002 — Refocus on Metamorphosis

The V4–V6 prototypes remain sensorimotor benches, but the main line of research targets
trans-substrate portability and continuity.

## D003 — Frozen protocols

Any significant change made after observing a result creates a new numbered experiment.

## D004 — External evaluator

Exhaustive proofs and hidden tests do not count as experiments available to the
organism.

## D005 — No AGI claim

The M001–M011 validations are limited to the formal domains described in their
protocols.

## D006 — M012 must remove specialised compilers

The next accepted advance must concern the autonomous birth of a body, not another
hand-written backend.

## D007 — The working tree holds only living code

The code of a revoked experiment leaves the working tree; its scientific record stays.
Git history is the archive, and `archives/RETIRED_CODE.md` is its index: every removal
cites the commit where the file remains readable.

Reason: the inherited M012 / M013b stack, about 2,400 lines, formed an entirely
disconnected import subgraph and broke `pytest -q` by importing `torch`. Nothing
signalled it, because the sealed workflows only ran targeted test files.

## D008 — A permanent CI, distinct from sealed evaluations

`.github/workflows/ci.yml` protects the working tree on every pull request and never
produces a scientific result. Sealed evaluation workflows are still created per
experiment, run once, then retired to `archives/workflows/`: a consumed canonical
workflow must no longer be executable, otherwise the single-run rule holds only by
convention.

`scripts/check_repository_integrity.py` makes structural the three defects that had
escaped CI: an unimportable module, an orphan module, a phantom declared dependency.

## D009 — The next accepted advance must extend the language, not the catalogue

D006 required M012 to remove specialised compilers. The same requirement applies one
level up: **an advance that consists of choosing better within a hand-written catalogue
is not an advance.**

M012b, M013e, M014b and M014c share a limit none of their criteria measured.
`MetaPlasticitySession.identify` enumerates exactly twelve structural programs; all
learning reweights counters over that closed catalogue. The organism cannot express
anything it was not given, and M014c would have measured the quality of that
reweighting, not the growth of a capability.

M014c is therefore halted before evaluation, as M014 was, and replaced by M017 —
self-extending language. The roadmap changes order, not names: M015 and M016 are
deferred because they would laterally extend a paradigm whose core is not established.

## D010 — A measured quantity must have a dynamic range

M014b compared 14 queries to 14 queries, over a window four queries wide, with a
pre-registered margin of 25%. No result there was decidable: the criterion measured
sampling noise.

Every later experiment must therefore establish, **before freezing its protocol**, that
the chosen quantity varies over several orders of magnitude between the systems
compared, and that the retained margin exceeds the dispersion between environments.

Corollary: a structurally incapable baseline is a control, not a criterion. The closed
catalogue fails 0/42 in M017 development; freezing a threshold against it would pass
trivially. A criterion must oppose two organisms of identical capability at the first
episode, which only the mechanism under test separates afterwards.

## D011 — The project follows what its own failures identified

Four experiments failed — M014b, M017 on its threshold, M018, M019 — and **none failed
in the organism**. Each time, what was being built held; what gave way was the way of
judging whether it was better.

The repository's central question therefore becomes: **when does a proxy measure stop
tracking what it claims to track, and under what optimisation pressure?**

### What this decision does not claim

The problem is neither new nor unexplored. Goodhart's law, reward hacking,
specification gaming, novelty search and quality-diversity algorithms have worked on it
for a long time. Any wording suggesting the project enters vacant ground would be false,
and stating so is part of the decision.

### The real angle

Those bodies of work operate almost entirely where **the true objective is not exactly
verifiable**: reward hacking is diagnosed because a human finds the result suspicious.
Here, the behavioural equivalence of two finite automata is provable.

The repository can therefore show **where exactly** a measure comes loose, rather than
note that a result looks wrong. It is a decidable testbed for measure design, and that
is a modest, defensible contribution.

### Consequences

- `MEASURES.md` becomes a first-class register, beside `FAILURE_LOG.md`;
- the metamorphosis line is not abandoned: it produced the decidable domain, the two
  sealed validations and the six divergence cases. It becomes the **testbed** for the
  question rather than the question;
- M017 still stands ready to freeze, its results acquired and its criterion cleaned up.

## D012 — The repository is written in English

The repository is public. Registers, protocols, comments and docstrings are written in
English so the work is readable by the people most likely to find it useful.

French text predating this decision is translated rather than left in place: a
half-translated repository is worse than either language, since a reader cannot tell
which parts they are missing.
