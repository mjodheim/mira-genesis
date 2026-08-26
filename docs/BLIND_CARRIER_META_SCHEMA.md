# Blind carriers — the second reusable instrument

`mira-blind-carrier-v1` is a milestone-agnostic meta-schema for obtaining an **executable body**
from a process that was shown nothing about this project, and evaluating a learner against it
objectively. M113 is its first user.

It sits one level above [`BLIND_BANK_GENERATION.md`](BLIND_BANK_GENERATION.md), which describes how
a bank is sealed, committed to and revealed. That contract answers *how a held-out artifact is
obtained honestly*. This one answers *what the artifact is*, when the artifact has to be a machine
rather than a record.

It is **not** a replacement for an independent human maintainer, and no tier below
`human_maintained_sealed_bank` ever closes G4. The distinction is the point of the design, not a
caveat attached to it.

## What M112 left standing, in one word

M112's blind generator chose the *values* inside a carrier this project designed: five documents,
three integer fields, a reference into a side table. Its own decision record names what remained —
**the carrier**. The value chain, the document shape, the reference edge, the operators, the bounds
and the evaluator were all this project's.

Under this meta-schema the generator chooses the machine.

| chosen by the emitter | fixed by the reception contract |
|---|---|
| one of four wire surfaces, with its own tokens, separators and key names | the four surface *shapes* |
| one to four named state cells over their own finite domains, any of them latent | that state is finite cells over finite domains |
| two to six actions, nullary or unary, under names it invents | that an action is a name, an arity and an argument domain |
| a precondition per action, so the carrier can impose an order of use | the four comparison relations a precondition is built from |
| the effects, as assignments modulo the cell's domain | the five assignment modes |
| an error vocabulary, and which refused action returns which code | that a refusal returns a code |

## Why data and not arbitrary programs

A bank of arbitrary executables would make the sandbox, rather than the science, the load-bearing
part of every claim: the result would rest on containment of code written by a process the project
cannot inspect in advance, and the first question any reviewer would ask is about the sandbox.

Under this meta-schema an action is a finite list of arithmetic assignments modulo a declared domain
and a guard is a finite list of comparisons. No carrier can raise, loop, allocate without bound,
touch the filesystem, open a socket, import a module or execute generated source. Every carrier is
total, deterministic, side-effect-free and **exhaustible**, which is what makes an unreachable demand
provable rather than asserted.

That is a declared limit on what these results can mean, and it belongs in the claim rather than in
a footnote: the interaction *language* of each body is blind, the *space those languages are drawn
from* is not.

## The host holds no carrier semantics, and that is checkable

M107 put the operator semantics in the state and left the interpreter empty. `carrier_host` is the
same move for whole machines: it can execute any carrier under the meta-schema and has no way to
distinguish one from another beyond the bytes it was handed.

A scan for suspicious strings cannot establish that. Any word a carrier might use is a word some
report key might also use, and the collisions are noise — the first draft of the audit failed on
`closed`, `depth` and `mode`. What the claim actually means is **equivariance**: renaming every cell,
action, error and surface token consistently changes nothing the host computes except the names.

`scripts/audit_m113_boundaries.py` checks exactly that, over sixty carriers, comparing the full state
graph, the reachable and unreachable observation sets, the structural signature and every response
across a bijection. A host with a preference for some particular carrier fails it. Nothing else does.

## The meta-channel, and the honest shape of the boundary

A learner that cannot form a syntactically valid request discovers nothing, so something has to be
legitimately observable. The meta-channel reports the wire grammar and the action names with their
arities and argument domains — what a usage line, a schema endpoint or a protocol banner makes
observable in any real system.

It carries **no** cell, **no** domain, **no** initial configuration, **no** observability, **no**
precondition, **no** effect, **no** error vocabulary, **no** error mapping and **no** reachable set.
A learner handed it knows how to *speak* and nothing about what any sentence *does*.

The enforcement is worth stating precisely rather than glossing. The carrier lives in a closure
inside the channel, and a Python closure is introspectable: `session._send.__closure__` does contain
it. So this is an **audited boundary, not a sandbox**. The learner's source is parsed and refused if
it names a carrier-internal key or calls a host function that reads carrier structure. The claim is
that the learner does not read the carrier and that the claim is checked — not that reading it would
be impossible.

## Closure is computed, never inherited

