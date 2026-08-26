# Genesis II — reproducibility

## Runtime and external-call boundary

M107–M111 were materialized under canonical **CPython 3.11.16**. Their qualification executions record zero model calls, zero network calls, and zero remote-execution calls, and their checkers recompute the relevant boundary conditions rather than trusting prose assertions.

**M112 is intentionally different.** The M110/M111 tested apparatus still performs zero model/network/remote calls during qualification, but the held-out bank is created beforehand by exactly **one** isolated generator invocation:

- model: `qwen2.5:1.5b`;
- model blob prefix: `183715c435899236…`;
- runtime: Ollama `0.32.15`;
- image prefix: `ollama/ollama@sha256:57d60e686821ea81…`;
- sole qualifying input SHA-256 prefix: `191dfb19636bb5d6…`;
- one invocation, `done_reason=stop`, 5,488 tokens, 617 s;
- 100 emitted records, materialized as 20 five-record worlds because of the preserved pre-seal count defect.

The one generator call is an instrument for world authorship, not part of the claimed lineage.

## Replaying M107–M111

Each milestone has a checker that recomputes predicates from the preserved result and a replay mode that re-runs the canonical mechanism and compares a stable projection. Examples:

```bash
python scripts/check_m107_result.py --replay
python scripts/check_m108_result.py --replay
python scripts/check_m109_result.py --replay
python scripts/check_m110_result.py --replay
python scripts/check_m111_result.py --replay
```

The stable projection excludes process IDs, temporary paths, elapsed times, search paths, return codes, and other process ephemera. M110 and M111 pre-freeze rehearsals predicted their stable evidence digests from a throwaway CRLF checkout; the canonical results reproduced those predictions byte-for-byte.

Key raw predecessor bindings:

| artifact | raw SHA-256 |
|---|---|
| `experiments/M109/RESULT.json` | `0af98fb45a279fec9224bddbb4fa069d140cf21e94a3bb00699ba8c85e0c8009` |
| `experiments/M110/RESULT.json` | `163a46dadd815d98d03fede22905a181c4d406a19d391c5ee2631efc3a2488e3` |
| M109 terminal state digest | `5c08fa3036da6a914bf9a0db1ace60da5381c12fe3179e20fa30c8641f29ea38` |

A functionally equivalent rebuild is not accepted as the same lineage: the paper is about continuation through bound state and frozen apparatus.

## Verifying M112

M112 cannot be reproduced by simply calling the generator again. The frozen procedure permits **one** qualifying invocation and `retries_permitted` is false. A second invocation after observing the first bank would be a different experiment.

What a third party can verify instead:

1. the public commit order;
2. the pinned generator identity and sole input;
3. `ISOLATION_ATTESTATION.json`, measured inside the container before invocation;
4. the bank seal and published `sealed_payload_sha256`;
5. that the tested system was frozen while the bank was still unread;
6. the reveal authorization;
7. that revealed plaintext matches the published digest exactly;
8. that the M110 and M111 apparatus are restored unmodified;
9. every M112 predicate recomputed from the preserved result and revealed bank.

Canonical order recorded by M112:

```text
42f0ae0  generator and input frozen
849ee7b  materialization defect recorded, before sealing
e00ddd5  bank sealed; commitment published
50c7a0e  tested system frozen; bank still unread
007ab86  reveal authorized
2c4ffa3  result preserved, before any checker
```

Run:

```bash
python scripts/check_m112_result.py
```

M112's result is **mixed** and must remain so: procedural independence 10/10; diagnosis 24/24; transfer 22/24 under the inherited all-predicates rule. Transfer predicate P1 is an invocation/path artifact. P5 is a real measurement: one blind world has constructive image size 17 at bound 7 and 18 at bounds 9, 11 and 13. Nothing in the publication package changes that result.

Custody is procedural, not third-party: the project held the reveal key. A reader who does not accept project-held custody should treat M112 as evidence about public ordering and generator blindness, not third-party custody.

## What must fail

A valid reproduction path includes deliberate failure modes. The following should fail closed where applicable:

| attempt | expected |
|---|---|
| second canonical attempt | refused |
| second checker materialization where single-use is enforced | refused |
| canonical run on dirty worktree | refused |
| canonical run away from the freeze tag/commit | refused |
| edit to a bound apparatus member | refused |
| truncated/corrupted result | refused |
| evidence edit with recomputed digests | integrity may pass, but at least one scientific predicate must fail |
| M112 second qualifying generator invocation | not a reproduction; violates the frozen no-retry procedure |

## Bound-file digest modes

Later milestones bind JSON evidence by raw bytes and text members by SHA-256 over declared **LF-normalized** content where specified. The digest mode is part of the bound member declaration; a reproducer should not guess line-ending semantics from their checkout.

## Figures

The manuscript figures are downstream visualizations. `figure_data.json` transcribes only values already frozen in result summaries/results. `generate_figures.py` renders those values; it does not re-run, filter, resample, or retune an experiment. The generated PDF figures used by the manuscript are therefore publication artifacts, not scientific inputs.

## Independent reproduction

There is none. The paper must not imply otherwise. The project explicitly retains independent human reproduction and external adversarial audit as unresolved requirements for stronger generality claims.
