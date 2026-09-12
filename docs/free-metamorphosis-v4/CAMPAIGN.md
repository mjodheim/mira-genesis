# Genesis Free Metamorphosis v4 — public campaign chronology

**Snapshot date:** 12 September 2026  
**Policy:** `GENESIS_FREE_METAMORPHOSIS_OPEN_EMPIRICAL_V4_2026-09-12`

This is the sanitized public chronology for the private-host v4 campaign. Raw proposals, source paths, evaluator cases and operational artifacts remain private under P-032.

## Seed geometry

The retained generation-zero organism entered v4 with the following aggregate capability vector:

| Category | Score | Total | Headroom |
| --- | ---: | ---: | ---: |
| code_delegation | 4 | 5 | 1 |
| conversation | 2 | 4 | 2 |
| memory_media | 3 | 3 | 0 |
| personal_read | 3 | 4 | 1 |
| personal_write | 3 | 8 | 5 |
| self_modify | 3 | 4 | 1 |
| system_admin | 4 | 4 | 0 |

Warning count at seed: **7**.

Generation-zero tree digest:

`f597e8020ee06f02a93fd5b6cdbf4a4bf0c362de5983cb51e21ce81a33d2cc5d`

The seed passed the frozen hard external boundary. The vector deliberately retained headroom on multiple categories so selection could distinguish useful descendants without exposing individual evaluator cases.

## Lineage

```text
Generation 0
f597e802…
    |
    | Attempt 001
    | +1 personal_write
    | retained
    v
Generation 1
b720efef…
    |
    +---- Attempt 002
    |     aggregate delta = 0
    |     neutral archive: 94d41880…
    |     retained parent unchanged
    |
    +---- Attempt 003
    |     aggregate delta = 0
    |     neutral archive: d6c70542…
    |     retained parent unchanged
    |
    +---- Attempt 004
          in progress at this snapshot
```

## Attempt summary

| Attempt | Parent | Result | Aggregate fitness effect | Inherited? |
| --- | --- | --- | --- | --- |
| 001 | generation 0 | Pareto improvement | `personal_write 3/8 -> 4/8` | **yes — generation 1** |
| 002 | generation 1 | non-regressing neutral | no aggregate category or warning delta | **no — archived only** |
| 003 | generation 1 | non-regressing neutral | no aggregate category or warning delta | **no — archived only** |
| 004 | generation 1 | in progress | not yet observed | pending |

### Attempt 001 — first retained v4 descendant

The proposal tested a least-privilege hypothesis for explicit personal-write actions without broadening ordinary conversational authority.

Public identity anchors:

- proposer-bundle SHA-256: `fe9075eb9539aa4acfc83351653b42830ca41d035b899dafe6e1b1fc04c42e9e`
- proposal-context digest: `b62301533ff3ae697beb830724b00b6f29a48d9f4044432627ae5736a5f882d1`
- proposal-patch SHA-256: `339b85dbefb61f97b8463e7685ec5ca677c1ceea8db07ca3ac5070162e872d4f`
- changed-path count: `3`
- child tree digest: `b720efef4e9550b7156d05a10a828d8196fb3333a040a0e55a19b43998f918a2`
- observation digest: `cc816977ae1f507691ba9a728b208effedd099c97374ef9db6c202f51b7d5868`
- ledger record digest: `33779c436be6eab1631966e065e239e5955e49868b905ebd2320ad186a3c2084`

Decision:

> `Pareto improvement on frozen external capability vector`

The descendant preserved every other aggregate category and increased `personal_write` from 3/8 to 4/8. It therefore became retained **generation 1**.

### Attempt 002 — first neutral empirical branch

Attempt 002 started from generation 1 and tested a bounded conversational-continuity hypothesis on the primary generation path.

Public identity anchors:

- proposer-bundle SHA-256: `cc397b991910dc2077343ac7a7c9c104c2499a2156529d554ea65f7e7e92ebd5`
- proposal-context digest: `24e737d655bccc862fdaa6ff709dfb0e2f8110dc61685e29f2b43970e0c542c4`
- proposal-patch SHA-256: `4646607db8d77b853f4407b1f45da08717b72d59f85c3b816bb0f436d8d2362d`
- changed-path count: `1`
- candidate tree digest: `94d418801a4ed9cbfe771d8436f4b685ebdcaa87fdb28fe3ea6ae4ac9d48e88a`
- observation digest: `de0e71ea10b587a5bd1889d75117be02a4fe79aaa0c841a101aa2ff05507d2f5`
- neutral-archive record digest: `4164e9156153bbfebcfc4bc24454cbf8d2422a73939b81b106342ba1c783470a`

Decision:

> `non-regressing neutral innovation archived; retained parent unchanged`

All protected aggregate scores and the warning count remained unchanged. The candidate was preserved as neutral empirical memory but did not become an ancestor. Generation 1 remained the retained parent.

### Attempt 003 — second neutral empirical branch

Attempt 003 again started from retained generation 1. It tested a narrow personal-read reliability hypothesis: accept an opaque service-provided cloud-file identifier as well as an exact filename, without broadening tool authority.

Public identity anchors:

- proposer-bundle SHA-256: `323e78aecb41245319e6c2a92e0b7ddafb75fbc7d099784196237e44e15884ad`
- proposal-context digest: `c15fd7e3fbab74f487af76bde0c87822335fff08d23a35eefdd39c2fa91194ce`
- proposal-patch SHA-256: `8759c5e939e1f04e6312230d78e808c3d524ae548891bbe09a9bac0469748879`
- changed-path count: `2`
- candidate tree digest: `d6c705422d6bb797fb31ef964f7f04ffdd0a9db522a6dc82e898e81225e7023d`
- observation digest: `cfe278116c2080d249c6afad0e26369ce8763b42eae6e4385cf323282b9e2f41`
- neutral-archive record digest: `2b6d6ff98368da87ba64d3cc3db76bb371e67e81ea499162b668727b0c0c105b`

Decision:

> `non-regressing neutral innovation archived; retained parent unchanged`

Every aggregate capability category and the warning count remained unchanged. The candidate was therefore archived as empirical memory and did not become an ancestor.

### Attempt 004 — next branch from retained generation 1

The proposer bundle for attempt 004 was generated only after attempt 003 had been recorded. Its SHA-256 is:

`6cf5914d86c6ff3b3cf986c7394321f31e96fd3cfb08a643f2236d24e4eceadd`

Its proposal-context digest is:

`95b18db22096c010081c2a56a2dbfb19a10b8144fd44e5499dbbec600342a1d7`

The bundle starts from retained generation 1, not from either neutral candidate. Its bounded aggregate history includes one retained improvement and two neutral hypotheses without exposing individual evaluator cases.

At this snapshot, attempt 004 has **no scientific verdict yet**.

## What has been established so far

The campaign has demonstrated one full real-host v4 transition:

`external variation -> external measurement -> selection -> retained descendant -> next proposer starts from descendant`

It has also demonstrated repeated neutral-memory paths:

`external variation -> hard pass -> no positive/negative aggregate delta -> archived empirical memory -> no ancestry change`

This is stronger than a sequence of unrelated patch evaluations because the retained-generation identity controls the parent of every later proposal, while rejected-but-safe neutral hypotheses remain available as bounded empirical memory.

It is still far short of open-ended evolution. The next important evidence would be a second retained generation, especially where a later retained improvement causally depends on the earlier inherited generation-1 change.

## Publication boundary

The values above are non-confidential aggregate measurements and cryptographic commitments. The corresponding private parent archives, patches, evaluator cases, source paths and raw logs are intentionally not published.
