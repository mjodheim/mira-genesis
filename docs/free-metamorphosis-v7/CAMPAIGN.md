# Genesis Free Metamorphosis v7 — public campaign chronology

**Snapshot:** 20 September 2026, after canonical Attempt 016 and before canonical Attempt 017  
**Policy:** `GENESIS_FREE_METAMORPHOSIS_RECURSIVE_SEARCH_V7_2026-09-18`  
**Canonical observations used:** 16 / 24  
**Retained generation:** 2  
**Strong cumulative criterion:** 3 / 4 conditions satisfied

This chronology is sanitized. Private source, patches, evaluator cases and operational artifacts remain outside this repository.

## Campaign shape

Attempts 001–006 accumulated plateau evidence without a champion promotion. v7 then produced two distinct champion promotions, followed by bounded neutral-frontier exploration and one later hard-boundary rejection.

```text
pre-v7 retained champion
  |
  +-- A007 PROMOTION
  |      retained generation 1
  |
  +-- A008 neutral
  |
  +-- A009 PROMOTION
         retained generation 2
         |
         +-- A010 neutral depth 1
         +-- A011 neutral depth 1
         |      +-- A012 neutral depth 2
         +-- A013 neutral depth 1
         |      +-- A014 neutral depth 2
         +-- A015 hard-boundary reject
         +-- A016 neutral depth 2 (from A013)
         +-- A017 next: champion
```

## Aggregate retained champion after A009

| Category | Score | Total |
| --- | ---: | ---: |
| code_delegation | 25 | 25 |
| conversation | 15 | 20 |
| execution_personal_read | 2 | 2 |
| memory_media | 15 | 15 |
| personal_read | 20 | 20 |
| personal_write | 35 | 40 |
| self_modify | 20 | 20 |
| system_admin | 20 | 20 |

Warning count: **7**. Remaining aggregate headroom is concentrated in `conversation` and `personal_write`.

## Attempt record

| Attempt | Parent | Verdict | Aggregate effect |
| ---: | --- | --- | --- |
| 001–006 | bounded campaign parents | plateau, no promotion | search evidence accumulated |
| 007 | champion | **promotion** | `execution_personal_read 0/2 -> 1/2` |
| 008 | champion | neutral | no aggregate delta |
| 009 | champion | **promotion** | `execution_personal_read 1/2 -> 2/2` |
| 010 | champion | neutral depth 1 | no aggregate delta |
| 011 | champion | neutral depth 1 | no aggregate delta |
| 012 | A011 neutral | neutral depth 2 | no aggregate delta |
| 013 | champion | neutral depth 1 | no aggregate delta |
| 014 | A013 neutral | neutral depth 2 | no aggregate delta |
| 015 | champion | hard-boundary reject | frozen API test boundary failed |
| 016 | A013 neutral | neutral depth 2 | no aggregate delta |
| 017 | champion | next | generated after A016 |

### A007 — first v7 promotion

High-level mechanism: personal-read content recovery.

- proposal patch SHA-256: `6ec5b824bddcbbc14ab8402b62efbda9f3ad8bc0c696d4d9461e28dbcc06198c`
- transcript SHA-256: `3fe06133516e5e2270d1107a22516f52a0268269448d04d0ddef3b969a6073bb`
- resulting champion tree: `d0ea8db7be26564ebc1adca8e825ab426ff584c3c5d7a3f1efbe646a3e91b864`

### A008 — neutral

An initial malformed proposer output was rejected before evaluator entry; no observation was spent. The conforming canonical output hard-passed with no aggregate delta.

- patch: `a10e76eec82219ff0029e627722e27b43d209ec671054b40a0d7d37f8149c564`
- transcript: `b78866a3d1932c9e3893b42af951bf78c2eeb46b346ab392df2e27d00b742fc7`
- neutral tree: `ae74ec1f56c932de6b1cde98bd95ebbb593f85df5aeaf7b30371a5d5d2637574`

### A009 — second promotion

A pre-evaluation byte-identity newline transport issue was repaired using the preserved raw proposer bytes; no observation was spent by the failed transport run.

- raw patch: `05ed1f53546b1cfe3583db7eb474987d066a9a988a88e5e3686c0b07ce681214`
- transcript: `e4c291a4c3694aaa712bf337101277454dcef6be5a155ccfde44a98a41c39151`
- canonical composed patch: `091585fb830d7ae50a30add742363db735ff277e569fbee29cab7f226835a480`
- resulting champion tree: `8c85b82d6dec7e29c029677f5cd7c6a9e0df466fb5cd831252cdb71b879b4cea`

### A010–A014 — neutral-frontier traversal

A010, A011 and A013 were champion-equivalent depth-1 neutrals. A012 descended from A011 and A014 descended from A013, both reaching depth 2 without losing the retained champion.

