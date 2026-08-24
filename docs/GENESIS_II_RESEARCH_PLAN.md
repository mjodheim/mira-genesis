# Mira Genesis II — research plan

**Status:** active; M102 positive, M103/H48 protocol frozen and canonical run not authorised
**Date:** 2026-08-24

## Why Genesis II stays in this repository

Genesis II is not a new project or a reset of the scientific record. It is the continuation of the
same auditable software lineage. The point of the next phase is precisely to test whether capabilities
already acquired and persisted by the lineage remain causally useful when the representation and
demand family changes.

Opening a fresh research repository would weaken that continuity test by making predecessor state,
negative results, provenance, rollback history and causal controls external to the active record.
Product-facing software may later live in a separate repository; the scientific lineage remains in
`mjodheim/mira-genesis`.

## Genesis I archival boundary

The first publication boundary is the reviewed M094-M100 case study:

**Mira Genesis: A Reproducible Case Study of Causal Cumulative Capability Acquisition in a Persistent Software Lineage**

Persistent DOI: `10.5281/zenodo.22067855`

M100 remains the frozen scientific predecessor. Genesis II does not rewrite the paper or enlarge the
M100 claim. It starts from the limitation the paper names explicitly: the qualified cumulative chain
is still inside one authored affine-operation family with authored targets, bounds and interpreter.

## Genesis II research question

Genesis II asks a stronger question:

> Can a continuing lineage acquire a reusable transformation capability because one observed demand
> exposes a missing abstraction, preserve that capability across process death, and then use it to
> improve constructive reach and enable a later acquisition in materially different representation
> families?

The phase is about **transfer of acquired improvement machinery**, not a larger benchmark number.
The central comparison is always against an otherwise identical fresh lineage that did not retain the
producer-domain acquisition.

## M101 — cross-family cumulative transfer

M101 is the first test.

The planned carrier families are deliberately different:

1. **text** — scalar string transformations;
2. **records** — exact structured mapping transformations;
3. **Python syntax** — source/AST transformations whose success is checked from produced source and
   execution where appropriate.

The producer-domain demand is text. It must expose, only through observable input/output behaviour,
a limitation that cannot be solved by one inherited atomic transformation. The acquisition process
must not receive a target operation name and must not have access to the record or syntax
qualification families.

From a small carrier-neutral micro-language, the lineage is expected to acquire a generic two-stage
composition capability. The important property is not the label `compose`: the registered symbolic
definition must contain no text-, record-, syntax-, class-, field-, key- or qualification-specific
identifier and must operate only on an opaque value plus references to prior transformations.

After registration and producer-process death, that acquired capability is tested in the record and
Python-syntax families. A fresh baseline receives the same authored atomics, interpreter, public
demand, compute budget and observation budget but not the acquired capability.

A later Python-syntax demand then requires a new registered transformation whose construction is
causally dependent on the transferred capability. The later operation must retain a live reference
to its predecessor rather than cache an equivalent host implementation.

## What would be new if M101 is positive

A positive M101 would be stronger than M100 in four specific ways:

- the enabling capability is acquired because of an observed demand rather than because an exact
  affine target signature is handed to the acquisition mechanism;
- the acquired capability must transfer from its producer representation to at least two materially
  different consumer representations;
- the transfer is paired against a fresh-lineage baseline with the same authored substrate and
  resource budget;
- the transferred capability must become necessary to a later acquisition in a consumer family,
  while hard persistence, conservation, mutation/ablation, corruption, rollback and stable replay
  remain intact.

If those conditions pass, the result may justify moving G4 from `open` to **partial bounded
cross-family mechanism evidence**. It would not close G4: all M101 families and evaluators remain
project-authored, and no independent external maintainer or uncontaminated private domain is added.

## M101 outcome

M101 attempt 1 qualified positively from corrected v4 freeze `b3e172b`. The acquired A capability
passed all eight held-out transfer worlds while eight fresh equal-budget baselines passed zero
hidden cases, and A remained causally necessary for later B acquisition. M100 conservation and all
mutation, ablation, corruption, rollback, isolation and stable-replay controls passed; the
independent checker computed P1–P15 true. D070 therefore moves G4 to partial bounded cross-family
mechanism evidence, exactly within the boundary predicted above.

The result does not alter the M094–M100 paper or create a new publication claim. The next research
question follows the measured residual ceiling: deeper cumulative retention under genuine
interference and at least one independently maintained domain or interface.

## What a negative M101 would mean

A negative result is expected to be useful. Depending on the failing condition, it would locate a
specific ceiling such as:

- the acquired abstraction is carrier-specific rather than generic;
- the fresh baseline can reconstruct the same consumer reach without retained lineage state;
- transfer changes search cost but not constructive reach;
- a later operation only appears dependent because the host interpreter contains an equivalent
  shortcut;
