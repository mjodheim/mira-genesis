# M052 — exact finite-domain behavioral-equivalence pruning

**Status: DEVELOPMENT — qualification pending.**

## Purpose

M051 searches a frozen grammar of eighty variable-length compositions. M052 asks one narrower question: can the search avoid repeatedly evaluating syntax that is exactly behaviorally equivalent on a declared finite domain, while preserving fail-closed selection and independent hidden validation?

## Frozen construction

M052 reuses the unchanged M051 grammar and its eighty candidates. It introduces no new transform, reduction, empty-input policy, runtime or code-generation mechanism.

The declared finite domain contains every integer sequence of length zero through three over `{-2, -1, 0, 1, 2}`: exactly 156 inputs.

Each candidate is executed on every domain input. Its complete value/error vector is hashed into a behavioral signature. Candidates with the same signature form one exact finite-domain equivalence class. One deterministic canonical representative is retained per class; all other members are pruned before public task search.

## Authority separation

- the equivalence audit sees only the frozen grammar and declared finite domain;
- the proposer receives public probes only;
- the hidden validator receives the selected canonical representative and hidden probes;
- the validator has no adoption authority;
- no component has repository, network, credential, deployment or production authority.

## Permanent episodes

The tests must preserve:

- exact enumeration of all 156 domain inputs;
- complete partition of all eighty M051 candidates;
- at least one non-singleton equivalence class and a strict reduction in evaluated representatives;
- one positive public episode selecting a unique behavioral class;
- independent hidden acceptance;
- public ambiguity terminating as `insufficient_evidence`;
- hidden contradiction returning a negative verdict;
- rejection of tampered candidate artifacts;
- rejection of empty or out-of-domain evidence;
- deterministic manifest replay.

## Qualification rule

M052 passes in development only if the complete Python 3.11 and Python 3.13 matrices and repository-integrity job pass on the exact documented head. Every failed qualification remains part of the append-only history and must not be erased by a later correction.

## Claim boundary

M052 establishes, at most, exact equivalence pruning over one small finite input domain and one frozen eighty-candidate grammar. Equality of signatures is not claimed outside that domain. M052 does not establish general program equivalence, symbolic theorem proving, arbitrary code synthesis, unknown-runtime discovery, open-ended evolution, general intelligence, consciousness or production safety.

M052 remains bounded and noncanonical. M042 remains the only positive canonical continuous-lineage completion.
