# M021 — Status

**DEVELOPMENT RIG HARDENING**

M021 asks whether four selection measures move an exact, hidden ground truth rather
than merely improving their own scores.

## Implemented

- four rankers: objective, novelty, niche-first quality-diversity approximation and
  minimal criterion;
- M019's longer selection horizon correction;
- common random numbers for paired measures at each seed;
- exact held-out verification;
- non-mutating deep-copy audits;
- separate adaptive and frozen held-out quality;
- a 24-paired-seed minimum before comparison;
- a 100-per-mille development separation floor;
- targeted unit tests and a dedicated development workflow.

## Not done

- no full 24-seed comparison has been recorded;
- no raw development artifact is versioned;
- no uncertainty estimate or frozen decision rule exists;
- the quality-diversity row is not a persistent MAP-Elites archive;
- no protocol is frozen or hashed;
- no canonical workflow exists or is authorised.

## Current scientific status

**No conclusion.** A three-seed run is only a smoke test. M021 remains a rig under
construction until the paired comparison and its per-seed diagnostics have been
examined.
