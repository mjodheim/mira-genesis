# M041 canonical result — negative before migration

**Scientific outcome: negative.**

M041 asked whether one frozen lineage could satisfy all ten Genesis gates, including passive
resource-limited candidate validation before post-migration adoption. The unique sealed run did
not reach that boundary: its fresh cumulative pre-migration lineage failed while generating the
third hidden task.

## Immutable identities

| Identity | Value |
|---|---|
| Frozen parent | `9bb971ef9c997c55326cb8a338bb6496fc26e8e6` |
| Marker-only arming head | `6c404f7fce00087048dcb7d6e346bd5c84308cf8` |
| Frozen protocol SHA-256 | `473daec4a372d5fa2e7d23870040c97e03d4e934c191afa2e8bf0a07d0bc6291` |
| Sealed completion seed | `4616374729204286922` |
| Sealed-spec digest | `bdc6656c65f663ac80d09f0a656d5ac1d646717eaa60881ad53782a825d8ee19` |
| First canonical workflow run | `30937650241` |
| Workflow artifact | `8903789752` |
| Artifact archive digest | `sha256:bd2be6af5087788c985833f792edf255c5a180b74194fb480eadba855e3cb888` |
| Exact JSON SHA-256 | `f62a74b80df7629106de22db8058ac8fc1154e0b998dfda47c5ad4f2eee9a3fe` |
| Exact JSON bytes | `1,842` |

The exact first result is committed as `results/artifacts/M041_CANONICAL_RESULT.json`.

## Falsifier reached

The engine returned:

`cycle 3 task generation found no tool-dependent target`

The failure occurred in the inherited M039 cumulative-lineage generator before opaque-substrate
migration, post-migration rewriting or M041 isolated validation. The sealed seed generated two
usable improvement cycles but the third cycle's finite search found no admissible target that
required the lineage-owned tool under the frozen mechanism.

## Gate interpretation

Because the single lineage did not complete its frozen prerequisite history, none of the ten
gates is credited in the combined M041 result. This does not revoke the separate positive
canonical evidence from M038, M039 or M040, and it does not contradict the positive M041
consumed development result. It shows that the exact one-lineage completion construction is not
robust across this sealed seed.

The result specifically identifies a generation-coverage failure:

- the isolated-validation mechanism passed development controls;
- the default M040 path remained unchanged;
- the frozen canonical runner and marker guard operated correctly;
- the sealed cumulative generator could not always construct its third required tool-dependent
  task.

## Scientific consequence

M041 may not be rerun with another seed, wider enumeration or relaxed criteria. Any repair must
be a separately named experiment with a new pre-result protocol.

The next legitimate experiment should test a generator chosen before measurement for
**constructive availability**: every cycle must derive an admissible, genuinely new,
tool-dependent target by construction while preserving hiddenness, equal-budget ablations and
seed-only replay. It must not select or tune that repair using the M041 seed beyond the recorded
failure class.

## Scope

This is a negative bounded-DFA completion result. It says nothing about arbitrary code,
general intelligence, consciousness or production autonomy. The explicit human release
boundary remains unchanged.