- A010 patch `b17868edee6015151dc363f94f0a5d67c723b1276c4444173c0fa254ef27b955`; neutral tree `62d5cbd5e2265dadcc20e3dda522f14d76d80a5b06484fa2e0049fae4db7bf15`
- A011 patch `9295a53cf2bae38a1f61f8b5b2eb37a908fe3b55e7dc40536f36c92e298b0e3f`; neutral tree `618dd6299e8ce962362588f57d9e8a5a27625200ab4fad8a370f90b6e8a3f812`
- A012 canonical patch `52bf897423ef8ffdb8c3930d9a43c2b66ad17653d08234e65252ba023a1ded01`; depth-2 tree `612a227ee1a25c6a5faa10c504e4251bb0fd0ee1c838c14b820250c0091664ee`
- A013 patch `649039a6fef84cdc91b0ed10824bbc3d9b3825ea944aaeb41effde6f1bdb2a54`; neutral tree `6f9f55b7e4b241054e35d57f4971b2aae4e30b5f2fa4262041f38391f22ea72e`
- A014 patch `008443234e9217cba3cc8844cb2c079e3caff0a86c7e0b3d12c4d0b511970d06`; depth-2 tree `0af4c4e54733141d11b3a946fd00ee6152e753cdca822743388c31886c23392e`

A010 had a stale pre-evaluation workflow assertion corrected without spending an observation. A012 had an initial proposer transcript that changed the frozen schema/tournament contract; it was rejected pre-evaluator and the exact canonical prompt was rerun.

These results establish real neutral stepping-stone traversal, not the still-missing neutral-caused promotion.

### A015 — hard-boundary reject

High-level mechanism: credential/client lifecycle invalidation for personal writes.

The descendant failed the frozen hard boundary: **276 tests passed, 13 failed, 1 skipped**. It was not retained or admitted as neutral.

- proposal patch: `869a21fab2bb761cd1e77e5302b610388f5267b59e970a31ed88bb062d0f79a3`
- transcript: `99730f80010727bf709b701b2b0d9bd14c7b6ed1f0a66eb822cc7975563c6cbd`
- rejected descendant tree: `88fdc0cae45e8bfd5fc9e2b1467d023e68f2a92e8f7824278923c28b792e3713`
- canonical result: `48ab3c79dc4e80d4f1c4511c6da39d175621347817de7800875e8c9bf2999031`

### A016 — neutral depth 2

A016 was selected from the A013 neutral at depth 1. Its sanitized hypothesis was to preserve legitimate repeated conversation turns by distinguishing the current channel event by event identity rather than deleting historical turns merely because their text matches the current message.

The descendant hard-passed with **292 tests passed, 0 failed, 1 skipped**, warning count 7, and no aggregate capability delta. It was admitted as a depth-2 neutral, not promoted.

- patch: `7a9403f38ef1615bdbe2894fdfb0296dad69d114e193c086c22c4562d3807cd8`
- transcript: `cf18f80559572cfdaa7ae5fbc7d53041c19305cddaf6999679f27f2380bf8432`
- parent tree: `6f9f55b7e4b241054e35d57f4971b2aae4e30b5f2fa4262041f38391f22ea72e`
- canonical descendant tree: `b49c6f24e0c7624cdf14d098eee004288f2d501b46e4057a7ec0d9010ebd2582`
- neutral id: `neutral-016-b49c6f24e0c7`
- canonical result SHA-256: `d610e7ecdcc8ef2b2b998907601ac02978c9fad9410ee41b2a34b49af4353eb2`
- deterministic tournament score: **206**

This is the third clean neutral-parent traversal in the line and again does **not** satisfy the missing causal-neutral promotion condition.

### A017 — next state

A017 is odd and returns to the retained champion.

- next bundle SHA-256: `82f0597d1aa66662d63c19e91a955223a66b578787aa4ade718a62a55bd1a03b`
- next context digest: `a30f2d6822aa5d1b5232b517fd98cf3d988befc0fa689903b15914074d948fc8`
- next prompt SHA-256: `1a701223279a1098833d6ecd4918f3dab1b119d2f04fda7e244a961aad3ed6da`
- parent kind: champion
- parent tree: `8c85b82d6dec7e29c029677f5cd7c6a9e0df466fb5cd831252cdb71b879b4cea`

#### First A017 proposer output rejected pre-evaluator

The first received A017 transcript was rejected before any external observation because its declared selected candidate was not the deterministic tournament winner under the frozen v7 scoring procedure.

- transcript SHA-256: `59f86a7d03f37624dad5134b960b7d4e66b0eeb312b5ae329ab4a028aaa4ff10`
- declared proposal patch SHA-256: `2ca4fc117985c4f1a30d12703c47ebef04b461b3e6ea9a5339c295c958f46284`
- declared selected candidate: `c01-self-eval-original-turn`
- recomputed ranking: `c03-conversation-long-horizon-summary = 197`, `c02-nats-publish-failure-contract = 183`, `c04-stream-conversation-id-early = 183`, `c01-self-eval-original-turn = 172`
- evaluator observations spent by this output: **0**
- campaign attempts used remain: **16 / 24**

