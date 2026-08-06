# M050 — bounded composition of migration primitives

**Status: PASSED IN DEVELOPMENT after one preserved failing qualification run.**

## Question

M049 selected one complete strategy from four frozen alternatives. M050 asks the next narrower question: can public evidence determine one pipeline assembled from separately frozen input, reduction, and empty-input primitives, while an independent validator retains exclusive access to hidden evidence?

## Frozen construction

The composer explores exactly 24 pipelines:

- input: `identity`, `absolute`, or `unique`;
- reduction: `maximum`, `minimum`, `sum`, or `mean_floor`;
- empty input: `zero` or `reject`.

Every pipeline contains exactly one primitive from each family. The composer may not invent primitives, change their order, widen the budget, generate source code, access hidden probes, or discover a runtime.

## Preserved qualification history

CI run `31083479890` (run number `410`) on commit `3bc3b50` failed in both Python matrices while repository integrity passed. The frozen positive episode expected outputs that required applying both `absolute` and `unique`, although the declared grammar permits exactly one input primitive. Consequently no pipeline survived and five M050 tests failed. This negative result is retained as evidence of a protocol-fixture mismatch rather than erased or rerun.

The correction changed only the public and hidden probes so they uniquely identify the already-declared `unique + sum + zero` pipeline. It did not add primitives, enlarge the 24-candidate budget, weaken validation, or reinterpret the failed run.

CI run `31087299169` (run number `413`) on corrected commit `c75e9e70a48b382feeacefdca3d5b5e85d390d46` then passed:

- 822 tests on Python 3.11 with Node.js 20.20.2;
- 822 tests on Python 3.13 with Node.js 20.20.2;
- repository integrity, clean imports, orphan detection, and dependency consistency;
- no failed job and no rerun of either failing commit.

## Episodes

The permanent experiment includes:

1. a positive public episode that uniquely composes `unique + sum + zero`, followed by independent hidden acceptance;
2. an ambiguous public episode that must terminate as `insufficient_evidence`;
3. a unique public composition followed by a contradictory hidden probe that must be preserved as an independent rejection.

## Integrity and authority boundaries

Primitive, pipeline, composition, evidence, verdict, and manifest artifacts are domain-separated and content-addressed. Altered or out-of-family artifacts fail closed.

The experiment has no repository, network, credential, deployment, or production authority. It does not perform arbitrary code generation, unknown-runtime discovery, unrestricted compiler synthesis, open-ended evolution, or general intelligence.

## Qualified result

Within the fixed grammar and probe family, M050 establishes:

- deterministic exploration of exactly 24 frozen pipelines;
- unique public-only composition when evidence is sufficient;
- explicit failure on ambiguity and contradiction;
- independent hidden validation without adoption authority;
- preservation of a negative hidden verdict;
- rejection of tampered artifacts;
- deterministic replay and explicit claim boundaries.

## Claim boundary

The positive result applies only to this fixed three-stage grammar and fixed arithmetic probe family. It does not establish general program synthesis, arbitrary compiler construction, autonomous substrate discovery, production safety, or canonical continuous-lineage evidence. M042 remains the only positive canonical continuous-lineage completion.
