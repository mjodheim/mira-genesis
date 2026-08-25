# M111 / H56 — canonical result

> **VERDICT: POSITIVE (attempt 1). H56 supported within its frozen bounds — all three halves. D080.**

Deliberately **outside** the protocol's bound apparatus list, so every bound member keeps the exact
bytes it had at freeze time and `experiment/m111-frozen-protocol-v1` stays verifiable by anyone.

| | |
|---|---|
| frozen protocol | `395b2c3507dc13bb07ae927ecda32febad5b4537a73a356ec670df90a0e66ce1` |
| bound apparatus | `a9ba20f12617d5e89a177e73040e7fd9e14911a3c9c4e5ff97fd647e55de5687` |
| population | `9ee85959f9be39be9c84fa083ac656863380a70dfcddb52bd961623139bc3313` |
| machinery predecessor (M109) | `262e0bd5…`, raw `0af98fb4…` |
| carrier predecessor (M110) | `cbd3ea3e…`, raw `163a46da…` |
| M109 terminal state | `5c08fa3036da6a914bf9…` |
| result | `7b14b07e768b1c9291a069f4198b0b0becd92773d856ef539f48027bdca42cf7` |
| stable evidence | `f77c8b8930e8568dd0f91362b3879e15e5ee5e2faa752367c4671ab4230f327e` |
| raw result bytes | `aa1c8a270a7e4b3c420aa798c67f7ba9ba60f44a7a09b0948d22c3637481165a` |
| check report | `c2109e52faa525b594d8b5e3851701b6db3640053f354f4750c21098515d5638` |
| runtime | CPython 3.11.16 |

P1–P24 all computed true; replay performed and equal; zero model, network and remote-execution calls
across **127 isolated processes** over five worlds in two strata.

**The stable evidence digest is byte-identical to the one `PRE_FREEZE_REHEARSAL.md` predicted before
the freeze**, in a throwaway clone that received the sources with CRLF.

## The exhibit

In each ambiguous world two demands present the machinery with the **identical feature row**
`(F, T, T)` and have **different limiting components**. No function of the feature vocabulary is right
on both. This is an information bound, exhibited rather than argued, and every static arm fails at
least one of the pair — unanimously, on all three ambiguous worlds:

| arm | `A` | `B` |
|---|---|---|
| `M0` hardwired to the operator axis | **0/3** | **0/3** |
| `M1` generation 1 | **0/3** | **0/3** |
| `M2` generation 2, M109's terminal state | **3/3** | **0/3** |
| `always_signal`, an authored fixed strategy | **0/3** | **3/3** |
| **the acquired diagnostic policy** | **3/3** | **3/3** |

## The budget is what makes it a diagnosis

One probe per world, shared across a sequence, and the determined demand comes first:

| arm | `A` | `B` | probes spent |
|---|---|---|---|
| never-probe | 3/3 | **0/3** | 0 |
| always-probe | 3/3 | **0/3** | 3 |
| **acquired policy** | **3/3** | **3/3** | 3 |

Always-probe holds the same budget and spends it on the demand its own record would have told it was
determined. The acquired policy does not fire there, keeps the probe, and spends it where its record
says it does not know. Both probe orders give the same result, which is how the order is shown to
carry no answer.

## Recursive depth three, by lemma

| | |
|---|---|
| pooled record | **19 episodes from 5 worlds**; undetermined `[3]`, determined `[1, 5, 7]` |
| policy rule space at `M1` | **18**, separating programs **0** |
| policy rule space at `M2` | **127**, separating programs **25** |
| generation 3 | acquired, 7 consistent policies, fires on rows `[2, 3]` |
| generation 2 ablated | **refused** — `no_expressible_policy_and_no_operator_makes_one_expressible` |

The policy must fire on row 3 and not row 7. Row 3 lies below row 7 componentwise, so every monotone
program true at the lower row is true at the upper one. M109's terminal state already holds an
operator **the lineage adopted for itself** — `ACQUIRED_cfc43adf`, truth table `[1, 0]`, negation,
non-monotone — taken by the widened search that generation 2 unlocked. Generation 2 does not merely
precede generation 3: it **creates its expressibility**, and removing it refuses the acquisition by
lemma rather than by failed search.

## One policy, and a measurement that forced it

Across **1 160 worlds** — a 160-world census plus a 1 000-world search over both declared seed ranges
— row-3 ambiguity and row-7 reachability **never co-occur**. Independence predicts about 25 such
worlds; zero were found. So the record is pooled across a two-stratum population and **one** policy is
acquired from the whole history, rather than being refitted per world.

## What the controls returned

| | |
|---|---|
| ablation of generation 3 | byte-exact return to `M2`; the ambiguous demand lost |
| mutation of the policy | the ambiguous demand lost |
| corruption | fails closed on identity mismatch |
| every probe | left the serialized state byte-identical; none is an adoption |
| conservation | every demand `M2` resolved is still resolved |
| arms | one adapter, one probe budget, identical world and demand bytes |

## Conceded, and declared inside the frozen protocol

The registry, the **probe primitive** and the budget remain **authored**. The lineage does not invent
experimentation; it decides where to spend one. The population is **selected for ambiguity by
design**. The acquired policy also fires on row 2, which is unreachable because `¬g1 ⟹ g2`, and that
is disclosed rather than trimmed. Elimination is complete only because two candidates remain; with
three live candidates one probe would not suffice, and this milestone does not test that case.

**G1–G10 do not advance.** Acceleration is measured and reported, not claimed.

## The defensible claim

**Bounded self-directed diagnosis and acquisition-machinery adaptation at recursive depth three.**
The lineage derives, from a record spanning its own history, which failure rows its vocabulary does
not determine, and spends a scarce experiment exactly there — and that derivation was inexpressible
in the language it held before generation 2.

See `../../DECISIONS.md` (D080), `PRE_REGISTRATION.md`, `ADVERSARIAL_REVIEW.md` and
`PRE_FREEZE_REHEARSAL.md`.
