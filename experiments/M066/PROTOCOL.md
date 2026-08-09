# M066 — canonical-history governance correction

**Status: POSITIVE CANONICAL. CLOSED.**

M066 is the required successor to the negative M065 canonical attempt. It changes no task bank,
budget, threshold, substrate, candidate grammar, rollback mechanism, evidence case, arm or
scientific decision rule.

## Preserved negative evidence

M065 parent `b1489d7a3a264de8a9e783eb139dafe28732b040` passed qualification run
`31286019961`, attempt 1. Marker commit `a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57`
then triggered canonical run `31287477458`, attempt 1. Guard job `93178824313` failed before task-bank
selection because the frozen workflow ran `git rev-list --all` after fetching all references. The
unmerged pull-request branch and canonical `main` commit both contained the marker addition, so a
lateral ref was misclassified as a second canonical occurrence. The first-result and reproduction
jobs were skipped. No bank was selected and no canonical artifact was created. The run is not
rerun or repaired.

## Sole correction

M066 counts marker occurrences only along the first-parent history of the pushed `main` head:

```text
git rev-list --first-parent HEAD -- experiments/M066/CANONICAL_ARMED.json
```

A marker introduced, changed, deleted or re-added on canonical history is still rejected when the
count differs from one. A same-path commit reachable only from a lateral pull-request ref does not
belong to canonical history and cannot block the run. A permanent Git graph test proves both
counts against the same repository.

## Unchanged decision rule

- continuous CPython v6 → Node ESM v8 → whole-WebAssembly v9 lineage;
- four equal-budget arms and three post-migration cycles;
- 8,192 candidates per arm and cycle;
- complete lineage must pass 18/18 hidden observations and strictly exceed every control;
- all retained capabilities, exact archives, journal chain, corrected rollback, causal memory and
  replay must pass.

The executable M066 digest is
`f66ab480dfa0631e730753b7e45e3b83da7e2938d3e28e4aa2f497a6e383d66b`. The portable 23-file
commitment has file SHA-256
`02cabd7d86a93ceaba811b591b6c271cf066653add61044af83143558e2fd1c0`. Development evidence
cannot arm the canonical workflow.

## Canonical boundary

The exact frozen parent must pass the complete suite, integrity and Python 3.11/3.13 qualification.
Only a subsequent marker-only commit may run a first Python 3.11 result on workflow attempt one.
Python 3.13 must consume that artifact and reproduce its exact bytes. Any M066 failure is preserved
and requires a new successor; M066 is never rerun into success.

Canonical run `31291899534`, attempt 1, passed this boundary without repair or rerun. Bank index 0
was selected, the first result was preserved and Python 3.13.14 reproduced its exact bytes. The
experiment is closed; see `STATUS.md` and `results/M066_CANONICAL_RESULT.md`.
