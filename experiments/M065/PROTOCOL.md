# M065 — corrected qualification protocol

**Status: NEGATIVE CANONICAL GUARD QUALIFICATION. CLOSED BY M066.**

M065 is the required successor to the failed M064 freeze candidate. It changes no task bank,
budget, threshold, substrate, candidate grammar or four-arm decision rule.

## Preserved negative evidence

M064 frozen parent `ec92af78b57203d32c2ee504db91b4166ec83fdf` failed GitHub qualification
run `31281234286`, attempt 1. Both Python versions passed 1,084/1,085 tests and rejected the same
checkout-dependent source commitment. GitHub review then identified that M064's forced rollback
compared its untouched saved input to itself. No M064 marker was created and no canonical task bank
was selected.

## Corrections

M065 makes exactly three corrections:

1. the forced corrupt staged state must differ from the pre-transaction state;
2. rollback must deserialize the pre-transaction canonical bytes into the state actually returned,
   audit that object, and compare its digest to the pre-fault commitment;
3. the canonical marker must be its first occurrence anywhere in path history, while the
   first-result job is permitted only when `github.run_attempt == 1`.

The first two are the scientific reason for the new experiment number. The third closes the two
governance defects found before any canonical execution.

## Unchanged decision rule

- continuous CPython v6 → Node ESM v8 → whole-WebAssembly v9 lineage;
- four equal-budget arms and three post-migration cycles;
- 8,192 candidates per arm and cycle;
- entire public survivor class admitted before digest selection;
- complete lineage must pass 18/18 hidden observations and strictly exceed every control;
- all retained capabilities, exact archives, journal chain, causal memory and replay must pass.

The executable protocol digest is
`1057daa152c554bff88a150c757c7f2864b23beda08a5a5f3d7112409f78aa51` and the unchanged task-bank
commitment is `7134e3f0ce4c3e84ccb52834bea08ce41501104e1c76245b1e97e2c1981a33da`.

## Canonical boundary

Development evidence is not canonical. The exact parent must first pass the complete local suite,
repository integrity, the portable 22-file commitment audit and the Python 3.11/3.13 GitHub
matrix. Only then may a first-history marker-only commit select one bank. A failed first result or
byte reproduction is preserved and requires M066 for any scientific repair.

The exact parent passed qualification run `31286019961`, attempt 1. Marker commit
`a517e6bb76e8476ab6aca8c0a68c5bcfc3501d57` triggered canonical run `31287477458`, attempt 1.
Guard job `93178824313` rejected the marker because frozen `git rev-list --all` counted both the
canonical commit and its still-fetched pull-request branch occurrence. The first-result and
reproduction jobs were skipped; no bank or artifact exists. M065 is not rerun. D025 requires M066.
