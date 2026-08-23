# M101 status

M101 is the first planned Genesis II experiment.

**Current state:** the complete pre-run boundary is frozen. The final protocol binds the reviewed
pre-registration, exact M100 predecessor, carrier-neutral acquisition mechanism, separate
execution-only consumer capsule, independent definition/result checkers, recursive stable projection
and the complete fifteen-world population. The population received only its source-only preflight;
the M101 scientific mechanism has never executed it. No canonical run, scientific result or D070
decision exists on this branch.

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

Steps 1--8 are complete and frozen. Development-only fixtures exercised the complete 42-process
chronology and all causal controls; this evidence is apparatus validation, not qualification. The
committed population contains exactly 1 producer trigger, 2 text holdouts, 3 record transfers, 3
direct syntax transfers, 3 B-reuse worlds and 3 M100-conservation worlds, each with four public and
four hidden cases. Its preflight constructed and parsed those records only and explicitly recorded
that acquisition, registration, baseline, transfer, execution, mutation, ablation and rollback were
not run.

The immutable freeze ref is `experiment/m101-frozen-protocol`. The runner will refuse an armed run
unless the working tree is clean, `HEAD` is exactly that ref, every bound digest still matches and
`experiments/M101/RESULT.json` is absent. The remaining step is therefore a distinct owner-authorized
action: one local `--arm` canonical Track-A run, followed by the independent stable replay/checker.

If implementation shows that a decisive condition is impossible or ill-posed before qualification,
record a named pre-run amendment rather than silently editing `PRE_REGISTRATION.md`. If any decisive
condition fails after the first canonical result exists, preserve the negative result and use a
successor milestone for the repair.

D070 remains intentionally unfilled until a canonical M101 result has been independently replayed.