M112's `P5` is the reason this section exists. Four fixed-point bounds — 7, 9, 11, 13 — were declared
because seven expression nodes closed the constructive image on 1 160 project-generated worlds. The
first blind world closed at nine and `P5` came out false. The bound was an empirical regularity of
project-authored worlds wearing a certificate's clothes.

Nothing here inherits a bound:

- a carrier's reachable set is a **breadth-first fixed point** — the frontier is expanded until it is
  empty, and the certificate records the iteration at which growth stopped;
- a learner's exploration converges by the same criterion, and `closed_at_level` records which level;
- `EXPLORATION_CEILING` is a **termination guarantee against a hostile payload**, not an operating
  parameter. A carrier reaching it is non-qualifying under a rule frozen before any carrier existed,
  and is never re-run larger.

M113's devkit survey over 1 200 carriers found observations first appearing as deep as **level 11**,
in a distribution whose bulk sits at 2 and 3. Any bound chosen from the shallow majority would have
been wrong on the tail, exactly as M112's was.

## Two completenesses, which are not the same fact

A bounded composition space stops because it was told to. That is not a fixed point, but it is still
completeness of a kind an experiment can rest a refusal on: every sequence the space admits has been
tried.

Conflating the two is expensive and the cost was measured. A first draft reported `closed: false`
whenever the bound stopped the expansion, so **every** bounded attempt returned `undetermined` with a
budget reason — while only 2 attempts in 88 had actually reached the ceiling. `closed_by_fixed_point`
and `complete_for_the_bound` are now separate fields. Either justifies a refusal; neither is budget
exhaustion.

## Three design choices that are easy to get wrong

**A feature must not determine its own label.** The first draft computed `g0` as a width comparison,
so every row on which it was true mapped to the observation interface *by definition* and the
attribution question answered itself. `g0` is now observed nondeterminism under the learner's own
projection: somewhere in exploration, one request was answered two ways from what the interface
reports as the same place. That is a thing the learner watched happen, and a latent cell that never
changes anything visible correctly produces no such signal.

**Exploration alone cannot see nondeterminism.** It prunes on the projection, so each projection is
expanded from exactly one path and a machine that is not a machine in the learner's language looks
like one until two arrivals are compared. So they are compared: the same request is issued after each
of two paths reaching the same projection. And a budget that cannot afford that comparison must not
be reported as the absence of a collision — the distinguishing phase returns whether it completed,
and an unfinished exploration is `undetermined`.

**A demand rule that takes "the first determined pair" is biased.** The census iterates the smallest
entry state and the least target first, so that rule systematically poses the trivial corner. Over
300 devkit carriers the reachable arm landed **zero** times out of twenty-one on a feature row where
the inherited cascades disagree, so the acquired machinery had no opportunity to help or harm and
every arm scored identically. M110 already had the answer: it posed **rows**, not targets, and took
the canonical least demand for each row it censused.

## Making an incompatible body structural

The weakest part of any refusal benchmark is that "impossible" usually means "phrased so that a
careful reader gives up". Here it means a value tuple over the carrier's own observable cells that
**no request sequence of any length can produce**, established by exhausting the state space.

Each qualifying carrier yields a **pair**, and the pair is one object: the carrier reference, the
budget, the meta-channel, the entry configuration and the evaluator are stored once, and the twins
carry only their target and their class. `assert_demand_pair_delta` derives both and refuses the pair
unless the only differing fields are the target and the class label. M075-B recorded why this must be
a representation rather than a check: a check has to enumerate every field that must stay equal, and
missing one silently readmits the defect.

Claiming a construction on the unreachable twin is scored as an **invented adapter** — the failure
G1 names — and it is reachable in practice rather than in theory: a learner whose observation
interface is narrower than the demand can match the narrowed projection in good faith and be wrong.
On M113's development population the fresh lineage does exactly that on 13 of 44 such demands.

## Reusing this for another milestone

The host and the meta-schema carry no milestone-specific threshold, hypothesis or agent identity. To
add a milestone:

1. add `metamorphosis/<milestone>_carrier_bank.py` binding the meta-schema to that milestone's
   hypothesis, analysis plan and tested system, and keep its evaluator in a module the mutable body
   does not import;
2. register its digest-bearing paths in `.gitattributes` **in the same commit that creates the
   directory**, before any digest exists to be wrong;
3. add its readiness check and its boundary audit to CI as decisive steps.

Step 3 is not optional. M086-A recorded a positive verdict against a threshold that could not fail,
partly because a scientific checker existed without being decisive in CI. A green CI must guarantee
the properties the registers claim it guarantees.