The output is not an A017 scientific result and is not eligible for repair by editing the transcript after the fact. A fresh proposer output must satisfy the same frozen A017 prompt and tournament contract.


#### Second A017 proposer output rejected pre-evaluator

The second received A017 output supplied a matching patch, but the transcript again changed the frozen v7 transcript/tournament contract. It used `mira-free-metamorphosis-proposer-transcript-v7` with proposer-defined `tournament`, custom per-candidate score fields and candidate fields that do not match the frozen `research_tournament` schema. The laboratory therefore rejected it before deterministic tournament verification or external evaluation.

- transcript SHA-256: `7f242b7c21b6160515bfc3ecf0ab1d43685683724979462bdfb27ad025d73dd2`
- proposal patch SHA-256: `942bf77ebc3608623baecbb47917cdf7251eb2a0bdc7d33f480b7a219ba09b01`
- patch bytes: **2185**
- transcript bytes: **11294**
- declared hypothesis: expose the existing Drive folder-creation side effect as a bounded personal-write tool
- evaluator observations spent by this output: **0**
- campaign attempts used remain: **16 / 24**

The patch is not eligible for canonical evaluation without a fresh proposer transcript produced under the exact frozen A017 contract; the laboratory does not rewrite malformed proposer output into compliance after the fact.


#### Third A017 proposer output rejected pre-evaluator

The third A017 output restored the exact frozen external transcript v3 schema and supplied a matching patch, but failed deterministic tournament selection. The frozen scorer ranks a different candidate first.

- transcript SHA-256: `f26520ee67df6aeb49e0b3654caf64ce58d39eb58404a0cedc7b1dea7351de63`
- proposal patch SHA-256: `1de7cdf9f055fb82d55985dff67c5809aaa0ae5be7ad0a60d2ebf11b97a52fed`
- declared selected candidate: `c01-conversation-memory-commit`
- frozen recomputed ranking:
  1. `c05-personal-write-delivery-receipt = 240`
  2. `c02-conversation-postgres-title-parity = 226`
  3. `c01-conversation-memory-commit = 220`
  4. `c04-personal-write-drive-upsert = 200`
  5. `c03-conversation-stream-turn-commit = 180`
- evaluator observations spent by this output: **0**
- campaign attempts used remain: **16 / 24**

Because the patch implements c01 rather than the deterministic winner c05, the laboratory cannot repair the transcript or substitute a different winner after the fact. A fresh proposer run under the unchanged canonical A017 prompt is required.


#### v7.1 control-plane repair before A017 retry

The three pre-evaluation A017 failures exposed a proposer-information defect: the prompt required the exact deterministic tournament rubric to be read from `proposal-context.json`, but the distributed context serialized the research memory and weights without serializing the scoring formula itself.

The laboratory scorer, strategy weights, research memory, evaluator and budget remain frozen. The repair is disclosure-only and consumes **0** observations. The exact scorer has been reconstructed against the third rejected A017 tournament and reproduces the frozen ranking bit-for-bit at the integer-score level: `240, 226, 220, 200, 180`.

- erratum: `ERRATUM_V7_1_TOURNAMENT_RUBRIC.md`
- canonical observations remain: **16 / 24**
- A017 parent remains: retained A009 champion
- prior A017 bundle: retained as historical evidence, not to be reused for a fresh proposer run
- repaired control head: `547a9fd4487556c978b43946e1b48c11f928d127`
- frozen scorer blob remains byte-identical: `fc9bdfac7171a18dde275ac1d3b9d01e9650571c`
- repaired A017 context digest: `e3219bb8d190a1378e8d8c0eadaa6d5d15b4384c4d08c0be6227b5d1ee51ed67`
- repaired A017 prompt SHA-256: `31abdb630d8428a0a3d2bdc1c6ba72bd2dabd63f80caba2e539073f15e741153`
- repaired A017 bundle SHA-256: `09d182e9516eae303f1d14bd0f92aba6df42edef6af5b6d5ddc913366b6bf96e`
- next action: run a fresh external proposer against the repaired bundle; do not reuse any prior A017 patch/transcript

No rejected A017 transcript or patch is repaired in place.

## Strong cumulative criterion after A016

| Condition | Status |
| --- | --- |
| at least two champion promotions | **satisfied** — A007, A009 |
| promotion causally through an admitted neutral | **not yet satisfied** |
| post-bootstrap proposal selected under a strategy descendant generated from new v7 evidence | **satisfied** |
| later bundle inherits promoted champion | **satisfied** |

Correct reading after A016: **3/4**, not completion.
