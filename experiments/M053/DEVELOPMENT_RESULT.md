# M053 — development result

## Status

**PASSED IN DEVELOPMENT, on a re-attempted qualification.**

This is a bounded, noncanonical development result. It does not replace or amend the canonical
status of M042 and does not establish arbitrary code generation, unrestricted self-modification,
open-ended evolution, unknown-runtime discovery, general intelligence, consciousness or
production safety.

## Qualification evidence

Documented head: `12b0c31507872f91c368480f8b30d246e6887023`.

`experiments/M053/PROTOCOL.md` requires the complete Python 3.11 matrix, the complete Python
3.13 matrix and the repository-integrity job to pass on the exact documented head. Run
`31162378285` satisfies all three in one run:

| Required job | Verdict | Evidence |
|---|---|---|
| Tests (Python 3.11) | **PASSED** | 11 steps executed, **852 passed** in `455.46` seconds. |
| Tests (Python 3.13) | **PASSED** | 11 steps executed, **852 passed** in `576.23` seconds. |
| Repository integrity | **PASSED** | 10 steps executed: clean imports, no orphan module, dependency consistency. |

### Trigger disclosure

The qualifying run was started by `workflow_dispatch` on the branch reference, not by the
`pull_request` event. This is recorded rather than glossed because it differs from how M048–M052
qualified.

It makes the evidence more exact, not less: a `pull_request` run executes a merge reference
computed against `main`, while a dispatch on the branch executes literally
`12b0c31507872f91c368480f8b30d246e6887023`, which is the head the protocol names. The workflow,
the matrix and the integrity job are identical in both cases.

The reason for the dispatch was mechanical. The `pull_request` run `31122253673` reached a state
GitHub reported as `queued` while refusing cancellation as `completed`, and never released its
remaining job.

## Append-only qualification history

Four attempts preceded the verdict. Two produced no scientific information at all and are
recorded as infrastructure events rather than negative verdicts.

| Attempt | Run | Head | Outcome |
|---|---|---|---|
| 1 | `31118366409` | `49a72af` | **No verdict.** Failed during *Set up job* with `Service Unavailable` while resolving GitHub Actions downloads. No M053 code executed. |
| 2 | `31122253673` | `12b0c31` | **No verdict.** All three jobs queued for roughly fifteen minutes and were cancelled with zero steps executed. |
| 3 | `31122253673`, re-run | `12b0c31` | Partial. `Tests (Python 3.11)` and `Tests (Python 3.13)` obtained runners and passed with 852 tests each. `Repository integrity` was cancelled after about 54 minutes in queue with zero steps executed. The run then stopped progressing. |
| 4 | `31162378285` | `12b0c31` | **PASSED.** All three required jobs executed and passed. |

No attempt re-ran a job that had produced a verdict. Every re-run applied only to jobs that had
never started. The test results of attempt 3 agree with those of attempt 4: 852 tests on both
Python versions.

### Rerun disclosure

M049, M051 and M052 record that they passed on a first qualification attempt with no rerun used.
**M053 cannot make that statement.**

No observation is replaced — the cancelled jobs executed nothing, so there was no earlier verdict
for a later one to overwrite. But a reader of an append-only register should be able to tell a
first-attempt qualification from this one without opening the CI history.

## Corrected construction

The qualified head is not the originally proposed implementation. A defect in the rollback claim
was found by review **before any qualification verdict existed** and corrected in `12b0c31`.

### The defect

`Registry` is a frozen dataclass and `adopt` returns a new instance, so the original

    restored = founder

rebound an object that had never been mutated. `rollback_exact` compared that untouched registry
against its own checkpoint and could not evaluate to `False` for any input. The field carried the
same name as in M047 and M048, where it means a forced journal corruption was detected and the
exact accepted state restored.

### The correction

The fault is applied to the accepted extension artifact itself: the newest accepted operator is
changed while its content address is left untouched. That fault is detected — through both a
checkpoint mismatch and a failed digest re-derivation — before anything is restored. Recovery
rebuilds the registry from a serialised snapshot rather than a retained object, and refuses it
unless the checkpoint matches and every artifact digest re-derives.

Rollback counts as exact only when the fault is detected, the intact registry reports no fault
under the same detector, and the restored accepted tuple, checkpoint and serialisation all match
byte for byte. Because a detector that cannot answer no proves nothing, the negative case is
pinned by its own permanent test.

Correcting an unqualified experiment before its first verdict does not violate the append-only
rule: there was no verdict to preserve. Had the defect been found after a verdict, D003 would
have required a separately numbered experiment.

## Observed construction

Within the frozen M053 protocol and test bank, the qualifying run establishes:

- the founder language is the unchanged M051 catalogue of **80** programs;
- every founder candidate is exhaustively evaluated against the public probes before synthesis,
  and **0 of 80** survive;
- synthesis is refused while any founder candidate survives;
- the meta-language contains exactly **16** ASTs, all evaluated using public probes only;
- the unique public survivor is `current subtract previous`, artifact digest
  `130b0fc5cb549383b74f75362262a0cadc8333c6ee01e156d3bd9c71fc53dd35`;
- that expression is not stored as an accepted founder primitive;
- hidden probes accept it, and a contradictory hidden probe returns a negative result;
- a tampered artifact is rejected on digest mismatch;
- an unvalidated artifact cannot be adopted;
- the adopted extension solves a **maximum**-over-adjacent-transitions task that no founder
  candidate solves, so the second family is not a replay of the creation answer;
- a deliberately weak public episode terminates as `insufficient_evidence` without widening the
  language or the budget;
- a forced post-adoption fault is detected and the exact accepted state restored;
- the manifest is deterministic, digest
  `6bbf98db8fc7e7bf66638aedae78352b65d24a6cdfb99edbfc3eb3c803d45a09`;
- repository, network, credential, deployment and production authority remain absent.

## Claim boundary

The founder language cannot express any operation over adjacent elements: its transforms are
element-wise or set-valued and its reductions are whole-sequence. The capability gain is
therefore structural rather than a matter of degree, and this is the substance of the result.

The mechanism that obtains it is not. The accepted extension is selected by exhaustive filter
over 16 materialised programs — the same select-from-a-finite-set shape as M049 (1 of 4), M050
(1 of 24), M051 (1 of 80) and M052 (1 of 38 classes), raised one level. The protocol permits a
bounded meta-language for describing safe extensions, and the concrete expression is produced
only after the limitation is observed, so M053 satisfies its own anti-cheating rules.

**Whether that constitutes the rupture D016 demanded is settled, and negatively.** M054 removed
the catalogue and constructed from formation rules; M055 put that construction inside the
migrated M048 body and its ablation showed the acquisition buys search cost, not expressive
power. **D019** closes the line and records that M053 may not be cited as evidence that the
lineage grew a capability.

M053 is noncanonical. **M042 remains the only positive canonical continuous-lineage
completion.**
