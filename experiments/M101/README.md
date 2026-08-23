# M101 status

M101 is the first planned Genesis II experiment.

**Current state:** pre-registered design plus two enabling implementation slices. The carrier-neutral
runtime and development-only unit fixtures now exercise exact M100-byte migration, closed
public-demand projection, A acquisition/registration, text-record-syntax reuse, later A-dependent B
acquisition, live mutation, ablation, corruption and conservation. A separate two-file execution-only
capsule also reuses registered A and B in isolated fresh processes, and a standalone checker
independently recomputes content addresses and symbolic A/B semantics without importing either M101
implementation module. This is apparatus development evidence only: no qualification pool, frozen
scientific runner, final protocol, canonical run or scientific result exists on this branch.

Authoritative design documents:

- `PRE_REGISTRATION.md` — frozen scientific question, population shape, controls, fifteen decisive
  conditions and falsifiers;
- `PROTOCOL_DRAFT.json` — machine-readable pre-implementation form; it explicitly forbids producing
  a verdict;
- `../../docs/GENESIS_II_RESEARCH_PLAN.md` — phase-level rationale and relation to M100;
- `../../docs/IP_REVIEWS/M101_PUBLICATION_REVIEW.md` — pre-publication provenance/IP decision.

## Required next commit sequence

Implementation must not jump directly to a result. The next research branch work should proceed in
this order:

1. implement the minimal carrier-neutral M101 state/runtime and prove M100 migration/conservation;
2. implement A acquisition on a development-only fixture;
3. implement record and Python-syntax carrier adapters without exposing qualification worlds to A
   acquisition;
4. implement the later A-dependent B acquisition;
5. implement the independent validator/checker and all causal controls;
6. author the exact 15-world pool and perform only the preflight permitted by the pre-registration;
7. adversarially audit leakage, structural-insufficiency proof, baseline parity, process isolation,
   rollback and stable-projection policy;
8. write `PROTOCOL.json` binding exact mechanism/pool/checker/capsule/predecessor digests and freeze it;
9. only then allow one armed local Track-A canonical run.

The current implementation reaches the first development form of step 5. The isolated capsule proves
only individual fresh consumer invocations; it does not yet establish the full process-death
chronology, independent qualification replay, untouched population or frozen bindings required by
the pre-registration. The next load-bearing increment is to complete causal-control coverage across
that isolated boundary and adversarially audit the capsule/checker split before authoring the exact
15-world pool later in the sequence.

If implementation shows that a decisive condition is impossible or ill-posed before qualification,
record a named pre-run amendment rather than silently editing `PRE_REGISTRATION.md`. If any decisive
condition fails after the first canonical result exists, preserve the negative result and use a
successor milestone for the repair.

D070 remains intentionally unfilled until a canonical M101 result has been independently replayed.