- state survives serialization but not complete producer death;
- consumer qualification leaks into producer acquisition;
- the cumulative relation fails under semantic mutation, ablation or exact rollback;
- stable replay retains unprojected process ephemera.

The attempt must remain negative if any frozen decisive condition fails. No post-verdict repair may
turn the same attempt positive.

## Phase ordering

M101 is deliberately pre-registered before its enabling implementation. Work proceeds in this order:

1. public IP/provenance review;
2. pre-registration of H46, conditions, falsifiers, population shape and controls;
3. implementation of the carrier-neutral runtime and acquisition mechanism;
4. independent checker and qualification-authoring apparatus;
5. adversarial review before any canonical execution;
6. exact population/mechanism/checker digests bound in a final `PROTOCOL.json`;
7. local Track-A canonical run from a clean tree;
8. independent replay and only then a D070 decision.

No result may be produced from the pre-implementation draft protocol.

## Likely successors

M101 should not pre-decide its successor. If transfer is positive, the next useful pressure is likely
one of two directions: broader demand-derived acquisition across additional operation families, or
longer cumulative retention under interference. If M101 is negative, M102 should target the measured
cause rather than add breadth around an unresolved failure.

Independent external transfer remains governed by the existing M085 / generality boundary and is not
silently substituted by project-authored M101 worlds.

## M102 — registered-policy improvement under interference

M101's positive result leaves its prior acquisitions in an append-only, interference-free state.
M102 therefore pre-registers H47 against a different failure mode: two carrier-local bindings have
the same inherited flat registry key but incompatible descriptors. A no-upgrade lineage must either
refuse the later binding or overwrite and forget the earlier one.

The proposed lineage may advance only by acquiring a generic state-owned addressing policy from the
observable collision, validating a transactionally re-indexed descendant, and registering that
policy. The policy must then remain causally necessary, with live M101 B, for a later four-effect
capability executed and scored from actual SQLite database state. Equal-budget flat-policy controls,
destructive forgetting, K/B mutation and ablation, exact predecessor conservation, process death,
corruption, rollback and stable replay remain decisive.

SQLite supplies an independently maintained execution interface, not independent task authorship:
the adapters, tasks and evaluator remain project-authored. Even a positive M102 could move only the
bounded mechanism record, not close G4/G5 or support a general-agent claim.

### M102 qualified outcome

The complete thirteen-record population and protocol were frozen before the unique owner-authorized
attempt 1. Accepted candidate `4549f17f…` produced protocol `59689da6…`, whose annotated freeze tag
binds exact M101 T2 bytes, Python/SQLite identities, mechanism, capsules, pool, independent
definition/result checkers, P1-P15 and stable projection.

Adversarial review corrected four pre-freeze falsifiers: a declared-but-not-executed B dependency,
a host-side K-origin gate that manufactured causality, and Python docstring formatting that mixed
representation with conservation, plus protocol construction that did not fail closed outside the
canonical runtime. C acquisition fails without K only because the live flat policy cannot represent
the joint collision relation. The canonical result then passed P1-P15 with result `92d4ed3e…`, stable
evidence `eab68a79…` and independent report `3ba2f130…`. D071 supports bounded
continual-interference and registry meta-policy evidence; project-authored tasks prevent G4/G5
closure.

## M103 — acquisition machinery must itself gain constructive reach

M102's acquired K changes how capabilities are addressed, but both K and C are still found by fixed
host-side hypothesis constructors. M103 therefore targets the next causal layer. Starting from exact
M102 U2, the lineage must observe a requirement outside the complete constructive image of inherited
constructor S0, acquire and serialize a generic improvement S-prime to that constructor, survive
producer death, and use live S-prime to acquire a later capability that an otherwise identical
equal-budget S0 lineage cannot construct.

H48 freezes S0 as a context-invariant linear constructor. The positive demands contain identical
initial payloads that require different traces under different observable contexts, so S0 remains
incapable at every budget. S-prime may be assembled only from a generic constructor-feature
substrate on a DEVELOPMENT fixture and must refuse when public evidence leaves multiple semantic
classes. Configuration and disposable-filesystem consumers become available only after S-prime's
producer dies.

The protocol distinguishes acquisition-time causality from runtime causality. S-prime must remain
necessary to acquire later hypotheses, including after another process death. If compiled consumers
can execute after S-prime is removed, that independence is reported rather than masked by a fake
live reference. Mutation, ablation, corruption, exact rollback, fresh/more-budget S0, M100-M102
retention, isolated processes and stable replay remain decisive. A positive result would be bounded
acquisition-machinery improvement evidence, not recursive self-improvement, independent task
authorship, G4/G5 closure, general-agent evidence or AGI.
