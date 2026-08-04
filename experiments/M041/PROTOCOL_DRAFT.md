# M041 — isolated single-lineage completion audit

**Status: development protocol draft. No frozen block, canonical seed or M041 outcome exists.**

## Question

Can the positive cumulative M040 lineage place its accepted post-migration candidate behind an
independent, disposable and resource-limited validation boundary before the M041 body adopts
it, while preserving the exact M040 task, control and replay decisions?

A later frozen M041 run may support the first bounded Genesis completion claim only if the
same lineage satisfies all ten gates in `GENESIS_COMPLETION_CRITERIA.md`. Development runs
establish mechanism and controls only.

## Why M041 follows M040

M040 canonically joined autonomous diagnosis, internal tool ownership, repeated improvement,
opaque-substrate migration and post-migration plasticity in one lineage. Its candidate search
and exact audit remained part of one deterministic process. M023 independently demonstrated a
disposable resource-limited subprocess boundary for bounded source candidates, but that
boundary was not part of the M040 lineage.

M041 therefore adds no new task advantage and does not widen M040's scientific claim. It tests
whether the accepted post-migration DFA proposal can be re-evaluated outside the search
process before M041 performs its release adoption.

## Candidate model

The candidate is passive canonical DFA data, not executable user-supplied code. A fixed trusted
runner receives only:

- the candidate DFA;
- the pre-adoption parent DFA;
- the hidden target DFA after the search has completed;
- committed task observations;
- a critical regression subset containing observations on which parent and target agree;
- immutable resource and structural limits.

The candidate itself has no import, filesystem, network, process or syscall authority. The
trusted runner is executed in a fresh temporary directory and is the only executable object in
the workspace.

## Isolation boundary

Each validation must use a new subprocess workspace with explicit limits for:

- CPU time;
- address-space memory;
- output file size;
- process count;
- open file descriptors;
- wall time;
- captured output;
- maximum states, observations and serialised input bytes.

The workspace contains no parent archive, migration packet, tool registry, journal, expected
result artefact or repository checkout. A candidate cannot modify the search process or the
M041 release body.

The protocol must state clearly that this passive-data boundary does not authorise arbitrary
code execution and is not a general container or micro-VM sandbox.

## Independent adoption gate

The M040 search result is treated as a proposal inside M041. Before M041 release adoption, the
independent workspace must verify:

1. canonical DFA schema and dimensions;
2. structural limits and valid transitions;
3. the candidate digest supplied by the search process;
4. all committed observation answers;
5. every critical regression answer;
6. exact equivalence with the hidden target using the fixed runner's independent product
   traversal;
7. strict improvement over the pre-adoption parent on the committed observations;
8. deterministic workspace identity and byte-identical repeated validation.

Any timeout, malformed output, digest mismatch, resource failure, incomplete observation set,
regression failure or non-exact candidate rejects release adoption.

## One-lineage gate audit

The M041 result must carry a machine-readable verdict for each Genesis gate:

1. autonomous diagnosis;
2. internal tool ownership;
3. self-rewrite;
4. isolated validation;
5. held-out improvement;
6. adoption and rollback;
7. complete trans-substrate metamorphosis;
8. post-migration plasticity;
9. repeated improvement cycles;
10. measurement integrity.

Development may establish gates 1–9 as mechanically eligible. Gate 10 remains false until a
frozen protocol, marker-only arming commit and unique first canonical execution exist.

## Controls and falsifiers

M041 must reject or expose all of the following:

- one transition changed after search selection;
- one accepting flag changed;
- candidate digest changed independently of its data;
- target or case omission;
- duplicate or reordered cases that change the committed case digest;
- a candidate that improves task quality but breaks a critical regression;
- a stale candidate validated against a different parent;
- subprocess timeout or malformed output;
- validation performed after M041 release adoption;
- a replay whose workspace digest or verdict differs.

M040 canonical artefacts and identities are immutable and may not be regenerated or replaced by
M041.

## Development order

1. implement the passive DFA workspace and mutation controls;
2. add a pre-adoption validator hook whose default-disabled path leaves M040 byte-identical;
3. wrap a fresh M040-style development lineage in an M041 release transaction;
4. prove isolated validation occurs before M041 adoption and that failure leaves the release
   body unchanged;
5. replay the complete lineage and both workspace validations from a development seed;
6. retain every development failure;
7. freeze only after complete Python 3.11/3.13 CI and repository-integrity checks pass;
8. execute one immutable M041 canonical evaluation.

## Non-claims

M041 remains a bounded deterministic-DFA experiment. Even a positive result would not establish
arbitrary code safety, open-ended evolution, general intelligence, consciousness or permission
to modify external systems.
