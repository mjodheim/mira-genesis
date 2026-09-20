# Genesis Free Metamorphosis v7 — public campaign chronology

**Snapshot:** 20 September 2026, after canonical Attempt 015 and before canonical Attempt 016  
**Policy:** `GENESIS_FREE_METAMORPHOSIS_RECURSIVE_SEARCH_V7_2026-09-18`  
**Canonical observations used:** 15 / 24  
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
         +-- A016 next: selected from A013 neutral
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
| 016 | A013 neutral | pending | event-identity conversation hypothesis |

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

### A016 — pre-evaluation state

A016 is selected from the A013 neutral at depth 1. Its sanitized hypothesis is to preserve legitimate repeated conversation turns by distinguishing the current channel event by event identity rather than deleting historical turns merely because their text matches the current message.

- patch: `7a9403f38ef1615bdbe2894fdfb0296dad69d114e193c086c22c4562d3807cd8`
- transcript: `cf18f80559572cfdaa7ae5fbc7d53041c19305cddaf6999679f27f2380bf8432`
- context: `25bc01451cbbd004c211977119de9560ff02077db5b396bc1b608dc5f7e0f213`
- prompt: `1e9b0cae278444648439bbd3021a02738ee4b53feeef9fc5a24bb75db1ed7f1c`
- parent tree: `6f9f55b7e4b241054e35d57f4971b2aae4e30b5f2fa4262041f38391f22ea72e`
- deterministic tournament score: **206**

No A016 result is claimed in this snapshot.

## Strong cumulative criterion after A015

| Condition | Status |
| --- | --- |
| at least two champion promotions | **satisfied** — A007, A009 |
| promotion causally through an admitted neutral | **not yet satisfied** |
| post-bootstrap proposal selected under a strategy descendant generated from new v7 evidence | **satisfied** |
| later bundle inherits promoted champion | **satisfied** |

Correct reading: **3/4**, not completion.
