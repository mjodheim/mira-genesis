# M067 — bounded opaque body-contract discovery

**Status: PASSED LOCALLY; EXACT-COMMIT QUALIFICATION PENDING.**

## Research question

Can the inherited M048 version-eight lineage recover enough of an undisclosed target-body contract
to preserve its four accepted skills, using public behaviour alone, and can that procedure succeed
uniformly across a precommitted class of structurally different contracts?

M067 is a successor to M066 only because it removes a material handhold: M066's whole-body ABI and
compiler were known and authored. M067 never supplies a complete target adapter to the discoverer.

## Opaque boundary

`metamorphosis/m067_opaque_body_runtime.mjs` owns four contracts behind these handles:

- `body-0d62a9c8`;
- `body-3f91e574`;
- `body-71bc406e`;
- `body-c4a28f13`.

The body-bank commitment is
`019c70ec4ec82e45747cabf495ef4778a52b76036d6f3292217d91187c5fbfe3`.
Attestation returns only handles, the bank commitment, individual opaque digests and
`contract_descriptors_disclosed: false`. Public and hidden transaction modes return only an
attempt identifier, acceptance bit and optional raw four-byte reply. The runtime imports crypto
only and holds no filesystem, network or repository authority.

## Frozen candidate grammar

The anchor search contains exactly **288** candidates:

`3 frame families × 2 checksums × 4 opcodes × 3 reply offsets × 2 byte orders × 2 transforms`.

The dimensions are:

- frames: `register`, `stack`, `mailbox`;
- checksum: seeded XOR or seeded sum;
- opaque operation bytes: `0x11`, `0x29`, `0x43`, `0x67`;
- reply offsets: 0, 1 or 2 in a four-byte reply;
- byte order: little or big endian;
- transform: identity or XOR `0xa5a5`;
- signed fixed-point result scale: 300.

After the `add` anchor fixes framing and reply decoding, the remaining three operation bytes are
permuted over `max`, `mean` and `mul`. This yields six complete candidates per anchor survivor.
The runtime caps every batch at 50,000 attempts.

## Evidence separation

Targets are observed by executing the inherited M048 version-eight body. They are not computed
from the semantic names carried in its module declarations. The four skills are `add`, `max`,
`mean` and `mul`, with five public cases each: **20 public observations**.

Discovery has no hidden-case parameter. A separate process mode owns three disjoint cases per
skill: **12 hidden observations**. D021 applies to the entire public equivalence class: every
survivor must pass every hidden case before the smallest adapter digest may choose a representation.

## Controls

For every body, the protocol requires:

- a complete default adapter to fail;
- discovered framing with default semantic opcode order to fail;
- an empty transcript to return `insufficient_evidence` with no adapter;
- a transcript with one corrupted expected value to return no survivor;
- a semantic opcode mutation to fail independent hidden validation.

## Qualification rule

M067 is qualified in development only if the complete Python 3.11 and Python 3.13 GitHub matrices,
repository integrity and attribution checks pass on the exact documented commit. Local success is
development evidence only. M067 is not a canonical experiment and does not reopen or replace the
M066 canonical result.

## Frozen identities and boundary

- executable protocol digest:
  `79447865ea7af9c47d482cbc4deb297d469fd07ab9c6c6b364a8be04ed305c91`;
- candidate grammar: finite and authored;
- body bank: four contracts, authored and committed;
- complete target adapters handed to discoverer: no;
- arbitrary unknown-body adaptation claimed: no;
- repository, network, credential and deployment authority: none.

The supported claim, if qualified, is bounded discovery across this committed contract class. It
does not establish arbitrary device adaptation, general compiler synthesis, open-ended evolution,
general intelligence or consciousness.
