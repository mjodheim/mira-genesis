# M043 Q4 — disposable validation, versioned adoption and exact rollback

**Status: passed in development. Qualification CI completed successfully.**

## Question

Can a Mealy candidate produced by the Q2/Q3 development rig be validated outside the
candidate-producing lineage, adopted as one versioned transaction, and rolled back to the
exact prior accepted body, tool registry, learning state and causal journal after a forced
post-commit fault?

Q4 is development rig qualification only. It does not select a seed, freeze a hidden task
bank, authorise a canonical workflow or establish a new continuous-lineage result.

## Three separated roles

`metamorphosis/m043_adoption.py` and
`metamorphosis/m043_validation_worker.py` keep three roles distinct:

1. the lineage emits a candidate package containing a parent-bound Q2 trace, public task
   identity, target commitment and frozen Q3 budget;
2. a fresh Python process receives only the accepted parent and that package, strictly
   parses them, replays every Q2 certificate and returns the reconstructed candidate;
3. the existing Q3 evaluator privately compares that candidate with the hidden target by
   exact product equivalence.

The disposable worker does not import Q3 task/evaluator code and never receives the hidden
target body, a witness construction or target-derived operation arguments. The lineage does
not validate itself, and the worker alone cannot accept a candidate: adoption requires both
the isolated replay result and the evaluator-side exact comparison.

## Candidate package

A versioned candidate package binds:

- the complete parent-lineage snapshot digest;
- the exact indexed parent-body digest;
- the public task identifier and hidden-target commitment;
- the canonical Q2 rewrite trace;
- the frozen depth, node and state budget;
- the expected exact final-body digest.

Strict parsing rejects missing or extra fields, unknown schemas, malformed digests, invalid
budgets and malformed traces. Stale packages are rejected before a worker process is
started. The fixed payload limit is 131,072 bytes and the disposable process has a fixed
ten-second timeout.

## Independent disposable replay

The worker runs through `python -I -m metamorphosis.m043_validation_worker` in a fresh
temporary working directory. It:

- reconstructs the parent from strict Mealy JSON;
- reparses the candidate package;
- verifies the exact parent identity;
- enforces the declared depth and state limits;
- replays the Q2 trace with independent certificate recomputation;
- verifies the exact final-body identity;
- returns the candidate body and deterministic identities.

The runtime process identifier proves process separation but is excluded from the canonical
validation-report digest, so repeated development qualification remains byte-deterministic.

## Combined exact validation gate

After isolated replay, the evaluator confirms that:

- the candidate is exactly equivalent to the committed hidden target;
- the parent is not equivalent and has an exact distinguishing word;
- the Q3 structural-incapacity certificate binds the same parent and target commitment;
- the candidate and trace remain inside the frozen Q3 limits;
- every body, behaviour and trace identity returned by the worker recomputes exactly;
- the worker process differs from the orchestrating process.

Any disagreement rejects the package without mutating lineage state.

## Versioned transactional adoption

An accepted decision stages one new immutable `LineageSnapshot` containing:

- the accepted Mealy body;
- a tool record for the exact trace and its certified effect sequence;
- a portable learning state containing the successful trace identity and updated operation
  priority;
- the accepted target commitment;
- one hash-chained causal journal entry;
- a monotonically increasing version.

The journal binds the prior full-snapshot digest, the new core-state digest, candidate
package, validation report, accepted body, registry and learning state. The transaction is
committed only after a complete post-commit audit.

Snapshots use canonical JSON and domain-separated SHA-256 identities. Parsing may receive
an externally preserved expected digest; this is required to detect replacement of an
otherwise self-consistent serialised snapshot.

## Exact rollback campaigns

Q4 deliberately corrupts each staged component after provisional commit:

1. accepted Mealy body;
2. tool registry;
3. portable learning state;
4. causal journal.

Every corruption is detected by the post-commit audit. The store then restores the exact
checkpoint object and verifies equality of both canonical bytes and snapshot digest. Failed
transactions create no lineage version and append no journal entry. A separate explicit
rollback from accepted version 1 to archived version 0 also restores the original snapshot
exactly.

## Deterministic development qualification

`run_q4_development_qualification()` uses the first deterministic Q3 development fixture as
a qualification case, not as a selected seed or frozen bank. It records:

- disposable worker separation;
- exact hidden-target match;
- exact parent incapacity;
- one successful versioned adoption;
- one registered tool and one causal journal entry;
- explicit rollback to version zero;
- exact restoration after all four forced faults;
- rejection of a tampered final identity;
- rejection of a stale package;
- absence of the hidden target body from the worker request.

The report excludes runtime-only process identifiers and reproduces identically across
repeated runs.

## Permanent falsification suite

The focused suite contains 33 tests covering:

- strict candidate-package parsing and byte-identical round trips;
- complete-lineage rather than body-only parent binding;
- pre-worker rejection of wrong task, commitment and budget;
- tampered final identities;
- disposable process separation and exact evaluator agreement;
- deterministic report identity despite varying worker process identifiers;
- accepted-only staging;
- versioned body, registry, learning-state and journal updates;
- snapshot round trips and externally committed tamper rejection;
- rejected-decision immutability;
- four forced post-commit fault campaigns with byte-identical restoration;
- explicit version rollback;
- worker independence from Q3 evaluator code;
- worker malformed-request, wrong-parent and budget rejection;
- deterministic complete Q4 development reporting.

Final qualification workflow run `31001898372` passed the complete repository with **705
tests on Python 3.11**, **705 tests on Python 3.13**, clean imports, no orphan modules and
consistent declared dependencies.

The initial workflow run `31001191874` already passed both 705-test matrices but exposed one
repository-integrity defect: the disposable worker was launched dynamically through `-m`
and was therefore invisible to the static reachability audit. The runner now declares that
entry-point edge explicitly. No functional Q4 test failed and no failed test job was rerun.

## Next boundary

Q5 may now define a genuinely opaque Mealy-native substrate whose semantics are recovered
only through bounded public probes, followed by exact native synthesis. Q4 does not
authorise that substrate, a hidden bank, selected seed or canonical M043 workflow.
