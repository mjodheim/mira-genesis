# Genesis II — reproducibility

## Runtime

CPython **3.11.16** is the canonical frozen runtime for every milestone on this line, not a
preference. Results were materialized under it and the checkers refuse any other version.

No milestone on this line makes a model call, a network call or a remote-execution call. Every
canonical result records all three as zero, and the checkers compute it rather than assert it.

## Replaying a milestone

Each milestone has one independent checker that recomputes its predicates from the preserved result
and, with `--replay`, re-runs the experiment and compares stable projections:

```bash
python scripts/check_m110_result.py --replay
```

```bash
python scripts/check_m111_result.py --replay
```

A replay compares a **stable projection** that excludes PIDs, search paths, return codes, elapsed
times, temporary paths and interpreter versions. It should be byte-identical on any machine running
the canonical interpreter over the same population and apparatus.

## What must fail

A reproduction that cannot fail is not one. Each of these is expected to exit non-zero:

| attempt | expected |
|---|---|
| a second canonical attempt | refused, failed closed |
| a second checker report | refused, failed closed |
| any canonical run on a dirty worktree | refused, failed closed |
| any canonical run at a commit that is not the freeze tag | refused, failed closed |
| a bound apparatus member edited after the freeze | refused, failed closed |
| a truncated result | refused, failed closed |
| a result whose evidence is edited **and whose digests are recomputed** | integrity passes, a **predicate fails** |

The last row is the one worth exercising. It is what distinguishes a claim carried by measurements
from one carried by hashes over them, and it was exercised in the pre-freeze rehearsal of both
milestones.

## Verifying the lineage rather than a rebuild

M110 and M111 restore their predecessors from frozen bytes and refuse unless the reconstruction
reproduces the digests the predecessor recorded. The checkers bind the raw SHA-256 of those files:

| | |
|---|---|
| `experiments/M109/RESULT.json` | `0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009` |
| `experiments/M110/RESULT.json` | `163a46dadd815d98d03fede22905a181c4d406a19d391c5ee2631efc3a2488e3` |
| M109 terminal state digest | `5c08fa3036da6a914bf9…` |

A functionally equivalent rebuild of M109 would fail these checks. That is deliberate: the claim is
about a continuation, not about a system that happens to behave the same way.

## Bound-file digest modes

Protocols bind JSON evidence by **raw bytes** and Python and Markdown members by SHA-256 over
**LF-normalized** content, with the mode recorded per member. A third party recomputes exactly what
was frozen instead of guessing which their checkout produced. Pre-freeze rehearsals were run in
throwaway clones checked out with `core.autocrlf true` for that reason, and both milestones predicted
their stable evidence digest before the freeze; both predictions held byte for byte.

## Independent reproduction

There is none, and the package must say so. `MIRA_GENERALITY_CRITERIA.md` requires independent
reproduction and an external adversarial audit for any general-agent claim; neither exists, and no
sentence in the paper may imply otherwise.
