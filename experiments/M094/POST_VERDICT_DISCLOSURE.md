# M094 — post-verdict disclosure, and the attempt it withdrew

> **Resolved on 19 August 2026 by withdrawal and re-run.** Attempt 1 is preserved at
> `WITHDRAWN_RESULT_ATTEMPT_1.json` and `WITHDRAWN_QUALIFICATION_ATTEMPT_1.json`. The store was
> corrected to adopt and restore in bytes, and **attempt 2** was run at commit `43ef9d30`:
> verdict `positive`, 12 of 12 conditions computed and true, qualification 2/2 satisfied on the
> same draw, and `mira_core/contracts.py` restored to sha `de1034e5…` — the byte-identical CRLF
> original, with `git status` showing the file unmodified.
>
> The account below is attempt 1's, unaltered. It is the reason attempt 2 exists.

---

# The disclosure as written against attempt 1

**Status: the canonical run is complete and the checker's verdict is `positive`, 12 of 12
conditions computed and true. This document records a defect found *after* that verdict, in the
evidence for P11. It is disclosed and deliberately not repaired.**

The protocol's own falsifier list contains:

> a real defect in the system is corrected after the verdict in order to save the result

A verdict now exists. So the defect below is written down and left alone. Whether it is material
enough to withdraw the run is the project owner's decision, not one this document makes.

## The run

| | |
|---|---|
| source commit | `210e8f048e47deb9434df1e10db0e8010a2710e5` |
| protocol | `2d879f2f48e32a91…`, amendments A1–A4 in force |
| pool | `0016300c4064c0ca…`, 8 entries |
| adopted mechanism | `259e12f5cbf86ec7…` — `Goal` and `Observation`, both tied at demand 4 |
| working tree at start | clean |
| model calls / network calls | 0 / 0 |
| attempt | 1, no prior attempts preserved |
| elapsed | 538 s |
| qualification | `positive` — `AgentResult` 10/10 via `as_dict`, `ContainerSpec` 10/10 via `to_dict`, both validator-accepted, cross-component |

## The defect

P11 is *"rollback is exact and behavioural"*. The run recorded, and the checker read:

```
fault_struck_the_live_file:                True
damage_was_behavioural:                    True
restoration_is_byte_exact:                 True
restored_matches_the_original_behaviour:   True
store_version_after_restore:               0
```

Three of those are supported. **`restoration_is_byte_exact` is not**, as its wording claims.

`TransformationStore` reads a component with `Path.read_text(encoding="utf-8")`, which applies
universal-newline decoding and turns `CRLF` into `LF`, and writes it back with
`write_text(..., newline="")`, which performs no translation. Its digest is computed over the
decoded text. So the roundtrip normalises line endings, and the digest compares equal because it
never sees them.

Measured on the run's own target:

| | bytes | sha256 (16) |
|---|---|---|
| `mira_core/contracts.py` before the run | 2356 (CRLF) | `de1034e57cc2d3b1` |
| after adoption and rollback | 2280 (LF) | `69db44dc4f5fabc5` |
| the restored bytes with CRLF put back | 2356 | `de1034e57cc2d3b1` |

The content is identical — `git diff` is empty, the component compiles, and the run verified the
restored behaviour by executing it. What is not true is that the file on disk was restored byte for
byte.

## How much this is, and how much it is not

- **Against the repository's content model, the file is unchanged.** Git stores blobs with `LF`;
  the working tree held `CRLF` because of `core.autocrlf`. `git status` flagged the file, `git diff`
  showed nothing, and the committed blob is the same one it was before the run.
- **Against the on-disk bytes, restoration was not exact.** A claim of byte-exactness is stronger
  than the evidence, and P11 is worded in exactly those terms.
- **The behavioural half of P11 is unaffected.** The fault struck the live file, the damage was
  observable by executing the component, and the restored component behaves as the original did.
  Those were measured by execution, not by digest.

## Why this is disclosed rather than fixed

Fixing it means reading and writing bytes rather than text, and re-running. That would be
correcting a real defect after a verdict in order to save the result, which the protocol names as a
falsifier. The repair is obvious and small; making it now is precisely what the discipline forbids.

The options are the owner's:

1. **Accept the run with this disclosure attached**, on the ground that the repository's content
   model is `LF`, git records no change, and the behavioural half of P11 stands.
2. **Withdraw the run**, preserve it as `WITHDRAWN_RESULT_ATTEMPT_1.json`, repair the store to
   operate on bytes, and re-run. The retry policy forbids a reroll for a better outcome; it does not
   forbid withdrawing a run whose instrument is defective, provided the superseded run is preserved
   and disclosed and the attempt number is derived from the preserved artifacts.
3. **Narrow P11's wording** in a further amendment, from byte-exact to content-exact-and-behavioural,
   which is what the instrument actually measures — and note that this would be amending a condition
   after seeing it pass, which is weaker than either of the above.

## A note on where this came from

This repository has fought `CRLF`/`LF` before: M064 recorded a commitment matching only its CRLF
working-tree copy and was disqualified for it; M086-A repeated it; 34 artifacts were found in the
same state on one day; and this branch added `.gitattributes` protection for two more. Every one of
those was about *artifacts*. This is the first time it has reached the *mechanism* — the rollback
that P11 exists to certify — and it got there because the store measures a file by decoding it.

The working tree was returned to its checked-out state with `git checkout` after the run. That
restores the `CRLF` the checkout had; it does not alter the result, which is preserved in
`RESULT.json`, nor this record.
